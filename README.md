# Enki pour Home Assistant

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration)

Contrôlez vos appareils **Enki** (Leroy Merlin) depuis Home Assistant.

Mêmes identifiants que l’**application mobile Enki**. La box Enki doit déjà fonctionner avec l’app — rien à configurer de plus côté HA.

## Feuille de route

**Supporté**

- Ventilateurs Inspire (Siroco+, Cadix, …) — ventilateur, lumière kit, vitesse, sens, modes
- Luminaires Enki (Eglo, Lexman, …) — ON/OFF, luminosité, blanc variable
- Prises / interrupteurs (Edisio, …) — ON/OFF
- Panneaux solaires Envertech-Lexman — production (W)

**Beta**

- Volets roulants (Evology, …) — ouverture, fermeture, position 0–100 %

**Bientôt**

- Radiateurs ACOVA ARLAN

**Pas prévu pour l’instant**

- Alarme Enki
- Inclusion au store HACS global (dépôt custom pour l’instant)

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

## Aide

| Sujet | Lien |
|-------|------|
| Appareils supportés (détail) | [docs/SUPPORTED_DEVICES.md](docs/SUPPORTED_DEVICES.md) |
| Signaler un bug | [Issues](https://github.com/cyrilcolinet/enki-integration-hass/issues) |
| Demander un appareil | [Feature request](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=feature_request.yml) |
| Contribuer | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Développement | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Support produit Enki | [support.enki-home.com](https://support.enki-home.com/) |

## Avertissement

Intégration communautaire, **non affiliée** à Leroy Merlin, Adeo ou Enki. API cloud non officielle, susceptible d’évoluer sans préavis.

Projet dérivé de [CyrilP/hass-enki-component](https://github.com/CyrilP/hass-enki-component).

## Licence

[MIT](LICENSE)
