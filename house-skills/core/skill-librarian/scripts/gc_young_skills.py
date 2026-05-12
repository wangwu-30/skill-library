#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

from skill_library_utils import (
    iso_now,
    load_lifecycle_config,
    locate_library_root,
    now_utc,
    parse_datetime,
    read_json,
    usage_counts_available,
    usage_tracking_mode,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GC for young house skills.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=None,
        help="Override the configured TTL for young skills",
    )
    parser.add_argument(
        "--promote-min-uses",
        type=int,
        default=None,
        help="Override the configured promotion use-count threshold",
    )
    parser.add_argument(
        "--promote-recent-days",
        type=int,
        default=None,
        help="Override the configured recent-use promotion window",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply archive and promotion moves instead of reporting only",
    )
    return parser.parse_args()


def ensure_expiration(metadata: dict, ttl_days: int) -> dt.datetime:
    expires_at = parse_datetime(metadata.get("expires_at"))
    if expires_at is not None:
        return expires_at

    created_at = parse_datetime(metadata.get("created_at")) or now_utc()
    return created_at + dt.timedelta(days=ttl_days)


def archive_target(root: Path, skill_dir: Path) -> Path:
    destination = root / "house-skills" / "archive" / skill_dir.name
    if not destination.exists():
        return destination
    suffix = now_utc().strftime("%Y%m%d%H%M%S")
    return destination.with_name(f"{skill_dir.name}-{suffix}")


def move_skill(skill_dir: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(skill_dir), str(destination))
    return destination


def review_young_skills(
    root: Path,
    ttl_days: int | None = None,
    promote_min_uses: int | None = None,
    promote_recent_days: int | None = None,
    apply: bool = False,
) -> tuple[list[dict], dict]:
    lifecycle_config = load_lifecycle_config(root)
    ttl_days = (
        ttl_days
        if ttl_days is not None
        else int(lifecycle_config["young"]["default_ttl_days"])
    )
    promote_min_uses = (
        promote_min_uses
        if promote_min_uses is not None
        else int(lifecycle_config["promotion"]["min_use_count"])
    )
    promote_recent_days = (
        promote_recent_days
        if promote_recent_days is not None
        else int(lifecycle_config["promotion"]["recent_use_within_days"])
    )
    auto_promote = bool(lifecycle_config["promotion"]["auto_promote_eligible"])
    auto_archive = bool(lifecycle_config["young"]["auto_archive_expired"])
    young_root = root / "house-skills" / "young"
    core_root = root / "house-skills" / "core"
    archive_root = root / "house-skills" / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    core_root.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    summary = {
        "promoted": 0,
        "archived": 0,
        "kept": 0,
        "skipped": 0,
        "ttl_days": ttl_days,
        "promote_min_uses": promote_min_uses,
        "promote_recent_days": promote_recent_days,
        "auto_promote": auto_promote,
        "auto_archive": auto_archive,
    }
    now = now_utc()

    for skill_dir in sorted(young_root.iterdir() if young_root.exists() else []):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue

        result = {
            "skill_name": skill_dir.name,
            "action": "",
            "use_count": 0,
            "usage_mode": "none",
            "expires_at": "",
            "error": "",
        }

        metadata_path = skill_dir / "metadata.json"
        if not metadata_path.exists():
            result["action"] = "skip"
            result["error"] = "missing metadata.json"
            results.append(result)
            summary["skipped"] += 1
            continue

        metadata = read_json(metadata_path)
        metadata.setdefault("stage", "young")
        metadata.setdefault("status", "active")

        expires_at = ensure_expiration(metadata, ttl_days)
        last_used_at = parse_datetime(metadata.get("last_used_at"))
        use_count = int(metadata.get("use_count", 0) or 0)
        usage_mode = usage_tracking_mode(metadata)
        result["use_count"] = use_count
        result["usage_mode"] = usage_mode
        result["expires_at"] = expires_at.isoformat()

        promotable = (
            auto_promote
            and usage_counts_available(metadata)
            and use_count >= promote_min_uses
            and last_used_at is not None
            and last_used_at >= now - dt.timedelta(days=promote_recent_days)
        )
        expired = auto_archive and expires_at <= now

        if promotable:
            if apply:
                destination = core_root / skill_dir.name
                if destination.exists():
                    raise SystemExit(f"Promotion target already exists: {destination}")
                moved_dir = move_skill(skill_dir, destination)
                moved_metadata_path = moved_dir / "metadata.json"
                moved_metadata = read_json(moved_metadata_path)
                moved_metadata["stage"] = "core"
                moved_metadata["status"] = "stable"
                moved_metadata["expires_at"] = None
                moved_metadata["promoted_at"] = iso_now()
                moved_metadata["updated_at"] = moved_metadata["promoted_at"]
                write_json(moved_metadata_path, moved_metadata)
            result["action"] = "promote"
            results.append(result)
            summary["promoted"] += 1
            continue

        if expired:
            if apply:
                destination = archive_target(root, skill_dir)
                moved_dir = move_skill(skill_dir, destination)
                moved_metadata_path = moved_dir / "metadata.json"
                moved_metadata = read_json(moved_metadata_path)
                moved_metadata["stage"] = "archive"
                moved_metadata["status"] = "archived"
                moved_metadata["archive_reason"] = "young-expired"
                moved_metadata["archived_at"] = iso_now()
                moved_metadata["updated_at"] = moved_metadata["archived_at"]
                write_json(moved_metadata_path, moved_metadata)
            result["action"] = "archive"
            results.append(result)
            summary["archived"] += 1
            continue

        if apply and metadata.get("expires_at") is None:
            metadata["expires_at"] = expires_at.isoformat()
            metadata["updated_at"] = iso_now()
            write_json(metadata_path, metadata)

        result["action"] = "keep"
        results.append(result)
        summary["kept"] += 1

    return results, summary


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    results, summary = review_young_skills(
        root,
        ttl_days=args.ttl_days,
        promote_min_uses=args.promote_min_uses,
        promote_recent_days=args.promote_recent_days,
        apply=args.apply,
    )

    for result in results:
        if result["action"] == "skip":
            print(f"SKIP  {result['skill_name']}: {result['error']}")
        elif result["action"] == "promote":
            print(
                f"PROMOTE {result['skill_name']}: "
                f"usage_mode={result['usage_mode']}, use_count={result['use_count']}"
            )
        elif result["action"] == "archive":
            print(f"ARCHIVE {result['skill_name']}: expired_at={result['expires_at']}")
        elif result["action"] == "keep":
            print(
                f"KEEP   {result['skill_name']}: "
                f"usage_mode={result['usage_mode']}, "
                f"use_count={result['use_count']}, expires_at={result['expires_at']}"
            )

    print(
        "Summary: "
        f"promoted={summary['promoted']}, archived={summary['archived']}, "
        f"kept={summary['kept']}, "
        f"ttl_days={summary['ttl_days']}, "
        f"promote_min_uses={summary['promote_min_uses']}, "
        f"promote_recent_days={summary['promote_recent_days']}, "
        f"auto_promote={str(summary['auto_promote']).lower()}, "
        f"auto_archive={str(summary['auto_archive']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
