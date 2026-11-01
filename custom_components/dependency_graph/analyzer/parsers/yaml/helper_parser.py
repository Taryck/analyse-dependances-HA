from ...parsers.base_parser import BaseParser
from ...readers.include_resolver import ORIGIN

class MappingParser(BaseParser):
    def parse(self, domain, entries, source_file="configuration.yaml"):
        # Une section vide ou ignorée par le résolveur n'est pas une erreur.
        if entries is None or entries == {} or entries == []:
            return
        if not isinstance(entries, dict):
            self.db.error('configuration.yaml', f'{domain} doit être un dictionnaire')
            return
        for key, item in entries.items():
            if key == ORIGIN or not isinstance(item, dict):
                continue
            self.add(f'{domain}.{key}', domain, domain, 'yaml', source_file,
                     item.get('name') or item.get('alias'), config_id=key,
                     unique_id=item.get('unique_id'), attributes=item)
