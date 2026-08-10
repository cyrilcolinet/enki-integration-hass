"""Anonymized request/response report for failed Enki API calls.

Attached to :class:`EnkiConnectionError` and surfaced in Home Assistant
diagnostics so a failing call (method, path, headers, payload, response body)
can be shared without a round-trip. Everything that could identify the user is
stripped: secret headers are blanked, id-like path/body segments and long or
sensitively-keyed values are redacted. Only the shape and the gateway's own
error message survive.
"""

from __future__ import annotations

import json
import re
from typing import Any

_REDACTED = "***"
_SECRET_HEADERS = frozenset({"authorization", "x-gateway-apikey", "homeid"})
_ID_SEGMENT = re.compile(r"[0-9a-f]{16,}", re.IGNORECASE)
_SENSITIVE_KEY = re.compile(
    r"(id|url|uri|token|serial|mac|host|uuid|key|secret|email|phone|address|ssid|name)",
    re.IGNORECASE,
)
_URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_MAX_STR = 60
_MAX_TEXT_BODY = 500


def mask_ids(text: str) -> str:
    """Replace long hex id segments (node/home/device ids) with a placeholder."""
    return _ID_SEGMENT.sub("{id}", text)


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Blank secret header values (auth token, gateway key, homeId), keep the rest."""
    return {
        key: (_REDACTED if key.lower() in _SECRET_HEADERS else value)
        for key, value in headers.items()
    }


def anonymize(node: Any, key_hint: str = "") -> Any:
    """Recursively strip identifying values, keeping structure, enums and numbers."""
    if isinstance(node, dict):
        return {key: anonymize(value, key) for key, value in node.items()}
    if isinstance(node, list):
        return [anonymize(item, key_hint) for item in node]
    if isinstance(node, str):
        if _URL.match(node):
            return "<url>"
        if _SENSITIVE_KEY.search(key_hint):
            return _REDACTED
        if len(node) > _MAX_STR:
            return f"<redacted:{len(node)}>"
        return node
    return node


def _anonymize_body(body: str) -> Any | None:
    text = body.strip()
    if not text:
        return None
    try:
        return anonymize(json.loads(text))
    except json.JSONDecodeError:
        return mask_ids(text[:_MAX_TEXT_BODY])


def build_request_report(
    method: str,
    path: str,
    headers: dict[str, str],
    payload: Any,
    status: int,
    body: str,
) -> dict[str, Any]:
    """Assemble an anonymized report of a failed request for diagnostics."""
    report: dict[str, Any] = {
        "method": method,
        "path": mask_ids(path),
        "status": status,
        "request_headers": redact_headers(headers),
    }
    if payload is not None:
        report["request_payload"] = anonymize(payload)
    response_body = _anonymize_body(body)
    if response_body is not None:
        report["response_body"] = response_body
    return report
