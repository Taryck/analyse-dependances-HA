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

class InterfaceFiltersTests(unittest.TestCase):
    """Vérifie les règles métier qui alimentent les colonnes de l'interface."""

    def test_organisation_not_counted_as_functional_dependency(self):
        """Une pièce compte comme rattachement, pas comme dépendance fonctionnelle."""
        with tempfile.TemporaryDirectory() as tmp:
            service = GraphService(tmp)
            service.storage.mkdir(parents=True, exist_ok=True)
            db = Database(service.db_path)
            db.add({'object_id':'floor.rdc','domain':'floor','object_type':'floor','source_type':'json','source_file':'core.floor_registry','name':'RDC','attributes':{}})
            db.add({'object_id':'area.salon','domain':'area','object_type':'area','source_type':'json','source_file':'core.area_registry','name':'Salon','attributes':{'floor_id':'rdc'}})
            db.add({'object_id':'sensor.test','domain':'sensor','object_type':'entity','source_type':'json','source_file':'core.entity_registry','name':'Test','entity_id':'sensor.test','attributes':{'area_id':'salon'}})
            db.db.execute("UPDATE objects SET floor_id='rdc',floor_name='RDC' WHERE object_id='area.salon'")
            db.db.execute("UPDATE objects SET area_id='salon',area_name='Salon',floor_name='RDC' WHERE object_id='sensor.test'")
            # Cette référence simule un lien de classement présent dans la table.
            # Elle ne doit pas devenir une dépendance fonctionnelle.
            db.db.execute("INSERT INTO dependencies(source_id,target_id,source_file,yaml_path,reference_type) VALUES (?,?,?,?,?)", ('sensor.test','area.salon','core.entity_registry','area_id','organisation'))
            db.commit()
            db.close()
            result=service.list_objects()
            by_id={item['object_id']:item for item in result['items']}
            self.assertEqual(by_id['sensor.test']['depend_on_count'],0)
            self.assertEqual(by_id['area.salon']['depend_on_count'],0)
            self.assertEqual(by_id['area.salon']['required_by_count'],1)
            self.assertEqual(by_id['floor.rdc']['required_by_count'],1)
            self.assertEqual(service.list_objects(no_dependencies=True)['total'],3)
            self.assertEqual(service.list_objects(missing_only=True)['total'],0)

    def test_floor_filters_areas(self):
        """La liste des pièces doit provenir du registre, avec l'étage réel."""
        with tempfile.TemporaryDirectory() as tmp:
            service = GraphService(tmp)
            service.storage.mkdir(parents=True, exist_ok=True)
            db = Database(service.db_path)
            for oid, name, floor in [('area.salon','Salon','RDC'),('area.chambre','Chambre','1er')]:
                db.add({'object_id':oid,'domain':'area','object_type':'area',
                        'source_type':'json','source_file':'core.area_registry',
                        'name':name,'attributes':{}})
                db.db.execute('UPDATE objects SET floor_name=? WHERE object_id=?', (floor,oid))
            db.commit()
            db.close()
            values = service.values()
            self.assertIn({'floor':'RDC','area':'Salon'},values['floor_areas'])
            self.assertIn({'floor':'1er','area':'Chambre'},values['floor_areas'])
            self.assertNotIn({'floor':'RDC','area':'Chambre'},values['floor_areas'])
