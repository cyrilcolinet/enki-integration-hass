"""Unit tests for anonymized last-poll state export."""

from __future__ import annotations

from enki.domain.profile import sanitize_poll_state


def test_sanitize_poll_state_strips_identifiers() -> None:
    raw = {
        "node_id": "secret-node",
        "homeId": "secret-home",
        "fan_speed": 3,
        "airflow_mode": "MANUAL",
        "light_power": "ON",
        "brightness": 0.5,
    }
    assert sanitize_poll_state(raw) == {
        "airflow_mode": "MANUAL",
        "brightness": 0.5,
        "fan_speed": 3,
        "light_power": "ON",
    }


def test_sanitize_poll_state_redacts_endpoint_payload() -> None:
    raw = {
        "electrical_endpoints": [
            {"id": 1, "lastReportedValue": "ON", "nodeId": "secret"},
            {"id": 2, "lastReportedValue": {"power": "OFF", "brightness": 0.2}},
        ]
    }
    assert sanitize_poll_state(raw) == {
        "electrical_endpoints": [
            {"id": 1, "power": "ON"},
            {"id": 2, "power": "OFF", "brightness": 0.2},
        ]
    }
