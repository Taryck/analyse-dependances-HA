# Dependency Graph — intégration Home Assistant (HACS)

**Version 1.0.0b1 — première version intégrée à Home Assistant.**

Explorateur des entités, assistants, automatisations, catégories et dépendances de configuration.

## Installation (dépôt personnalisé HACS)

1. HACS → menu ⋮ → Dépôts personnalisés → URL de votre dépôt → catégorie **Integration**.
2. Installer « Dependency Graph » et **redémarrer Home Assistant**.
3. Paramètres → Appareils et services → Ajouter une intégration → « Dependency Graph ».
4. Ouvrir **Dépendances** dans la barre latérale, puis cliquer **Analyser**.

Le panneau est réservé aux dévelopeurs & administrateurs. Il propose recherche, filtres domaine/catégorie,
listes paginées, fiches JSON, dépendances entrantes/sortantes et liens de navigation.

## Stockage

- Sources : configuration HA active, lecture seule (`configuration.yaml`, `.storage/`).
- Index SQLite : `.storage/dependency_graph.db`.
- YAML assemblé : `.storage/dependency_graph_global.yaml`.
- Aucun add-on Docker, aucune modification des fichiers sources.
- L'analyse est **manuelle** (bouton Analyser), hors boucle événementielle.

## Limites / sécurité

- **Bêta** : les API de panneaux peuvent évoluer selon la version de Home Assistant.
- Les commentaires YAML/Jinja ne sont pas considérés comme dépendances
- Les informations brutes des registres peuvent contenir des métadonnées sensibles ; accès admin obligatoire.
- Cette version n'est **pas encore validée sur un nombre important d'instance Home Assistant**.

## Validation locale du moteur

```bash
python -m unittest discover -s tests -v
```

<<<<<<< Updated upstream
## Commandes
Soit sur une copie, soit sur un partage samba
```py main.py                      # aide et valeurs trouvées dans la base
py main.py analize "C:\TEMP\HA" --verbose
py main.py analize "\\[HA IP]\config" --verbose
py main.py objects_list --domain sensor
py main.py objects_list --Filter "ID=*sdb*rdc*"
py main.py objects_list --category "Champs Calculés"
py main.py detail sensor.sdb_rdc_sur_humidity
py main.py detail sdb_rdc_sur_hum  # fragment unique autorisé
py main.py values
py main.py errors
py main.py detail --help
```

**`analize`** analyse les objets HA et leur dépendances.

**`objects_list`** affiche une ligne par objet, avec des filtres.

**`detail`** affiche un objet en **JSON indenté** : `object` (métadonnées),
`configuration` (données de source), `depend_on` (entités utilisées) et
`required_by` (objets utilisateurs). Un même utilisateur est affiché une seule
fois, avec une liste `locations` (fichier, chemin relatif, type de référence).
Les étapes portant un `alias` sont affichées par leur alias plutôt que par un
indice numérique ; l'indice est conservé lorsqu'il n'existe pas d'alias.

**`values`** affiche les valeurs distinctes réellement présentes en SQLite.
Les catégories sont lues dans le registre même si aucun objet ne les utilise.

**`errors`** affiche les anomalies enregistrées lors de la dernière analyse.

## Comment fonctionnent les tests ?

```
py -m unittest discover -s tests -v
```

`tests/test_analysis.py` est un programme de **tests automatiques**, pas un
script à exécuter sur la vraie configuration. Pour chaque test, il :

1. Crée un petit dossier Home Assistant fictif dans un répertoire temporaire.
2. Y écrit des exemples YAML et JSON contrôlés.
3. Lance `main.py` comme le ferait un utilisateur Windows.
4. Vérifie les objets, dépendances et JSON retournés.
5. Supprime les fichiers temporaires à la fin du test.

Quatre scénarios sont testés :

- `test_analysis_and_comments` : références actives, commentaires YAML et Jinja,
  accents, génération hors du dossier HA, réanalyse.
- `test_grouped_locations_and_aliases` : un seul utilisateur avec plusieurs
  localisations, remplacement des indices par les alias.
- `test_categories_and_values` : deux catégories `Tempo` de portées distinctes,
  catégorie de capteur Template et affichage de `values`.
- `test_help_and_ambiguous_identifier` : aide contextuelle et objet introuvable.

Un test réussi signifie que **le scénario fictif est couvert** ; cela ne
prouve pas que toutes les structures possibles de Home Assistant sont gérées.

## Limitations de l'analyse statique

Les références `entity_id` explicites et certains appels Jinja (`states`,
`is_state`, `state_attr`...) sont reconnus, ce qui veut dire que cerains autres,
plus exotiques ne sont pas reconnus. Les commentaires YAML et les blocs
`{# ... #}` Jinja sont exclus. Les références construites dynamiquement et les
relations indirectes via `device_id` ne sont pas toutes résolues. Les
expressions complexes peuvent nécessiter un analyseur Jinja plus complet.

## Préparation à une future application Home Assistant

Cette version est **une intégration HACS**, mais peut aussi être testé et utilisée
sur une copie de la configuration en **mode CLI**  (branche local-cli).


## Version 1.0 beta

