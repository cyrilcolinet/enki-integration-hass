<p align="center">
  <img src="custom_components/enki/brand/icon.png" alt="Enki" width="128" height="128">
</p>

<h1 align="center">Enki pour Home Assistant</h1>

<p align="center">
  <strong>Intégration cloud pour l’écosystème Enki / Leroy Merlin</strong><br>
  Ventilateurs, éclairage, prises, capteurs, volets, chauffage, scénarios et plus — depuis Home Assistant, avec les mêmes identifiants que l’app mobile.
</p>

<p align="center">
  <a href="https://github.com/cyrilcolinet/enki-integration-hass/actions/workflows/ci.yml"><img src="https://github.com/cyrilcolinet/enki-integration-hass/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/cyrilcolinet/enki-integration-hass" alt="License MIT"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2024.12+-41BDF5?logo=home-assistant&logoColor=white" alt="Home Assistant 2024.12+"></a>
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="docs/SUPPORTED_DEVICES.md">Appareils</a> ·
  <a href="docs/ROADMAP.md">Feuille de route</a> ·
  <a href="https://github.com/cyrilcolinet/enki-integration-hass/releases">Releases</a> ·
  <a href="https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml">Bug</a> ·
  <a href="CONTRIBUTING.md">Contribuer</a>
</p>

---

## Pourquoi cette intégration ?

L’app **Enki** pilote des centaines de références (Lexman, Equation, Inspire, Edisio, Evology, Noirot, Envertech, …) via le **cloud Leroy Merlin**. Cette intégration expose ces appareils dans Home Assistant en s’appuyant sur les **capabilities API** du référentiel Enki — comme l’app mobile — et non sur une liste figée de modèles.

| | |
|---|---|
| **Connexion** | E-mail + mot de passe Enki (OAuth Keycloak) |
| **Prérequis** | Box Enki opérationnelle, appareils visibles dans l’app |
| **Architecture** | Hub cloud (`iot_class: cloud_polling`), micro-services Enki |
| **Détection** | Capability-first : nouveaux appareils compatibles API sans mise à jour forcée |

> **Hors périmètre :** Zigbee tiers appairé sur la box (Sonoff, Tuya, Aqara, …) → [Zigbee2MQTT](https://www.zigbee2mqtt.io/) ou ZHA. Seules les marques Enki / Leroy Merlin listées dans [`lib/enki_scope.py`](custom_components/enki/lib/enki_scope.py) sont importées.

## Fonctionnalités

| Domaine | Exemples de matériel | Entités HA |
|---------|----------------------|------------|
| Ventilation | Inspire Siroco+, Cadix, Radix, … | `fan`, `light` (kit LED) |
| Éclairage | Eglo, Lexman, dimmables, RGB | `light` |
| Prises & relais | Edisio, Equation ON/OFF | `light` / ON-OFF power |
| Solaire | Envertech-Lexman | `sensor` (production W) |
| Capteurs | Lexman, Sedea, Sonoff (Enki) | `binary_sensor`, `sensor` |
| Sirène | Lexman | `switch` |
| **Beta** Volets | Evology, Nodon, … | `cover` |
| **Beta** Chauffage | Noirot, fil pilote Equation | `climate`, `select` |
| **Beta** Fuite d’eau | Lexman | `binary_sensor`, `sensor` |
| **Beta** Scénarios | Scénarios cloud Enki | `button` |

Détail par appareil : [docs/SUPPORTED_DEVICES.md](docs/SUPPORTED_DEVICES.md) · Historique : [docs/ROADMAP.md](docs/ROADMAP.md)

## Installation

### HACS (recommandé)

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

1. **HACS** → **Intégrations** → **⋮** → **Dépôts personnalisés**
2. URL : `https://github.com/cyrilcolinet/enki-integration-hass` — catégorie **Integration**
3. **Explorer et télécharger des dépôts** → **Enki** → **Télécharger**
4. **Redémarrer** Home Assistant

Store HACS global (objectif) : [docs/HACS.md](docs/HACS.md#store-hacs-par-défaut)

### Ajouter l’intégration

1. **Paramètres** → **Appareils et services** → **Ajouter une intégration**
2. Rechercher **Enki** — saisir e-mail et mot de passe Enki
3. Les entités apparaissent après le premier poll (~30 s)

### Installation manuelle

Téléchargez une [release](https://github.com/cyrilcolinet/enki-integration-hass/releases) ou clonez ce dépôt, copiez `custom_components/enki/` dans `config/custom_components/`, redémarrez HA.

## Configuration

**Paramètres** → **Appareils et services** → **Enki** → **Configurer**

| Option | Description |
|--------|-------------|
| Intervalle de rafraîchissement | Fréquence de poll cloud (défaut 30 s) |
| Télémétrie (opt-in) | Notification + lien GitHub pré-rempli pour appareils inconnus ; rien n’est envoyé sans clic |
| Reconfigurer | Changer e-mail / mot de passe |

## Dépannage

| Symptôme | Piste |
|----------|-------|
| Identifiants invalides | Vérifier e-mail/mot de passe sur l’app Enki ; reconfigurer l’intégration |
| HTTP 403 | Clé gateway obsolète après MAJ app Enki → [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Aucun appareil | Appareil actif dans l’app, même foyer |
| Bug | [Issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml) + logs `enki` |

## Ressources

| | |
|---|---|
| 📋 | [Appareils supportés](docs/SUPPORTED_DEVICES.md) |
| 🗺️ | [Feuille de route](docs/ROADMAP.md) |
| 🛠️ | [Développement & clés APK](docs/DEVELOPMENT.md) |
| 📡 | [Télémétrie opt-in](docs/TELEMETRY.md) |
| 🏠 | [Support Enki](https://support.enki-home.com/) |
| 🔗 | [Projet d’origine — CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component) |

## Crédits & licence

Intégration **communautaire**, non affiliée à Leroy Merlin, Adeo ou Enki. API cloud non officielle, susceptible d’évoluer.

- Fork de [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component)
- Capteurs / sirènes : inspiration [StephaneBranly/ha-enki](https://github.com/StephaneBranly/ha-enki)
- Icône : [MarioCadenas/hass-enki-component](https://github.com/MarioCadenas/hass-enki-component)

Licence [MIT](LICENSE)
