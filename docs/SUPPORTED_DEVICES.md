# Appareils et fonctionnalités supportés

Détail par type d’appareil et entités Home Assistant créées. L’intégration détecte les appareils via leurs **capabilities** API (comme l’app mobile), pas seulement par modèle.

Version de référence : **1.2.0**

## Ventilateurs Inspire (Siroco+, Aruba+, Cadix, Radix, …)

**Entités HA :** ventilateur + lumière (kit LED)

| Fonction | Détail |
|----------|--------|
| Marche / arrêt | Vitesse 0 ou coupure moteur |
| Vitesse | 6 niveaux (mapping pourcentage HA) |
| Sens de rotation | Été (brise descendante) / hiver (déstratification) |
| Modes | Manuel, brise, ventilation, boost, auto, nuit (selon modèle) |

Le ventilateur et sa lumière sont **indépendants** : allumer l’un n’allume pas l’autre.

## Luminaires Enki (Eglo, Lexman, …)

**Entité HA :** lumière

| Fonction | Détail |
|----------|--------|
| Marche / arrêt | ON / OFF |
| Luminosité | Selon modèle |
| Blanc variable | Température de couleur (Kelvin), selon modèle |

## Prises et interrupteurs (Edisio, …)

**Entité HA :** lumière ON/OFF (API power Enki)

| Fonction | Détail |
|----------|--------|
| Marche / arrêt | Via `switch-electrical-power` |

Les nœuds multi-circuits peuvent créer **une entité par circuit** (endpoint BFF).

## Panneaux solaires (Envertech-Lexman)

**Entité HA :** capteur de production (W)

| Fonction | Détail |
|----------|--------|
| Production instantanée | Valeur lue sur le dashboard BFF |

## Volets roulants — beta (Evology, Nodon, …)

**Entité HA :** cover « Volet (beta) »

| Fonction | Détail |
|----------|--------|
| Ouverture / fermeture | Commandes cover HA |
| Position | 0–100 % (si l’API motorisation répond) |

Support **expérimental** : retours de testeurs bienvenus via [feature request](https://github.com/cyrilcolinet/enki-integration-hass/issues/new?template=feature_request.yml).

## Fonctionnalités transverses

- **Auth OAuth** — refresh token, sessions plus stables
- **Télémétrie opt-in** — notification pour appareils inconnus, lien GitHub pré-rempli (rien n’est envoyé sans clic)
- **Diagnostics** — export JSON anonymisé depuis l’UI Enki

## En cours / non supporté

| Statut | Appareils |
|--------|-----------|
| Bientôt | Radiateurs ACOVA ARLAN |
| Non planifié | Alarme Enki (pas d’API identifiée) |
| Hors périmètre | Box Enki, appairage, compte Leroy Merlin → [support Enki](https://support.enki-home.com/) |

Documentation API : [API.md](API.md)
