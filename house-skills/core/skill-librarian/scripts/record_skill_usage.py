#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from skill_library_utils import (
    DEFAULT_USAGE_TRACKING_MODE,
    iso_now,
    load_lifecycle_config,
    locate_library_root,
    read_json,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record usage for a house skill.")
    parser.add_argument("--root", type=Path, default=None, help="Skill library root")
    parser.add_argument("--skill-path", type=Path, required=True, help="Skill root path")
    parser.add_argument(
        "--refresh-young-ttl-days",
        type=int,
        default=None,
        help="Override the configured young TTL refresh window",
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "hub"],
        default="manual",
        help="How this usage event was recorded",
    )
    return parser.parse_args()


def resolve_skill_path(root: Path, skill_path: Path) -> Path:
    if skill_path.is_absolute():
        return skill_path.resolve()
    return (root / skill_path).resolve()


def main() -> int:
    args = parse_args()
    root = locate_library_root(args.root, Path(__file__))
    lifecycle_config = load_lifecycle_config(root)
    skill_root = resolve_skill_path(root, args.skill_path)
    metadata_path = skill_root / "metadata.json"

    if not metadata_path.exists():
        raise SystemExit(f"metadata.json not found: {metadata_path}")

    metadata = read_json(metadata_path)
    stage = metadata.get("stage", "young")
    usage_tracking = metadata.setdefault("usage_tracking", {})
    if not isinstance(usage_tracking, dict):
        usage_tracking = {}
        metadata["usage_tracking"] = usage_tracking
    if usage_tracking.get("mode") == DEFAULT_USAGE_TRACKING_MODE or "mode" not in usage_tracking:
        usage_tracking["mode"] = args.mode
    elif args.mode == "hub":
        usage_tracking["mode"] = "hub"
    metadata["last_used_at"] = iso_now()
    metadata["updated_at"] = metadata["last_used_at"]
    metadata["use_count"] = int(metadata.get("use_count", 0) or 0) + 1

    if stage == "young":
        refresh_ttl_days = (
            args.refresh_young_ttl_days
            if args.refresh_young_ttl_days is not None
            else int(lifecycle_config["young"]["refresh_ttl_days_on_use"])
        )
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            days=refresh_ttl_days
        )
        metadata["expires_at"] = expires_at.isoformat()

    write_json(metadata_path, metadata)
    print(
        f"Recorded usage for {skill_root.name}: stage={stage}, mode={usage_tracking['mode']}, use_count={metadata['use_count']}, expires_at={metadata.get('expires_at')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
