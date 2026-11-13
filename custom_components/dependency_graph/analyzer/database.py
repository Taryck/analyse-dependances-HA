"""SQLite : objets, erreurs et références (phase 2)."""
import sqlite3
import json

class Database:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS objects (
            object_id TEXT PRIMARY KEY, domain TEXT, object_type TEXT,
            source_type TEXT, source_file TEXT, name TEXT, config_id TEXT,
            entity_id TEXT, unique_id TEXT, attributes TEXT);
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY, source_file TEXT, message TEXT);
        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY, source_id TEXT, target_id TEXT,
            source_file TEXT, yaml_path TEXT, reference_type TEXT,
            UNIQUE(source_id, target_id, yaml_path, reference_type));
        ''')
        self._ensure_columns()
        self.db.executescript('''
        CREATE INDEX IF NOT EXISTS idx_dependency_source ON dependencies(source_id);
        CREATE INDEX IF NOT EXISTS idx_dependency_target ON dependencies(target_id);
        CREATE INDEX IF NOT EXISTS idx_objects_area ON objects(area_id);
        CREATE INDEX IF NOT EXISTS idx_objects_floor ON objects(floor_id);
        CREATE INDEX IF NOT EXISTS idx_objects_category ON objects(category_id);
        ''')

    def _ensure_columns(self):
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(objects)')}
        for column in ('area_id','area_name','floor_id','floor_name',
                       'category_id','category_name','labels'):
            if column not in columns:
                self.db.execute(f'ALTER TABLE objects ADD COLUMN {column} TEXT')
        self.db.commit()

    def reset(self):
        for table in ('objects','errors','dependencies'):
            self.db.execute(f'DELETE FROM {table}')
        self.db.commit()

    def add(self, obj):
        keys = ('object_id','domain','object_type','source_type','source_file',
                'name','config_id','entity_id','unique_id','attributes')
        existing = self.db.execute('SELECT source_file,source_type FROM objects WHERE object_id=?',
                                   (obj['object_id'],)).fetchone()
        if existing:
            self.error(obj['source_file'],
                f"Doublon {obj['object_id']} : première source {existing['source_type']}:"
                f"{existing['source_file']}, deuxième {obj['source_type']}:"
                f"{obj['source_file']} (ignorée)")
            return False
        values = [json.dumps(obj.get(k), ensure_ascii=False, default=str)
                  if k == 'attributes' else obj.get(k) for k in keys]
        self.db.execute(f"INSERT INTO objects ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})", values)
        return True

    def reconcile_automations(self):
        """Relie les définitions YAML aux entités du registre par unique_id exact.

        L'ID d'une automation YAML correspond habituellement au unique_id du registre.
        Aucun rapprochement n'est effectué sur le nom ou l'alias.
        """
        configs = list(self.db.execute("SELECT * FROM objects WHERE domain='automation' AND object_type='automation'"))
        for config in configs:
            entity = self.db.execute("""SELECT * FROM objects WHERE domain='automation'
                AND entity_id IS NOT NULL AND unique_id=?""", (config['config_id'],)).fetchone()
            if not entity:
                continue
            # L'identité canonique est l'entity_id du registre; les informations YAML
            # sont conservées comme métadonnées de configuration.
            attrs = json.loads(entity['attributes'] or '{}')
            attrs['yaml_configuration'] = json.loads(config['attributes'] or '{}')
            attrs['yaml_source_file'] = config['source_file']
            attrs['yaml_config_id'] = config['config_id']
            self.db.execute('UPDATE objects SET attributes=?,config_id=? WHERE object_id=?',
                            (json.dumps(attrs,ensure_ascii=False),config['config_id'],entity['object_id']))
            self.db.execute('DELETE FROM objects WHERE object_id=?', (config['object_id'],))

    def reconcile_config_objects(self):
        """Fusionne les objets de configuration associés à des entités.

        Cette opération s'exécute après l'extraction de toutes les dépendances :
        les références venant des entrées de configuration sont déjà reliées
        directement aux entités. Ne conserve que les objets sans correspondance.
        """
        rows = list(self.db.execute(
            "SELECT * FROM objects WHERE object_type IN ('helper', 'config_entry') "
            "OR object_id LIKE 'input\\_%\\_config.%' ESCAPE '\\'"
        ))
        for row in rows:
            oid = row['object_id']
            # Un helper déjà inventorié sous son entity_id n'est PAS un doublon.
            if row['object_type'] == 'helper' and row['entity_id'] == oid:
                continue
            attrs = json.loads(row['attributes'] or '{}')
            if row['object_type'] == 'config_entry':
                entry_id = row['config_id'] or attrs.get('entry_id')
                if not entry_id:
                    continue
                entities = list(self.db.execute(
                    "SELECT * FROM objects WHERE entity_id IS NOT NULL "
                    "AND json_extract(attributes, '$.config_entry_id')=?", (entry_id,)
                ))
            else:
                # input_datetime_config.heure_fin_hc -> input_datetime.heure_fin_hc.
                # Les anciennes entrées possèdent parfois un unique_id plutôt
                # qu'un entity_id. Ne jamais apparier par le seul nom affiché.
                domain = row['domain']
                key = oid.split('.', 1)[1] if '.' in oid else ''
                if domain.endswith('_config'):
                    domain = domain[:-7]
                if not key or not domain.startswith('input_'):
                    continue
                entity_id = f'{domain}.{key}'
                entities = list(self.db.execute(
                    "SELECT * FROM objects WHERE entity_id=? OR object_id=?", (entity_id, entity_id)
                ))
                if not entities and row['unique_id']:
                    entities = list(self.db.execute(
                        "SELECT * FROM objects WHERE domain=? AND unique_id=? "
                        "AND entity_id IS NOT NULL", (domain, row['unique_id'])
                    ))
                if len(entities) != 1:
                    continue

            if not entities:
                continue
            for entity in entities:
                if entity['object_id'] == oid:
                    continue
                item_attrs = json.loads(entity['attributes'] or '{}')
                if row['object_type'] == 'config_entry':
                    item_attrs['config_entry_configuration'] = attrs
                else:
                    item_attrs['helper_configuration'] = attrs
                    item_attrs['helper_source_file'] = row['source_file']
                self.db.execute(
                    'UPDATE objects SET attributes=? WHERE object_id=?',
                    (json.dumps(item_attrs, ensure_ascii=False), entity['object_id'])
                )
                # Une dépendance dont la source est la configuration doit
                # désormais appartenir à l'entité. L'unicité est préservée.
                self.db.execute(
                    "INSERT OR IGNORE INTO dependencies "
                    "(source_id,target_id,source_file,yaml_path,reference_type) "
                    "SELECT ?,target_id,source_file,yaml_path,reference_type "
                    "FROM dependencies WHERE source_id=?", (entity['object_id'], oid)
                )
            self.db.execute('DELETE FROM dependencies WHERE source_id=?', (oid,))
            self.db.execute('DELETE FROM objects WHERE object_id=?', (oid,))

    def enrich_objects(self):
        """Associe pièces, étages, catégories et étiquettes sans modifier l'identité."""
        rows = list(self.db.execute('SELECT object_id,domain,object_type,attributes FROM objects'))
        index = {}
        for row in rows:
            if row['object_type'] in ('area','floor','category','label'):
                index[row['object_id']] = json.loads(row['attributes'] or '{}')
        areas = {k.split('.',1)[1]: v for k,v in index.items() if k.startswith('area.')}
        floors = {k.split('.',1)[1]: v for k,v in index.items() if k.startswith('floor.')}
        labels = {k.split('.',1)[1]: v for k,v in index.items() if k.startswith('label.')}
        categories = {k.split('.',1)[1]: v for k,v in index.items() if k.startswith('category.')}
        for row in rows:
            attrs = json.loads(row['attributes'] or '{}')
            area_id = attrs.get('area_id')
            if not area_id and attrs.get('device_id'):
                area_id = self.device_areas.get(attrs['device_id']) if hasattr(self, 'device_areas') else None
            area = areas.get(area_id, {})
            floor_id = attrs.get('floor_id') or area.get('floor_id')
            # Home Assistant conserve les catégories sous un dictionnaire par portée.
            # Exemple : {'helpers': '01...', 'automation': '01...'}.
            # Un simple attrs['category_id'] manquerait ces associations.
            category_scope = 'automation' if row['domain'] == 'automation' else 'helpers'
            scopes = attrs.get('categories') or {}
            category_id = attrs.get('category_id')
            if isinstance(scopes, dict):
                category_id = scopes.get(category_scope) or category_id
            # Les objets YAML réconciliés avec leur entité de registre
            # conservent les catégories du registre dans attrs.

            category = categories.get(f'{category_scope}.{category_id}', {}) or categories.get(category_id, {})
            # "helpers" est une portée de catégories, pas un filtre de domaine.
            # Un sensor Template créé depuis l'UI peut être classé dans helpers.
            # La portée a déjà été prise en compte lors de la recherche.
            label_ids = attrs.get('labels') or []
            if not isinstance(label_ids, list): label_ids = []
            label_names = [labels.get(x, {}).get('name', x) for x in label_ids]
            self.db.execute('''UPDATE objects SET area_id=?,area_name=?,floor_id=?,floor_name=?,
                category_id=?,category_name=?,labels=? WHERE object_id=?''',
                (area_id, area.get('name'), floor_id, floors.get(floor_id, {}).get('name'),
                 category_id, category.get('name'), ', '.join(label_names), row['object_id']))

    def error(self, source, message):
        print(f'[ERREUR] {source}: {message}')
        self.db.execute('INSERT INTO errors(source_file,message) VALUES (?,?)',(source,message))

    def commit(self): self.db.commit()
    def close(self): self.db.close()
