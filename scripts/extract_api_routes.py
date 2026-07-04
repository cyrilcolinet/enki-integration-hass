#!/usr/bin/env python3
"""Extract Enki Retrofit API routes from an Android APK and diff vs the integration.

Usage:
    python scripts/extract_api_routes.py path/to/enki.apk
    python scripts/extract_api_routes.py path/to/enki.apk --json scripts/apk/api_routes.json
    python scripts/extract_api_routes.py path/to/enki.apk --check

Parses DI bindings (ag6.java / zf6.java) for api-enki-*-prod base URLs, then scans
Retrofit interfaces (@msa/@jbi/…) for relative paths. Compares wired integration
routes from capability_routing.py and gateway_registry.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JADX_DIR = REPO_ROOT / ".apk-work" / "jadx"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402
from extract_gateway_keys import BINDING_PATTERN, ensure_jadx, parse_bindings  # noqa: E402

HTTP_METHODS = {
    "msa": "GET",
    "jbi": "POST",
    "mf6": "DELETE",
    "ibi": "PUT",
    "kbi": "PATCH",
}
ROUTE_PATTERN = re.compile(
    r"@(" + "|".join(HTTP_METHODS) + r')\("([^"]+)"\)',
)


@dataclass(frozen=True, slots=True)
class ApiRoute:
    slug: str
    iface: str
    method: str
    path: str
    full_path: str


@dataclass(frozen=True, slots=True)
class IntegrationRoute:
    transport_id: str
    slug: str
    path_prefix: str
    capability: str
    full_path: str


def parse_iface_routes(sources_dir: Path, slug: str, iface: str, base_url: str) -> list[ApiRoute]:
    iface_path = sources_dir / f"{iface}.java"
    if not iface_path.is_file():
        return []
    prefix = base_url.rstrip("/").split("enki.api.devportal.adeo.cloud", 1)[-1]
    routes: list[ApiRoute] = []
    text = iface_path.read_text(encoding="utf-8", errors="replace")
    for match in ROUTE_PATTERN.finditer(text):
        verb = HTTP_METHODS[match.group(1)]
        rel = match.group(2)
        routes.append(
            ApiRoute(
                slug=slug,
                iface=iface,
                method=verb,
                path=rel,
                full_path=f"{prefix}/{rel}",
            )
        )
    return routes


def extract_routes(apk_path: Path, jadx_dir: Path) -> list[ApiRoute]:
    sources_dir = ensure_jadx(apk_path, jadx_dir)
    di_files = [sources_dir / "ag6.java", sources_dir / "zf6.java"]
    bindings = parse_bindings(di_files)

    slug_base: dict[str, str] = {}
    for source in di_files:
        if not source.is_file():
            continue
        for match in BINDING_PATTERN.finditer(source.read_text(encoding="utf-8", errors="replace")):
            slug_base.setdefault(match.group(1), match.group(0))

    routes: list[ApiRoute] = []
    for binding in bindings:
        base_match = re.search(
            rf"https://enki\.api\.devportal\.adeo\.cloud/{re.escape(binding.slug)}/v1/",
            "\n".join(
                line
                for source in di_files
                if source.is_file()
                for line in source.read_text(encoding="utf-8", errors="replace").splitlines()
                if binding.slug in line
            ),
        )
        if not base_match:
            continue
        base_url = base_match.group(0)
        routes.extend(parse_iface_routes(sources_dir, binding.slug, binding.iface, base_url))
    return routes


def integration_routes() -> list[IntegrationRoute]:
    bootstrap("enki.api.gateway_registry")
    bootstrap("enki.api.capability_routing")
    registry = load_module("enki.api.gateway_registry")
    routing = load_module("enki.api.capability_routing")

    by_transport = {
        svc.transport_id: svc
        for svc in registry.ENKI_MICRO_SERVICES
        if svc.wired and svc.transport_id
    }
    routes: list[IntegrationRoute] = []
    for read in routing.CAPABILITY_READS:
        svc = by_transport.get(read.transport_id)
        if svc is None:
            continue
        segment = read.capability.replace("_", "-")
        routes.append(
            IntegrationRoute(
                transport_id=read.transport_id,
                slug=svc.slug,
                path_prefix=svc.path_prefix,
                capability=read.capability,
                full_path=f"{svc.path_prefix}/{{nodeId}}/{segment}",
            )
        )
    return routes


def diff_routes(apk_routes: list[ApiRoute], wired: list[IntegrationRoute]) -> list[str]:
    """Report integration capabilities whose full path is missing from the APK catalog."""
    apk_paths = {route.full_path for route in apk_routes}
    errors: list[str] = []
    for route in wired:
        if route.full_path not in apk_paths:
            errors.append(
                f"missing in APK: {route.transport_id}/{route.capability} → {route.full_path}"
            )
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
    parser.add_argument("--json", type=Path, help="Write full APK route catalog as JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when wired integration routes are absent from the APK catalog",
    )
    args = parser.parse_args()

    if not args.apk.is_file():
        print(f"APK not found: {args.apk}", file=sys.stderr)
        return 1

    apk_routes = extract_routes(args.apk, args.jadx_dir)
    wired = integration_routes()

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "apk": str(args.apk),
            "route_count": len(apk_routes),
            "routes": [asdict(route) for route in apk_routes],
            "integration_routes": [asdict(route) for route in wired],
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(apk_routes)} APK routes to {args.json}")

    thermostat = [route for route in apk_routes if route.slug == "api-enki-thermostat-prod"]
    presence = [route for route in apk_routes if route.slug == "api-enki-presence-detector-prod"]
    print(f"APK routes: {len(apk_routes)} total")
    print(f"  api-enki-thermostat-prod: {len(thermostat)}")
    print(f"  api-enki-presence-detector-prod: {len(presence)}")
    print(f"Integration wired capability routes: {len(wired)}")

    errors = diff_routes(apk_routes, wired)
    if errors:
        print("\nIntegration routes not found in APK catalog:")
        for err in errors:
            print(f"  - {err}")
        if args.check:
            return 1
    elif args.check:
        print("\nAll wired integration routes present in APK catalog.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
