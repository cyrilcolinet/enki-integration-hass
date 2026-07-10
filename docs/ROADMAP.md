# Roadmap (detailed view)

Short version: [README](../README.md) · detailed view below.

| | |
|---|---|
| **Latest GitHub release** | [releases](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) |
| **Repository `manifest.json`** | 1.6.18 |

## Status by device

| Status | Device | Features |
|--------|----------|-------------------|
| ✅ Supported | Inspire fans (Siroco+, Cadix, …) | fan, LED kit light, speed, direction, modes (per referentiel) |
| ✅ Supported | Enki lights (Eglo, Lexman, …) | ON/OFF, brightness, tunable white, RGB (HS) if `change_hue` + `change_saturation` |
| ✅ Supported | Outlets / switches (Edisio, Equation, …) | ON/OFF via `switch-electrical-power` |
| ✅ Supported | Envertech-Lexman solar panels | production (W) via BFF dashboard |
| ✅ Supported | Motion / contact / vibration sensors (Lexman, …) | `binary_sensor` |
| ✅ Supported | Enki thermometers (Sedea, …) | temperature, humidity, battery |
| ✅ Supported | Lexman sirens | `switch` ON/OFF |
| ✅ Supported | Equation ON/OFF relay | ON/OFF (like Edisio outlets) |
| ✅ Supported | Equation pilot wire | `select` (comfort / eco / frost / off); stable since **v1.6.8** (`thermostat-prod`) |
| ✅ Supported | Noirot radiator | `climate` + window / presence detection; stable since **v1.6.8** (`thermostat-prod` + `presence-detector-prod`) |
| 🔬 Beta | Roller shutters (Evology, Nodon, …) | `cover` “Shutter (beta)” if active in the app; `ENKI_ACCESS_MOTORIZATION_API_KEY` (APK 2.25.1); limited real-world testing |
| 🔬 Beta | Lexman / Nodon dry-contact gate receiver | `button` “Trigger” via `power_on_with_timer` (`api-enki-power-prod`); Mpulse mode — field test [#56](https://github.com/cyrilcolinet/enki-integration-hass/issues/56) |
| 🔬 Beta | Lexman water leak detector | leak `binary_sensor` + battery `sensor`; reads OK remotely — on-site wet test pending ([#36](https://github.com/cyrilcolinet/enki-integration-hass/issues/36)) |
| 🔜 Soon | ACOVA ARLAN radiators | manufacturer allowlist OK, no test hardware |
| 🔬 Beta | Enki scenarios (“Open living room”, …) | `button` (v1.6.0+) |
| ⏳ Not planned | Enki alarm | no API identified |
| ✅ Prerequisite OK | Default HACS store | CI HACS + Hassfest green, releases published — [PR to `hacs/default`](HACS.md#default-hacs-store) |

**In scope:** devices visible in the Enki app (Wi‑Fi or via the Enki hub). **Setup:** configure them in the Enki app before adding this integration in Home Assistant.

**Out of scope:** third-party Zigbee on the hub (Sonoff, Tuya, Aqara, IKEA, …) → [Zigbee2MQTT](https://www.zigbee2mqtt.io/) or ZHA. Only **Enki / Leroy Merlin** brands in [`lib/enki_scope.py`](../custom_components/enki/lib/enki_scope.py) are imported.
