from ...parsers.base_parser import BaseParser

class EntityRegistryParser(BaseParser):
    def parse(self, payload, filename):
        for item in payload.get('data',{}).get('entities',[]):
            entity_id=item.get('entity_id')
            if not entity_id:
                self.db.error(filename,'Entité sans entity_id'); continue
            domain=entity_id.split('.',1)[0]
            self.add(entity_id,domain,'automation' if domain == 'automation' else 'entity','json',filename,item.get('name') or item.get('original_name'),entity_id=entity_id,unique_id=item.get('unique_id'),attributes=item)
