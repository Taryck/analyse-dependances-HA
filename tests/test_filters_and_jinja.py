"""Régressions pour les variables Jinja et les filtres multiples."""
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name, folder in [
    ('custom_components', ROOT / 'custom_components'),
    ('custom_components.dependency_graph', ROOT / 'custom_components/dependency_graph'),
]:
    package = types.ModuleType(name)
    package.__path__ = [str(folder)]
    sys.modules.setdefault(name, package)

from custom_components.dependency_graph.analyzer.database import Database
from custom_components.dependency_graph.analyzer.dependencies.all_objects import references
from custom_components.dependency_graph.service import GraphService


class FilterAndJinjaTests(unittest.TestCase):
    def test_variable_used_as_entity_reference(self):
        state = """{% set s = 'binary_sensor.ballon_250_en_marche' %}
{% if is_state(s, 'on') %}
{{ ((now() - states[s].last_changed).total_seconds() / 60) | round(0) }}
{% else %}0{% endif %}"""
        self.assertIn(
            ('binary_sensor.ballon_250_en_marche', 'jinja'),
            references(state, 'state'),
        )
        self.assertEqual(
            references("{% set label = 'sensor.unused' %} {{ label }}", 'state'),
            [],
        )

    def test_multiple_filters_and_measurement(self):
        with tempfile.TemporaryDirectory() as temp:
            service = GraphService(temp)
            service.storage.mkdir()
            db = Database(service.db_path)
            for entity, name, floor in (
                ('sensor.chauffage_temps', 'Chauffage Temps', 'RDC'),
                ('sensor.chauffage_puissance', 'Chauffage Puissance', 'RDC'),
                ('sensor.autre_temps', 'Autre Temps', 'Étage'),
            ):
                db.add({
                    'object_id': entity, 'entity_id': entity, 'domain': 'sensor',
                    'object_type': 'entity', 'source_type': 'json',
                    'source_file': 'core.entity_registry', 'name': name,
                    'floor_name': floor, 'attributes': {},
                })
            db.commit()
            db.close()
            metadata = {
                'sensor.chauffage_temps': {'measurement': 'duration', 'unit': 's'},
                'sensor.chauffage_puissance': {'measurement': 'power', 'unit': 'W'},
                'sensor.autre_temps': {'measurement': 'duration', 'unit': 's'},
            }
            result = service.list_objects(
                query='chauffage temps', domain=['sensor'],
                floor=['RDC', 'Étage'], measurements=metadata,
            )
            self.assertEqual(result['total'], 1)
            self.assertEqual(result['items'][0]['object_id'], 'sensor.chauffage_temps')
            result = service.list_objects(
                domain=['sensor'], measurement=['power'], unit=['W'],
                measurements=metadata,
            )
            self.assertEqual(result['total'], 1)
            self.assertEqual(result['items'][0]['object_id'], 'sensor.chauffage_puissance')
            values = service.values(measurements=metadata)
            self.assertIn({'measurement': 'power', 'unit': 'W'}, values['measurement_units'])


if __name__ == '__main__':
    unittest.main()
