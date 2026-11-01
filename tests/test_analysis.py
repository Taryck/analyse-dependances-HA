# -*- coding: utf-8 -*-
"""Tests hors Home Assistant : aucune connexion ni modification du serveur.

Chaque test crée un export HA miniature dans un répertoire temporaire,
exécute la même CLI que l'utilisateur et vérifie la base SQLite résultante.
Les données fictives disparaissent à la fin du test.
"""
import json
from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        # Un répertoire isolé empêche les tests d'altérer les données réelles.
        self.tmp = tempfile.TemporaryDirectory()
        # Sous Windows, SQLite verrouille le fichier tant que la connexion
        # reste ouverte. Les connexions de vérification sont donc toujours
        # fermées explicitement via contextlib.closing (voir les tests).
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ha = self.root / 'ha'
        self.ha.mkdir()
        (self.ha / '.storage').mkdir()
        (self.ha / 'configuration.yaml').write_text(
            'automation: !include automations.yaml\ntemplate: !include templates.yaml\n', encoding='utf-8')
        (self.ha / 'automations.yaml').write_text('''- id: '123'
  alias: Sécurité Halogène SdB Parent
  description: "sensor.commentaire_ignore"
  triggers:
  - trigger: state
    alias: Déclenchement humidité
    entity_id: sensor.reel
  conditions:
  - condition: state
    alias: Vérifier humidité
    entity_id: sensor.reel
    state: 'on'
  actions:
  - action: switch.turn_on
    alias: Allumer lampe
    target:
      entity_id: switch.lampe
  # entity_id: sensor.ancien
  - variables:
      expression: >-
        {# states('sensor.jinja_commentaire') #}
        {{ states('sensor.jinja_reel') }}
''', encoding='utf-8')
        (self.ha / 'templates.yaml').write_text('''- sensor:
  - name: Capteur calculé
    unique_id: calc_1
    state: >-
      {{ states('sensor.entree') | float(0) }}
      {# states('sensor.faux') #}
''', encoding='utf-8')
        self.db = self.root / 'test.db'

    def cli(self, *args):
        # Exécution réelle du programme, pas un appel direct aux fonctions.
        return subprocess.run([sys.executable, str(ROOT / 'main.py'), *map(str, args)],
                              cwd=self.root, encoding='utf-8', capture_output=True)

    def test_analysis_and_comments(self):
        result = self.cli('analize', self.ha, '--db', self.db)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with closing(sqlite3.connect(self.db)) as con, con:
            refs = {(r[0], r[1]) for r in con.execute(
                'SELECT source_id,target_id FROM dependencies')}
            self.assertIn(('automation_config.123', 'sensor.reel'), refs)
            self.assertIn(('automation_config.123', 'switch.lampe'), refs)
            self.assertIn(('automation_config.123', 'sensor.jinja_reel'), refs)
            self.assertIn(('template_sensor.calc_1', 'sensor.entree'), refs)
            for ignored in ('sensor.ancien', 'sensor.commentaire_ignore',
                            'sensor.jinja_commentaire', 'sensor.faux'):
                self.assertNotIn(ignored, {r[1] for r in refs})
        self.assertFalse((self.ha / 'global_configuration.yaml').exists())
        self.assertEqual((ROOT / 'global_configuration.yaml').read_text(
            encoding='utf-8').count('fichier_d_origine:'), 2)
        detail = self.cli('detail', 'automation_config.123', '--db', self.db)
        self.assertEqual(detail.returncode, 0, detail.stderr)
        parsed = json.loads(detail.stdout)
        self.assertEqual(parsed['object']['name'], 'Sécurité Halogène SdB Parent')
        self.assertIn('depend_on', parsed)
        self.assertIn('required_by', parsed)
        self.assertEqual(self.cli('analize', self.ha, '--db', self.db).returncode, 0)
        # Régression Windows : après les lectures SQLite, le fichier doit
        # pouvoir être renommé, puis supprimé par TemporaryDirectory.
        moved = self.db.with_suffix('.renamed')
        self.db.rename(moved)
        moved.rename(self.db)

    def test_grouped_locations_and_aliases(self):
        self.assertEqual(self.cli('analize', self.ha, '--db', self.db).returncode, 0)
        result = self.cli('detail', 'sensor.reel', '--db', self.db)
        # sensor.reel n'est pas inventorié : on insère un objet registre fictif.
        # Cela vérifie la présentation des dépendances entrantes.
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute('''INSERT INTO objects(object_id,domain,object_type,source_type,
                        source_file,name,entity_id,attributes) VALUES(?,?,?,?,?,?,?,?)''',
                        ('sensor.reel', 'sensor', 'entity', 'json', 'core.entity_registry',
                         'Capteur réel', 'sensor.reel', '{}'))
        result = self.cli('detail', 'reel', '--db', self.db)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data['required_by']), 1)
        locations = data['required_by'][0]['locations']
        self.assertEqual(len(locations), 2)
        self.assertTrue(any('Déclenchement humidité' in x['path'] for x in locations))
        self.assertTrue(any('Vérifier humidité' in x['path'] for x in locations))
        self.assertTrue(all('automation[' not in x['path'] for x in locations))

    def test_categories_and_values(self):
        # Deux catégories de même nom mais de portées différentes.
        categories = {'data': {'categories': {
            'helpers': [{'category_id': 'h1', 'name': 'Tempo'}],
            'automation': [{'category_id': 'a1', 'name': 'Tempo'}]}}}
        entities = {'data': {'entities': [{
            'entity_id': 'sensor.exemple', 'unique_id': 'sensor1',
            'categories': {'helpers': 'h1'}, 'name': 'Exemple'}]}}
        storage = self.ha / '.storage'
        (storage / 'core.category_registry').write_text(json.dumps(categories), encoding='utf-8')
        (storage / 'core.entity_registry').write_text(json.dumps(entities), encoding='utf-8')
        result = self.cli('analize', self.ha, '--db', self.db)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        values = self.cli('values', '--db', self.db)
        self.assertIn('Tempo', values.stdout)
        detail = self.cli('detail', 'sensor.exemple', '--db', self.db)
        self.assertEqual(json.loads(detail.stdout)['object']['category_name'], 'Tempo')
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(con.execute("SELECT count(*) FROM objects WHERE domain='category'").fetchone()[0], 2)

    def test_help_and_ambiguous_identifier(self):
        self.assertEqual(self.cli('objects_list', '--', 'help').returncode, 0)
        self.assertIn('analize', self.cli().stdout)
        self.assertEqual(self.cli('analize', self.ha, '--db', self.db).returncode, 0)
        result = self.cli('detail', 'absent_inconnu', '--db', self.db)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()

class V8OutputTests(AnalysisTests):
    """Tests de non-régression des changements de présentation V8."""

    def test_wildcard_and_missing_and_compact_locations(self):
        self.assertEqual(self.cli('analize', self.ha, '--db', self.db).returncode, 0)
        result = self.cli('detail', '*calc*1*', '--db', self.db)
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed['object']['object_id'], 'template_sensor.calc_1')
        dep = next(x for x in parsed['depend_on'] if x['id'] == 'sensor.entree')
        self.assertTrue(dep['missing'])
        self.assertEqual(set(dep['locations'][0]), {'path'})
        self.assertIn('file', dep)

    def test_category_scopes_separated(self):
        storage = self.ha / '.storage'
        (storage / 'core.category_registry').write_text(json.dumps({'data': {'categories': {
            'helpers': [{'category_id': 'h1', 'name': 'Tempo'}],
            'automation': [{'category_id': 'a1', 'name': 'Tempo'}]
        }}}), encoding='utf-8')
        self.assertEqual(self.cli('analize', self.ha, '--db', self.db).returncode, 0)
        values = self.cli('values', '--db', self.db).stdout
        self.assertIn('Catégories assistants (helpers) : Tempo', values)
        self.assertIn('Catégories automatisations : Tempo', values)
