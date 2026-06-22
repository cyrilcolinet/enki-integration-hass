# Publication HACS

Checklist alignée sur la [documentation officielle HACS](https://www.hacs.xyz/docs/publish/).

## Dépôt custom (installation immédiate)

Les utilisateurs ajoutent le dépôt dans HACS sans passer par le store par défaut.

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

1. Créer un tag sémantique (`v1.0.0`)
2. Publier une **GitHub Release** (pas seulement un tag)
3. Le workflow [`release.yml`](../.github/workflows/release.yml) met à jour `manifest.json` et attache `enki.zip`

## Store HACS par défaut (optionnel)

Procédure : [Include default repositories](https://www.hacs.xyz/docs/publish/include/)

Prérequis supplémentaires :

- Actions **HACS** et **Hassfest** vertes **sans** `ignore: brands`
- Au moins **une release** publiée
- PR sur [hacs/default](https://github.com/hacs/default) (fichier `integration`), entrée **alphabétique**
- `country` dans `hacs.json` si le produit est limité géographiquement (déjà `FR`)
- Brand : [`custom_components/enki/brand/icon.png`](../custom_components/enki/brand/icon.png) (chemin requis par HACS) ou PR vers [home-assistant/brands](https://github.com/home-assistant/brands) pour le domaine `enki`

## Validation locale

```bash
# Identique à l’action GitHub (nécessite Docker sur certaines machines)
# En CI : workflow Validate sur chaque push/PR
```

Sur GitHub : onglet **Actions** → workflow **Validate**.
