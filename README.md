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

La suite vérifie la compatibilité des imports du moteur, les données SQLite et le regroupement des liens.


## Version 1.4.0b1 — vérifications UI

- Logo carré (512×512) avec marges, sans étirement. Le panneau embarque son image pour ne pas dépendre d'une URL statique.
- Trois cadres **Objets**, **Catégorie**, **Localisation**, deux listes par cadre.
- Le serveur fournit `floor_areas` pour filtrer les pièces d'un étage.
- Le compteur « Dépend de » ignore les relations organisationnelles.
- La date de dernière analyse est persistée dans SQLite, sans analyse automatique.
- Les chemins des actions et déclencheurs sont affichés à partir de 1.

**Icône HACS :** certaines versions de HACS n'affichent pas les logos locaux de `brand/` dans la liste des dépôts personnalisés. Cela ne peut pas être corrigé par le JavaScript de ce panneau.


## Interface 1.5.0b1

Le panneau s'appelle toujours `frontend/panel.js`. Après la mise à jour HACS,
redémarrer Home Assistant et forcer le rechargement du navigateur (Ctrl+F5).
Le détail affiche les automatismes au format YAML reconstruit depuis les
données analysées (pas les commentaires ni la mise en page originale).
Les entités Template liées à une entrée `core.config_entries` affichent les
options de cette seule entrée, sans recopier toutes les entrées du registre.
