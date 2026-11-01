# Analyseur de configuration Home Assistant — V4 (ligne de commande)

L'application fonctionne **hors ligne** à partir d'une copie des fichiers Home Assistant.
Elle n'écrit jamais dans le dossier Home Assistant fourni : la base SQLite et
`global_configuration.yaml` sont créés du côté du programme.

## Installation sur Windows

Dans PowerShell, depuis le dossier où `main.py` est extrait :

```powershell
py -m pip install -r requirements.txt
py main.py analize "L:\HomeAssitant\VM" --verbose
```

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


## Correctif V9 : tests Windows (WinError 32)

Les tests de la V8 utilisaient `with sqlite3.connect(...) as con`. Ce bloc
valide ou annule la transaction, **mais ne ferme pas la connexion SQLite**.
Sous Windows, `TemporaryDirectory.cleanup()` ne peut alors pas supprimer
`test.db` : `PermissionError: [WinError 32]`.

Les tests utilisent maintenant `with closing(sqlite3.connect(...)) as con, con`
(`contextlib.closing`), ce qui ferme réellement la connexion même en cas
d'exception. Un test renomme aussi la base après consultation pour vérifier
que le fichier n'est plus verrouillé. Aucun changement du moteur d'analyse
ni de la structure des données.

Commande : `py -m unittest discover -s tests -v`
