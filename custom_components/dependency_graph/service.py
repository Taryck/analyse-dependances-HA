"""Accès synchrone aux fichiers/SQLite, exécuté hors de la boucle HA."""
import json
import re
from pathlib import Path
from .analyzer.database import Database
from .analyzer.inventory.object_inventory import scan
from .analyzer.dependencies.all_objects import scan_all
from .analyzer.detail import build_detail

class GraphService:
    """Encapsule l'analyse CLI pour la réutiliser dans Home Assistant."""
    def __init__(self, config_dir: str):
        self.root = Path(config_dir)
        self.storage = self.root / '.storage'
        self.db_path = self.storage / 'dependency_graph.db'
        self.global_path = self.storage / 'dependency_graph_global.yaml'

    def analyze(self):
        """Reconstruit entièrement la base ; n'écrit pas les sources HA."""
        scan(self.root, self.db_path, False, self.global_path)
        db = Database(self.db_path)
        try:
            refs = scan_all(self.root, db, self.global_path)
            objects = db.db.execute('SELECT count(*) FROM objects').fetchone()[0]
            errors = db.db.execute('SELECT count(*) FROM errors').fetchone()[0]
            return {'objects': objects, 'dependencies': refs, 'errors': errors}
        finally:
            db.close()

    def list_objects(self, query='', domain='', area='', floor='', category='', scope='', limit=500, offset=0):
        """Pagination et filtres serveur, pour ne pas charger 1000 fiches."""
        if not self.db_path.is_file():
            return {'items': [], 'total': 0, 'analyzed': False}
        db = Database(self.db_path)
        try:
            conditions=['1=1']; params=[]
            if query:
                conditions.append('(lower(object_id) LIKE ? OR lower(name) LIKE ?)')
                pattern='%'+query.lower().replace('*','%').replace('?','_')+'%'
                params.extend([pattern,pattern])
            for col,value in [('domain',domain),('area_name',area),('floor_name',floor),('category_name',category)]:
                if value:
                    conditions.append(f'lower({col}) LIKE ?');params.append('%'+value.lower()+'%')
            if scope:
                conditions.append("(object_id LIKE ? OR json_extract(attributes, '$.categories.' || ?) IS NOT NULL)")
                params.extend([f'category.{scope}.%',scope])
            where=' AND '.join(conditions)
            total=db.db.execute('SELECT count(*) FROM objects WHERE '+where,params).fetchone()[0]
            rows=db.db.execute('SELECT object_id,name,domain,object_type,source_file,area_name,floor_name,category_name FROM objects WHERE '+where+' ORDER BY domain,object_id LIMIT ? OFFSET ?',params+[min(limit,500),offset])
            return {'items':[dict(r) for r in rows], 'total':total,'analyzed':True}
        finally:db.close()

    @staticmethod
    def _redact(value):
        """Masque les champs de secrets avant toute transmission au navigateur.

        Le moteur conserve les registres pour l'analyse, mais l'API ne doit
        pas envoyer les mots de passe ou jetons de core.config_entries.
        """
        sensitive = re.compile(r'(password|passwd|secret|token|api_key|access_key|private_key|client_secret|authorization|credential)', re.I)
        if isinstance(value, dict):
            return {k: ('[MASQUÉ]' if sensitive.search(str(k)) else GraphService._redact(v))
                    for k, v in value.items()}
        if isinstance(value, list):
            return [GraphService._redact(v) for v in value]
        return value

    def detail(self, identifier):
        """Retourne une fiche et les relations regroupées de la V9."""
        if not self.db_path.is_file(): raise ValueError('Analyse non effectuée')
        db=Database(self.db_path)
        try: return self._redact(build_detail(db,identifier))
        finally: db.close()

    def values(self):
        """Valeurs de filtres et catégories par portée."""
        if not self.db_path.is_file():return {}
        db=Database(self.db_path)
        try:
            result={}
            for col in ('domain','area_name','floor_name'):
                result[col]=[r[0] for r in db.db.execute(f'SELECT DISTINCT {col} FROM objects WHERE {col} IS NOT NULL ORDER BY {col}')]
            for scope in ('helpers','automation'):
                result['category_'+scope]=[r[0] for r in db.db.execute('SELECT name FROM objects WHERE object_id LIKE ? ORDER BY name',(f'category.{scope}.%',))]
            return result
        finally:db.close()
