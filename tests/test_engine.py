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

    def test_reconcile_config_objects_and_unused_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = GraphService(tmp)
            service.storage.mkdir(parents=True, exist_ok=True)
            db = Database(service.db_path)
            db.add({'object_id':'input_datetime.heure_fin_hc','domain':'input_datetime',
                    'object_type':'entity','entity_id':'input_datetime.heure_fin_hc',
                    'source_file':'core.entity_registry','attributes':{}})
            db.add({'object_id':'input_datetime_config.heure_fin_hc','domain':'input_datetime',
                    'object_type':'helper','source_file':'input_datetime',
                    'config_id':'heure_fin_hc','attributes':{'name':'Heure fin HC'}})
            db.add({'object_id':'sensor.existant','domain':'sensor','object_type':'entity',
                    'entity_id':'sensor.existant','source_file':'core.entity_registry',
                    'attributes':{'config_entry_id':'entry-1'}})
            db.add({'object_id':'config_entry.entry-1','domain':'filter','object_type':'config_entry',
                    'config_id':'entry-1','source_file':'core.config_entries',
                    'attributes':{'entry_id':'entry-1','domain':'filter',
                                  'options':{'entity_id':'sensor.source'}}})
            db.add({'object_id':'sensor.source','domain':'sensor','object_type':'entity',
                    'entity_id':'sensor.source','source_file':'core.entity_registry','attributes':{}})
            db.add({'object_id':'sensor.inutile','domain':'sensor','object_type':'entity',
                    'entity_id':'sensor.inutile','source_file':'core.entity_registry','attributes':{}})
            db.db.execute("INSERT INTO dependencies (source_id,target_id,source_file,yaml_path,reference_type) VALUES (?,?,?,?,?)",
                          ('sensor.existant','sensor.source','core.config_entries','options.entity_id','direct'))
            db.reconcile_config_objects()
            db.commit()
            self.assertIsNone(db.db.execute(
                "SELECT 1 FROM objects WHERE object_id='config_entry.entry-1'").fetchone())
            self.assertIsNone(db.db.execute(
                "SELECT 1 FROM objects WHERE object_id='input_datetime_config.heure_fin_hc'").fetchone())
            db.close()
            data = service.list_objects()
            self.assertEqual(data['total'], 4)
            unused = {row['object_id'] for row in service.list_objects(no_dependencies=True)['items']}
            self.assertIn('sensor.inutile', unused)
            self.assertIn('input_datetime.heure_fin_hc', unused)
            self.assertNotIn('sensor.existant', unused)
            self.assertNotIn('sensor.source', unused)
            self.assertEqual(service.detail('sensor.existant')['configuration']['source'],
                             'core.config_entries')
            self.assertEqual(service.detail('input_datetime.heure_fin_hc')['configuration']['data']['name'],
                             'Heure fin HC')

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
