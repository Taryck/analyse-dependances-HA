"""Tests exécutables sans installer Home Assistant."""
import json
import tempfile
import unittest
from pathlib import Path
# Charge les modules métier sans importer __init__.py de l'intégration HA.
import sys, types
root=Path(__file__).resolve().parents[1]
for name,folder in [('custom_components',root/'custom_components'),('custom_components.dependency_graph',root/'custom_components/dependency_graph')]:
    package=types.ModuleType(name)
    package.__path__=[str(folder)]
    sys.modules.setdefault(name,package)
from custom_components.dependency_graph.analyzer.database import Database
from custom_components.dependency_graph.analyzer.detail import build_detail
from custom_components.dependency_graph.service import GraphService

class IntegrationEngineTests(unittest.TestCase):
    def test_database_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Database(str(Path(tmp)/'test.db'))
            try:
                db.add({'object_id':'sensor.test','domain':'sensor','object_type':'entity','source_type':'json','source_file':'core.entity_registry','name':'Essai','entity_id':'sensor.test','attributes':{}})
                db.db.execute('INSERT INTO dependencies(source_id,target_id,source_file,yaml_path,reference_type) VALUES (?,?,?,?,?)',('sensor.test','sensor.absent','core.config_entries','template_config.X.options.state','jinja'))
                db.commit()
                detail=build_detail(db,'sensor.test')
                self.assertEqual(detail['depend_on'][0]['id'],'sensor.absent')
                self.assertTrue(detail['depend_on'][0]['missing'])
                self.assertEqual(detail['depend_on'][0]['file'],'core.config_entries')
            finally:db.close()

    def test_service_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=GraphService(tmp)
            self.assertFalse(service.list_objects()['analyzed'])

    def test_secret_redaction(self):
        result=GraphService._redact({'options':{'api_token':'private','state':'{{ states("sensor.test") }}'}})
        self.assertEqual(result['options']['api_token'],'[MASQUÉ]')
        self.assertIn('sensor.test',result['options']['state'])
