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
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Default-41BDF5.svg" alt="HACS Default"></a>
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

Use your Enki devices in Home Assistant, with the same email and password as the Enki app. Lights, blinds, heating, cameras, sensors and scenes appear as normal Home Assistant devices, ready for dashboards, automations and voice assistants.

> **Unofficial project.** Community-maintained, **not** affiliated with or endorsed by Leroy Merlin, ADEO or Enki. See the [disclaimer](docs/DISCLAIMER.md).

## What you get

- **Lights and outlets** — switch, dim, change colour and white temperature
- **Blinds and shutters** — open, close, stop, set a position
- **Heating** — radiators and pilot wire, with target temperature and modes
- **Ceiling fans** — speed, direction and the light kit
- **Cameras** — the latest motion snapshot, and a live view on the solar camera
- **Alarm** — arm and disarm, with the modes set up in the app
- **Sensors** — motion, opening, temperature, humidity, water leak, battery, solar production
- **Scenes** — run the scenes you created in the Enki app

The full list, device by device, is in [supported devices](docs/SUPPORTED_DEVICES.md).

Home Assistant also gets ready-made automations — notify on camera motion, alert on a water leak, close the blinds at sunset, and [a dozen more](docs/BLUEPRINTS.md).

## Before you start

- An **Enki account** — the one you use in the app
- Your devices **already installed in the Enki app**: this integration reads your Enki home, it does not replace pairing
- A few Enki services have been closed by Leroy Merlin's cloud for everyone, so instant consumption and a few other readings stay empty ([details](docs/API.md#authentication))

Devices paired on the hub that are not Enki brands — Sonoff, Tuya, Aqara and the like — are not imported. [Zigbee2MQTT](https://www.zigbee2mqtt.io/) or ZHA handle those.

## Installation

### With HACS (recommended)

Enki is in the default HACS store, so there is nothing to add by hand.

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

1. **HACS** → search **Enki** → **Download** (the button above opens it on your own instance)
2. **Restart** Home Assistant
3. **Settings** → **Devices & services** → **Add integration** → **Enki**, then enter your Enki email and password
4. Your devices show up after about 30 seconds

<details>
<summary>Enki does not appear in the HACS search?</summary>

A new entry can take a while to reach every HACS instance. In the meantime:

1. **HACS** → **⋮** → **Custom repositories**
2. URL `https://github.com/cyrilcolinet/enki-integration-hass`, category **Integration** → **Add**
3. Search **Enki** → **Download** → restart Home Assistant
</details>

### By hand

Download a [release](https://github.com/cyrilcolinet/enki-integration-hass/releases), copy the `custom_components/enki/` folder into your `config/custom_components/` folder, restart Home Assistant, then add the integration from **Settings → Devices & services**.

Coming from [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component)? Follow the [migration guide](docs/MIGRATION.md).

## Settings

**Settings** → **Devices & services** → **Enki** → **Configure**

- **Refresh interval** — how often Home Assistant asks Enki for news, every 30 seconds by default
- **Telemetry** — off unless you turn it on. It offers a pre-filled GitHub link when an unknown device shows up; nothing leaves your home until you click
- **Reconfigure** — change the email or password

## If something goes wrong

- **Wrong password** — Home Assistant asks you to sign in again, from **Settings → Repairs**
- **No device appears** — check the device is visible in the Enki app, in the same home
- **A device does not react** — open an [issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml); the bug form lists what to attach
- **A message in Settings → Repairs** — it usually explains what to do; if not, the issue link above works too

## Learn more

- 📋 [Supported devices](docs/SUPPORTED_DEVICES.md)
- ⚡ [Ready-made automations](docs/BLUEPRINTS.md)
- 🗺️ [Roadmap](docs/ROADMAP.md)
- 🛠️ [Development notes](docs/DEVELOPMENT.md) and [API notes](docs/API.md)
- 📡 [Telemetry, opt-in](docs/TELEMETRY.md)
- ⚠️ [Disclaimer](docs/DISCLAIMER.md)
- 🏠 [Enki support](https://support.enki-home.com/)

## Credits and licence

Community integration, based on [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component), not affiliated with Leroy Merlin, ADEO or Enki — see the [disclaimer](docs/DISCLAIMER.md).

[MIT](LICENSE) licence
