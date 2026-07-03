# Contribuer

Merci de contribuer. Pour l’installation locale, les tests et la CI, voir [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Avant de coder

1. Vérifier les [issues ouvertes](https://github.com/cyrilcolinet/enki-integration-hass/issues)
2. Nouvel appareil Enki : **feature request** avec le résultat de `scripts/discover_devices.py` (sans mot de passe)
3. Contexte API : [docs/API.md](docs/API.md)
4. Clé API volets (beta) : [docs/BETA_VOLETS_KEY.md](docs/BETA_VOLETS_KEY.md)

## Qualité attendue

Avant toute PR :

```bash
ruff check .
ruff format .
pytest tests/unit -v
```

La CI fait la même chose + Hassfest + HACS.

## Organisation du code

- **`api/`** — auth, transport HTTP, client REST Enki
- **`domain/`** — modèles et capacités (aucun import Home Assistant)
- **`lib/`** — conversion et parsing purs, testables sans HA
- **`platforms/`** — logique partagée des plateformes (pas les fichiers loader HA)
- **`telemetry/`** — opt-in profils appareils et nudge legacy
- **Racine** — loaders plateforme HA (`fan.py`, `light.py`, `sensor.py`, `binary_sensor.py`, `climate.py`, `cover.py`, `number.py`, `select.py`, `switch.py`) + `config_flow.py` — liste complète dans `__init__.py` → `PLATFORMS`

Imports publics via les `__init__.py` de chaque package (`from enki.api import EnkiAPI`, etc.).

## Pull requests

- Une PR = un sujet
- Commit impératif (`fix:`, `feat:`, `docs:`)
- Tests unitaires pour la logique modifiée
- Pas de credentials dans le code ou les commits

Modèle : [.github/pull_request_template.md](.github/pull_request_template.md)

## Code de conduite

[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
