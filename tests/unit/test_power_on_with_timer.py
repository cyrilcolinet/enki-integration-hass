"""Unit tests for power_on_with_timer dry-contact API routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.client import EnkiAPI


@pytest.mark.asyncio
async def test_power_on_with_timer_posts_without_body() -> None:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock()
    http.power_on_with_timer = AsyncMock()
    api._get_http = AsyncMock(return_value=http)  # noqa: SLF001

    await api.async_power_on_with_timer("home-1", "node-gate")

    http.power_on_with_timer.assert_awaited_once_with("home-1", "node-gate")
    await api.async_close()
