from readers.include_resolver import ORIGIN

class BaseParser:
    def __init__(self, db):
        self.db = db

    def add(self, object_id, domain, kind, source_type, source_file, name=None,
            config_id=None, entity_id=None, unique_id=None, attributes=None):
        return self.db.add(dict(object_id=str(object_id), domain=domain,
            object_type=kind, source_type=source_type, source_file=source_file,
            name=name, config_id=str(config_id) if config_id is not None else None,
            entity_id=entity_id, unique_id=unique_id, attributes=attributes))

    def source(self, item):
        return item.get(ORIGIN, 'configuration.yaml') if isinstance(item, dict) else 'configuration.yaml'
