"""Config entries : seules les entrées Template utiles aux dépendances sont conservées.
Ne pas copier les secrets des autres intégrations dans SQLite.
"""
from ...parsers.base_parser import BaseParser

class ConfigEntriesParser(BaseParser):
    def parse(self, payload, filename):
        for entry in payload.get('data',{}).get('entries',[]):
            if not isinstance(entry,dict) or entry.get('domain')!='template':
                continue
            entry_id=entry.get('entry_id')
            if not entry_id: continue
            attrs={'entry_id':entry_id,'domain':'template',
                   'options':entry.get('options') or {},
                   'title':entry.get('title')}
            self.add('template_config.'+entry_id,'template','template_config',
                     'json',filename,entry.get('title'),config_id=entry_id,attributes=attrs)
