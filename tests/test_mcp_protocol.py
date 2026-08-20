from __future__ import annotations

import sys

import httpx
import pytest
from conftest import LIBRARIAN_SCRIPTS, REPO_ROOT, load_script
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

server = load_script("skill_mcp_server", LIBRARIAN_SCRIPTS / "skill_mcp_server.py")


@pytest.mark.anyio
async def test_mcp_stdio_lists_and_calls_skill_request() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            str(LIBRARIAN_SCRIPTS / "skill_mcp_server.py"),
            "--root",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        assert [tool.name for tool in tools.tools] == ["skill_request"]
        response = await session.call_tool(
            "skill_request", {"intent": "maintain the local skill library catalog"}
        )

    assert not response.isError
    rendered = "\n".join(getattr(item, "text", "") for item in response.content)
    assert "decision: reuse-existing-skill" in rendered
    assert "skill_path: house-skills/core/" in rendered
    assert "skill_path: house-skills/young" not in rendered


@pytest.mark.parametrize(
    "json_response",
    [
        False,
        True,
    ],
)
@pytest.mark.anyio
async def test_mcp_streamable_http_lists_and_calls_skill_request(
    json_response: bool,
) -> None:
    argv = ["--transport", "streamable-http"]
    if json_response:
        argv.append("--json-response")
    args = server.parse_args(argv)
    server.ROOT = REPO_ROOT
    server.ALLOW_WRITES = False
    mcp_server = server.create_mcp_server(args)
    app = server.create_streamable_http_app(mcp_server, None)
    transport = httpx.ASGITransport(app=app)
    http_client = httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
    )

    async with (
        mcp_server.session_manager.run(),
        http_client,
        streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http_client) as (
            read_stream,
            write_stream,
            get_session_id,
        ),
        ClientSession(read_stream, write_stream) as session,
    ):
        initialize_result = await session.initialize()
        tools = await session.list_tools()
        response = await session.call_tool(
            "skill_request",
            {"intent": "maintain the local skill library catalog"},
        )
        session_id = get_session_id()

    assert str(initialize_result.protocolVersion)
    assert [tool.name for tool in tools.tools] == ["skill_request"]
    assert session_id is None
    assert mcp_server.session_manager.stateless is True
    assert mcp_server.session_manager._server_instances == {}
    assert not response.isError
    rendered = "\n".join(getattr(item, "text", "") for item in response.content)
    assert "decision: reuse-existing-skill" in rendered
    assert "skill_path: house-skills/core/" in rendered
    assert "skill_path: house-skills/young" not in rendered


@pytest.mark.anyio
async def test_streamable_http_security_and_request_limits() -> None:
    token = "a" * server.MIN_BEARER_TOKEN_CHARS
    args = server.parse_args(
        [
            "--transport",
            "streamable-http",
            "--json-response",
            "--allowed-origin",
            "https://trusted.example",
        ]
    )
    server.ROOT = REPO_ROOT
    server.ALLOW_WRITES = False
    mcp_server = server.create_mcp_server(args)
    app = server.create_streamable_http_app(mcp_server, token)
    transport = httpx.ASGITransport(app=app)
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "security-test", "version": "1.0"},
        },
    }
    common_headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }

    async with (
        mcp_server.session_manager.run(),
        httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client,
    ):
        unauthenticated = await client.post("/mcp", json=initialize, headers=common_headers)
        unauthenticated_get = await client.get("/mcp", headers={"accept": "text/event-stream"})
        unauthenticated_delete = await client.delete("/mcp")
        wrong_host = await client.post(
            "/mcp",
            json=initialize,
            headers={
                **common_headers,
                "authorization": f"Bearer {token}",
                "host": "attacker.example",
            },
        )
        wrong_origin = await client.post(
            "/mcp",
            json=initialize,
            headers={
                **common_headers,
                "authorization": f"Bearer {token}",
                "origin": "https://attacker.example",
            },
        )
        oversized = await client.post(
            "/mcp",
            content=b"x" * (server.MAX_HTTP_REQUEST_BYTES + 1),
            headers={
                **common_headers,
                "authorization": f"Bearer {token}",
            },
        )
        wrong_content_type = await client.post(
            "/mcp",
            content=b"not-json",
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "text/plain",
                "authorization": f"Bearer {token}",
            },
        )
        accepted = await client.post(
            "/mcp",
            json=initialize,
            headers={
                **common_headers,
                "authorization": f"Bearer {token}",
                "origin": "https://trusted.example",
            },
        )

    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"].startswith("Bearer")
    assert unauthenticated_get.status_code == 401
    assert unauthenticated_delete.status_code == 401
    assert wrong_host.status_code == 421
    assert wrong_origin.status_code == 403
    assert oversized.status_code == 413
    assert wrong_content_type.status_code == 400
    assert accepted.status_code == 200
    assert accepted.json()["result"]["serverInfo"]["name"] == "skill-library"


@pytest.mark.anyio
async def test_streamable_http_bearer_auth_with_official_client() -> None:
    token = "b" * server.MIN_BEARER_TOKEN_CHARS
    args = server.parse_args(
        [
            "--transport",
            "streamable-http",
            "--json-response",
        ]
    )
    server.ROOT = REPO_ROOT
    server.ALLOW_WRITES = False
    mcp_server = server.create_mcp_server(args)
    app = server.create_streamable_http_app(mcp_server, token)
    transport = httpx.ASGITransport(app=app)
    http_client = httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": f"Bearer {token}"},
    )

    async with (
        mcp_server.session_manager.run(),
        http_client,
        streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http_client) as (
            read_stream,
            write_stream,
            _get_session_id,
        ),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()

    assert [tool.name for tool in tools.tools] == ["skill_request"]
