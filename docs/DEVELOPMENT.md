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

## Scripts locaux (hors Home Assistant)

Les scripts dans `scripts/` s’exécutent **sur votre machine de dev**, pas dans le conteneur HA. Ils parlent directement à l’API Enki cloud (ou analysent un APK). Home Assistant n’a pas besoin d’être installé — seulement Python 3 et `pip install -r requirements-dev.txt`.

| Script | Usage |
|--------|--------|
| `scripts/fetch_gateway_keys.py` | Vérifie le login et lit `mobile-config` `/settings` (pas les clés gateway) |
| `scripts/extract_gateway_keys.py` | Extrait les clés gateway depuis un APK (jadx + DI module) ; `--apply` met à jour `const.py` |
| `scripts/discover_devices.py` | Exporte les profils appareils anonymisés du compte |

```bash
source .venv/bin/activate
python3 scripts/fetch_gateway_keys.py
python3 scripts/extract_gateway_keys.py chemin/vers/enki.apk
python3 scripts/extract_gateway_keys.py chemin/vers/enki.apk --apply --update-known
python3 scripts/discover_devices.py votre@email.com 'mot-de-passe'
```

Les clés gateway sont embarquées dans l’APK (une par micro-service). Utiliser `extract_gateway_keys.py --apply` après chaque mise à jour de l’app Enki.

## Langue du dépôt

- **Code Python** (commentaires, docstrings) : anglais — voir [CONTRIBUTING.md](../CONTRIBUTING.md#langue)
- **Markdown** (`docs/`, `README.md`, …) : français
- **UI Home Assistant** (`strings.json`, traductions) : français

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
| HACS | Validation dépôt (éligibilité store par défaut) |

Tests live : uniquement via `workflow_dispatch` avec secrets `ENKI_*` configurés sur le dépôt.

## Publier une release

1. Mettre à jour `custom_components/enki/manifest.json` avec la version cible (ex. `1.5.0`)
2. Taguer et pousser :

```bash
git tag v1.5.0
git push origin v1.5.0
```

3. Créer la **GitHub Release** depuis le tag — le workflow [`release.yml`](../.github/workflows/release.yml) attache `enki.zip` avec la version du tag injectée dans le manifest du ZIP (sans commit automatique sur le dépôt).

Si le secret **`ENKI_APK_URL`** est configuré (URL directe vers l’APK Enki Play Store / artifact), le job **Validate gateway keys (APK)** décompile l’APK avec jadx et échoue la release si les clés `gateway_keys_data.py` divergent (`extract_gateway_keys.py --check`). Sans ce secret, la validation est ignorée et la release continue comme avant.

## Documentation technique

| Document | Contenu |
|----------|---------|
| [API.md](API.md) | Endpoints cloud Enki (reverse engineering) |
| [HACS.md](HACS.md) | Checklist publication HACS |
| [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) | Matériel et statut réel par appareil |

## Structure du code

Home Assistant exige que les **loaders de plateforme** et `config_flow.py` restent à la racine de `custom_components/enki/`. Le reste est organisé par couche :

```
custom_components/enki/
├── __init__.py, manifest.json, config_flow.py, coordinator.py, entity.py
├── binary_sensor.py, climate.py, cover.py, fan.py, light.py
├── number.py, select.py, sensor.py, switch.py, diagnostics.py
├── const.py, exceptions.py, strings.json, translations/, brand/
│
├── api/                    # couche cloud
│   ├── client.py           # discovery + REST commands
│   ├── auth.py             # OAuth Keycloak
│   ├── transport.py        # HTTP per micro-service
│   ├── gateway_registry.py # APK micro-service catalogue
│   └── gateway_keys.py     # runtime key store + mobile-config settings path
│
├── domain/                 # modèle métier (sans import HA)
│   ├── models.py, capabilities.py, state.py, profile.py
│
├── platforms/              # logique interne partagée
│   ├── light/behavior.py
│   └── fan/airflow.py
│
├── telemetry/
│   ├── reporter.py
│   └── nudge.py
│
└── lib/                    # fonctions pures (0 import HA)
    ├── conversion.py, bff.py, battery.py, capability_path.py
    ├── heating.py, shutter.py, enki_scope.py
```

Plateformes enregistrées dans `__init__.py` → `PLATFORMS` : `binary_sensor`, `climate`, `cover`, `fan`, `light`, `number`, `select`, `sensor`, `switch`.

### Conventions d’import

| Package | Rôle | Exemple |
|---------|------|---------|
| `enki.api` | Client cloud public | `from enki.api import EnkiAPI` |
| `enki.domain` | Modèle et capacités | `from enki.domain.models import EnkiDevice` |
| `enki.lib` | Helpers testables sans HA | `from enki.lib.conversion import speed_to_percentage` |
| `enki.platforms.fan` | Logique ventilateur | `from enki.platforms.fan.airflow import preset_to_enki_airflow_mode` |
| `enki.telemetry` | Opt-in télémétrie | `from enki.telemetry import EnkiTelemetryReporter` |

Voir aussi [CONTRIBUTING.md](../CONTRIBUTING.md) pour les conventions de PR.
