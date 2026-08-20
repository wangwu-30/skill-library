from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parents[1]
LIBRARIAN_SCRIPTS = REPO_ROOT / "house-skills/core/skill-librarian/scripts"
CONVERTER_SCRIPTS = REPO_ROOT / "house-skills/core/skill-converter/scripts"

for script_dir in (LIBRARIAN_SCRIPTS, CONVERTER_SCRIPTS):
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))


def load_script(name: str, path: Path) -> ModuleType:
    module_name = f"skill_library_test_{name}"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    root = tmp_path / "library"
    (root / "catalog").mkdir(parents=True)
    (root / "catalog/tracked_repos.json").write_text('{"repos": []}\n', encoding="utf-8")
    (root / "catalog/reviewed_core.lock.json").write_text(
        '{"schema_version": 1, "skills": []}\n', encoding="utf-8"
    )
    (root / "house-skills/config").mkdir(parents=True)
    (root / "house-skills/config/lifecycle.json").write_text(
        '{"young": {"default_ttl_days": 14}}\n', encoding="utf-8"
    )
    return root
