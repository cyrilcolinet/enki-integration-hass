# Roadmap (detailed view)

Short version: [README](../README.md) · detailed view below.

| | |
|---|---|
| **Latest GitHub release** | [releases](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) |
| **Version** | see [`manifest.json`](../custom_components/enki/manifest.json) |

## Status by device

| Status | Device | Features |
|--------|----------|-------------------|
| ✅ Supported | Inspire fans (Siroco+, Cadix, Radix, …) | `fan`, LED kit `light`, speed, direction, modes (per referentiel); Cadix exposes main + ambient ring as separate lights with optimistic fan/light coupling (**v1.11**) |
| ✅ Supported | Enki lights (Eglo, Lexman, …) | ON/OFF, brightness, tunable white, RGB (HS) if `change_hue` + `change_saturation` |
| ✅ Supported | Outlets / switches (Edisio, Equation, …) | ON/OFF via `switch-electrical-power`, instant consumption (W) |
| ✅ Supported | Evology 2-channel in-wall module | one `switch` per channel (`check_channel1/2_electrical_power`) |
| ✅ Supported | Water-heater on/off relay (Lexman/Nodon 83424574) | `switch` re-typed as boiler ([#87](https://github.com/cyrilcolinet/enki-integration-hass/issues/87)) |
| ✅ Supported | Envertech-Lexman solar panels | production (W) via BFF dashboard |
| ✅ Supported | Motion / contact / vibration sensors (Lexman, …) | `binary_sensor` (+ activation `switch`, vibration sensitivity `number`) |
| ✅ Supported | Evology multisensor | motion/presence `binary_sensor`, brightness `sensor` (`check_brightness_level`) |
| ✅ Supported | Enki thermometers (Sedea, …) | temperature, humidity, battery `sensor` |
| ✅ Supported | Lexman sirens | `switch` ON/OFF |
| ✅ Supported | Equation pilot wire | `select` (comfort / eco / frost / off); stable since **v1.6.8** (`thermostat-prod`) |
| ✅ Supported | Noirot radiator | `climate` + window / presence `binary_sensor`; stable since **v1.6.8** (`thermostat-prod` + `presence-detector-prod`) |
| ✅ Supported | Thermostat config knobs | temperature offset `number`, child-lock + preheating `switch` (**v1.18**, decoded from the app — real-hardware validation welcome) |
| ✅ Supported | Lexman / Nodon dry-contact gate receiver | `button` “Trigger” via `power_on_with_timer` (`api-enki-power-prod`); Mpulse mode; stable since **v1.6.17** ([#56](https://github.com/cyrilcolinet/enki-integration-hass/issues/56)); electric-strike contact `binary_sensor` (**v1.13**) |
| 🔬 Beta | Cameras (Lexman/Meari) | last-event snapshot `camera`, last motion/event `sensor`, SD-card `binary_sensor`; **no live video** (TUTK Kalay P2P native SDK) ([#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)) |
| 🔬 Beta | Roller shutters (Evology, Nodon, Lexman RTS, …) | `cover` “Shutter (beta)”; position when advertised, otherwise open/close/stop (RTS); `select` wiring direction; `ENKI_ACCESS_MOTORIZATION_API_KEY` |
| 🔬 Beta | Lexman water leak detector | leak `binary_sensor` + battery `sensor`; reads OK remotely — on-site wet test pending ([#36](https://github.com/cyrilcolinet/enki-integration-hass/issues/36)) |
| 🔬 Beta | Enki scenarios (“Open living room”, …) | `button` (v1.6.0+) |
| 🔜 Soon | ACOVA ARLAN radiators | manufacturer allowlist OK, no test hardware |
| 🔜 Soon | Camera config controls (motion on/off, sensitivity) | REST-doable on Meari cameras; needs an indoor-camera owner to validate write endpoints ([#165](https://github.com/cyrilcolinet/enki-integration-hass/issues/165)) |
| ⏳ Not planned | Camera live video | TUTK Kalay Nebula P2P — native SDK, no Python path |
| ⏳ Not planned | Enki alarm | no API identified |
| ✅ Published | Default HACS store | listed in the default store — install from HACS directly (see [HACS.md](HACS.md)) |

## Tooling

- **Capability coverage report** — `scripts/capability_coverage.py` cross-references the APK route catalogue against what the integration handles, so a new capability the app gains surfaces as an auto-discovered gap ([#167](https://github.com/cyrilcolinet/enki-integration-hass/issues/167)). See [DEVELOPMENT.md](DEVELOPMENT.md).

**In scope:** devices visible in the Enki app (Wi‑Fi or via the Enki hub). **Setup:** configure them in the Enki app before adding this integration in Home Assistant.

**Out of scope:** third-party Zigbee on the hub (Sonoff, Tuya, Aqara, IKEA, …) → [Zigbee2MQTT](https://www.zigbee2mqtt.io/) or ZHA. Only **Enki / Leroy Merlin** brands in [`lib/enki_scope.py`](../custom_components/enki/lib/enki_scope.py) are imported.
