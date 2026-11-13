# ARCHITECTURE ET CONVENTIONS
# ---------------------------
# Ce module ne doit jamais écrire dans les registres sources Home Assistant.
# Les écritures concernent exclusivement les fichiers propres à l'intégration.
# Les données sont lues dans un thread via hass.async_add_executor_job.
# Les identifiants HA restent inchangés : aucune renumérotation dans la base.
# Les relations fonctionnelles viennent du code YAML/Jinja analysé.
# Les relations d'organisation proviennent des registres HA (étage/pièce).
# Une référence manquante est une cible absente de la table des objets.
# La présentation française appartient au frontend, pas aux tables SQLite.
# Les requêtes SQL utilisent des paramètres pour les valeurs fournies par l'UI.
# Seuls les noms de colonnes de tri présents dans la liste blanche sont admis.
# Les appels WebSocket sont réservés aux administrateurs de Home Assistant.
# Les exceptions internes sont consignées dans les journaux du serveur.
# Le navigateur ne reçoit pas les champs de secrets identifiés par _redact.
# La date de dernière analyse est enregistrée après une reconstruction réussie.
# Le bouton d'analyse reste manuel : aucun scan n'est programmé au démarrage.
# La base peut être supprimée puis reconstruite sans modifier les sources HA.
# Ce commentaire décrit les invariants de sécurité et les choix de conception.

"""Accès synchrone aux fichiers/SQLite, exécuté hors de la boucle HA."""
import json
import yaml
from datetime import datetime, timezone
import re
from pathlib import Path
from .analyzer.database import Database
from .analyzer.inventory.object_inventory import scan
from .analyzer.dependencies.all_objects import scan_all
from .analyzer.detail import build_detail
from .analyzer.dashboard import scan_dashboards

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
            refs += scan_dashboards(self.root, db, self.global_path)
            objects = db.db.execute('SELECT count(*) FROM objects').fetchone()[0]
            errors = db.db.execute('SELECT count(*) FROM errors').fetchone()[0]
            # La date est écrite seulement après la reconstruction complète.
            # SQLite conserve cette information même après un redémarrage de HA.
            # Une reconstruction échouée ne remplace pas la date du dernier succès.
            db.db.execute("CREATE TABLE IF NOT EXISTS analysis_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            analyzed_at = datetime.now(timezone.utc).isoformat()
            db.db.execute("INSERT OR REPLACE INTO analysis_metadata (key, value) VALUES ('analyzed_at', ?)", (analyzed_at,))
            db.db.commit()
            return {'objects': objects, 'dependencies': refs, 'errors': errors, 'analyzed_at': analyzed_at}
        finally:
            db.close()

    def list_objects(self, query='', domain='', area='', floor='', category='', scope='', family='', limit=500, offset=0, sort='object_id', descending=False, missing_only=False, no_dependencies=False, measurement=None, unit=None, measurements=None):
        """Inventaire paginé avec compteurs de voisins distincts et tri serveur."""
        if not self.db_path.is_file():
            return {'items': [], 'total': 0, 'analyzed': False, 'analyzed_at': None}
        db = Database(self.db_path)
        try:
            conditions = ['1=1']; params = []
            # Les mots séparés par des espaces sont recherchés dans leur ordre,
            # comme si l'utilisateur avait saisi « chauffage*temps ».
            # Les caractères % et _ sont échappés pour éviter un LIKE inattendu.
            if query:
                # Les mots sont séparés par un espace et deviennent des jokers LIKE.
                # Les caractères SQL spéciaux sont échappés ; * reste un joker.
                terms = [t for t in re.split(r'\s+', query.strip()) if t]
                def escape_term(term):
                    return (term.lower().replace('\\', '\\\\')
                            .replace('%', '\\%').replace('_', '\\_')
                            .replace('*', '%').replace('?', '_'))
                pattern = '%' + '%'.join(escape_term(t) for t in terms) + '%'
                conditions.append(
                    "(lower(o.object_id) LIKE ? ESCAPE '\\' "
                    "OR lower(COALESCE(o.name,'')) LIKE ? ESCAPE '\\')"
                )
                params.extend([pattern, pattern])

            # Chaque filtre accepte zéro, une ou plusieurs valeurs.
            # OU au sein d'un filtre, ET entre les familles de filtres.
            def selected(value):
                if isinstance(value, str):
                    return [value] if value else []
                return [v for v in value if isinstance(v, str) and v]

            def in_values(column, values):
                if values:
                    conditions.append(f"o.{column} IN ({','.join('?' for _ in values)})")
                    params.extend(values)

            in_values('domain', selected(domain))
            in_values('area_name', selected(area))
            in_values('floor_name', selected(floor))

            categories, scopes = selected(category), selected(scope)
            if categories:
                # Ne pas confondre deux catégories de même nom appartenant
                # à des portées différentes (helpers / automation).
                if scopes:
                    clauses = []
                    for current_scope in scopes:
                        clauses.append(
                            "(o.category_id IN (SELECT substr(object_id, length(?) + 11) "
                            "FROM objects WHERE object_id LIKE ? AND name IN (" +
                            ','.join('?' for _ in categories) + ")))"
                        )
                        params.extend([current_scope, f'category.{current_scope}.%', *categories])
                    conditions.append('(' + ' OR '.join(clauses) + ')')
                else:
                    in_values('category_name', categories)
            if scopes:
                conditions.append('(' + ' OR '.join(
                    "(o.object_id LIKE ? OR json_extract(o.attributes, '$.categories.' || ?) IS NOT NULL)"
                    for _ in scopes
                ) + ')')
                for current_scope in scopes:
                    params.extend([f'category.{current_scope}.%', current_scope])

            families = selected(family)
            if families:
                org = "o.domain IN ('area','floor','category','label')"
                helpers = "o.domain IN ('input_boolean','input_datetime','input_number','input_select','input_text','input_button','counter','timer','schedule')"
                autom = "o.domain IN ('automation','script','scene')"
                mapping = {
                    'organisation': org, 'assistants': helpers,
                    'automatisations': autom, 'dashboards': "o.domain = 'dashboard'",
                    'entites': f"NOT ({org} OR {helpers} OR {autom} OR o.domain = 'dashboard')",
                }
                chosen = [mapping[f] for f in families if f in mapping]
                if chosen:
                    conditions.append('(' + ' OR '.join(chosen) + ')')
            # Les classes et unités viennent des états HA actifs, pas du
            # registre des entités, qui ne contient généralement pas ces attributs.
            # Un objet sans état actif ne correspond pas à un filtre de mesure.
            classes, units = selected(measurement), selected(unit)
            if classes or units:
                matching = [
                    entity_id for entity_id, meta in (measurements or {}).items()
                    if (not classes or meta.get('measurement') in classes)
                    and (not units or meta.get('unit') in units)
                ]
                if matching:
                    # json_each évite la limite de paramètres SQLite si HA
                    # possède plusieurs milliers d'entités mesurées.
                    conditions.append('o.entity_id IN (SELECT value FROM json_each(?))')
                    params.append(json.dumps(matching))
                else:
                    conditions.append('0=1')
            # Les cases à cocher dépendent des compteurs calculés dans counted.
            # On les applique dans la requête externe, avant LIMIT/OFFSET.
            # Les filtres de famille/domaine sont appliqués en amont dans WHERE.
            where = ' AND '.join(conditions)
            total = db.db.execute('SELECT count(*) FROM objects o WHERE ' + where, params).fetchone()[0]
            columns = {'object_id':'object_id','name':'name','domain':'domain','floor_name':'floor_name','area_name':'area_name','depend_on_count':'depend_on_count','required_by_count':'required_by_count','missing_count':'missing_count'}
            order = columns.get(sort, 'object_id')
            direction = 'DESC' if descending else 'ASC'
            # Les compteurs fonctionnels sont séparés des liens de classement.
            # Une pièce rattachée à un étage ne dépend pas fonctionnellement de lui.
            # Le domaine Organisation HA force donc « Dépend de » à zéro.
            # En revanche, « Utilisé par » inclut les objets classés dans une pièce.
            # On ne mélange pas le nombre d'occurrences YAML avec les objets distincts.
            # La requête calcule les compteurs sans charger toutes les dépendances en Python.
            sql = f"""WITH counted AS (
                SELECT o.object_id,o.name,o.domain,o.object_type,o.source_file,o.area_name,o.floor_name,o.category_name,
                  (SELECT count(DISTINCT d.target_id) FROM dependencies d WHERE (d.source_id=o.object_id OR d.source_id=o.entity_id) AND d.reference_type NOT IN ('organisation','area','floor','category','label')) AS functional_out,
                  (SELECT count(DISTINCT d.source_id) FROM dependencies d WHERE (d.target_id=o.object_id OR d.target_id=o.entity_id) AND d.reference_type NOT IN ('organisation','area','floor','category','label')) AS functional_in,
                  (SELECT count(DISTINCT d.target_id) FROM dependencies d LEFT JOIN objects x ON x.object_id=d.target_id OR x.entity_id=d.target_id WHERE (d.source_id=o.object_id OR d.source_id=o.entity_id) AND d.reference_type NOT IN ('organisation','area','floor','category','label') AND x.object_id IS NULL) AS missing_count,
                  (CASE WHEN o.area_id IS NOT NULL AND o.domain!='area' THEN 1 ELSE 0 END) + (CASE WHEN o.category_id IS NOT NULL AND o.domain NOT IN ('category') THEN 1 ELSE 0 END) + (CASE WHEN o.floor_id IS NOT NULL AND o.domain='area' THEN 1 ELSE 0 END) AS org_out,
                  (SELECT count(*) FROM objects x WHERE (o.domain='area' AND x.area_id=substr(o.object_id,6) AND x.object_id!=o.object_id) OR (o.domain='floor' AND x.domain='area' AND x.floor_id=substr(o.object_id,7)) OR (o.domain='category' AND x.category_id=substr(o.object_id,instr(o.object_id,'.')+1+instr(substr(o.object_id,instr(o.object_id,'.')+1),'.')) AND x.object_id!=o.object_id)) AS org_in
                FROM objects o WHERE {where}
              ) SELECT *,CASE WHEN domain IN ('area','floor','category','label') THEN 0 ELSE functional_out END AS depend_on_count,
                  functional_in+CASE WHEN domain IN ('area','floor','category','label') THEN org_in ELSE 0 END AS required_by_count
              FROM counted
              WHERE (NOT ? OR missing_count > 0)
                AND (NOT ? OR functional_out = 0)
              ORDER BY {order} {direction},object_id ASC LIMIT ? OFFSET ?"""
            # Pour conserver une pagination correcte, le total doit respecter
            # exactement les mêmes filtres calculés que la requête de lignes.
            # Une sous-requête compte les résultats sans LIMIT/OFFSET.
            count_sql = sql.rsplit(' ORDER BY ', 1)[0]
            # Les deux booléens SQLite (0/1) sont liés via des paramètres.
            filtered_params = params + [int(missing_only), int(no_dependencies)]
            total = db.db.execute('SELECT COUNT(*) FROM (' + count_sql + ')', filtered_params).fetchone()[0]
            rows = db.db.execute(sql, filtered_params + [min(limit,500),offset])
            # Le vieux fichier SQLite peut ne pas posséder cette table.
            # Une analyse lancée avec cette version la créera automatiquement.
            exists = db.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='analysis_metadata'").fetchone()
            timestamp = None
            if exists:
                record = db.db.execute("SELECT value FROM analysis_metadata WHERE key='analyzed_at'").fetchone()
                timestamp = record[0] if record else None
            return {'items':[dict(r) for r in rows], 'total':total,'analyzed':True,'analyzed_at':timestamp}
        finally:
            db.close()

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
        try:
            data = build_detail(db,identifier)
            obj = data['object']; oid = obj['object_id']; domain = obj.get('domain')
            # Relations d'organisation, indépendantes des références YAML.
            links_out = []
            links_in = []
            def add(target, dest, label):
                """Ajoute un lien d'organisation seulement si la cible existe.

                La fiche doit pouvoir être ouverte depuis l'interface.
                On ignore donc les IDs de pièces/étages supprimés du registre.
                """
                if target and db.db.execute('SELECT 1 FROM objects WHERE object_id=?', (target,)).fetchone():
                    dest.append({'id':target,'file':'Registre Home Assistant','locations':[{'path':label}]})
            if domain == 'area':
                add('floor.' + obj['floor_id'] if obj.get('floor_id') else None, links_out, 'Étage')
                for r in db.db.execute('SELECT object_id FROM objects WHERE area_id=? AND object_id!=?',(oid[5:],oid)):
                    add(r[0],links_in,'Pièce')
            elif domain == 'floor':
                for r in db.db.execute("SELECT object_id FROM objects WHERE domain='area' AND floor_id=?",(oid[6:],)):
                    add(r[0],links_in,'Étage')
            elif domain == 'category':
                # Identifiant category.<portée>.<id> ; ne pas mélanger les portées.
                parts = oid.split('.',2)
                if len(parts)==3:
                    for r in db.db.execute('SELECT object_id,attributes FROM objects WHERE category_id=?',(parts[2],)):
                        attrs=json.loads(r['attributes'] or '{}')
                        if (attrs.get('categories') or {}).get(parts[1])==parts[2]:
                            add(r['object_id'],links_in,'Catégorie '+parts[1])
            else:
                add('area.' + obj['area_id'] if obj.get('area_id') else None,links_out,'Pièce')
                if obj.get('category_id'):
                    for scope in ('helpers','automation'):
                        add('category.'+scope+'.'+obj['category_id'],links_out,'Catégorie '+scope)
            data['organisation_depend_on']=links_out
            data['organisation_required_by']=links_in
            # Les propriétés du registre d'entités décrivent son identité,
            # mais les paramètres fonctionnels résident dans core.config_entries.
            # Le rattachement doit utiliser l'identifiant exact de l'entrée :
            # un capteur ``filter`` n'est pas nécessairement de domaine template.
            attrs = json.loads(db.db.execute(
                'SELECT attributes FROM objects WHERE object_id=?', (oid,)
            ).fetchone()[0] or '{}')
            entry_id = attrs.get('config_entry_id')
            if entry_id and domain not in ('automation', 'script', 'scene'):
                # Chercher par config_id, pas par nom ou domaine : cela couvre
                # filter, template et toutes les intégrations qui exposent une
                # entrée associée à l'entité dans le registre.
                entry = db.db.execute(
                    "SELECT attributes FROM objects WHERE config_id=? "
                    "AND object_type='config_entry' LIMIT 1", (entry_id,)
                ).fetchone()
                if entry:
                    settings = json.loads(entry[0] or '{}')
                    # Éviter de dupliquer le registre : conserver uniquement
                    # les paramètres qui expliquent le comportement de l'entité.
                    # Les secrets seront masqués récursivement par _redact.
                    data['configuration'] = {
                        'source': 'core.config_entries',
                        'domain': settings.get('domain'),
                        'options': settings.get('options') or {},
                        'data': settings.get('data') or {},
                    }
            if domain in ('automation', 'script', 'scene'):
                config = data.get('configuration')
                if isinstance(config, (dict, list)):
                    data['configuration_yaml'] = yaml.safe_dump(
                        self._redact(config), allow_unicode=True,
                        sort_keys=False, default_flow_style=False,
                    )
            return self._redact(data)
        finally: db.close()

    def values(self, measurements=None):
        """Valeurs de filtres et catégories par portée."""
        if not self.db_path.is_file():return {}
        db=Database(self.db_path)
        try:
            result={}
            for col in ('domain','area_name','floor_name'):
                result[col]=[r[0] for r in db.db.execute(f'SELECT DISTINCT {col} FROM objects WHERE {col} IS NOT NULL ORDER BY {col}')]
            # Un couple (étage, pièce) provient directement des objets area.
            # area.floor_id est enrichi depuis core.area_registry lors de l'analyse.
            # floor_name et area_name sont des noms affichables, pas des identifiants.
            # Le DISTINCT évite les doublons si plusieurs objets pointent vers la pièce.
            # Les pièces sans étage ne sont affichées que lorsque « Tous les étages » est choisi.
            # Le navigateur reçoit un tableau de dictionnaires simple à filtrer.
            result['floor_areas'] = [
                {'floor': row['floor_name'], 'area': row['name']}
                for row in db.db.execute("SELECT DISTINCT floor_name, name FROM objects WHERE domain = 'area' AND floor_name IS NOT NULL AND name IS NOT NULL ORDER BY floor_name, name")
            ]
            for scope in ('helpers','automation'):
                result['category_'+scope]=[r[0] for r in db.db.execute('SELECT name FROM objects WHERE object_id LIKE ? ORDER BY name',(f'category.{scope}.%',))]
            # Les valeurs proviennent des états actuels, sans inventer de
            # classe de mesure à partir du nom ou de l'unité.
            metadata = list((measurements or {}).values())
            result['measurement'] = sorted({
                m['measurement'] for m in metadata if m.get('measurement')
            })
            result['unit'] = sorted({
                m['unit'] for m in metadata if m.get('unit')
            })
            result['measurement_units'] = [
                {'measurement': measure, 'unit': unit}
                for measure, unit in sorted({
                    (m['measurement'], m['unit']) for m in metadata
                    if m.get('measurement') and m.get('unit')
                })
            ]
            return result
        finally:db.close()
