"""Stand-ins must have the shape of what they stand in for (#282).

Browsing a doorbell in Media called `get_videophone_events` on `EnkiAPI`, a
method only the transport has. It shipped because the test set that method on a
plain `MagicMock`, which invented it: the whole path was green against a client
that does not exist. A mock will answer to any name, so nothing fails until a
user opens the page.

Where a stand-in can be built with `spec_set`, that is the real guard — it also
catches production calling a method the test never configured. The coordinator
cannot: its Home Assistant base class is stubbed down to almost nothing here, so
`spec_set` would reject `last_update_success` and the rest. This test covers
both by reading the test suite itself and checking that every method a test
configures on a stand-in exists on the class it stands in for.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

from enki.api.client import EnkiAPI
from enki.api.transport import EnkiHttpClient
from enki.coordinator import EnkiCoordinator

TESTS_ROOT = Path(__file__).resolve().parents[2]

# The last link of the attribute chain, and what it stands in for:
# `entry.runtime_data.api.x = …` and `api.x = …` both land on EnkiAPI.
STAND_INS = {
    "api": EnkiAPI,
    "http": EnkiHttpClient,
    "transport": EnkiHttpClient,
    "coordinator": EnkiCoordinator,
    "runtime_data": EnkiCoordinator,
}

# Home Assistant's DataUpdateCoordinator provides these; conftest stubs it out,
# so they are invisible to introspection and would read as invented.
HA_COORDINATOR_MEMBERS = frozenset(
    {
        "always_update",
        "async_add_listener",
        "async_config_entry_first_refresh",
        "async_refresh",
        "async_request_refresh",
        "async_set_updated_data",
        "async_shutdown",
        "config_entry",
        "data",
        "hass",
        "last_exception",
        "last_update_success",
        "logger",
        "name",
        "update_interval",
    }
)

MOCK_FACTORIES = frozenset({"MagicMock", "AsyncMock", "Mock"})


def _real_members(cls: type) -> set[str]:
    """Class members, plus whatever `__init__` assigns to self."""
    members = set(dir(cls))
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(cls.__init__)))
    except (OSError, TypeError, SyntaxError):  # pragma: no cover - C or stubbed
        return members
    members.update(
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )
    return members


def _owner(target: ast.Attribute) -> str | None:
    """Who the assigned attribute belongs to, one link up the chain."""
    base = target.value
    if isinstance(base, ast.Attribute):
        return base.attr
    if isinstance(base, ast.Name):
        return base.id
    return None


def _specced_names(tree: ast.AST) -> set[str]:
    """Stand-ins already built with spec/spec_set — the mock library guards those."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        func = node.value.func
        factory = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if factory in MOCK_FACTORIES and any(
            keyword.arg in {"spec", "spec_set"} for keyword in node.value.keywords
        ):
            for target in node.targets:
                names.add(target.attr if isinstance(target, ast.Attribute) else target.id)
    return names


def _invented_methods(path: Path, members: dict[type, set[str]]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    specced = _specced_names(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            owner = _owner(target)
            cls = STAND_INS.get(owner or "")
            if cls is None or owner in specced or target.attr.startswith("_"):
                continue
            if cls is EnkiCoordinator and target.attr in HA_COORDINATOR_MEMBERS:
                continue
            known = members.setdefault(cls, _real_members(cls))
            if target.attr not in known:
                found.append(f"{path.name}: {owner}.{target.attr} is not on {cls.__name__}")
    return found


def test_no_test_configures_a_method_its_stand_in_does_not_have() -> None:
    members: dict[type, set[str]] = {}
    invented = [
        finding
        for path in sorted(TESTS_ROOT.rglob("test_*.py"))
        for finding in _invented_methods(path, members)
    ]

    assert invented == [], (
        "A test configures a method that does not exist on the real class, so it "
        "proves nothing about production code:\n  " + "\n  ".join(invented)
    )
