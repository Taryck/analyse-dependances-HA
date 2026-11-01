# Dependency Graph — intégration Home Assistant (HACS)

**Version 1.0.0b1 — première version intégrée à Home Assistant.**

Explorateur des entités, assistants, automatisations, catégories et dépendances de configuration.

## Installation (dépôt personnalisé HACS)

1. Publier **le contenu de ce ZIP à la racine d’un dépôt GitHub** (pas le ZIP lui-même).
2. HACS → menu ⋮ → Dépôts personnalisés → URL de votre dépôt → catégorie **Integration**.
3. Installer « Dependency Graph » et **redémarrer Home Assistant**.
4. Paramètres → Appareils et services → Ajouter une intégration → « Dependency Graph ».
5. Ouvrir **Dépendances** dans la barre latérale, puis cliquer **Analyser**.

Le panneau est réservé aux administrateurs. Il propose recherche, filtres domaine/catégorie,
listes paginées, fiches JSON, dépendances entrantes/sortantes et liens de navigation.

## Stockage

- Sources : configuration HA active, lecture seule (`configuration.yaml`, `.storage/`).
- Index SQLite : `.storage/dependency_graph.db`.
- YAML assemblé : `.storage/dependency_graph_global.yaml`.
- Aucun add-on Docker, aucune modification des fichiers sources.
- L'analyse est **manuelle** (bouton Analyser), hors boucle événementielle.

## Limites / sécurité

- **Bêta** : les API de panneaux peuvent évoluer selon la version de Home Assistant.
- Les commentaires YAML/Jinja ne sont pas considérés comme dépendances ; les expressions dynamiques restent partiellement non résolues.
- `missing: true` signifie absent de l'inventaire, pas forcément absent du Home Assistant actif.
- Les informations brutes des registres peuvent contenir des métadonnées sensibles ; accès admin obligatoire.
- Cette version n'est **pas encore validée sur une instance Home Assistant réelle**.
- Avant publication publique, remplacer les URL `OWNER/REPOSITORY` dans `manifest.json`, publier le dépôt et vérifier HACS/hassfest.

## Validation locale du moteur

```bash
python -m unittest discover -s tests -v
```

<<<<<<< Updated upstream
## Commandes

```powershell
py main.py                      # aide et valeurs trouvées dans la base
py main.py analize "L:\HomeAssitant\VM" --verbose
py main.py objects_list --domain sensor
py main.py objects_list --Filter "ID=*sdb*rdc*"
py main.py objects_list --category "Champs Calculés"
py main.py detail sensor.sdb_rdc_sur_humidity
py main.py detail sdb_rdc_sur_hum  # fragment unique autorisé
py main.py values
py main.py errors
py main.py detail --help
```

**`analize`** remplace les anciens `scan` et `deps` : il recrée l'inventaire,
puis les dépendances. Les anciennes commandes `objects`, `object` et
`dependencies` ont été retirées.

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

```powershell
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
`is_state`, `state_attr`...) sont reconnus. Les commentaires YAML et les blocs
`{# ... #}` Jinja sont exclus. Les références construites dynamiquement et les
relations indirectes via `device_id` ne sont pas toutes résolues. Les
expressions complexes peuvent nécessiter un analyseur Jinja plus complet.

## Préparation à une future application Home Assistant

Cette version est **une application CLI**, pas encore une app Home Assistant.
La séparation actuelle vise à faciliter une future interface graphique :

- `readers/` : chargement de fichiers, sans interface utilisateur ;
- `parsers/` : interprétation des objets HA ;
- `inventory/` : orchestration de l'inventaire ;
- `dependencies/` : analyse des références ;
- `database.py` : persistance SQLite ;
- `main.py` : interface CLI, destinée à être remplacée ou complétée par une API.

Pour une future app Home Assistant, prévoir une configuration du chemin source,
un dossier persistant pour SQLite, une exécution sans privilèges excessifs,
un traitement en lecture seule du répertoire de configuration, ainsi qu'une
interface HTTP indépendante de la CLI. **Aucun dépôt d'apps, Dockerfile,
manifest ou interface Web n'est créé à ce stade.**

## Version V8

- `detail "*hc*hp*"` accepte `*` et `?`, sous réserve d'une seule correspondance.
- Les relations sont regroupées par identifiant avec `file` au même niveau que
  `id` et des `locations` ne contenant que `path`.
- `depend_on` ajoute `missing: true` si la cible n'est pas inventoriée.
  Cela indique une **absence dans l'inventaire**, pas nécessairement une
  entité réellement inexistante dans Home Assistant (export incomplet possible).
- Les champs vides/null et `supported_features: 0` sont masqués dans `detail`.
  Les zéros métier (seuils, valeurs, etc.) sont conservés.
- `values` distingue les catégories `helpers` et `automation`.
- `objects_list --category-scope helpers` ou `--category-scope automation`
  filtre explicitement leur portée.
- Le fichier `HACS_PREPARATION.md` décrit la future intégration HACS.

Exemples :

```powershell
py main.py analize "L:\HomeAssitant\VM" --verbose
py main.py detail "*hc*hp*"
py main.py values
py main.py objects_list --domain category --category-scope helpers
py main.py objects_list --domain category --category-scope automation
py -m unittest discover -s tests -v
```
=======
La suite vérifie la compatibilité des imports du moteur, les données SQLite et le regroupement des liens.
>>>>>>> Stashed changes
