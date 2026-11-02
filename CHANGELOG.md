# 1.6.0b1

- Analyse Jinja : résolution des variables définies par `{% set s = 'entity_id' %}` puis utilisées dans `is_state(s, ...)` ou `states[s]`. Corrige la dépendance de `sensor.ballon_duree_250` vers `binary_sensor.ballon_250_en_marche`.
- Recherche multi-mots ordonnée : `chauffage temps` correspond à `chauffage*temps`, dans l'identifiant ou le nom.
- Filtres multi-sélection : famille, domaine, type et nom de catégorie, étage et pièce. OU dans un même filtre, ET entre filtres.
- Nouveau filtre Mesure : classe `device_class` et unité `unit_of_measurement` liées, issues des états courants de Home Assistant.
- Tests de régression pour les variables Jinja, les sélections multiples, la recherche et les mesures.
- Le logo unique et toutes les versions précédentes du journal sont conservés.

# 1.5.1b3

- Reconnaissance de `options.source` comme référence directe, notamment pour les assistants `utility_meter`.
- Ajout d'un test de régression pour `statistics.options.entity_id` et `utility_meter.options.source`, couvrant les liens fonctionnels et leurs compteurs.
- Diagnostic de l'icône HACS : problème de résolution des marques locales côté HACS (voir hacs/integration#5402 et #5223). Le fichier unique `brand/icon.png` est conservé, sans duplication.

# 1.5.1b2

- Suppression des trois copies identiques du logo : un seul PNG conservé dans `brand/icon.png`.
- Le panneau utilise directement ce fichier par une route statique dédiée.
- Aucun changement dans l'analyse des dépendances ; historique précédent conservé.

# 1.5.1b1

- Association de toutes les entrées `core.config_entries` via `config_entry_id`, indépendamment du domaine.
- Affichage des options et données de configuration pertinentes, avec masquage des secrets.
- Extraction des dépendances depuis `options` et `data` pour toutes les entités associées.
- Tests de régression couvrant Filter, Template, partage d’entrée et masquage.
