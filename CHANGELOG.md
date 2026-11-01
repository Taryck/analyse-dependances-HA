## 1.4.0b1

- Correction réelle de `floor_areas` côté Python.
- Logo carré et embarqué dans le panneau, nouveaux fichiers de marque.
- Compteurs fonctionnels séparés des rattachements.
- Nouveau fichier JavaScript pour contourner le cache.

## 1.2.0b1

- Nouvelle interface large avec filtres Famille → Domaine, Étage → Pièce et catégories HA distinctes.
- Tableau enrichi avec étage, pièce, compteurs, état et tri par colonne.
- Logo fourni affiché dans le panneau.
- Nouveau nom de module JavaScript pour éviter le cache du navigateur et de Home Assistant.
- Commentaires supplémentaires dans le JavaScript.

# Historique

## 1.1.0b1
- Interface pleine largeur (38 % inventaire / 62 % fiche).
- Familles et domaines dépendants, catégories HA séparées par portée.
- Filtres étage puis pièce, colonnes étage/pièce préservées.
- Colonnes Dépend de / Utilisé par / Références manquantes et tri sur chaque colonne.
- Liens d'organisation cliquables : pièce → étage, objet → pièce/catégorie, étage/pièce/catégorie → objets rattachés.
- Icône fournie par l'utilisateur dans `brand/icon.png`.
- Index SQLite sur les relations et les associations d'organisation.

## 1.3.0b1
- Interface : trois cadres **Objets**, **Catégorie**, **Localisation**, chacun avec deux filtres côte à côte.
- Localisation : étage puis pièce, avec liste des pièces limitée à l'étage.
- Compteurs : « Dépend de » exclut les rattachements ; « Utilisé par » inclut les rattachements pour les objets d'organisation.
- Cases à cocher : références manquantes et objets sans dépendance fonctionnelle.
- Dernière analyse mémorisée dans SQLite, date/heure affichée sous le bouton Analyser, surbrillance après 24 heures.
- Logo carré non déformé et visible dans l'en-tête ; nouveaux noms d'assets pour éviter le cache.
- Index des actions et déclencheurs affichés à partir de 1 dans les chemins de dépendances.
- Documentation des méthodes et des règles de l'interface ; tests complémentaires.
