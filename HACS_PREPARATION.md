# Préparation de l'intégration HACS (pas encore une intégration installable)

## Principe

La V8 reste une application **CLI hors Home Assistant**. Ne pas installer le
projet dans `custom_components` à ce stade. La transformation visée est une
**intégration personnalisée HACS**, pas un add-on Docker.

## Structure cible

```text
custom_components/dependency_graph/
  __init__.py           # initialisation et arrêt de l'intégration
  manifest.json         # métadonnées Home Assistant
  config_flow.py        # installation depuis Paramètres > Intégrations
  coordinator.py        # déclenchement/rafraîchissement asynchrone de l'analyse
  api.py                # accès aux objets et relations pour le frontend
  analyzer/             # moteur d'analyse indépendant de l'interface
    database.py
    readers/
    parsers/
    dependencies/
  frontend/             # écran de recherche et fiche interactive
hacs.json
README.md
.github/workflows/validate.yml
```

## Contraintes d'architecture à respecter

1. **Moteur indépendant de la CLI** : garder l'analyse, les requêtes SQLite
   et la sérialisation JSON dans des fonctions réutilisables. `main.py` ne doit
   servir qu'au terminal.
2. **Ne pas analyser depuis le thread principal de HA** : exécuter les accès
   fichiers et SQLite via un exécuteur, sans bloquer l'event loop.
3. **Lire le répertoire de configuration réel** (`hass.config.config_dir`)
   sans dépendre d'un export Windows ou d'un chemin codé en dur.
4. **Stocker la base et les fichiers temporaires dans un chemin contrôlé** ;
   éviter d'écrire `global_configuration.yaml` dans la configuration HA.
5. **Accès en lecture seule aux sources HA** : ne pas modifier les registres
   `.storage` ni les fichiers YAML.
6. **Éviter les secrets** : ne pas exposer `core.config_entries` en entier
   au navigateur. N'exposer que les paramètres pertinents et filtrés.
7. **UI de navigation** : tableau filtrable (ID, nom, domaine, pièce,
   catégorie), fiche avec `depend_on`/`required_by`, liens cliquables,
   marqueur `missing`, filtres de portée de catégorie.
8. **Actualisation** : action de rescannage manuel et état de progression ;
   pas de scan automatique à chaque affichage de fiche.
9. **Tests** : tests du moteur sans HA, puis tests d'intégration avec mocks HA,
   validations Hassfest et HACS avant publication.

## HACS

La documentation HACS impose un seul composant sous
`custom_components/` et tous les fichiers nécessaires à l'exécution dans
ce répertoire. `manifest.json` doit contenir les métadonnées obligatoires.

Références :
- https://hacs.xyz/docs/publish/integration/
- https://hacs.xyz/docs/publish/include/

**Aucun composant Home Assistant fonctionnel ni interface web n'est livré dans
la V8.** Ce document fixe seulement les interfaces et contraintes pour la suite.
