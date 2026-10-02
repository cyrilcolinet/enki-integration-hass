"""Tie a gateway key to the micro-service it signs, from the APK call sites (#275).

The extractor used to pick, among the key literals near a wrapper class, the one
that occurred most often. Wrapper files serve several services and hold several
keys — ``fdr.java`` holds five, two of them tied — so the winner was luck, and a
neighbouring service's key shipped silently. It happened five times (#45, #256,
#268, #270), and each time the resulting ``403 You cannot consume this service``
read exactly like Adeo closing an API product.

The app never leaves the link to chance: the DI module binds a base URL to a
retrofit interface, and the key reaches that interface through a short chain of
holders. Followed, it gives proof instead of a guess::

    ui6.java   new fdr(new bp1((nn5) i75.h(this, ".../api-enki-consumption-prod/v1/", nn5.class)))
    fdr.java   bp1Var.O("63NAg…", …)            # the literal, handed to a holder
    bp1.java   Object O(String str, …) { nn5 nn5Var = (nn5) this.c; nn5Var.d(str, …) }
    nn5.java   @qva("consumption/{nodeId}/check-instant-consumption")

Three shapes carry the key, and all three appear in the current app:

* the interface is cast at the call site — ``((rt9) pz7Var.c).d("key", …)``;
* the receiver is a holder whose method reaches the interface — the chain above;
* the receiver is a holder with no methods at all, just the interface as a field
  — ``this.a.a.i("key", …)`` for the siren.

Resolving all 27 wired services this way agrees with every key the integration
ships and contradicts none, which is what makes it usable as a gate.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol


class Sources(Protocol):
    """Class name to decompiled source: a plain dict in tests, lazy on a real dump."""

    def get(self, name: str, default: str = "", /) -> str: ...


class JadxSources:
    """Reads `defpackage/*.java` on demand — the dump is far too big to hold."""

    def __init__(self, defpackage: Path) -> None:
        self._dir = defpackage
        self._cache: dict[str, str] = {}

    def get(self, name: str, default: str = "", /) -> str:
        if name not in self._cache:
            path = self._dir / f"{name}.java"
            try:
                self._cache[name] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._cache[name] = default
        return self._cache[name] or default

    def names_holding_a_key(self) -> list[str]:
        """Classes with a 32-alphanumeric literal, the only ones worth parsing."""
        needle = re.compile(rb'"[A-Za-z0-9]{32}"')
        return sorted(
            path.stem for path in self._dir.glob("*.java") if needle.search(path.read_bytes())
        )


# A key literal: 32 alphanumerics, as the app writes them.
KEY_LITERAL = r'"([A-Za-z0-9]{32})"'
# `var.method("key"` — the receiver may be a local, a field, or a field chain.
CALL = re.compile(r"\b(\w+)\s*\.\s*(\w+)\(\s*" + KEY_LITERAL)
# `((iface) something).method("key"` — the interface named at the call site.
CAST_CALL = re.compile(r"\(\(\s*(\w+)\s*\)[^;()]*\)\s*\.\s*(\w+)\(\s*" + KEY_LITERAL)
LOCAL_DECL = re.compile(r"\b(\w+)\s+(\w+)\s*=")
FIELD_DECL = re.compile(
    r"^\s*(?:public|private|protected|final|static|volatile|transient|\s)+(\w+)\s+(\w+)\s*;",
    re.M,
)
# `nn5 nn5Var = (nn5) this.c;` and `uvo uvoVar = this.a;` — reading the held interface.
FIELD_READ = re.compile(r"\b(\w+)\s+\w+\s*=\s*(?:\(\s*\w+\s*\)\s*)?this\.\w+")
# A retrofit route: a path, so it has a separator or a placeholder.
ROUTE_ANNOTATION = re.compile(r'@[a-z0-9]+\("([^"]*[/{][^"]*)"\)')
# jadx indents class members by four spaces, so a member body ends at `\n    }`.
METHOD_SIGNATURE = re.compile(
    r"^    (?:public|protected|private|static|final|synchronized|\s)+[\w<>\[\],.?\s]+\s(\w+)\(",
    re.M,
)
SERVICE_BINDING = re.compile(
    r'"https://enki\.api\.devportal\.adeo\.cloud/(api-enki-[^/]+)/v1/",\s*(\w+)\.class'
)


def declared_routes(source: str) -> set[str]:
    """The routes a retrofit interface declares."""
    return set(ROUTE_ANNOTATION.findall(source))


def is_retrofit_interface(source: str) -> bool:
    return bool(ROUTE_ANNOTATION.search(source))


def method_bodies(source: str, name: str) -> str:
    """Every body of `name` in this class, concatenated."""
    bodies = []
    for match in METHOD_SIGNATURE.finditer(source):
        if match.group(1) != name:
            continue
        end = source.find("\n    }", match.start())
        bodies.append(source[match.start() : end if end != -1 else len(source)])
    return "\n".join(bodies)


def _receiver_types(source: str) -> dict[str, set[str]]:
    """Declared type of every local and field in this class, by name."""
    types: dict[str, set[str]] = defaultdict(set)
    for pattern in (LOCAL_DECL, FIELD_DECL):
        for declared_type, name in pattern.findall(source):
            types[name].add(declared_type)
    return types


def _interfaces_reached(sources: Sources, holder: str, method: str) -> set[str]:
    """The retrofit interfaces a holder hands this method's first argument to."""
    held = sources.get(holder, "")
    if not held:
        return set()
    if is_retrofit_interface(held):
        # The receiver is the interface itself — nothing to walk through.
        return {holder}
    body = method_bodies(held, method)
    if body:
        # A holder method often reads more than one field — the interface plus a
        # cache or a mapper. Only a class declaring routes can sign a request.
        return {
            field_type
            for field_type in FIELD_READ.findall(body)
            if is_retrofit_interface(sources.get(field_type, ""))
        }
    # A holder with no method of that name is a pure pass-through (siren's u8n):
    # the interface it holds as a field is the only thing the key can reach.
    return {
        field_type
        for field_type, _ in FIELD_DECL.findall(held)
        if is_retrofit_interface(sources.get(field_type, ""))
    }


def interfaces_by_key(sources: Sources, names: Iterable[str]) -> dict[str, Counter[str]]:
    """Every key literal in `names`, mapped to the interfaces it is handed to.

    `names` is the subset of classes that hold a key literal — the whole dump is
    half a gigabyte, and only a couple of dozen files carry one.
    """
    found: dict[str, Counter[str]] = defaultdict(Counter)
    for name in names:
        source = sources.get(name, "")
        if '"' not in source:
            continue
        for interface, _method, key in CAST_CALL.findall(source):
            found[key][interface] += 1
        receivers = _receiver_types(source)
        for receiver, method, key in CALL.findall(source):
            for holder in receivers.get(receiver, ()):
                for interface in _interfaces_reached(sources, holder, method):
                    found[key][interface] += 1
    return found


def interfaces_by_slug(di_sources: Iterable[str]) -> dict[str, set[str]]:
    """Micro-service slug to the retrofit interfaces the DI module binds to it."""
    bound: dict[str, set[str]] = defaultdict(set)
    for source in di_sources:
        for slug, interface in SERVICE_BINDING.findall(source):
            bound[slug].add(interface)
    return bound


def keys_for_slug(
    sources: Sources,
    by_key: dict[str, Counter[str]],
    interfaces: set[str],
) -> set[str]:
    """The keys handed to any interface bound to one micro-service."""
    wanted = {name for name in interfaces if is_retrofit_interface(sources.get(name, ""))}
    return {key for key, reached in by_key.items() if wanted & set(reached)}
