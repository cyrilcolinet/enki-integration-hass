# Migrating from CyrilP/hass-enki-component

Both integrations use the same Home Assistant domain (`enki`) and the same folder (`custom_components/enki`). You are **replacing the code**, not adding a second integration.

## Quick path

1. **HACS** → **Integrations** → **Enki** → **Update**  
   (or copy `custom_components/enki/` from a [release](https://github.com/cyrilcolinet/enki-integration-hass/releases) manually)
2. **Restart** Home Assistant
3. Done — **do not** remove the integration in **Settings → Integrations**

Your email and password stay in the existing config entry. No need to add Enki again.

## HACS updates — automatic?

Custom repositories do **not** update silently by default. HACS shows an **Update** badge when a new release is available — you still click **Update**, then restart HA.

To enable automatic updates: **HACS** → **Integrations** → **Enki** → enable automatic updates (if available in your HACS version).

## What the integration migrates for you (v1.6.16+)

On first start after upgrading, `async_migrate_entry` runs once:

| Legacy (CyrilP) | After migration |
|---|---|
| `scan_interval` in config entry **data** | moved to **Options** |
| Config entry `unique_id` `"Enki - user@email.com"` | normalized to `user@email.com` |
| Solar sensor `…-power_production` | renamed to `…-power-production` |

Fan and light entities keep the same `unique_id` in most cases — automations should keep working.

## If something looks wrong

- **Polling too fast/slow** — **Enki** → **Configure** → adjust scan interval
- **Duplicate solar sensor** — remove the orphaned entity (old `power_production` id) in **Settings → Devices & services → Entities**
- **Stale entities** — **Enki** → **Reload** (or restart HA)

## Do not

- Uninstall the Enki integration before upgrading (you lose the config entry)
- Add a second Enki integration (same domain — will abort or conflict)
- Run both CyrilP and cyrilcolinet code at once (only one `custom_components/enki` folder)

## Canonical repo

Active development: **[cyrilcolinet/enki-integration-hass](https://github.com/cyrilcolinet/enki-integration-hass)**  
Original project: **[CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component)** (archived — README redirects here)
