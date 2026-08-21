"""A failed check-light-state read must not block a light command (#143)."""

from __future__ import annotations

from typing import Any

import pytest
from enki.api.client import EnkiAPI
from enki.exceptions import EnkiConnectionError


class _FakeHttp:
    def __init__(self, *, raise_read: bool) -> None:
        self.raise_read = raise_read
        self.posted: dict[str, Any] | None = None

    async def get_light_state(self, home_id: str, node_id: str) -> dict[str, Any]:
        if self.raise_read:
            raise EnkiConnectionError(
                "GET check-light-state failed: HTTP 400",
                status=400,
            )
        return {"lastReportedValue": {"power": "OFF", "brightness": 0.2}}

    async def change_light_state(self, home_id: str, node_id: str, payload: dict[str, Any]) -> None:
        self.posted = payload


def _api_with(fake: _FakeHttp, monkeypatch: pytest.MonkeyPatch) -> EnkiAPI:
    api = EnkiAPI("user", "pass")

    async def _get_http() -> _FakeHttp:
        return fake

    monkeypatch.setattr(api, "_get_http", _get_http)
    return api


@pytest.mark.asyncio
async def test_command_sent_when_state_read_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHttp(raise_read=True)
    api = _api_with(fake, monkeypatch)
    await api.async_change_light_state("home", "node", {"power": "ON", "brightness": 0.5})
    assert fake.posted is not None  # command went out despite the 400 readback
    assert fake.posted["power"] == "ON"
    assert fake.posted["brightness"] == 0.5


@pytest.mark.asyncio
async def test_command_merges_full_state_when_read_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeHttp(raise_read=False)
    api = _api_with(fake, monkeypatch)
    await api.async_change_light_state("home", "node", {"power": "ON"})
    assert fake.posted["brightness"] == 0.2  # merged from lastReportedValue
