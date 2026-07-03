# Enki pour Home Assistant

[![CI](https://github.com/cyrilcolinet/enki-integration-hass/actions/workflows/ci.yml/badge.svg)](https://github.com/cyrilcolinet/enki-integration-hass/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/cyrilcolinet/enki-integration-hass?label=release)](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest)
[![License: MIT](https://img.shields.io/github/license/cyrilcolinet/enki-integration-hass)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12+-41BDF5?logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration)

Contrôlez vos appareils **Enki** (Leroy Merlin) depuis Home Assistant.

Mêmes identifiants que l’**application mobile Enki**. La box Enki doit déjà fonctionner avec l’app — rien à configurer de plus côté HA.

**Liens rapides :** [Installation HACS](#installation-avec-hacs) · [Appareils supportés](docs/SUPPORTED_DEVICES.md) · [Dernière release](https://github.com/cyrilcolinet/enki-integration-hass/releases/latest) · [Signaler un bug](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml) · [Contribuer](CONTRIBUTING.md)

## Feuille de route

| Statut | Appareil | Fonctionnalités |
|--------|----------|-------------------|
| ✅ Supporté | Ventilateurs Inspire (Siroco+, Cadix, …) | ventilateur, lumière kit, vitesse, sens, modes |
| ✅ Supporté | Luminaires Enki (Eglo, Lexman, …) | ON/OFF, luminosité, blanc variable, couleur RGB (HS) |
| ✅ Supporté | Prises / interrupteurs (Edisio, …) | ON/OFF |
| ✅ Supporté | Panneaux solaires Envertech-Lexman | production (W) |
| ✅ Supporté | Capteurs mouvement / ouverture (Lexman, …) | binary_sensor |
| ✅ Supporté | Thermomètres connectés (Sedea, …) | température, humidité, batterie |
| ✅ Supporté | Sirènes Lexman | ON/OFF |
| 🔬 Beta | Volets roulants (Evology, …) | ouverture, fermeture, position 0–100 % |
| 🔜 Bientôt | Radiateurs ACOVA ARLAN | — |
| 🔜 Bientôt | Scénarios Enki (« Ouvrir Salon », …) | — |
| ⏳ Pas prévu | Alarme Enki | — |
| ⏳ Pas prévu | Store HACS global | dépôt custom pour l’instant |

Détail complet par appareil : [docs/SUPPORTED_DEVICES.md](docs/SUPPORTED_DEVICES.md)

## Prérequis

- Home Assistant **2024.12** ou plus récent
- [HACS](https://hacs.xyz/) installé (méthode recommandée)
- Compte Enki / Leroy Merlin (e-mail + mot de passe de l’app)
- Box Enki configurée et appareils visibles dans l’app mobile

## Installation avec HACS

1. Ouvrez **HACS** → **Intégrations**
2. Menu **⋮** (en haut à droite) → **Dépôts personnalisés**
3. Collez l’URL : `https://github.com/cyrilcolinet/enki-integration-hass`
4. Catégorie : **Integration** → **Ajouter**
5. **HACS** → **Intégrations** → **Explorer et télécharger des dépôts**
6. Recherchez **Enki** → **Télécharger**
7. **Redémarrez** Home Assistant

Vous pouvez aussi cliquer sur le badge **Open in HACS** en haut de cette page.

## Ajouter l’intégration

1. **Paramètres** → **Appareils et services**
2. **Ajouter une intégration** (en bas à droite)
3. Cherchez **Enki**
4. Saisissez l’**e-mail** et le **mot de passe** de votre compte Enki
5. Validez — vos appareils apparaissent après quelques secondes

## Options

**Paramètres** → **Appareils et services** → **Enki** → **Configurer**

| Option | Description |
|--------|-------------|
| Intervalle de rafraîchissement | Fréquence de mise à jour depuis le cloud (défaut : 30 s) |
| Télémétrie (opt-in) | Notification pour appareils inconnus ; lien GitHub pré-rempli, rien n’est envoyé sans votre clic |

Pour **changer le mot de passe** : même menu → **Reconfigurer**.

## Problèmes fréquents

**« Identifiants invalides »** — Vérifiez e-mail et mot de passe sur l’app Enki.

**Aucun appareil détecté** — L’appareil doit être actif dans l’app (même foyer).

**Erreur dans les journaux** — Redémarrez HA après une mise à jour HACS ; vérifiez que la box Enki est en ligne.

Bug : [ouvrir une issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml) avec version HA, version intégration et logs `enki`.

## Installation manuelle (sans HACS)

1. Téléchargez ce dépôt (ou la dernière [release](https://github.com/cyrilcolinet/enki-integration-hass/releases))
2. Copiez `custom_components/enki/` dans `config/custom_components/`
3. Redémarrez Home Assistant
4. Ajoutez l’intégration comme ci-dessus

## Aide et ressources

| | Sujet | Lien |
|---|-------|------|
| 📋 | Appareils supportés (détail) | [docs/SUPPORTED_DEVICES.md](docs/SUPPORTED_DEVICES.md) |
| 🔬 | Volets beta — guide testeur | [SUPPORTED_DEVICES.md § testeurs](docs/SUPPORTED_DEVICES.md#pour-les-testeurs) |
| 📦 | Releases et changelog | [GitHub Releases](https://github.com/cyrilcolinet/enki-integration-hass/releases) |
| 🐛 | Signaler un bug | [Nouvelle issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=bug.yml) |
| 💡 | Demander un appareil | [Feature request](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=feature_request.yml) |
| 🤝 | Contribuer | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 🛠️ | Développement local | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| 📡 | Télémétrie opt-in | [docs/TELEMETRY.md](docs/TELEMETRY.md) |
| 🏠 | Support produit Enki | [support.enki-home.com](https://support.enki-home.com/) |
| 🔗 | Projet d’origine | [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component) |

## Avertissement

Intégration communautaire, **non affiliée** à Leroy Merlin, Adeo ou Enki. API cloud non officielle, susceptible d’évoluer sans préavis.

Projet dérivé de [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component). Capteurs et sirènes : portage partiel depuis [StephaneBranly/ha-enki](https://github.com/StephaneBranly/ha-enki). Oui, on s’appelle tous les deux **Cyril** avec [CyrilP](https://github.com/CyrilP) — ce n’est pas la même personne : **CyrilP** est l’auteur du repo d’origine ; **moi** ([cyrilcolinet](https://github.com/cyrilcolinet)), je maintiens ce fork à part. Même prénom, deux comptes GitHub, zéro télépathie.

## Licence

[MIT](LICENSE)
