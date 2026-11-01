# 1.5.1b2

- Suppression des trois copies identiques du logo : un seul PNG conservé dans `brand/icon.png`.
- Le panneau utilise directement ce fichier par une route statique dédiée.
- Aucun changement dans l'analyse des dépendances ; historique précédent conservé.

# 1.5.1b1

- Association de toutes les entrées `core.config_entries` via `config_entry_id`, indépendamment du domaine.
- Affichage des options et données de configuration pertinentes, avec masquage des secrets.
- Extraction des dépendances depuis `options` et `data` pour toutes les entités associées.
- Tests de régression couvrant Filter, Template, partage d’entrée et masquage.
