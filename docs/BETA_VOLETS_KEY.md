# Clé API volets — guide contributeur

Ce document s’adresse aux **personnes à l’aise avec le réseau / le débogage mobile**. Les testeurs lambda n’ont pas besoin de le lire : voir [Beta volets — pour les testeurs](SUPPORTED_DEVICES.md#pour-les-testeurs) dans `SUPPORTED_DEVICES.md`.

## Pourquoi cette clé existe

L’app mobile Enki envoie, avec chaque requête cloud, un en-tête **`X-Gateway-APIKey`** propre au micro-service (ventilateurs, lumières, volets, etc.). L’intégration Home Assistant embarque ces clés dans `custom_components/enki/const.py`.

Pour les **volets** (`api-enki-access-and-motorizations-prod`), la clé **`ENKI_ACCESS_MOTORIZATION_API_KEY`** n’est pas encore connue publiquement. Tant qu’elle est vide dans `const.py`, l’intégration **n’importe pas** les volets (`is_cover` retourne false) : aucune entité « Volet (beta) » dans Home Assistant.

**Ce n’est pas :**

- le mot de passe du compte Enki ;
- un secret personnel lié à un foyer ;
- une donnée à partager publiquement sur les réseaux sociaux (c’est une clé applicative Leroy Merlin / Adeo, réutilisable pour toute l’intégration une fois intégrée au repo).

**Une seule capture suffit** pour débloquer tous les utilisateurs à la prochaine release.

## Ce qu’il faut récupérer

Lors d’un contrôle de volet dans l’app Enki, repérer une requête HTTP vers :

```text
…/api-enki-access-and-motorizations-prod/v1/access-and-motorizations/…
```

Copier la valeur de l’en-tête :

```text
X-Gateway-APIKey: <valeur à transmettre au mainteneur>
```

Actions typiques visibles dans l’URL : `check-shutter-position`, `change-shutter-position`, `check-shutter-opening`.

## Méthode recommandée — mitmproxy

### Prérequis

- PC et téléphone sur le **même réseau Wi‑Fi**
- [mitmproxy](https://mitmproxy.org/) installé sur le PC
- App **Enki** sur le téléphone, avec au moins un volet fonctionnel

### Étapes

1. **Lancer mitmproxy** sur le PC :
   ```bash
   mitmweb
   ```
   Interface web : http://127.0.0.1:8081 — proxy écoute sur le port **8080**.

2. **Configurer le proxy Wi‑Fi sur le téléphone**  
   Réglages Wi‑Fi → réseau actuel → proxy manuel → IP du PC, port **8080**.

3. **Installer le certificat mitmproxy** sur le téléphone  
   Sur le téléphone, ouvrir http://mitm.it et suivre les instructions (iOS ou Android). Sans certificat, le trafic HTTPS de l’app ne sera pas visible.

4. **Contrôler un volet dans l’app Enki**  
   Ouvrir, fermer ou régler la position d’un volet.

5. **Filtrer le trafic** dans mitmweb  
   Rechercher `access-and-motorizations` ou `change-shutter`.

6. **Copier `X-Gateway-APIKey`** depuis les en-têtes de la requête.

7. **Désactiver le proxy** sur le téléphone une fois terminé.

### Transmission au projet

Ouvrir une [issue](https://github.com/cyrilcolinet/enki-integration-hass/issues/new) ou commenter sur une issue volets existante avec :

- la valeur de `X-Gateway-APIKey` (texte seul) ;
- modèle de volet testé (ex. Evology SIN2RS1) ;
- confirmation que la commande fonctionnait dans l’app au moment de la capture.

**Ne jamais joindre :** e-mail, mot de passe, tokens Bearer, homeId, nodeId.

## Alternative — HTTP Toolkit

[HTTP Toolkit](https://httptoolkit.com/) propose une interface graphique (connexion téléphone Android via ADB, ou proxy manuel similaire à mitmproxy). Le principe est identique : intercepter une requête `access-and-motorizations` et lire `X-Gateway-APIKey`.

## Intégration côté repo

Le mainteneur ajoute la clé dans :

```python
# custom_components/enki/const.py
ENKI_ACCESS_MOTORIZATION_API_KEY = "…"
```

Puis publie une nouvelle version. Les utilisateurs n’ont rien à modifier manuellement s’ils passent par HACS.

## Références

- Notes API volets : [API.md](API.md#roller-shutters-evology-sin2rs1--beta)
- Testeurs (sans proxy) : [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md#pour-les-testeurs)
