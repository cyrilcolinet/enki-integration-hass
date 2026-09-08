"""Runtime gateway API keys (const.py defaults + optional runtime overrides)."""

from __future__ import annotations

import re
from typing import Any

from .. import gateway_keys_data
from ..const import ENKI_BASE_URL, LOGGER
from ..exceptions import EnkiConnectionError
from .gateway_registry import (
    LEGACY_SLUG_ALIASES,
    SERVICE_BY_CONST_KEY,
    SERVICE_BY_SLUG,
    SLUG_TO_CONST_KEY,
)

KEY_PATTERN = re.compile(r"^[A-Za-z0-9]{32}$")
# Enki app: GET settings on api-enki-mobile-config-prod (not Firebase config/app/).
MOBILE_CONFIG_PATH = "/api-enki-mobile-config-prod/v1/settings"

_API_KEY_FIELD_NAMES = frozenset(
    {
        "apiKey",
        "apikey",
        "gatewayApiKey",
        "gateway_api_key",
        "xGatewayApiKey",
        "x-gateway-apikey",
    }
)
_SERVICE_FIELD_NAMES = frozenset(
    {
        "service",
        "serviceName",
        "microService",
        "microservice",
        "gateway",
        "name",
        "slug",
        "id",
        "key",
    }
)


def _normalize_slug(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"api-enki-[a-z0-9-]+-prod", value)
    if not match:
        return None
    slug = match.group(0)
    return LEGACY_SLUG_ALIASES.get(slug, slug)


def _const_key_for_slug(slug: str) -> str | None:
    return SLUG_TO_CONST_KEY.get(slug)


def _is_api_key(value: object) -> bool:
    return isinstance(value, str) and bool(KEY_PATTERN.fullmatch(value))


def parse_mobile_config_keys(payload: object) -> dict[str, str]:
    """Map const.py symbol names to gateway keys if present in a JSON payload.

    The live mobile-config ``/settings`` endpoint returns app version flags only
    (minIOSVersion, maintenance, …) — not gateway keys. This parser remains for
    tests and any future config shape that includes service/apiKey pairs.
    """
    found: dict[str, str] = {}

    def record(slug: str | None, api_key: object) -> None:
        if not slug or not _is_api_key(api_key):
            return
        const_key = _const_key_for_slug(slug)
        if const_key and const_key not in found:
            found[const_key] = api_key

    def walk(node: object) -> None:
        if isinstance(node, dict):
            slug: str | None = None
            api_key: object = None
            for key, value in node.items():
                if key in _SERVICE_FIELD_NAMES:
                    slug = _normalize_slug(str(value)) or slug
                if key in _API_KEY_FIELD_NAMES:
                    api_key = value
            if slug and api_key is not None:
                record(slug, api_key)

            for key, value in node.items():
                if isinstance(key, str):
                    normalized = _normalize_slug(key)
                    if normalized and _is_api_key(value):
                        record(normalized, value)
                    elif _is_api_key(value) and key.endswith("ApiKey"):
                        # e.g. heatingApiKey — infer slug from field prefix
                        prefix = key.removesuffix("ApiKey").replace("_", "-").lower()
                        for svc_slug in SERVICE_BY_SLUG:
                            if prefix in svc_slug:
                                record(svc_slug, value)
                                break
                walk(value)
            return

        if isinstance(node, list):
            for item in node:
                walk(item)
            return

        if isinstance(node, str):
            if _is_api_key(node):
                return
            _normalize_slug(node)

    walk(payload)
    return found


class GatewayKeyStore:
    """Merged view of hardcoded const keys and optional runtime overrides."""

    def __init__(self) -> None:
        self._defaults: dict[str, str] = {}
        self._runtime: dict[str, str] = {}
        self.reload_from_const()

    def reload_from_const(self) -> None:
        self._defaults = {
            svc.const_key: getattr(gateway_keys_data, svc.const_key, "")
            for svc in SERVICE_BY_CONST_KEY.values()
        }

    def apply_mobile_config(self, payload: object) -> dict[str, str]:
        """Apply gateway keys from a config payload; returns newly resolved symbols."""
        resolved = parse_mobile_config_keys(payload)
        for const_key, value in resolved.items():
            if not value:
                continue
            self._runtime[const_key] = value
            if not getattr(gateway_keys_data, const_key, ""):
                setattr(gateway_keys_data, const_key, value)
                LOGGER.debug("Gateway key loaded from mobile-config: %s", const_key)
        return resolved

    def get_const_value(self, const_key: str) -> str:
        return self._runtime.get(const_key) or getattr(gateway_keys_data, const_key, "")

    def get_transport_key(self, transport_id: str) -> str | None:
        from .gateway_registry import SERVICE_BY_TRANSPORT_ID

        svc = SERVICE_BY_TRANSPORT_ID.get(transport_id)
        if svc is None:
            return None
        value = self.get_const_value(svc.const_key)
        return value or None


async def fetch_mobile_config(http_client: Any) -> dict[str, Any]:
    """Fetch Enki app settings (same endpoint as the mobile app GET settings).

    The mobile app sends only ``X-Gateway-APIKey`` (no ``Authorization``) on this
    endpoint; we still attach Bearer when available for consistency.
    """
    if not gateway_keys_data.ENKI_MOBILE_CONFIG_API_KEY:
        raise EnkiConnectionError(
            "ENKI_MOBILE_CONFIG_API_KEY is required for mobile-config",
        )
    await http_client.ensure_token()
    url = f"{ENKI_BASE_URL}{MOBILE_CONFIG_PATH}"
    headers = http_client._auth.auth_headers(
        {"X-Gateway-APIKey": gateway_keys_data.ENKI_MOBILE_CONFIG_API_KEY},
    )
    async with http_client.session.get(url, headers=headers) as response:
        if response.status != 200:
            raise EnkiConnectionError(
                f"GET {MOBILE_CONFIG_PATH} failed: HTTP {response.status}",
            )
        payload = await response.json()
        return payload if isinstance(payload, dict) else {}
