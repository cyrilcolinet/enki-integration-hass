<p align="center">
  <img src="https://raw.githubusercontent.com/cyrilcolinet/enki-integration-hass/main/custom_components/enki/brand/icon.png" alt="Enki" width="128" height="128">
</p>

<h1 align="center">Enki for Home Assistant</h1>

<p align="center">
  <strong>Cloud integration for the Enki / Leroy Merlin smart home ecosystem</strong><br>
  Fans, lights, switches, sensors, covers, heating, cameras, scenarios, and more — from Home Assistant, using the same credentials as the mobile app.
</p>

<p align="center">
  <a href="https://github.com/cyrilcolinet/enki-integration-hass/actions/workflows/ci.yml"><img src="https://github.com/cyrilcolinet/enki-integration-hass/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/cyrilcolinet/enki-integration-hass" alt="License MIT"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2025.1+-41BDF5?logo=home-assistant&logoColor=white" alt="Home Assistant 2025.1+"></a>
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="docs/SUPPORTED_DEVICES.md">Devices</a> ·
  <a href="docs/ROADMAP.md">Roadmap</a> ·
  <a href="https://github.com/cyrilcolinet/enki-integration-hass/releases">Releases</a> ·
  <a href="https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml">Bug</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

The **Enki** app controls hundreds of products (Lexman, Equation, Inspire, Edisio, Evology, Noirot, Envertech, …) through the **Leroy Merlin cloud**. This integration exposes in Home Assistant **everything visible in the Enki app** — using Enki **API capabilities** from the referentiel, like the mobile app, rather than a fixed model list.

## Why this integration?

- **Connection** — Enki email + password (OAuth Keycloak)
- **Requirements** — Enki account; devices **already set up and visible in the Enki app** (Wi‑Fi or via the Enki hub — the hub is not mandatory for all devices)
- **Before Home Assistant** — Pair and configure devices in the **Enki app first**; this integration does not replace Enki pairing or device setup
- **Architecture** — Cloud polling (`iot_class: cloud_polling`), Enki micro-services
- **Detection** — Capability-first: new API-compatible devices without forced updates

> **Out of scope:** third-party Zigbee paired on the hub (Sonoff, Tuya, Aqara, …) → use [Zigbee2MQTT](https://www.zigbee2mqtt.io/) or ZHA. Only Enki / Leroy Merlin brands listed in [`lib/enki_scope.py`](custom_components/enki/lib/enki_scope.py) are imported.

## Features

### Supported

- **Ventilation** (Inspire Siroco+, Cadix, Radix, …) — `fan`, `light` (LED kit); the **Cadix** exposes its main light and ambient ring as separate lights with optimistic fan/light coupling (since **v1.11**)
- **Lighting** (Eglo, Lexman, dimmables, RGB) — `light`
- **Outlets & relays** (Edisio, Equation ON/OFF) — `light` / ON-OFF power; **Evology 2-channel module** — one `switch` per channel
- **Water heater relay** (Lexman/Nodon on-off relay re-typed as boiler) — `switch`
- **Solar** (Envertech-Lexman) — `sensor` (production W)
- **Sensors** (Lexman, Sedea, Evology multisensor, …) — `binary_sensor` (motion, presence, contact), `sensor` (temp, humidity, battery, brightness)
- **Siren** (Lexman) — `switch`
- **Heating** (Noirot radiator, Equation pilot wire) — `climate`, `select` (stable since **v1.6.8**); config knobs — temperature offset `number`, child-lock + preheating `switch` (**v1.18**)
- **Gate / garage / electric-strike dry contact** (Lexman 83424576, Nodon SIN-4-1-20, Evology) — `button` impulse (stable since **v1.6.17**) + `binary_sensor` contact state (since **v1.13**)

### Beta

- **Covers** (Evology, Nodon, …) — `cover`
- **Water leak** (Lexman) — `binary_sensor`, `sensor` (on-site leak test pending — [#36](https://github.com/cyrilcolinet/enki-integration-hass/issues/36))
- **Cameras** (Lexman/Meari) — `camera` (last-event snapshot), `sensor` (last motion, last event), `binary_sensor` (SD card); live video is not available (TUTK Kalay P2P native SDK) — [#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)
- **Scenarios** (Enki cloud) — `button`

### Blueprints

Ready-made automations under `blueprints/automation/enki/` — import via **Settings → Automations & scenes → Blueprints → Import**.

**Security & alerts**

- **Camera motion notification** — notify with the last-event snapshot on motion (`camera_motion_notification.yaml`)
- **Camera tamper alert** — notify when a camera reports its SD card removed (`camera_tamper_alert.yaml`)
- **Water leak alert** — urgent notification on a leak, optional siren + power cut-off (`water_leak_alert.yaml`)
- **Vibration / glass-break alert** — notify (+ optional siren) on a vibration sensor (`vibration_glass_break_alert.yaml`)
- **Siren on motion when armed** — sound the siren + notify on motion while an "armed" toggle is on (`siren_on_motion_when_armed.yaml`)
- **Contact open reminder** — notify when a door/window stays open too long (`contact_open_reminder.yaml`)
- **Low battery alert** — notify when an Enki battery sensor drops below a threshold (`low_battery_alert.yaml`)
- **High consumption alert** — notify when a power sensor stays above a threshold (`high_consumption_alert.yaml`)
- **Device offline alert** — notify when a device goes offline or unavailable (`device_offline_alert.yaml`)
- **Firmware update available** — notify when a device has an update (`firmware_update_notification.yaml`)

**Comfort, energy & scheduling**

- **Motion-activated light** — light on with motion, off after a delay, optionally only when dark (`motion_activated_light.yaml`)
- **Lights on at sunset** — lights on at sunset, off at a set time (`lights_on_at_sunset.yaml`)
- **Fan auto by temperature** — run a ceiling fan from a temperature sensor with hysteresis (`fan_auto_temperature.yaml`)
- **Fan auto by humidity** — run a fan from a humidity sensor with hysteresis (bathroom, laundry) (`humidity_ventilation.yaml`)
- **Covers sun schedule** — open shutters at sunrise, close them at sunset (`covers_sun_schedule.yaml`)
- **Heating pause on open window** — turn a radiator off while a window is open, back on when it closes (`heating_pause_on_open_window.yaml`)
- **Frost protection when away** — drop radiators to a frost temp on an away toggle, restore on return (`away_heating_frost.yaml`)
- **Pilot-wire day/night schedule** — switch a pilot-wire heater between two modes at two times (`pilot_wire_day_night.yaml`)
- **Turn everything off when away** — switch off chosen lights and outlets on an away toggle (`turn_off_when_away.yaml`)
- **Solar surplus switch** — run a load when solar production exceeds a threshold (`solar_surplus_switch.yaml`)
- **Run scenario on schedule** — press an Enki scenario at a time on chosen days (`run_scenario_on_schedule.yaml`)

Per-device detail: [docs/SUPPORTED_DEVICES.md](docs/SUPPORTED_DEVICES.md) · History: [docs/ROADMAP.md](docs/ROADMAP.md)

## Installation

### HACS (recommended)

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

1. **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. URL: `https://github.com/cyrilcolinet/enki-integration-hass` — category **Integration**
3. **Explore & download repositories** → **Enki** → **Download**
4. **Restart** Home Assistant

Default HACS store (goal): [docs/HACS.md](docs/HACS.md#default-hacs-store)

Upgrading from [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component)? See [docs/MIGRATION.md](docs/MIGRATION.md).

### Add the integration

1. In the **Enki app**, finish pairing and configuration for every device you want in Home Assistant
2. **Settings** → **Devices & services** → **Add integration**
3. Search for **Enki** — enter Enki email and password
4. Entities appear after the first poll (~30 s)

### Manual install

Download a [release](https://github.com/cyrilcolinet/enki-integration-hass/releases) or clone this repo, copy `custom_components/enki/` into `config/custom_components/`, restart HA.

## Configuration

**Settings** → **Devices & services** → **Enki** → **Configure**

- **Refresh interval** — Cloud poll frequency (default 30 s)
- **Telemetry (opt-in)** — Notification + pre-filled GitHub link for unknown devices; nothing is sent without a click
- **Reconfigure** — Change email / password

## Troubleshooting

- **Invalid credentials** — Verify email/password in the Enki app; reconfigure the integration
- **HTTP 403** — Outdated gateway key after Enki app update → [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- **No devices** — Device active in the app, same home
- **Bug** — [Issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml) + `enki` logs

## Resources

- 📋 [Supported devices](docs/SUPPORTED_DEVICES.md)
- 🗺️ [Roadmap](docs/ROADMAP.md)
- 🛠️ [Development & APK keys](docs/DEVELOPMENT.md)
- 📡 [Opt-in telemetry](docs/TELEMETRY.md)
- 🏠 [Enki support](https://support.enki-home.com/)
- 🔗 [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component)

## Credits & license

**Community** integration, not affiliated with Leroy Merlin, Adeo, or Enki. Unofficial cloud API, subject to change.

- Based on [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component)

[MIT](LICENSE) license
