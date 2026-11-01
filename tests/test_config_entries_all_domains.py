"""Régressions pour les entrées HA non-Template et leurs dépendances."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name, folder in [('custom_components', ROOT/'custom_components'), ('custom_components.dependency_graph', ROOT/'custom_components/dependency_graph')]:
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(folder)]
    sys.modules.setdefault(name, pkg)

from custom_components.dependency_graph.analyzer.database import Database
from custom_components.dependency_graph.analyzer.parsers.json.config_entries_parser import ConfigEntriesParser
from custom_components.dependency_graph.analyzer.dependencies.all_objects import scan_all
from custom_components.dependency_graph.service import GraphService


class ConfigEntriesRegression(unittest.TestCase):
    """Reproduit une configuration Filter avec moyenne mobile de 24 heures."""

    def test_filter_and_shared_entries(self):
        """Vérifie affichage, dépendances et associations multi-entités."""
        with tempfile.TemporaryDirectory() as tmp:
            service = GraphService(tmp)
            service.storage.mkdir()
            db = Database(service.db_path)
            for entity in ('sensor.sdb_rdc_humidity_moy', 'sensor.second_filter'):
                db.add({'object_id':entity, 'domain':'sensor', 'object_type':'entity',
                        'source_type':'json','source_file':'core.entity_registry',
                        'entity_id':entity, 'name':entity,
                        'attributes':{'config_entry_id':'FILTER_1'}})
            db.add({'object_id':'sensor.temp_sdb_rdc_humidity', 'domain':'sensor',
                    'object_type':'entity','source_type':'json','source_file':'core.entity_registry',
                    'entity_id':'sensor.temp_sdb_rdc_humidity','attributes':{}})
            ConfigEntriesParser(db).parse({'data':{'entries':[
                {'entry_id':'FILTER_1','domain':'filter','title':'Filtered sensor',
                 'data':{},'options':{'entity_id':'sensor.temp_sdb_rdc_humidity',
                 'filter':'time_simple_moving_average',
                 'window_size':{'hours':24,'minutes':0,'seconds':0},
                 'password':'DO_NOT_SEND'}},
                {'entry_id':'TEMPLATE_1','domain':'template','options':{'state':'{{ states("sensor.temp_sdb_rdc_humidity") }}'}},
            ]}}, 'core.config_entries')
            self.assertEqual(db.db.execute("SELECT count(*) FROM objects WHERE object_type='config_entry'").fetchone()[0],2)
            config = service.storage/'test_global.yaml'
            config.write_text('{}',encoding='utf8')
            scan_all(Path(tmp),db,config)
            db.close()
            for entity in ('sensor.sdb_rdc_humidity_moy','sensor.second_filter'):
                detail=service.detail(entity)
                self.assertEqual(detail['configuration']['options']['window_size']['hours'],24)
                self.assertEqual(detail['configuration']['options']['password'],'[MASQUÉ]')
                self.assertEqual(detail['configuration']['domain'],'filter')
                self.assertIn('sensor.temp_sdb_rdc_humidity',[x['id'] for x in detail['depend_on']])
                self.assertEqual(service.list_objects(query=entity)['items'][0]['depend_on_count'],1)

if __name__ == '__main__':
    unittest.main()
