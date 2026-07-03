"""Load Enki integration modules from scripts without Home Assistant.

Home Assistant loads ``custom_components/enki/__init__.py``, which must not run
from standalone scripts. This module registers lightweight package stubs in
``sys.modules`` so only the requested submodules are loaded via importlib.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENKI_ROOT = REPO_ROOT / "custom_components" / "enki"

_PACKAGE_PATHS: dict[str, Path] = {
    "enki": ENKI_ROOT,
    "enki.api": ENKI_ROOT / "api",
    "enki.domain": ENKI_ROOT / "domain",
    "enki.lib": ENKI_ROOT / "lib",
    "enki.platforms": ENKI_ROOT / "platforms",
    "enki.platforms.light": ENKI_ROOT / "platforms" / "light",
    "enki.telemetry": ENKI_ROOT / "telemetry",
}


def _ensure_package(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]

    module = types.ModuleType(name)
    path = _PACKAGE_PATHS.get(name)
    if path is not None and path.is_dir():
        module.__path__ = [str(path)]  # type: ignore[attr-defined]

    sys.modules[name] = module
    if "." in name:
        parent_name, attr = name.rsplit(".", 1)
        parent = _ensure_package(parent_name)
        setattr(parent, attr, module)
    return module


def _module_path(qualified_name: str) -> Path:
    rel = qualified_name.removeprefix("enki.").replace(".", "/")
    return ENKI_ROOT / f"{rel}.py"


def load_module(qualified_name: str) -> types.ModuleType:
    """Import an ``enki.*`` module without executing ``enki/__init__.py``."""
    if qualified_name in sys.modules:
        return sys.modules[qualified_name]

    if qualified_name.count(".") >= 1:
        _ensure_package(qualified_name.rsplit(".", 1)[0])

    path = _module_path(qualified_name)
    if not path.is_file():
        raise ImportError(f"Enki module not found: {qualified_name} ({path})")

    spec = importlib.util.spec_from_file_location(qualified_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {qualified_name} from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


def bootstrap(*modules: str) -> None:
    """Pre-register ``enki`` package stubs, then load the listed modules."""
    _ensure_package("enki")
    for pkg in (
        "enki.api",
        "enki.domain",
        "enki.lib",
        "enki.platforms",
        "enki.platforms.light",
        "enki.telemetry",
    ):
        _ensure_package(pkg)

    for name in ("enki.const", "enki.exceptions"):
        load_module(name)

    for name in modules:
        if name not in ("enki.const", "enki.exceptions"):
            load_module(name)


def bootstrap_api_client() -> types.ModuleType:
    """Load ``EnkiAPI`` and discovery helpers for ``discover_devices.py``."""
    bootstrap(
        "enki.lib.bff",
        "enki.lib.conversion",
        "enki.lib.enki_scope",
        "enki.lib.shutter",
        "enki.lib.capability_path",
        "enki.domain.models",
        "enki.domain.state",
        "enki.domain.capabilities",
        "enki.domain.profile",
        "enki.api.gateway_registry",
        "enki.api.gateway_keys",
        "enki.api.auth",
        "enki.api.transport",
        "enki.api.client",
    )
    return sys.modules["enki.api.client"]


def bootstrap_fetch_keys() -> None:
    """Load modules required by ``fetch_gateway_keys.py``."""
    bootstrap(
        "enki.api.gateway_registry",
        "enki.api.gateway_keys",
        "enki.api.auth",
    )
