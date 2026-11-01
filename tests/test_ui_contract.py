"""Tests de contrat : champs consommés par le panneau et produits par Python."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / 'custom_components' / 'dependency_graph'

class UiContractTests(unittest.TestCase):
    def test_panel_name_and_manifest(self):
        manifest = json.loads((COMP/'manifest.json').read_text())
        panel = (COMP/'frontend/panel.js').read_text()
        setup = (COMP/'__init__.py').read_text()
        self.assertEqual(manifest['iot_class'], 'local_polling')
        self.assertIn('panel.js', setup)
        self.assertIn('customElements.define', panel)

    def test_ui_controls_have_handlers(self):
        panel = (COMP/'frontend/panel.js').read_text()
        for name in ('family','domain','scope','category','floor','area',
                     'missing-only','no-dependencies','analyze','prev','next'):
            self.assertIn('id="'+name+'"', panel)
            self.assertIn("this.$('"+name+"')", panel)

    def test_filter_response_contract(self):
        panel = (COMP/'frontend/panel.js').read_text()
        service = (COMP/'service.py').read_text()
        for key in ('domain','floor_name','area_name','floor_areas',
                    'category_helpers','category_automation'):
            self.assertIn(key, panel)
            if key.startswith('category_'):
                self.assertIn("'category_'+scope", service)
            else:
                self.assertIn(key, service)

    def test_list_response_contract(self):
        panel = (COMP/'frontend/panel.js').read_text()
        service = (COMP/'service.py').read_text()
        for key in ('object_id','name','floor_name','area_name','depend_on_count',
                    'required_by_count','missing_count','analyzed_at'):
            self.assertIn(key, panel)
            self.assertIn(key, service)

    def test_detail_and_source_contract(self):
        panel = (COMP/'frontend/panel.js').read_text()
        service = (COMP/'service.py').read_text()
        for key in ('organisation_depend_on','organisation_required_by',
                    'depend_on','required_by','configuration_yaml'):
            self.assertIn(key, panel)
            self.assertIn(key, service)
        self.assertIn('yaml.safe_dump', service)
        self.assertIn("document.createElement('details')", panel)

if __name__ == '__main__':
    unittest.main()
