from .automation_parser import AutomationParser
from .helper_parser import MappingParser
from .template_parser import TemplateParser
from readers.include_resolver import ORIGIN

DOMAINS = ('script','scene','input_boolean','input_number','input_text','input_select',
           'input_datetime','input_button','counter','timer','schedule','group')

def parse_yaml(data, db):
    if not isinstance(data, dict):
        db.error('configuration.yaml', 'Racine YAML invalide')
        return
    for domain, entries in data.items():
        if domain == ORIGIN:
            continue
        if isinstance(entries, dict) and ORIGIN in entries and 'contenu' in entries:
            source = entries[ORIGIN]
            entries = entries['contenu']
        else:
            source = 'configuration.yaml'
        if domain == 'automation':
            AutomationParser(db).parse(entries, source)
        elif domain == 'template':
            TemplateParser(db).parse(entries, source)
        elif domain in DOMAINS:
            MappingParser(db).parse(domain, entries, source)
