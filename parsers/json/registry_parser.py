"""Registres HA : les clés et structures diffèrent selon le registre."""
from parsers.base_parser import BaseParser

REGISTRIES = {
    'core.area_registry': ('areas', 'id', 'area'),
    'core.floor_registry': ('floors', 'floor_id', 'floor'),
    'core.label_registry': ('labels', 'label_id', 'label'),
    'core.category_registry': ('categories', 'category_id', 'category'),
}

class RegistryParser(BaseParser):
    def parse(self, payload, filename):
        collection, key, domain = REGISTRIES[filename]
        data = payload.get('data', {}).get(collection, [])
        # category_registry: {"helpers": [...], "automation": [...]}.
        if filename == 'core.category_registry' and isinstance(data, dict):
            entries = [(scope, item) for scope, group in data.items()
                       if isinstance(group, list) for item in group]
        elif isinstance(data, list):
            entries = [(None, item) for item in data]
        else:
            self.db.error(filename, f'Structure inattendue pour data.{collection}')
            return
        for scope, item in entries:
            if not isinstance(item, dict):
                self.db.error(filename, 'Entrée de registre non dictionnaire')
                continue
            value = item.get(key)
            if not value:
                self.db.error(filename, f'Clé {key} absente')
                continue
            attributes = dict(item)
            if scope:
                attributes['category_scope'] = scope
            self.add(f'{domain}.{scope}.{value}' if scope else f'{domain}.{value}', domain, domain, 'json', filename,
                     item.get('name'), config_id=value, attributes=attributes)
