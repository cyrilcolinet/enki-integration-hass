"""Unit tests for the anonymized request/response failure report."""

from __future__ import annotations

from enki.lib.request_report import build_request_report


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "Enki/1.0 (iPhone)",
        "Accept": "application/json",
        "Authorization": "Bearer secret-token-value",
        "X-Gateway-APIKey": "abcdef0123456789abcdef0123456789",
        "homeId": "66dd9883202f215627708142",
        "X-Correlation-Id": "iOS_ABC123",
    }


def test_report_redacts_secret_headers_and_masks_path_ids() -> None:
    report = build_request_report(
        "GET",
        "/api-enki-lighting-prod/v1/lighting/66dd9883202f215627708142/check-light-state",
        _headers(),
        None,
        400,
        '{"message": "invalid request"}',
    )
    assert report["method"] == "GET"
    assert report["status"] == 400
    # id in the path is masked
    assert "66dd9883202f215627708142" not in report["path"]
    assert "{id}" in report["path"]
    # secret headers blanked, safe ones kept
    headers = report["request_headers"]
    assert headers["Authorization"] == "***"
    assert headers["X-Gateway-APIKey"] == "***"
    assert headers["homeId"] == "***"
    assert headers["Accept"] == "application/json"
    # the gateway's own reason survives
    assert report["response_body"] == {"message": "invalid request"}


def test_report_anonymizes_response_body_ids_but_keeps_enums() -> None:
    report = build_request_report(
        "POST",
        "/api-enki-lighting-prod/v1/lighting/66dd9883202f215627708142/change-light-state",
        _headers(),
        {"power": "ON", "brightness": 50, "colorTemperature": "T3000K"},
        500,
        '{"nodeId": "66dd9883202f215627708142", "state": "ERROR"}',
    )
    # request payload enums/numbers preserved
    assert report["request_payload"] == {
        "power": "ON",
        "brightness": 50,
        "colorTemperature": "T3000K",
    }
    # response body: id-keyed value redacted, enum kept
    assert report["response_body"]["nodeId"] == "***"
    assert report["response_body"]["state"] == "ERROR"


def test_report_keeps_non_json_body_truncated_and_id_masked() -> None:
    report = build_request_report(
        "GET",
        "/api-enki-power-prod/v1/power/66dd9883202f215627708142/check-electrical-power",
        _headers(),
        None,
        502,
        "Bad gateway for 66dd9883202f215627708142",
    )
    assert report["response_body"] == "Bad gateway for {id}"
