# Publication HACS

Checklist alignée sur la [documentation officielle HACS](https://www.hacs.xyz/docs/publish/).

## Dépôt custom (installation actuelle)

En attendant l’inclusion dans le store par défaut, les utilisateurs ajoutent le dépôt manuellement ou via le badge **Open in HACS**.

1. Dépôt **public** sur GitHub
2. Fichier [`hacs.json`](../hacs.json) à la racine avec au minimum `name`
3. Structure `custom_components/enki/` avec `manifest.json`
4. README d’installation
5. Workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (lint, tests, HACS, Hassfest) **sans erreur**

### Lien d’installation rapide (my.home-assistant.io)

Après publication du dépôt, générez un lien :

[Créer un lien HACS](https://my.home-assistant.io/create-link/?redirect=hacs_repository&owner=cyrilcolinet&repository=enki-integration-hass&category=integration)

Exemple Markdown pour le README :

```markdown
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=enki-integration-hass&category=integration)
```

## Métadonnées GitHub (obligatoire pour HACS)

Configurer sur la page **Settings** du dépôt GitHub :

| Champ | Exemple |
|-------|---------|
| **Description** | Home Assistant integration for Enki (Leroy Merlin) — Inspire fans, lights |
| **Topics** | `home-assistant`, `hacs`, `hacs-integration`, `enki`, `leroy-merlin`, `inspire` |
| **Issues** | Activées |

## Releases (recommandé)

HACS affiche les 5 dernières releases si elles existent.

1. Créer un tag sémantique (`v1.5.0`) aligné sur `custom_components/enki/manifest.json`
2. Publier une **GitHub Release** (pas seulement un tag)
3. Le workflow [`release.yml`](../.github/workflows/release.yml) injecte la version du tag dans le ZIP HACS attaché (`enki.zip`) — le fichier `manifest.json` du dépôt git doit être mis à jour manuellement avant le tag

## Store HACS par défaut

Procédure : [Include default repositories](https://www.hacs.xyz/docs/publish/include/)

**État du dépôt :** les prérequis techniques sont couverts par la CI sur chaque push/PR :

| Prérequis | Statut |
|-----------|--------|
| Action **HACS** (`hacs/action`, sans `ignore: brands`) | ✅ [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| Action **Hassfest** | ✅ idem |
| `hacs.json` + `country: FR` | ✅ [`hacs.json`](../hacs.json) |
| Au moins **une release** GitHub | ✅ [releases](https://github.com/cyrilcolinet/enki-integration-hass/releases) |
| Brand `custom_components/enki/brand/icon.png` | ✅ (icône HA post-install ; CDN HACS = placeholder tant que le domaine n’est pas dans [home-assistant/brands](https://github.com/home-assistant/brands)) |

**Reste à faire côté publication :** PR sur [hacs/default](https://github.com/hacs/default) (fichier `integration`), entrée **alphabétique** : `cyrilcolinet/enki-integration-hass`.

## Validation locale

Les mêmes vérifications que le workflow **CI** (ruff, pytest, Hassfest, HACS action) tournent sur chaque push/PR. Sur GitHub : onglet **Actions** → workflow **CI**.
