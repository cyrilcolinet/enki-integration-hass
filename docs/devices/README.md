# Profils appareils (référentiel)

Fiches JSON anonymisées (capabilities + `possibleValues`) pour documenter des modèles Enki **sans compte ni nodeId**. Source : API referentiel ou contributions communautaires.

| Appareil | Fabricant | deviceId | Statut HA (fork) | Fiche |
|----------|-----------|----------|------------------|-------|
| Relais ON/OFF | Equation | `63a053851a423d4a245a877c` | ✅ ON/OFF (conso / timers : non) | [JSON](./63a053851a423d4a245a877c.json) |
| Détecteur de fuite | Lexman | `651eada55b3a798ef6b6bc5c` | 🔬 beta v1.5.0+ — batterie OK, fuite sans clé `ENKI_WATER_SENSOR_API_KEY` | [JSON](./651eada55b3a798ef6b6bc5c.json) |
| Contrôleur fil pilote | Equation | `63a054c81a423d4a245a877e` | 🔬 beta v1.5.0+ — sans clé `ENKI_HEATING_API_KEY` | [JSON](./63a054c81a423d4a245a877e.json) |
| Radiateur connecté | Noirot | `67a4b12bae1eca4709a45680` | 🔬 beta v1.5.0+ — sans clé `ENKI_HEATING_API_KEY` | [JSON](./67a4b12bae1eca4709a45680.json) |

Profils importés depuis [StephaneBranly/ha-enki#15](https://github.com/StephaneBranly/ha-enki/pull/15) (contribution [@zetiti10](https://github.com/zetiti10)). Périmètre **Enki / Leroy Merlin uniquement** — pas de Zigbee tiers (→ Zigbee2MQTT / ZHA).

Pour proposer un nouveau profil : télémétrie opt-in dans HA, [issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=feature_request.yml), ou PR avec un JSON dans ce dossier.
