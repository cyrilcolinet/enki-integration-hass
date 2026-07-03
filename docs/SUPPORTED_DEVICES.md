# Appareils et fonctionnalités supportés

Détail par type d’appareil et entités Home Assistant créées. L’intégration détecte les appareils via leurs **capabilities** API (comme l’app mobile), pas seulement par modèle.

| | |
|---|---|
| **Dernière release GitHub** | [v1.3.3](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) |
| **Version `manifest.json` (dépôt)** | 1.5.0 |

**Écart release / dépôt :** v1.3.3 n’inclut pas encore RGB (HS) ni chauffage/fuite. RGB est sur `main` (1.4.1). Chauffage, fuite et filtre fabricant Enki sont sur la branche courante (1.5.0).

Vue synthèse : [ROADMAP.md](ROADMAP.md) · version courte (HACS) : [README § Feuille de route](../README.md#feuille-de-route)

## Périmètre

Cette intégration couvre **uniquement l’écosystème Enki / Leroy Merlin** : Lexman, Equation, Inspire, Noirot, Edisio, Eglo, Sedea, Evology, Nodon, ACOVA, Envertech, etc. (liste exacte : [`lib/enki_scope.py`](../custom_components/enki/lib/enki_scope.py)).

**Important :** beaucoup de ces appareils utilisent **Zigbee en radio** via la box Enki — c’est normal et ils restent dans le périmètre. En revanche, tout **Zigbee tiers** appairé sur la box (Sonoff, Tuya, Aqara, IKEA, …) ou tout nœud **sans fabricant Enki connu** est **ignoré** à la découverte : intégrez-les via **Zigbee2MQTT** ou **ZHA**, pas ce dépôt.

## Ventilateurs Inspire (Siroco+, Aruba+, Cadix, Radix, …)

**Entités HA :** `fan` + `light` (kit LED)

| Fonction | Détail |
|----------|--------|
| Marche / arrêt | Vitesse 0 ou coupure moteur |
| Vitesse | Jusqu’à 6 niveaux (mapping pourcentage HA ; max selon référentiel) |
| Sens de rotation | Été / hiver si `change_fan_rotation_direction` (API `CLOCKWISE` / `COUNTERCLOCKWISE`) |
| Modes | Presets HA dérivés du référentiel : `manual`, `breeze`, et selon modèle `ventilation`, `boost`, `auto`, `sleep` (libellé UI « Nuit ») |

Le ventilateur et sa lumière sont **indépendants** : allumer l’un n’allume pas l’autre.

## Luminaires Enki (Eglo, Lexman, …)

**Entité HA :** `light`

| Fonction | Détail |
|----------|--------|
| Marche / arrêt | ON / OFF |
| Luminosité | Si `change_brightness` ou `change_light_state` |
| Blanc variable | Température de couleur (`colorTemperature`, ex. `T3500K`) si annoncée |
| Couleur RGB | Mode HS si `change_hue` + `change_saturation` (depuis manifest **1.4.0**, pas dans la release v1.3.3) |

## Prises, relais et interrupteurs (Edisio, Equation, …)

**Entité HA :** `light` ON/OFF (API `switch-electrical-power`, pas l’API lighting)

| Modèle / type | Statut |
|---------------|--------|
| Prises Edisio | ✅ ON/OFF |
| Relais ON/OFF Equation ([profil](./devices/63a053851a423d4a245a877c.json)) | ✅ ON/OFF |

Les nœuds multi-circuits peuvent créer **une entité par circuit** (endpoint BFF). Conso (`check_electrical_consumption`) et timers : pas encore exposés.

## Panneaux solaires (Envertech-Lexman)

**Entité HA :** `sensor` (production W)

| Fonction | Détail |
|----------|--------|
| Production instantanée | Valeur lue sur le dashboard BFF (`description.value`) |

## Capteurs Enki (Lexman, Sedea, …)

Micro-services alignés sur [StephaneBranly/ha-enki](https://github.com/StephaneBranly/ha-enki) (clés gateway déjà dans `const.py`).

### Mouvement / ouverture / vibration

**Entités HA :** `binary_sensor`

| Capabilité API | Entité |
|----------------|--------|
| `check_motion_detection` / `check_motion_detector_state` | Mouvement |
| `check_contact_sensor_state` | Contact (ouvert / fermé) |
| `check_vibration_detection` | Vibration |

### Température / humidité / batterie

**Entités HA :** `sensor`

| Capabilité API | Entité |
|----------------|--------|
| `check_current_temperature` | Température (°C) — sauf thermostats (température sur `climate`) |
| `check_current_humidity` | Humidité (%) |
| `check_battery_health` | Batterie (%, mapping Enki) |

Thermomètres **Sedea** (écran) : température, humidité, batterie.

### Sirène Lexman

**Entité HA :** `switch` (ON/OFF via `switch_siren_status`)

### Réglages capteur contact

**Entités HA :** `switch` (activation détection), `number` (sensibilité vibration 1–5)

### Fuite d’eau (Lexman) — beta (v1.5.0+)

**Entités HA :** `binary_sensor` (fuite), `sensor` (batterie)

**Profil :** [651eada55b3a798ef6b6bc5c.json](./devices/651eada55b3a798ef6b6bc5c.json)

| Capabilité | Service | Statut actuel |
|------------|---------|---------------|
| `check_battery_health` | `battery-health` | ✅ clé connue |
| `check_water_sensor_state` | `water-sensor` | 🔬 clé `ENKI_WATER_SENSOR_API_KEY` vide — entité créée, état fuite absent |

## Chauffage — beta (v1.5.0+)

| Modèle | Entités HA | Profil |
|--------|------------|--------|
| Fil pilote Equation | `select` (COMFORT, ECO, FROST_PROTECTION, OFF, …) | [63a054c81a423d4a245a877e.json](./devices/63a054c81a423d4a245a877e.json) |
| Radiateur Noirot | `climate`, `binary_sensor` (fenêtre, présence), `switch` (modes détection) | [67a4b12bae1eca4709a45680.json](./devices/67a4b12bae1eca4709a45680.json) |

**Clé API :** `ENKI_HEATING_API_KEY` dans `const.py` (vide aujourd’hui). Sans clé : entités visibles, lectures ignorées, commandes refusées avec message explicite. Capture : [API.md](API.md#heating-and-water-sensors-v150).

Catalogue JSON : [docs/devices/README.md](./devices/README.md)

## Volets roulants — beta (Evology, Nodon, …)

**Entité HA prévue :** `cover` « Volet (beta) »

| Fonction | Détail |
|----------|--------|
| Ouverture / fermeture | Commandes cover HA |
| Position | 0–100 % via `change-shutter-position` |

**État actuel :** `ENKI_ACCESS_MOTORIZATION_API_KEY` est **vide** dans `const.py`. Tant qu’elle l’est, les volets **ne sont pas importés** (`is_cover` = false) : ni entité cover, ni appareil dans HA. Le code existe (`cover.py`, `lib/shutter.py`) et s’activera dès qu’une release inclura la clé.

Retours contributeurs réseau : [BETA_VOLETS_KEY.md](BETA_VOLETS_KEY.md).

### Pour les testeurs (volets)

**Aujourd’hui**, sans clé API motorisation publiée, vous **ne verrez pas** de volet dans Home Assistant — c’est attendu.

Quand une release inclura `ENKI_ACCESS_MOTORIZATION_API_KEY` :

1. Mettre à jour l’intégration Enki (**v1.3.3+** minimum, ou la release qui annonce la clé) via HACS, puis redémarrer Home Assistant.
2. Vérifier l’entité **« Volet (beta) »** sous Enki.
3. Tester ouvrir / fermer / positionner vs l’app mobile Enki.
4. Remonter le résultat (modèle, version HA, version intégration, extrait journaux `enki` si échec).

## Fonctionnalités transverses

- **Auth OAuth** — refresh token Keycloak
- **Télémétrie opt-in** — notification pour profils inconnus, lien GitHub pré-rempli (rien n’est envoyé sans clic)
- **Diagnostics** — export JSON anonymisé depuis l’UI Enki

## En cours / non supporté

| Statut | Sujet |
|--------|--------|
| Beta (clé manquante) | Volets, chauffage, fuite d’eau (voir ci-dessus) |
| Bientôt | Radiateurs ACOVA ARLAN (même API heating si capabilities compatibles) |
| Bientôt | Scénarios Enki |
| Non planifié | Alarme Enki (pas d’API identifiée) |
| Hors périmètre | Box Enki, appairage, compte Leroy Merlin → [support Enki](https://support.enki-home.com/) |

Documentation API : [API.md](API.md)
