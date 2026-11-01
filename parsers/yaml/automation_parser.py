from parsers.base_parser import BaseParser

class AutomationParser(BaseParser):
    def parse(self, entries, source_file="configuration.yaml"):
        if entries is None or entries == {} or entries == []:
            return
        if not isinstance(entries, list):
            self.db.error('configuration.yaml', 'automation doit être une liste')
            return
        for item in entries:
            if not isinstance(item, dict):
                continue
            config_id = item.get('id')
            if config_id is None:
                self.db.error(source_file, f"Automatisation sans id : {item.get('alias','?')}")
                continue
            self.add(f'automation_config.{config_id}', 'automation', 'automation',
                     'yaml', source_file, item.get('alias'),
                     config_id=config_id, attributes=item)
