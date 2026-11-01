# -*- coding: utf-8 -*-
"""Point d'entrée de l'analyseur Home Assistant.

Phase 1 : scan construit global_configuration.yaml, puis inventorie YAML et JSON.
Phase 2 : deps-automations relit le YAML global et relève les références.

Les filtres des commandes objects sont insensibles à la casse et acceptent un
préfixe unique (ex. --source auto pour automations.yaml).
Sans argument, cette aide et les valeurs disponibles en base sont affichées.
"""
import argparse
import fnmatch
import re
import yaml
import json
from collections import defaultdict
import sys
from pathlib import Path
from database import Database
from inventory.object_inventory import scan
from dependencies.all_objects import scan_all

DEFAULT_DB = 'ha_dependencies.db'

# La sortie Windows doit préserver les caractères accentués.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def resolve_filter(db, column, value):
    """Résout un préfixe unique à partir des valeurs réellement présentes."""
    if not value:
        return None
    allowed = {'domain','object_type','source_file','source_type'}
    if column not in allowed:
        raise ValueError(f'Colonne non autorisée : {column}')
    values = [row[0] for row in db.db.execute(
        f'SELECT DISTINCT {column} FROM objects WHERE {column} IS NOT NULL ORDER BY {column}')]
    matches = [v for v in values if v.casefold().startswith(value.casefold())]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"Aucune valeur {column} ne commence par '{value}'. Possibles : {', '.join(values)}")
    raise ValueError(f"Filtre '{value}' ambigu pour {column} : {', '.join(matches)}")


def show_values(db):
    """Présente les filtres utilisables, en distinguant les portées de catégories.

    Home Assistant stocke des catégories indépendantes pour les assistants
    (helpers) et les automatisations (automation). Leurs noms peuvent coïncider.
    """
    print('\nValeurs disponibles dans la base :')
    columns = (('object_type','Types'),('domain','Domaines'),
               ('source_file','Fichiers sources'),('source_type','Formats'),
               ('area_name','Pièces'),('floor_name','Étages'))
    for column, title in columns:
        values = [row[0] for row in db.db.execute(
            f'SELECT DISTINCT {column} FROM objects WHERE {column} IS NOT NULL ORDER BY {column}')]
        print(f"  {title} : {', '.join(values) if values else '(aucune donnée)'}")
    for scope, title in (('helpers', 'Catégories assistants (helpers)'),
                         ('automation', 'Catégories automatisations')):
        values = [row['name'] for row in db.db.execute(
            "SELECT name FROM objects WHERE object_id LIKE ? ORDER BY name",
            (f'category.{scope}.%',))]
        print(f"  {title} : {', '.join(values) if values else '(aucune donnée)'}")


def resolve_object(db, identifier):
    """Résout un identifiant exact, un fragment ou un motif glob (*, ?).

    Aucun choix arbitraire : si plusieurs objets correspondent, la CLI
    indique les identifiants possibles et demande de préciser la recherche.
    """
    rows = list(db.db.execute(
        'SELECT * FROM objects WHERE object_id=? OR entity_id=? OR config_id=?',
        (identifier, identifier, identifier)))
    if not rows:
        pattern = identifier.casefold()
        glob = '*' in pattern or '?' in pattern
        rows = [row for row in db.db.execute('SELECT * FROM objects')
                if any(fnmatch.fnmatchcase((row[field] or '').casefold(), pattern)
                       if glob else pattern in (row[field] or '').casefold()
                       for field in ('object_id','entity_id','name'))]
    if len(rows) != 1:
        raise ValueError('Objet introuvable' if not rows else
                         'Nom ambigu : ' + ', '.join(row['object_id'] for row in rows))
    return rows[0]


def location_label(db, dependency, object_row):
    """Transforme un chemin technique en chemin relatif à l'objet.

    Les alias YAML sont préférés aux indices, mais l'indice est conservé
    lorsqu'aucun alias ne permet d'identifier une étape.
    """
    path = dependency['yaml_path'] or ''
    # automation[18] désigne l'objet source, déjà connu : on l'enlève.
    import re
    path = re.sub(r'^automation\[\d+\]\.?', '', path)
    # Pour les capteurs Template créés dans l'interface, l'entrée technique
    # est déjà indiquée par le fichier source et l'objet affiché.
    path = re.sub(r'^template_config\.[^.]+\.', '', path)
    if not path:
        return '(racine)'
    attrs = json.loads(object_row['attributes'] or '{}') if object_row else {}
    config = attrs.get('yaml_configuration') or attrs
    # Remplace seulement les index d'étapes ayant un alias explicite.
    tokens = re.findall(r'([^\[.]+)|\[(\d+)\]', path)
    node = config
    labels = []
    for name, index in tokens:
        if name:
            labels.append(name)
            node = node.get(name) if isinstance(node, dict) else None
        else:
            pos = int(index)
            child = node[pos] if isinstance(node, list) and pos < len(node) else None
            alias = child.get('alias') if isinstance(child, dict) else None
            labels.append(f'[« {alias} »]' if alias else f'[{pos}]')
            node = child
    return '.'.join(labels).replace('.[', '[')


def grouped_links(db, object_ids, direction):
    """Regroupe toutes les occurrences d'un même objet en une entrée JSON.

    Le fichier appartient à l'objet *source* de la relation :
    - depend_on : l'objet affiché est la source ;
    - required_by : l'autre objet est la source.
    Les localisations ne contiennent donc plus de fichier ni de type.
    """
    key = 'source_id' if direction == 'depend_on' else 'target_id'
    other = 'target_id' if direction == 'depend_on' else 'source_id'
    grouped = {}
    for identifier in object_ids:
        for dep in db.db.execute(f'SELECT * FROM dependencies WHERE {key}=? ORDER BY id',
                                 (identifier,)):
            peer = dep[other]
            origin = db.db.execute('SELECT * FROM objects WHERE object_id=? OR entity_id=?',
                                   (dep['source_id'], dep['source_id'])).fetchone()
            path = location_label(db, dep, origin)
            item = grouped.setdefault(peer, {'file': dep['source_file'], 'id': peer,
                                              'locations': []})
            location = {'path': path}
            if location not in item['locations']:
                item['locations'].append(location)
            # Une référence sortante absente de l'inventaire est signalée.
            # Une entrée required_by n'a pas besoin de cet indicateur.
            if direction == 'depend_on':
                exists = db.db.execute(
                    'SELECT 1 FROM objects WHERE object_id=? OR entity_id=? LIMIT 1',
                    (peer, peer)).fetchone()
                if not exists:
                    item['missing'] = True
    return list(grouped.values())


def clean_empty(value):
    """Supprime récursivement les valeurs vides et les valeurs techniques neutres.

    Conserve False et 0 lorsqu'ils sont significatifs dans un paramètre
    métier (p. ex. seuil = 0). Seules les clés techniques dont la valeur 0
    signifie « aucun drapeau » sont écartées.
    """
    neutral_zero = {'supported_features'}
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if child is None or child == '' or child == [] or child == {}:
                continue
            if key in neutral_zero and child == 0:
                continue
            cleaned = clean_empty(child)
            if cleaned is not None and cleaned != '' and cleaned != [] and cleaned != {}:
                result[key] = cleaned
        return result
    if isinstance(value, list):
        return [clean_empty(x) for x in value if x is not None and x != '' and x != [] and x != {}]
    return value


def show_detail(db, identifier):
    """Expose les données métier sans logique liée au terminal.

    Cette structure JSON pourra être réutilisée par une future API Home
    Assistant : la présentation CLI est volontairement minimale.
    """
    row = resolve_object(db, identifier)
    attrs = json.loads(row['attributes'] or '{}')
    identity = {key: row[key] for key in row.keys() if key != 'attributes'}
    ids = {row['object_id']}
    if row['entity_id']:
        ids.add(row['entity_id'])
    payload = {
        'object': clean_empty(identity),
        'configuration': clean_empty(attrs.get('yaml_configuration') or attrs),
        'depend_on': grouped_links(db, ids, 'depend_on'),
        'required_by': grouped_links(db, ids, 'required_by'),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Analyse Home Assistant : inventaire et dépendances',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Exemples :
  py main.py analize "L:\\HomeAssitant\\VM" --verbose
  py main.py objects_list --domain sensor
  py main.py objects_list --Filter "ID=*sdb*rdc*"
  py main.py detail "*sdb*rdc*"
  py main.py objects_list --area rdc
  py main.py values
  py main.py errors""")
    sub=parser.add_subparsers(dest='command')
    p=sub.add_parser('analize',help='Recréer inventaire ET dépendances en une commande')
    p.add_argument('config'); p.add_argument('--db',default=DEFAULT_DB); p.add_argument('--verbose',action='store_true')
    p=sub.add_parser('objects_list',help='Lister et filtrer les objets')
    p.add_argument('--db',default=DEFAULT_DB)
    for option in ('domain','type','source','format','area','floor','category'):
        p.add_argument('--'+option)
    p.add_argument('--category-scope', choices=('helpers','automation'), help='Portée de la catégorie')
    p.add_argument('--filter','--Filter',action='append',help='CHAMP=motif (* et ?)')
    p=sub.add_parser('detail',help='Fiche JSON et dépendances dans les deux sens')
    p.add_argument('id'); p.add_argument('--db',default=DEFAULT_DB)
    for cmd in ('errors','values'):
        p=sub.add_parser(cmd); p.add_argument('--db',default=DEFAULT_DB)
    argv=sys.argv[1:]
    if argv[-2:]==['--','help']: argv=argv[:-2]+['--help']
    args=parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        if Path(DEFAULT_DB).is_file():
            db=Database(DEFAULT_DB)
            try: show_values(db)
            finally: db.close()
        return
    if args.command=='analize':
        scan(args.config,args.db,args.verbose)
        db=Database(args.db)
        try:
            count=scan_all(args.config,db)
            print(f'Analyse terminée : {count} références enregistrées.')
        finally: db.close()
        return
    db=Database(args.db)
    try:
        if args.command=='values': show_values(db)
        elif args.command=='errors':
            print('Source | Erreur')
            for r in db.db.execute('SELECT source_file,message FROM errors ORDER BY id'):
                print(f"{r['source_file']} | {r['message']}")
        elif args.command=='detail':
            try: show_detail(db,args.id)
            except ValueError as exc: parser.error(str(exc))
        elif args.command=='objects_list':
            try:
                filters=[(column,resolve_filter(db,column,value)) for column,value in
                    (('domain',args.domain),('object_type',args.type),('source_file',args.source),('source_type',args.format)) if value]
            except ValueError as exc: parser.error(str(exc))
            sql='SELECT * FROM objects WHERE 1=1'; params=[]
            for col,value in filters: sql+=f' AND {col}=?';params.append(value)
            rows=list(db.db.execute(sql+' ORDER BY domain,object_id',params))
            if args.category_scope:
                # Pour une catégorie, la portée est dans son object_id.
                # Pour une entité, elle est dans attributes.categories.
                def matches_scope(row):
                    if row['domain'] == 'category':
                        return row['object_id'].startswith('category.' + args.category_scope + '.')
                    attrs = json.loads(row['attributes'] or '{}')
                    return args.category_scope in (attrs.get('categories') or {})
                rows = [row for row in rows if matches_scope(row)]
            for option,idfield,namefield in ((args.area,'area_id','area_name'),(args.floor,'floor_id','floor_name'),(args.category,'category_id','category_name')):
                if option:
                    matches={(r[idfield],r[namefield]) for r in rows if
                             (r[idfield] or '').casefold().startswith(option.casefold()) or
                             (r[namefield] or '').casefold().startswith(option.casefold())}
                    if len(matches)>1: parser.error(f'Filtre ambigu : {option} : {matches}')
                    rows=[r for r in rows if (r[idfield],r[namefield]) in matches]
            fields={'id':'object_id','entity_id':'entity_id','nom':'name','name':'name',
                'domain':'domain','type':'object_type','source':'source_file','area':'area_name',
                'floor':'floor_name','category':'category_name','categorie':'category_name',
                'config_id':'config_id','unique_id':'unique_id','labels':'labels'}
            for expression in args.filter or []:
                if '=' not in expression: parser.error('Attendu CHAMP=MOTIF')
                field,pattern=expression.split('=',1)
                column=fields.get(field.strip().casefold())
                if not column: parser.error(f'Champ inconnu : {field}')
                rows=[r for r in rows if fnmatch.fnmatchcase((r[column] or '').casefold(),pattern.casefold())]
            print('ID | Nom | Domaine | Type | Source | Pièce | Étage | Catégorie')
            for r in rows:
                print(' | '.join(str(v or '-') for v in (r['object_id'],r['name'],r['domain'],r['object_type'],r['source_file'],r['area_name'],r['floor_name'],r['category_name'])))
            print(f'{len(rows)} objet(s)')
    finally: db.close()

if __name__=='__main__':
    main()
