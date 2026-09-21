"""Gateway API keys (shipped in ``gateway_keys_data.py``) and the mobile-config read."""

from __future__ import annotations

from typing import Any

from .. import gateway_keys_data
from ..const import ENKI_BASE_URL
from ..exceptions import EnkiConnectionError
from .gateway_registry import SERVICE_BY_TRANSPORT_ID

# Enki app: GET settings on api-enki-mobile-config-prod (not Firebase config/app/).
MOBILE_CONFIG_PATH = "/api-enki-mobile-config-prod/v1/settings"


def transport_key(transport_id: str) -> str | None:
    """Gateway key for a transport alias; None when unknown or not shipped."""
    svc = SERVICE_BY_TRANSPORT_ID.get(transport_id)
    if svc is None:
        return None
    return getattr(gateway_keys_data, svc.const_key, "") or None


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
