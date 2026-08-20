#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from search_skill_catalog import score_entry
from skill_consult import record_usage
from skill_library_utils import (
    MAX_JSON_BYTES,
    ensure_within_root,
    library_lock,
    locate_library_root,
    read_json,
    read_reviewed_core_manifest,
    skill_content_sha256,
)
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

ROOT: Path | None = None
ALLOW_WRITES = False
HOUSE_REUSE_SCORE = 45
ANY_REUSE_SCORE = 70
MAX_INTENT_CHARS = 2_000
MAX_CONTEXT_CHARS = 8_000
MAX_SKILL_BYTES = 512 * 1024
MAX_HTTP_REQUEST_BYTES = 64 * 1024
SCRIPT_TIMEOUT_SECONDS = 30
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8000
DEFAULT_HTTP_PATH = "/mcp"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_ALLOWED_HOSTS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
)
MIN_BEARER_TOKEN_CHARS = 32

Transport = Literal["stdio", "streamable-http"]


def port_number(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def http_path(value: str) -> str:
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "?" in value
        or "#" in value
        or any(character.isspace() for character in value)
    ):
        raise argparse.ArgumentTypeError(
            "HTTP path must be an absolute path without whitespace, query, or fragment"
        )
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the skill library over the Model Context Protocol."
    )
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help=(
            "Allow the MCP client to create temporary young skills. Disabled by default "
            "so the production server is read-only."
        ),
    )
    http = parser.add_argument_group("Streamable HTTP options")
    http.add_argument(
        "--host",
        default=DEFAULT_HTTP_HOST,
        help="Loopback listen address (default: 127.0.0.1)",
    )
    http.add_argument("--port", type=port_number, default=DEFAULT_HTTP_PORT, help="Listen port")
    http.add_argument(
        "--http-path",
        type=http_path,
        default=DEFAULT_HTTP_PATH,
        help="Streamable HTTP endpoint path (default: /mcp)",
    )
    http.add_argument(
        "--json-response",
        action="store_true",
        help="Return POST RPC responses as JSON instead of SSE",
    )
    http.add_argument(
        "--allowed-host",
        action="append",
        default=[],
        metavar="HOST[:PORT]",
        help="Accepted HTTP Host header; repeat for reverse-proxy names",
    )
    http.add_argument(
        "--allowed-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help="Accepted HTTP Origin header; repeat for trusted proxy/client origins",
    )
    http.add_argument(
        "--auth-token-env",
        metavar="ENV_VAR",
        help=(
            "Require a Bearer token read from this environment variable. "
            "The token is never accepted on the command line."
        ),
    )
    return parser.parse_args(argv)


def is_loopback_host(host: str) -> bool:
    return host.lower() in LOOPBACK_HOSTS


def validate_header_allowlist(values: list[str], *, label: str) -> list[str]:
    validated: list[str] = []
    for raw_value in values:
        value = raw_value.strip()
        if (
            not value
            or value != raw_value
            or len(value) > 512
            or any(character in value for character in "\r\n\t")
        ):
            raise ValueError(f"invalid {label}: {raw_value!r}")
        validated.append(value)
    return validated


def transport_security(args: argparse.Namespace) -> TransportSecuritySettings:
    if not is_loopback_host(args.host):
        raise ValueError(
            "Streamable HTTP must bind to 127.0.0.1, localhost, or ::1; "
            "use a TLS/authenticating reverse proxy or an SSH tunnel for remote access"
        )
    hosts = validate_header_allowlist(args.allowed_host, label="allowed host")
    origins = validate_header_allowlist(args.allowed_origin, label="allowed origin")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=list(dict.fromkeys([*DEFAULT_ALLOWED_HOSTS, *hosts])),
        allowed_origins=list(dict.fromkeys([*DEFAULT_ALLOWED_ORIGINS, *origins])),
    )


def read_bearer_token(environment_name: str | None) -> str | None:
    if environment_name is None:
        return None
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", environment_name):
        raise ValueError("auth token environment variable has an invalid name")
    token = os.environ.get(environment_name)
    if token is None:
        raise ValueError(f"auth token environment variable is not set: {environment_name}")
    if (
        len(token) < MIN_BEARER_TOKEN_CHARS
        or token != token.strip()
        or any(character.isspace() for character in token)
    ):
        raise ValueError(
            f"Bearer token in {environment_name} must contain at least "
            f"{MIN_BEARER_TOKEN_CHARS} non-whitespace characters"
        )
    return token


class BearerTokenMiddleware:
    """Protect an ASGI app with an operator-provided pre-shared Bearer token."""

    def __init__(self, app: ASGIApp, token: str):
        self.app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        authorization = Headers(scope=scope).get("authorization", "")
        scheme, separator, candidate = authorization.partition(" ")
        if (
            separator != " "
            or scheme.lower() != "bearer"
            or not secrets.compare_digest(candidate, self._token)
        ):
            response = JSONResponse(
                {"error": "invalid_token", "error_description": "Authentication required"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="skill-library"'},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class RequestBodyLimitMiddleware:
    """Reject oversized HTTP bodies before the MCP JSON parser reads them."""

    def __init__(self, app: ASGIApp, maximum_bytes: int):
        self.app = app
        self.maximum_bytes = maximum_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.maximum_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(
                    {"error": "invalid_request", "error_description": "Invalid Content-Length"},
                    status_code=400,
                )
                await response(scope, receive, send)
                return

        messages: list[dict[str, Any]] = []
        body_bytes = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            body_bytes += len(message.get("body", b""))
            if body_bytes > self.maximum_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        position = 0

        async def replay_receive() -> dict[str, Any]:
            nonlocal position
            if position < len(messages):
                message = messages[position]
                position += 1
                return message
            return await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {
                "error": "request_too_large",
                "error_description": (f"Request body exceeds {self.maximum_bytes} bytes"),
            },
            status_code=413,
        )
        await response(scope, receive, send)


def root_path() -> Path:
    if ROOT is None:
        raise RuntimeError("server root is not initialized")
    return ROOT


def run_script(script_name: str, *args: str) -> tuple[int, str, str]:
    root = root_path()
    script = root / "house-skills" / "core" / "skill-librarian" / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_SECONDS,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_catalog() -> None:
    root = root_path()
    catalog_path = root / "catalog" / "skill_catalog.json"
    if catalog_path.exists():
        return
    with library_lock(root):
        if catalog_path.exists():
            return
        code, _stdout, stderr = run_script("build_skill_catalog.py")
    if code != 0:
        raise RuntimeError(stderr or "failed to build skill catalog")


def read_catalog() -> dict[str, Any]:
    ensure_catalog()
    catalog_path = root_path() / "catalog" / "skill_catalog.json"
    if catalog_path.stat().st_size > MAX_JSON_BYTES:
        raise RuntimeError("catalog exceeds the configured size limit")
    catalog = read_json(catalog_path)
    if not isinstance(catalog.get("skills"), list):
        raise RuntimeError("catalog is missing its skills list; rebuild it")
    return catalog


def query_tokens(intent: str, context: str) -> tuple[str, list[str]]:
    phrase = " ".join(f"{intent} {context}".lower().split())
    return phrase, [token for token in phrase.split() if token]


def ranked_candidates(
    intent: str, context: str, limit: int = 6
) -> list[tuple[int, dict[str, Any]]]:
    catalog = read_catalog()
    phrase, tokens = query_tokens(intent, context)
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in catalog.get("skills", []):
        # Production trust boundary: only locally reviewed core skills may become
        # executable instructions. Mirrored upstream and young skills remain
        # searchable reference material in the maintainer CLI.
        if entry.get("execution_trust") != "reviewed-core":
            continue
        stage = entry.get("lifecycle_stage", "upstream")
        if stage == "archive" or entry.get("expired"):
            continue
        score = score_entry(entry, tokens, phrase)
        if score > 0:
            scored.append((score, entry))

    scored.sort(
        key=lambda item: (-item[0], item[1].get("repo_id", ""), item[1].get("skill_dir", ""))
    )
    return scored[:limit]


def skill_path(entry: dict[str, Any]) -> Path | None:
    rel_path = entry.get("skill_root_path")
    if not isinstance(rel_path, str) or not rel_path:
        return None
    try:
        path = ensure_within_root(
            root_path() / rel_path, root_path() / "house-skills" / "core", label="skill path"
        )
        canonical_relative = str(path.relative_to(root_path().resolve()))
        expected_hash = read_reviewed_core_manifest(root_path()).get(canonical_relative)
        catalog_hash = entry.get("reviewed_content_sha256")
        metadata = read_json(path / "metadata.json")
        if (
            not isinstance(catalog_hash, str)
            or catalog_hash != expected_hash
            or metadata.get("stage") != "core"
            or metadata.get("status") != "stable"
            or skill_content_sha256(path) != expected_hash
        ):
            return None
    except (OSError, ValueError):
        return None
    if not (path / "SKILL.md").exists():
        return None
    return path


def read_skill(entry: dict[str, Any]) -> tuple[Path, str] | None:
    path = skill_path(entry)
    if path is None:
        return None
    skill_file = path / "SKILL.md"
    if skill_file.is_symlink() or skill_file.stat().st_size > MAX_SKILL_BYTES:
        return None
    return path, skill_file.read_text(encoding="utf-8")


def should_reuse(score: int, entry: dict[str, Any]) -> bool:
    stage = entry.get("lifecycle_stage", "upstream")
    if stage in {"core", "young"} and score >= HOUSE_REUSE_SCORE:
        return True
    return score >= ANY_REUSE_SCORE


def record_house_usage(entry: dict[str, Any], path: Path) -> None:
    if not ALLOW_WRITES:
        return
    if entry.get("lifecycle_stage") not in {"core", "young"}:
        return
    try:
        with library_lock(root_path()):
            record_usage(root_path(), path, "hub")
    except Exception as exc:  # pragma: no cover - best effort telemetry
        print(f"[warn] usage recording failed: {exc}", file=sys.stderr)


def normalize_name(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")
    return normalized[:40].strip("-") or "task"


def safe_description(intent: str) -> str:
    cleaned = " ".join(intent.strip().split())
    cleaned = cleaned.replace(":", " -").replace("---", "-")
    if len(cleaned) > 180:
        cleaned = cleaned[:177].rstrip() + "..."
    return f"Use when an agent needs task-specific help for {cleaned}"


def source_note(candidates: list[tuple[int, dict[str, Any]]]) -> str:
    if not candidates:
        return "No matching skill was found in the local catalog."
    parts = []
    for score, entry in candidates[:3]:
        display = entry.get("skill_root_path") or entry.get("skill_dir") or entry.get("repo_id")
        parts.append(f"{display} score={score}")
    return "Closest catalog examples: " + "; ".join(parts)


def create_temporary_skill(
    intent: str, context: str, candidates: list[tuple[int, dict[str, Any]]]
) -> str:
    if not ALLOW_WRITES:
        raise PermissionError(
            "temporary skill creation is disabled; restart the server with --allow-writes"
        )
    digest = hashlib.sha1(f"{intent}\n{context}".encode()).hexdigest()[:8]
    name = f"temp-{normalize_name(intent)}-{digest}"
    with library_lock(root_path()):
        code, stdout, stderr = run_script(
            "create_house_skill_draft.py",
            "--name",
            name,
            "--description",
            safe_description(intent),
            "--source-note",
            source_note(candidates),
            "--context",
            context or "No extra context was provided by the caller.",
            "--source-summary",
            candidate_summary(candidates),
        )
    if code != 0 and "Destination already exists" not in stderr:
        raise RuntimeError(stderr or stdout or "failed to create temporary skill")

    path = root_path() / "house-skills" / "young" / name
    if not (path / "SKILL.md").exists():
        raise RuntimeError(f"temporary skill was not created: {path}")
    return f"{path.relative_to(root_path())}\n\n{(path / 'SKILL.md').read_text(encoding='utf-8')}"


def candidate_summary(candidates: list[tuple[int, dict[str, Any]]]) -> str:
    if not candidates:
        return "No close catalog examples."
    lines = []
    for score, entry in candidates[:3]:
        display = entry.get("skill_root_path") or entry.get("skill_dir") or entry.get("repo_id")
        stage = entry.get("lifecycle_stage", "upstream")
        description = entry.get("description") or entry.get("title") or "No description"
        lines.append(f"- [{score}] [{stage}] {display}: {description}")
    return "\n".join(lines)


def skill_request(intent: str, context: str = "", allow_temporary: bool = False) -> str:
    """Return one ready-to-use skill for the caller's task intent."""
    intent = intent.strip()
    context = context.strip()
    if not intent:
        return "error: intent is required"
    if len(intent) > MAX_INTENT_CHARS:
        return f"error: intent exceeds {MAX_INTENT_CHARS} characters"
    if len(context) > MAX_CONTEXT_CHARS:
        return f"error: context exceeds {MAX_CONTEXT_CHARS} characters"

    candidates = ranked_candidates(intent, context)
    for score, entry in candidates:
        loaded = read_skill(entry)
        if loaded is None:
            continue
        path, skill_md = loaded
        if not should_reuse(score, entry):
            continue
        record_house_usage(entry, path)
        rel_path = path.relative_to(root_path())
        return (
            "# Skill Agent Result\n\n"
            "decision: reuse-existing-skill\n"
            f"skill_path: {rel_path}\n"
            f"match_score: {score}\n\n"
            "Use this skill for the requested task:\n\n"
            "----- BEGIN SKILL -----\n"
            f"{skill_md.rstrip()}\n"
            "----- END SKILL -----\n"
        )

    if not allow_temporary or not ALLOW_WRITES:
        write_hint = (
            " Temporary creation is disabled by the server operator."
            if allow_temporary and not ALLOW_WRITES
            else ""
        )
        return (
            "# Skill Agent Result\n\n"
            "decision: no-fit\n\n"
            f"No reviewed core skill matched this intent.{write_hint}\n\n"
            "Closest examples:\n"
            f"{candidate_summary(candidates)}\n"
        )

    temporary = create_temporary_skill(intent, context, candidates)
    path_line, _, skill_md = temporary.partition("\n\n")
    return (
        "# Skill Agent Result\n\n"
        "decision: temporary-skill-created\n"
        f"skill_path: {path_line}\n\n"
        "Use this temporary skill for the requested task. It starts in `house-skills/young`; "
        "the live librarian can later keep, improve, or archive it.\n\n"
        "Closest examples considered internally:\n"
        f"{candidate_summary(candidates)}\n\n"
        "----- BEGIN SKILL -----\n"
        f"{skill_md.rstrip()}\n"
        "----- END SKILL -----\n"
    )


def create_mcp_server(args: argparse.Namespace) -> FastMCP:
    security = transport_security(args) if args.transport == "streamable-http" else None
    server = FastMCP(
        "skill-library",
        instructions=(
            "Accept one task intent from an agent and return only a locally reviewed core "
            "skill. Temporary skill creation is available only when the operator explicitly "
            "enables writes."
        ),
        host=args.host,
        port=args.port,
        streamable_http_path=args.http_path,
        json_response=args.json_response,
        # mcp==1.28.1 retains explicitly terminated stateful sessions in its
        # in-process registry. Keep this request/response-only service stateless
        # until the SDK guarantees bounded stateful-session cleanup.
        stateless_http=True,
        transport_security=security,
    )
    server.add_tool(
        skill_request,
        annotations=ToolAnnotations(
            title="Find a reviewed local skill",
            readOnlyHint=not args.allow_writes,
            destructiveHint=False,
            idempotentHint=not args.allow_writes,
            openWorldHint=False,
        ),
    )
    return server


def validate_runtime_args(args: argparse.Namespace) -> str | None:
    if args.transport == "stdio":
        if args.auth_token_env:
            raise ValueError("--auth-token-env is available only with Streamable HTTP")
        if (
            args.host != DEFAULT_HTTP_HOST
            or args.port != DEFAULT_HTTP_PORT
            or args.http_path != DEFAULT_HTTP_PATH
            or args.json_response
            or args.allowed_host
            or args.allowed_origin
        ):
            raise ValueError("Streamable HTTP options require --transport streamable-http")
        return None

    token = read_bearer_token(args.auth_token_env)
    if args.allow_writes and token is None:
        raise ValueError(
            "Streamable HTTP write mode requires --auth-token-env with a strong Bearer token"
        )
    return token


def create_streamable_http_app(server: FastMCP, token: str | None) -> ASGIApp:
    app: ASGIApp = RequestBodyLimitMiddleware(server.streamable_http_app(), MAX_HTTP_REQUEST_BYTES)
    if token is not None:
        app = BearerTokenMiddleware(app, token)
    return app


def run_streamable_http(server: FastMCP, args: argparse.Namespace, token: str | None) -> None:
    import uvicorn

    config = uvicorn.Config(
        create_streamable_http_app(server, token),
        host=args.host,
        port=args.port,
        log_level=server.settings.log_level.lower(),
        proxy_headers=False,
    )
    uvicorn.Server(config).run()


def main(argv: list[str] | None = None) -> int:
    global ALLOW_WRITES, ROOT
    args = parse_args(argv)
    try:
        token = validate_runtime_args(args)
        ROOT = locate_library_root(args.root, Path(__file__))
        ALLOW_WRITES = args.allow_writes
        server = create_mcp_server(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        run_streamable_http(server, args, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
