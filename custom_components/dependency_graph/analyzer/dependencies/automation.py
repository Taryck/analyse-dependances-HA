# -*- coding: utf-8 -*-
"""Phase 2 : dépendances structurelles dans les automatisations.

Le YAML est chargé avec safe_load : les commentaires YAML sont éliminés par le parseur.
Les chaînes Jinja sont inspectées uniquement si elles sont des valeurs effectives.
Les appels de services, identifiants d'appareils et alias ne sont pas des entités.
"""
from pathlib import Path
import re
import yaml

ENTITY = re.compile(r"(?<![\w.])([a-z_][a-z0-9_]*\.[a-z0-9_]+)(?![\w.])", re.I)
TEMPLATE_KEYS = {'value_template', 'wait_template', 'state', 'attributes', 'variables', 'template', 'value', 'datetime', 'time', 'message', 'data', 'data_template'}
ENTITY_KEYS = {'entity_id', 'above', 'below', 'at', 'entity'}
IGNORE_KEYS = {'alias', 'description', 'action', 'service', 'trigger', 'condition', 'type', 'domain', 'id', 'device_id', 'area_id', 'label_id', 'icon', 'fichier_d_origine'}


def scan_automations(root, db):
    path = Path(root) / 'global_configuration.yaml'
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    section = data.get('automation') or []
    source_file = 'configuration.yaml'
    if isinstance(section, dict) and 'contenu' in section:
        source_file = section.get('fichier_d_origine') or source_file
        section = section['contenu']
    if not isinstance(section, list):
        db.error(str(path), 'automation doit être une liste')
        return 0
    db.db.execute('DELETE FROM dependencies')
    count = 0

    def emit(source, target, location, kind):
        nonlocal count
        cur = db.db.execute("""INSERT OR IGNORE INTO dependencies
            (source_id,target_id,source_file,yaml_path,reference_type)
            VALUES (?,?,?,?,?)""", (source, target, source_file, location, kind))
        count += cur.rowcount

    def walk(value, location, source, key=None, in_template=False):
        if isinstance(value, dict):
            for k, child in value.items():
                if k in IGNORE_KEYS:
                    continue
                walk(child, f'{location}.{k}', source, k, in_template or k in TEMPLATE_KEYS)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f'{location}[{i}]', source, key, in_template)
        elif isinstance(value, str):
            is_template = '{{' in value or '{%' in value
            if key in ENTITY_KEYS:
                kind = 'entity_id' if key == 'entity_id' else 'entity_reference'
            elif is_template:
                kind = 'jinja'
            else:
                return
            for match in ENTITY.finditer(value):
                emit(source, match.group(1), location, kind)

    for i, item in enumerate(section):
        if not isinstance(item, dict) or item.get('id') is None:
            continue
        walk(item, f'automation[{i}]', f"automation_config.{item['id']}")
    db.commit()
    return count
