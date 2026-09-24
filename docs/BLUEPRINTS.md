# Ready-made automations

Blueprints live in `blueprints/automation/enki/`. Import one from **Settings → Automations & scenes → Blueprints → Import blueprint**, then create an automation from it and pick your devices.

## Security and alerts

| Blueprint | What it does |
|-----------|--------------|
| `camera_motion_notification.yaml` | Notifies with the last snapshot when a camera sees motion |
| `camera_tamper_alert.yaml` | Notifies when a camera reports its SD card removed |
| `water_leak_alert.yaml` | Urgent notification on a leak, with an optional siren and power cut-off |
| `vibration_glass_break_alert.yaml` | Notifies, and optionally sounds a siren, on a vibration sensor |
| `siren_on_motion_when_armed.yaml` | Sounds the siren and notifies on motion while an "armed" toggle is on |
| `contact_open_reminder.yaml` | Notifies when a door or window stays open too long |
| `low_battery_alert.yaml` | Notifies when a battery drops below a threshold |
| `high_consumption_alert.yaml` | Notifies when a power sensor stays above a threshold |
| `device_offline_alert.yaml` | Notifies when a device goes offline |
| `firmware_update_notification.yaml` | Notifies when a device has an update available |

## Comfort, energy and schedules

| Blueprint | What it does |
|-----------|--------------|
| `motion_activated_light.yaml` | Light on with motion, off after a delay, optionally only when dark |
| `lights_on_at_sunset.yaml` | Lights on at sunset, off at a set time |
| `fan_auto_temperature.yaml` | Runs a ceiling fan from a temperature sensor |
| `humidity_ventilation.yaml` | Runs a fan from a humidity sensor, for a bathroom or laundry room |
| `covers_sun_schedule.yaml` | Opens the blinds at sunrise, closes them at sunset |
| `heating_pause_on_open_window.yaml` | Turns a radiator off while a window is open |
| `away_heating_frost.yaml` | Drops radiators to a frost-protection temperature while away |
| `pilot_wire_day_night.yaml` | Switches a pilot-wire heater between two modes at two times |
| `turn_off_when_away.yaml` | Switches off chosen lights and outlets when you leave |
| `solar_surplus_switch.yaml` | Runs a load when solar production goes above a threshold |
| `run_scenario_on_schedule.yaml` | Runs an Enki scene at a chosen time, on chosen days |

## Device triggers

Enki sensors also offer native triggers in the automation editor — "motion detected", "leak detected", "window opened", "vibration detected" — under **Settings → Automations → Create → Device**, with nothing to write by hand.
