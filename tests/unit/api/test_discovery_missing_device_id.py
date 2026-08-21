"""Discovery must not crash on dashboard items missing deviceId (issue #126 comment)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from enki.api.client import EnkiAPI


@pytest.mark.asyncio
async def test_dashboard_item_without_device_id_is_skipped() -> None:
    api = EnkiAPI("user", "pass")
    # metadata has nodeId but no deviceId — used to raise KeyError and break the poll.
    result = await api._discover_dashboard_item(MagicMock(), "home", {"metadata": {"nodeId": "n1"}})
    assert result == (None, None)


@pytest.mark.asyncio
async def test_discover_home_isolates_a_failing_item() -> None:
    api = EnkiAPI("user", "pass")
    http = MagicMock()
    http.get_dashboard = AsyncMock(
        return_value={"sections": [{"items": [{"bad": True}, {"good": True}]}]}
    )

    async def fake_item(_http, _home, item):
        if item.get("good"):
            return "dev", "rec"
        raise RuntimeError("boom")

    with patch.object(EnkiAPI, "_discover_dashboard_item", AsyncMock(side_effect=fake_item)):
        devices, records = await api._discover_home(http, "home")

    # The failing item is skipped, the good one still discovered.
    assert devices == ["dev"]
    assert records == ["rec"]
