"""Button platform for Enki cloud scenarios."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnkiCoordinator
from .domain.models import EnkiDevice, EnkiScenario
from .entity import EnkiEntity
from .lib.shutter import shutter_preset_options


def _scenario_key(home_id: str, scenario_id: str) -> str:
    return f"{home_id}:{scenario_id}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnkiCoordinator = entry.runtime_data
    entities: dict[str, EnkiScenarioButton] = {}

    @callback
    def _sync_scenarios() -> None:
        current = {
            _scenario_key(scenario.home_id, scenario.scenario_id): scenario
            for scenario in coordinator.api.scenarios
        }

        for key, entity in list(entities.items()):
            if key not in current:
                coordinator.hass.async_create_task(entity.async_remove())
                del entities[key]

        new_entities: list[EnkiScenarioButton] = []
        for key, scenario in current.items():
            if key in entities:
                entities[key].refresh_from_scenario(scenario)
                continue
            entity = EnkiScenarioButton(coordinator, scenario.home_id, scenario.scenario_id)
            entity._attr_name = scenario.label
            entities[key] = entity
            new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    _sync_scenarios()
    remove_listener = coordinator.async_add_listener(_sync_scenarios)
    entry.async_on_unload(remove_listener)

    shutter_entities: list[EnkiShutterPresetButton] = []
    impulse_entities: list[EnkiImpulseRelayButton] = []
    for device in coordinator.data or []:
        for preset in shutter_preset_options(device.profile.possible_values):
            shutter_entities.append(EnkiShutterPresetButton(coordinator, device, preset))
        if device.profile.is_impulse_relay:
            impulse_entities.append(EnkiImpulseRelayButton(coordinator, device))
    if shutter_entities:
        async_add_entities(shutter_entities)
    if impulse_entities:
        async_add_entities(impulse_entities)


class EnkiScenarioButton(CoordinatorEntity[EnkiCoordinator], ButtonEntity):
    """Runs one Enki cloud scenario on press."""

    _attr_has_entity_name = True
    _attr_translation_key = "scenario"

    def __init__(self, coordinator: EnkiCoordinator, home_id: str, scenario_id: str) -> None:
        super().__init__(coordinator)
        self._home_id = home_id
        self._scenario_id = scenario_id
        self._attr_unique_id = f"{DOMAIN}-{home_id}-scenario-{scenario_id}"

    def refresh_from_scenario(self, scenario: EnkiScenario) -> None:
        """Apply latest cloud metadata (label) from coordinator refresh."""
        if self._attr_name != scenario.label:
            self._attr_name = scenario.label
            self.async_write_ha_state()

    def _current_scenario(self) -> EnkiScenario | None:
        for scenario in self.coordinator.api.scenarios:
            if scenario.home_id == self._home_id and scenario.scenario_id == self._scenario_id:
                return scenario
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        scenario = self._current_scenario()
        if scenario is not None:
            self._attr_name = scenario.label
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        scenario = self._current_scenario()
        return scenario is not None and scenario.enabled

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._home_id, "scenarios")},
            name="Enki scenarios",
            manufacturer="Leroy Merlin",
            model="Scenario",
        )

    async def async_press(self) -> None:
        await self.coordinator.api.async_activate_scenario(self._home_id, self._scenario_id)


class EnkiShutterPresetButton(EnkiEntity, ButtonEntity):
    """Runs one Enki roller shutter preset."""

    _attr_has_entity_name = True
    _attr_translation_key = "shutter_preset"

    def __init__(
        self,
        coordinator: EnkiCoordinator,
        device: EnkiDevice,
        preset: str,
    ) -> None:
        super().__init__(coordinator, device)
        self._preset = preset
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-preset-{preset.lower()}"
        self._attr_translation_placeholders = {"preset": preset.replace("_", " ").title()}

    async def async_press(self) -> None:
        await self.coordinator.api.async_execute_shutter_preset(
            self._device.home_id,
            self._device.node_id,
            self._preset,
        )


class EnkiImpulseRelayButton(EnkiEntity, ButtonEntity):
    """Triggers a timed dry-contact impulse (gate, garage, water heater relay)."""

    _attr_has_entity_name = True
    _attr_translation_key = "impulse_relay"

    def __init__(self, coordinator: EnkiCoordinator, device: EnkiDevice) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}-{device.node_id}-impulse"

    async def async_press(self) -> None:
        await self.coordinator.api.async_power_on_with_timer(
            self._device.home_id,
            self._device.node_id,
        )
