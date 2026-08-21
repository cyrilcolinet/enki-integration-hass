"""Unit tests for optional fan rotation API probing."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from enki.api import EnkiAPI
from enki.const import DIRECTION_FORWARD
from enki.exceptions import EnkiConnectionError


@pytest.mark.asyncio
async def test_get_fan_rotation_ignores_http_500_on_probe() -> None:
    api = EnkiAPI("user", "pass")
    http = AsyncMock()
    http.airflow_get = AsyncMock(side_effect=EnkiConnectionError("500"))

    rotation, supported = await api._read_fan_rotation(http, "home", "node")

    assert rotation is None
    assert supported is False


@pytest.mark.asyncio
async def test_get_fan_rotation_reads_fan_rotation_direction() -> None:
    api = EnkiAPI("user", "pass")
    http = AsyncMock()
    http.airflow_get = AsyncMock(return_value={"lastReportedValue": "CLOCKWISE"})

    rotation, supported = await api._read_fan_rotation(http, "home", "node")

    assert rotation == DIRECTION_FORWARD
    assert supported is True
    http.airflow_get.assert_awaited_once_with("home", "node", "check-fan-rotation-direction")


@pytest.mark.asyncio
async def test_set_fan_rotation_uses_change_fan_rotation_direction() -> None:
    api = EnkiAPI("user", "pass")
    http = AsyncMock()
    http.airflow_post = AsyncMock()
    api._get_http = AsyncMock(return_value=http)  # type: ignore[method-assign]

    await api.async_set_fan_rotation("home", "node", DIRECTION_FORWARD)

    http.airflow_post.assert_awaited_once_with(
        "home",
        "node",
        "change-fan-rotation-direction",
        "CLOCKWISE",
    )
