# Feuille de route (vue détaillée)

Version courte pour HACS : [README § Feuille de route](../README.md#feuille-de-route).  
Détail par appareil : [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md).

| | |
|---|---|
| **Dernière release GitHub** | [v1.3.3](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) |
| **Version `manifest.json` (dépôt)** | 1.5.0 |

**Écart release / dépôt :** v1.3.3 n’inclut pas encore RGB (HS) ni chauffage/fuite. RGB est sur `main` (1.4.1). Chauffage, fuite et filtre fabricant Enki sont sur la branche courante (1.5.0).

## Statut par appareil

| Statut | Appareil | Fonctionnalités |
|--------|----------|-------------------|
| ✅ Supporté | Ventilateurs Inspire (Siroco+, Cadix, …) | ventilateur, lumière kit, vitesse, sens, modes (selon référentiel) |
| ✅ Supporté | Luminaires Enki (Eglo, Lexman, …) | ON/OFF, luminosité, blanc variable, couleur RGB (HS) si `change_hue` + `change_saturation` |
| ✅ Supporté | Prises / interrupteurs (Edisio, Equation, …) | ON/OFF via `switch-electrical-power` |
| ✅ Supporté | Panneaux solaires Envertech-Lexman | production (W) via dashboard BFF |
| ✅ Supporté | Capteurs mouvement / ouverture / vibration (Lexman, …) | `binary_sensor` |
| ✅ Supporté | Thermomètres Enki (Sedea, …) | température, humidité, batterie |
| ✅ Supporté | Sirènes Lexman | `switch` ON/OFF |
| ✅ Supporté | Relais ON/OFF Equation | ON/OFF (comme prises Edisio) |
| 🔬 Beta | Volets roulants (Evology, Nodon, …) | code `cover` présent ; **aucune entité** tant que `ENKI_ACCESS_MOTORIZATION_API_KEY` est vide dans `const.py` |
| 🔬 Beta | Détecteur fuite Lexman (v1.5.0+) | entités créées ; **batterie OK**, état fuite inactif sans `ENKI_WATER_SENSOR_API_KEY` |
| 🔬 Beta | Fil pilote Equation (v1.5.0+) | entité `select` ; inactive sans `ENKI_HEATING_API_KEY` |
| 🔬 Beta | Radiateur Noirot (v1.5.0+) | `climate` + fenêtre / présence ; inactive sans `ENKI_HEATING_API_KEY` |
| 🔜 Bientôt | Radiateurs ACOVA ARLAN | allowlist fabricant OK, pas de matériel de test |
| 🔜 Bientôt | Scénarios Enki (« Ouvrir Salon », …) | — |
| ⏳ Pas prévu | Alarme Enki | pas d’API identifiée |
| ✅ Prérequis OK | Store HACS global | CI HACS + Hassfest vertes, releases publiées — [PR `hacs/default` à ouvrir](HACS.md#store-hacs-par-défaut) |

**Hors périmètre :** Zigbee tiers appairé sur la box (Sonoff, Tuya, Aqara, IKEA, …) → [Zigbee2MQTT](https://www.zigbee2mqtt.io/) ou ZHA. Seules les marques **Enki / Leroy Merlin** listées dans [`lib/enki_scope.py`](../custom_components/enki/lib/enki_scope.py) sont importées.
