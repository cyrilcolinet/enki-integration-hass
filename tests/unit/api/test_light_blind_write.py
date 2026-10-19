"""A bulb whose check-light-state is refused, read and write both (#337).

The reporter's Lexman colour bulb answers 400 to `check-light-state` and 500 to
`check-electrical-power`, while the Enki app drives it fine. With no reported
state to copy, every write went out as a one-key body and came back 400, so the
bulb was unusable from Home Assistant. Both attempts here are scoped to that
failure: a device whose read works sends exactly what it sent before.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.client import EnkiAPI
from enki.api.transport import EnkiHttpClient
from enki.exceptions import EnkiConnectionError
from enki.lib.conversion import LIGHT_STATE_FIELDS, merge_light_state_payload


def test_a_blind_write_names_every_field_the_app_names() -> None:
    payload = merge_light_state_payload({}, {"power": "ON"})

    assert set(payload) == set(LIGHT_STATE_FIELDS)
    assert payload["power"] == "ON"
    assert payload["brightness"] is None


def test_a_blind_off_is_padded_too() -> None:
    assert set(merge_light_state_payload({}, {"power": "OFF"})) == set(LIGHT_STATE_FIELDS)


def test_a_device_whose_read_works_sends_what_it_always_sent() -> None:
    """No padding where there is a reported object: it already names every field."""
    payload = merge_light_state_payload({"power": "OFF", "brightness": 10.0}, {"power": "ON"})

    assert payload == {"power": "ON", "brightness": 10.0}


def _api(refusal: EnkiConnectionError | None) -> tuple[EnkiAPI, MagicMock]:
    api = EnkiAPI("user@example.com", "secret")
    http = MagicMock(spec_set=EnkiHttpClient)
    http.get_light_state = AsyncMock(side_effect=EnkiConnectionError("400", status=400))
    http.change_light_state = AsyncMock(side_effect=refusal)
    http.switch_electrical_power = AsyncMock()
    api._get_http = AsyncMock(return_value=http)
    return api, http


@pytest.mark.asyncio
async def test_a_refused_on_off_is_retried_on_the_power_service() -> None:
    api, http = _api(EnkiConnectionError("refused", status=400))

    await api.async_change_light_state("home", "node", {"power": "ON"})

    http.switch_electrical_power.assert_awaited_once_with("home", "node", "ON")
    await api.async_close()


@pytest.mark.asyncio
async def test_a_refused_colour_change_is_not_retried() -> None:
    """The power service carries on/off and nothing else."""
    api, http = _api(EnkiConnectionError("refused", status=400))

    with pytest.raises(EnkiConnectionError):
        await api.async_change_light_state("home", "node", {"hue": 120.0})

    http.switch_electrical_power.assert_not_called()
    await api.async_close()


@pytest.mark.asyncio
async def test_the_lighting_error_is_what_the_user_sees_when_both_fail() -> None:
    api, http = _api(EnkiConnectionError("lighting refused", status=400))
    http.switch_electrical_power = AsyncMock(side_effect=EnkiConnectionError("power too"))

    with pytest.raises(EnkiConnectionError, match="lighting refused"):
        await api.async_change_light_state("home", "node", {"power": "ON"})
    await api.async_close()


@pytest.mark.asyncio
async def test_another_status_is_not_second_guessed() -> None:
    api, http = _api(EnkiConnectionError("gone", status=404))

    with pytest.raises(EnkiConnectionError):
        await api.async_change_light_state("home", "node", {"power": "ON"})

    http.switch_electrical_power.assert_not_called()
    await api.async_close()
