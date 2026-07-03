#!/usr/bin/env python3
"""Extract Enki X-Gateway-APIKey values from an Android APK.

Usage:
    python scripts/extract_gateway_keys.py path/to/enki.apk
    python scripts/extract_gateway_keys.py path/to/enki.apk --apply
    python scripts/extract_gateway_keys.py path/to/enki.apk --apply --update-known

Decompiles the APK with jadx (cached under .apk-work/jadx), parses the DI
module (ag6.java / zf6.java) for api-enki-*-prod bindings, then reads gateway
keys from the repository wrapper classes (fo9, j0g, une, n1m, …).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KEYS_PY = REPO_ROOT / "custom_components" / "enki" / "gateway_keys_data.py"
CONST_PY = KEYS_PY  # backward-compatible alias for tests/scripts
DEFAULT_JADX_DIR = REPO_ROOT / ".apk-work" / "jadx"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402

bootstrap("enki.api.gateway_registry")
registry = load_module("enki.api.gateway_registry")
ENKI_MICRO_SERVICES = registry.ENKI_MICRO_SERVICES
LEGACY_SLUG_ALIASES = registry.LEGACY_SLUG_ALIASES
SERVICE_BY_CONST_KEY = registry.SERVICE_BY_CONST_KEY

SERVICE_MAP: dict[str, str] = {svc.slug: svc.const_key for svc in ENKI_MICRO_SERVICES}
for legacy_slug, canonical in LEGACY_SLUG_ALIASES.items():
    SERVICE_MAP[legacy_slug] = SERVICE_MAP[canonical]

KEY_LITERAL = re.compile(r'"([A-Za-z0-9]{32})"')
ASSIGN_PATTERN = re.compile(r'^(ENKI_[A-Z_]+)\s*=\s*"([^"]*)"')
BINDING_PATTERN = re.compile(
    r'ng4\.e\([^,]+,\s*"https://enki\.api\.devportal\.adeo\.cloud/(api-enki-[^/]+)/v1/",\s*(\w+)\.class\)'
)
G3C_BINDING_PATTERN = re.compile(
    r'\.a\("https://enki\.api\.devportal\.adeo\.cloud/(api-enki-[^/]+)/v1/"\)'
)
WRAPPER_PATTERN = re.compile(r"\bnew\s+(\w+)\s*[\(,]")
SKIP_WRAPPERS = frozenset(
    {
        "ArrayList",
        "bme",
        "g3c",
        "hd8",
        "jkq",
        "kof",
        "r53",
        "tk",
        "utn",
        "vef",
        "vfe",
    }
)
SHARED_INFRA_WRAPPERS = frozenset(
    {
        "icb",
        "t9f",
        "ewi",
        "zgg",
        "mxn",
        "xkf",
        "ydo",
        "e5n",
        "tn9",
        "xn9",
        "kna",
        "npm",
        "pn1",
        "lh7",
        "nb6",
        "gd8",
        "z8g",
        "y9g",
        "vfe",
        "i3m",
    }
)
JUNK_KEYS = frozenset({"0123456789ABCDEFGHIJKLMNOPQRSTUV"})
INCOMPLETE_MARKERS = (
    "Method dump skipped",
    "UnsupportedOperationException",
    "decompiled incorrectly",
)


@dataclass(frozen=True, slots=True)
class ServiceBinding:
    slug: str
    iface: str
    wrappers: tuple[str, ...]
    source: str


def read_const_keys() -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in CONST_PY.read_text(encoding="utf-8").splitlines():
        match = ASSIGN_PATTERN.match(line.strip())
        if match and match.group(1).endswith("_API_KEY"):
            keys[match.group(1)] = match.group(2)
    return keys


def jadx_available() -> bool:
    return subprocess.run(["which", "jadx"], capture_output=True).returncode == 0


def ensure_jadx(apk_path: Path, jadx_dir: Path) -> Path:
    """Full decompile into jadx_dir; returns sources/defpackage path."""
    sources = jadx_dir / "sources" / "defpackage"
    ag6 = sources / "ag6.java"
    if ag6.is_file():
        return sources

    if not jadx_available():
        raise RuntimeError("jadx is required — install with: brew install jadx")

    jadx_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["jadx", "-d", str(jadx_dir), str(apk_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and not ag6.is_file():
        raise RuntimeError(f"jadx failed:\n{result.stderr}")
    return sources


def decompile_class(apk_path: Path, class_name: str, jadx_dir: Path) -> str:
    """Decompile a single class if missing or incomplete in the cached jadx output."""
    path = jadx_dir / "sources" / "defpackage" / f"{class_name}.java"

    def read_if_usable() -> str:
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in INCOMPLETE_MARKERS) and not KEY_LITERAL.search(text):
            return ""
        return text

    cached = read_if_usable()
    if cached:
        return cached

    out = jadx_dir / "single-class"
    out.mkdir(parents=True, exist_ok=True)
    fqcn = f"defpackage.{class_name}"
    subprocess.run(
        [
            "jadx",
            "--single-class",
            fqcn,
            "--show-bad-code",
            "-d",
            str(out),
            str(apk_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    single = out / "sources" / "defpackage" / f"{class_name}.java"
    if single.is_file():
        text = single.read_text(encoding="utf-8", errors="replace")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text
    return ""


def parse_bindings(di_sources: Iterable[Path]) -> list[ServiceBinding]:
    bindings: list[ServiceBinding] = []
    seen: set[str] = set()

    for source in di_sources:
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            for match in BINDING_PATTERN.finditer(line):
                slug, iface = match.group(1), match.group(2)
                if slug in seen:
                    continue
                wrappers = tuple(
                    name
                    for name in WRAPPER_PATTERN.findall(line.split("ng4.e", 1)[0])
                    if name not in SKIP_WRAPPERS
                )
                bindings.append(ServiceBinding(slug, iface, wrappers, source.name))
                seen.add(slug)

            g3c = G3C_BINDING_PATTERN.search(line)
            if not g3c:
                continue
            slug = g3c.group(1)
            if slug in seen:
                continue
            iface_match = re.search(r"\.f\((\w+)\.class\)", line)
            if not iface_match and bindings:
                continue
            iface = iface_match.group(1) if iface_match else ""
            wrappers = tuple(
                name for name in WRAPPER_PATTERN.findall(line) if name not in SKIP_WRAPPERS
            )
            bindings.append(ServiceBinding(slug, iface, wrappers, source.name))
            seen.add(slug)

    return bindings


def load_wrapper_source(wrapper: str, apk_path: Path, jadx_dir: Path) -> str:
    path = jadx_dir / "sources" / "defpackage" / f"{wrapper}.java"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return decompile_class(apk_path, wrapper, jadx_dir)


def keys_near_iface(text: str, iface: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not iface:
        return counts

    patterns = (
        rf"\(\s*{re.escape(iface)}\s*\)",
        rf"\(\s*defpackage\.{re.escape(iface)}\s*\)",
        rf"\b{re.escape(iface)}\s+\w+\s*=",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - 1200)
            end = min(len(text), match.end() + 400)
            window = text[start:end]
            for key in KEY_LITERAL.findall(window):
                if key not in JUNK_KEYS:
                    counts[key] += 1
    return counts


def keys_in_file(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for key in KEY_LITERAL.findall(text):
        if key not in JUNK_KEYS:
            counts[key] += 1
    return counts


def keys_for_iface_in_sources(sources_dir: Path, iface: str) -> Counter[str]:
    """Fallback: scan defpackage for keys near Retrofit iface casts."""
    counts: Counter[str] = Counter()
    if not iface:
        return counts
    for path in sources_dir.glob("*.java"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            counts.update(keys_near_iface(text, iface))
        except OSError:
            continue
    return counts


def ordered_wrappers(wrappers: tuple[str, ...]) -> list[str]:
    dedicated = [w for w in wrappers if w not in SKIP_WRAPPERS and w not in SHARED_INFRA_WRAPPERS]
    shared = [w for w in wrappers if w in SHARED_INFRA_WRAPPERS]
    return dedicated + shared


def resolve_key(
    binding: ServiceBinding,
    apk_path: Path,
    jadx_dir: Path,
) -> tuple[str | None, str]:
    """Return (key, method) for a service binding."""
    candidates: Counter[str] = Counter()
    wrappers = ordered_wrappers(binding.wrappers)
    if not wrappers:
        wrappers = ["icb"]

    for wrapper in wrappers:
        source = load_wrapper_source(wrapper, apk_path, jadx_dir)
        if not source:
            continue
        iface_counts = keys_near_iface(source, binding.iface)
        if iface_counts:
            candidates.update(iface_counts)
            key, count = iface_counts.most_common(1)[0]
            if count >= 2 or wrapper not in SHARED_INFRA_WRAPPERS:
                return key, f"{wrapper}.java+{binding.iface}"
        if wrapper not in SHARED_INFRA_WRAPPERS:
            file_counts = keys_in_file(source)
            if file_counts:
                key, count = file_counts.most_common(1)[0]
                if count >= 2 or len(file_counts) == 1:
                    return key, f"{wrapper}.java"

    for wrapper in wrappers:
        if wrapper not in SHARED_INFRA_WRAPPERS:
            continue
        source = load_wrapper_source(wrapper, apk_path, jadx_dir)
        if not source:
            continue
        file_counts = keys_in_file(source)
        if len(file_counts) == 1:
            key = next(iter(file_counts))
            return key, f"{wrapper}.java"

    sources_dir = jadx_dir / "sources" / "defpackage"
    iface_global = keys_for_iface_in_sources(sources_dir, binding.iface)
    if iface_global:
        key, _ = iface_global.most_common(1)[0]
        return key, f"iface-scan:{binding.iface}"

    if wrappers:
        first = wrappers[0]
        source = load_wrapper_source(first, apk_path, jadx_dir)
        if source:
            file_counts = keys_in_file(source)
            if file_counts:
                key, count = file_counts.most_common(1)[0]
                if count >= 3:
                    return key, f"{first}.java"

    if candidates:
        key, _ = candidates.most_common(1)[0]
        return key, f"iface:{binding.iface}"

    return None, "unresolved"


def extract_all_keys(apk_path: Path, jadx_dir: Path) -> dict[str, tuple[str | None, str]]:
    sources_dir = ensure_jadx(apk_path, jadx_dir)
    di_files = [sources_dir / "ag6.java", sources_dir / "zf6.java"]
    bindings = parse_bindings(di_files)

    resolved: dict[str, tuple[str | None, str]] = {}
    for binding in bindings:
        const_key = SERVICE_MAP.get(binding.slug)
        if not const_key:
            continue
        key, method = resolve_key(binding, apk_path, jadx_dir)
        resolved[const_key] = (key, f"{binding.slug} via {method}")

    for svc in ENKI_MICRO_SERVICES:
        resolved.setdefault(svc.const_key, (None, "not in DI module"))
    return resolved


def apply_to_const(
    extracted: dict[str, tuple[str | None, str]],
    *,
    update_known: bool = False,
) -> list[str]:
    read_const_keys()
    changes: list[str] = []
    lines = CONST_PY.read_text(encoding="utf-8").splitlines(keepends=True)

    for idx, line in enumerate(lines):
        match = ASSIGN_PATTERN.match(line.strip())
        if not match:
            continue
        symbol, current = match.group(1), match.group(2)
        if not symbol.endswith("_API_KEY"):
            continue
        new_key, _ = extracted.get(symbol, (None, ""))
        if not new_key:
            continue
        if current == new_key:
            continue
        if current and not update_known:
            continue
        indent = line[: len(line) - len(line.lstrip())]
        lines[idx] = f'{indent}{symbol} = "{new_key}"\n'
        if current:
            changes.append(f"{symbol}: {current} -> {new_key}")
        else:
            changes.append(f"{symbol}: (empty) -> {new_key}")

    if changes:
        CONST_PY.write_text("".join(lines), encoding="utf-8")
    return changes


def check_against_repo(
    extracted: dict[str, tuple[str | None, str]],
    *,
    allow_unresolved: bool = False,
) -> list[str]:
    """Return human-readable errors when APK keys diverge from gateway_keys_data.py."""
    const_keys = read_const_keys()
    errors: list[str] = []

    for svc in ENKI_MICRO_SERVICES:
        apk_key, detail = extracted.get(svc.const_key, (None, "missing from APK extract"))
        repo_key = const_keys.get(svc.const_key, "")

        if svc.wired:
            if not repo_key:
                errors.append(f"{svc.const_key} is empty in repo (wired: {svc.slug})")
            elif not apk_key and not allow_unresolved:
                errors.append(f"{svc.const_key} unresolved in APK (wired: {svc.slug})")
            elif apk_key and repo_key != apk_key:
                errors.append(
                    f"{svc.const_key} mismatch — repo={repo_key} apk={apk_key} ({detail})"
                )
            continue

        if repo_key and apk_key and repo_key != apk_key:
            errors.append(f"{svc.const_key} mismatch — repo={repo_key} apk={apk_key} ({detail})")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path, help="Path to Enki APK file")
    parser.add_argument(
        "--jadx-dir",
        type=Path,
        default=DEFAULT_JADX_DIR,
        help=f"jadx output cache (default: {DEFAULT_JADX_DIR})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write resolved keys into custom_components/enki/gateway_keys_data.py (empty only)",
    )
    parser.add_argument(
        "--update-known",
        action="store_true",
        help="With --apply, also replace keys that differ from the APK",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when APK keys differ from gateway_keys_data.py (no writes)",
    )
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="With --check, do not fail when wired services are unresolved in the APK",
    )
    args = parser.parse_args()

    if not args.apk.is_file():
        print(f"APK not found: {args.apk}", file=sys.stderr)
        return 1

    try:
        extracted = extract_all_keys(args.apk, args.jadx_dir)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    const_keys = read_const_keys()
    resolved_count = sum(1 for key, _ in extracted.values() if key)

    print(f"APK: {args.apk}")
    print(f"Registry services: {len(ENKI_MICRO_SERVICES)}")
    print(f"Resolved from APK: {resolved_count}/{len(ENKI_MICRO_SERVICES)}\n")

    print("=== Wired services ===")
    for svc in ENKI_MICRO_SERVICES:
        if not svc.wired:
            continue
        key, detail = extracted[svc.const_key]
        current = const_keys.get(svc.const_key, "")
        if not key:
            status = "MISSING"
        elif current == key:
            status = "OK"
        elif not current:
            status = "NEW"
        else:
            status = "CHANGED"
        print(f"  [{status}] {svc.const_key}: {key or '(unresolved)'}")
        if key and current and current != key:
            print(f"         const.py has: {current}")

    print("\n=== Newly resolved (empty in const.py) ===")
    for symbol in sorted(extracted):
        current = const_keys.get(symbol, "")
        key, detail = extracted[symbol]
        if current or not key:
            continue
        print(f'  {symbol} = "{key}"  # {detail}')

    print("\n=== All services ===")
    for svc in ENKI_MICRO_SERVICES:
        key, detail = extracted[svc.const_key]
        wired = "wired" if svc.wired else "future"
        print(f"  [{wired}] {svc.const_key}: {key or '(unresolved)'}")

    if args.apply:
        changes = apply_to_const(extracted, update_known=args.update_known)
        if changes:
            print(f"\n=== Applied {len(changes)} change(s) to const.py ===")
            for change in changes:
                print(f"  {change}")
        else:
            print("\n=== No changes applied ===")

    if args.check:
        errors = check_against_repo(extracted, allow_unresolved=args.allow_unresolved)
        if errors:
            print("\n=== APK key check FAILED ===", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("\n=== APK key check OK ===")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
