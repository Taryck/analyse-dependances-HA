"""Tests de non-régression Lovelace sans démarrer Home Assistant."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name, folder in [
    ("custom_components", root / "custom_components"),
    ("custom_components.dependency_graph", root / "custom_components/dependency_graph"),
]:
    module = types.ModuleType(name)
    module.__path__ = [str(folder)]
    sys.modules.setdefault(name, module)

from custom_components.dependency_graph.analyzer.database import Database
from custom_components.dependency_graph.analyzer.dashboard import scan_dashboards
from custom_components.dependency_graph.analyzer.detail import build_detail


class DashboardTests(unittest.TestCase):
    def test_storage_dashboard_and_functional_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = root / ".storage"
            storage.mkdir()
            (storage / "lovelace_dashboards").write_text(json.dumps({
                "data": {"items": [{"url_path": "maison", "title": "Maison"}]}
            }))
            (storage / "lovelace.maison").write_text(json.dumps({
                "data": {"config": {"views": [{
                    "title": "Salon", "cards": [
                        {"type": "entities", "entities": [
                            "sensor.temperature_salon",
                            {"entity": "switch.lampe"}
                        ]},
                        {"type": "button", "entity": "light.salon",
                         "tap_action": {"action": "toggle",
                                        "target": {"entity_id": ["switch.lampe"]}}},
                        {"type": "custom:button-card",
                         "name": "[[[ return states['sensor.temperature_salon'].state; ]]]"}
                    ]
                }]}}
            }))
            global_file = storage / "global.yaml"
            global_file.write_text("{}")
            db = Database(storage / "index.db")
            try:
                db.add({"object_id": "sensor.temperature_salon", "domain": "sensor",
                        "object_type": "entity", "entity_id": "sensor.temperature_salon",
                        "source_file": "test", "attributes": {}})
                count = scan_dashboards(root, db, global_file)
                db.commit()
                self.assertEqual(count, 5)
                details = build_detail(db, "sensor.temperature_salon")
                self.assertEqual(details["required_by"][0]["id"], "dashboard.maison")
                dashboard = build_detail(db, "dashboard.maison")
                self.assertEqual({entry["id"] for entry in dashboard["depend_on"]},
                                 {"sensor.temperature_salon", "switch.lampe", "light.salon"})
                self.assertIn("Salon", details["required_by"][0]["locations"][0]["path"])
            finally:
                db.close()

    def test_yaml_dashboard_and_include(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".storage").mkdir()
            (root / "views").mkdir()
            (root / "views/salon.yaml").write_text(
                "title: Salon\ncards:\n  - type: entity\n    entity: sensor.salon\n"
            )
            (root / "dashboard.yaml").write_text(
                "title: Appartement\nviews:\n  - !include views/salon.yaml\n"
            )
            global_file = root / ".storage/global.yaml"
            global_file.write_text(
                "lovelace:\n  dashboards:\n    appartement:\n"
                "      mode: yaml\n      title: Appartement\n"
                "      filename: dashboard.yaml\n"
            )
            db = Database(root / ".storage/index.db")
            try:
                self.assertEqual(scan_dashboards(root, db, global_file), 1)
                self.assertEqual(db.db.execute(
                    "SELECT target_id FROM dependencies").fetchone()[0], "sensor.salon")
            finally:
                db.close()

    def test_normal_text_not_an_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = root / ".storage"
            storage.mkdir()
            (storage / "lovelace").write_text(json.dumps({
                "data": {"config": {"views": [{"cards": [
                    {"type": "markdown", "content": "Le fichier sensor.exemple est cité"},
                    {"type": "entity", "entity": "sensor.reel"}
                ]}]}}
            }))
            global_file = storage / "global.yaml"
            global_file.write_text("{}")
            db = Database(storage / "index.db")
            try:
                self.assertEqual(scan_dashboards(root, db, global_file), 1)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
