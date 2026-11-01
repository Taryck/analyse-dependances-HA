from parsers.base_parser import BaseParser

HELPERS=('input_boolean','input_button','input_datetime','input_number','input_select','input_text')

class HelperJsonParser(BaseParser):
    def parse(self,payload,filename):
        data=payload.get('data',{})
        entries=data if isinstance(data,list) else data.get('items',[]) if isinstance(data,dict) else []
        if not isinstance(entries,list):
            self.db.error(filename,'Structure JSON des helpers inattendue'); return
        for item in entries:
            if not isinstance(item,dict): continue
            config_id=item.get('id')
            if not config_id:
                self.db.error(filename,'Helper sans id'); continue
            # L'id de stockage n'est pas nécessairement l'entity_id.
            entity_id=item.get('entity_id')
            object_id=entity_id or f'{filename}_config.{config_id}'
            self.add(object_id,filename,'helper','json',filename,item.get('name'),config_id=config_id,entity_id=entity_id,unique_id=item.get('unique_id'),attributes=item)
