# Feuille de route (vue détaillée)

Version courte pour HACS : [README § Feuille de route](../README.md#feuille-de-route).  
Détail par appareil : [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md).

| | |
|---|---|
| **Dernière release GitHub** | [v1.3.3](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) |
| **Version `manifest.json` (dépôt)** | 1.5.0 |

**Écart release / dépôt :** la [dernière release GitHub](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) (v1.3.3) n’inclut pas encore RGB (HS), chauffage, fuite ni volets. Le dépôt `main` est en **1.5.0** : RGB, clés gateway APK 2.25.1, chauffage / fuite / volets (beta), filtre fabricant Enki.

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
| 🔬 Beta | Volets roulants (Evology, Nodon, …) | `cover` « Volet (beta) » si volet actif dans l’app ; clé `ENKI_ACCESS_MOTORIZATION_API_KEY` (APK 2.25.1) ; peu testé en conditions réelles |
| 🔬 Beta | Détecteur fuite Lexman (v1.5.0+) | `binary_sensor` fuite + `sensor` batterie ; clés `ENKI_WATER_SENSOR_API_KEY` et `ENKI_BATTERY_HEALTH_API_KEY` (APK 2.25.1) |
| 🔬 Beta | Fil pilote Equation (v1.5.0+) | entité `select` (modes confort / éco / hors gel) ; clé `ENKI_HEATING_API_KEY` (APK 2.25.1) |
| 🔬 Beta | Radiateur Noirot (v1.5.0+) | `climate` + détection fenêtre / présence ; clé `ENKI_HEATING_API_KEY` (APK 2.25.1) |
| 🔜 Bientôt | Radiateurs ACOVA ARLAN | allowlist fabricant OK, pas de matériel de test |
| 🔬 Beta | Scénarios Enki (« Ouvrir Salon », …) | `button` (v1.6.0+) |
| ⏳ Pas prévu | Alarme Enki | pas d’API identifiée |
| ✅ Prérequis OK | Store HACS global | CI HACS + Hassfest vertes, releases publiées — [PR `hacs/default` à ouvrir](HACS.md#store-hacs-par-défaut) |

**Hors périmètre :** Zigbee tiers appairé sur la box (Sonoff, Tuya, Aqara, IKEA, …) → [Zigbee2MQTT](https://www.zigbee2mqtt.io/) ou ZHA. Seules les marques **Enki / Leroy Merlin** listées dans [`lib/enki_scope.py`](../custom_components/enki/lib/enki_scope.py) sont importées.
