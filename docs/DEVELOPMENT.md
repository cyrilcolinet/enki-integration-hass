# Développement

Documentation technique pour contribuer, tester et publier l’intégration.

## Prérequis

- Python 3.12+
- Home Assistant 2024.12+ (pour tester sur une instance réelle)

```bash
git clone https://github.com/cyrilcolinet/enki-integration-hass.git
cd enki-integration-hass
python3 -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Tests unitaires

Sans compte Enki ni matériel :

```bash
pytest tests/unit -v
```

## Lint et format

```bash
ruff check .
ruff format --check .   # ou ruff format . pour corriger
```

## Tests sur l’API réelle (optionnel)

1. Copier `.env.example` vers `.env`
2. Renseigner `ENKI_USERNAME`, `ENKI_PASSWORD`, `ENKI_HOME_ID`, `ENKI_NODE_ID`
3. Les IDs se récupèrent avec :

```bash
python3 scripts/discover_devices.py <email> <password>
```

4. Lancer les tests :

```bash
set -a && source .env && set +a
pytest tests/integration -v -m integration
```

Les tests live remettent le ventilateur et la lumière à l’arrêt en fin de session.

## Tester dans Home Assistant

Copier `custom_components/enki/` dans le dossier `config/custom_components/` de votre instance de dev, redémarrer, ajouter l’intégration via l’UI.

## CI

Workflow unique : [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Déclenché sur chaque push vers `main` et chaque pull request :

| Job | Rôle |
|-----|------|
| Lint | Ruff check + format |
| Unit tests | `pytest tests/unit` |
| Hassfest | Validation intégration HA |
| HACS | Validation dépôt HACS |

Tests live : uniquement via `workflow_dispatch` avec secrets `ENKI_*` configurés sur le dépôt.

## Publier une release

```bash
git tag v1.0.6
git push origin v1.0.6
```

Créer la release sur GitHub — le workflow `release.yml` génère le ZIP HACS et met à jour la version dans `manifest.json`.

## Documentation technique

| Document | Contenu |
|----------|---------|
| [API.md](API.md) | Endpoints cloud Enki (reverse engineering) |
| [HACS.md](HACS.md) | Checklist publication HACS |

## Structure du code

```
custom_components/enki/
├── api.py              # Client REST Enki
├── coordinator.py      # Polling
├── fan.py / light.py   # Plateformes HA
├── helpers.py          # Mapping pur (testable sans HA)
├── config_flow.py      # UI
└── translations/       # FR + EN
```

Voir aussi [CONTRIBUTING.md](../CONTRIBUTING.md) pour les conventions de PR.
