"""Représentation métier des détails et liens, réutilisée par l’API."""
import json
import re
import fnmatch
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
    if object_row and object_row['domain'] == 'dashboard':
        def view_name(match):
            index = match.group(1)
            title = (attrs.get('view_titles') or {}).get(index)
            return f'Vue « {title} »' if title else f'Vue {int(index) + 1}'
        return re.sub(r'^views\\[(\\d+)\\]', view_name, path).replace('.cards[', ' → Carte [').replace('.badges[', ' → Badge [').replace('.sections[', ' → Section [')
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


def build_detail(db, identifier):
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
    return payload

