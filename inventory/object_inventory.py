"""Orchestration de l'inventaire : deux lectures, YAML puis JSON."""
from pathlib import Path
from database import Database
from readers.yaml_reader import build_global
from parsers.yaml.dispatcher import parse_yaml
from parsers.json.dispatcher import parse_storage

def scan(root, db_path, verbose=False):
    root = Path(root).resolve()
    if not (root / 'configuration.yaml').is_file():
        raise FileNotFoundError(root / 'configuration.yaml')
    db = Database(db_path)
    try:
        db.reset()
        data = build_global(root)
        parse_yaml(data, db)
        parse_storage(root, db, verbose)
        db.reconcile_automations()
        db.enrich_objects()
        db.commit()
        objects = db.db.execute('SELECT count(*) FROM objects').fetchone()[0]
        errors = db.db.execute('SELECT count(*) FROM errors').fetchone()[0]
        print(f'Inventaire : {objects} objets ; {errors} erreurs ; global_configuration.yaml généré')
    finally:
        db.close()
