from ...parsers.base_parser import BaseParser

class TemplateParser(BaseParser):
    def parse(self, blocks, source_file="configuration.yaml"):
        if not isinstance(blocks,list): return
        for block in blocks:
            if not isinstance(block,dict): continue
            for domain in ('sensor','binary_sensor','switch','number','select','button','text','cover','light','fan','lock','weather'):
                entries=block.get(domain,[])
                if isinstance(entries,dict): entries=[entries]
                if not isinstance(entries,list): continue
                for item in entries:
                    if not isinstance(item,dict): continue
                    unique_id=item.get('unique_id')
                    if not unique_id:
                        self.db.error(source_file,f'Template {domain} sans unique_id : {item.get("name","?")}'); continue
                    self.add(f'template_{domain}.{unique_id}',domain,f'template_{domain}','yaml',source_file,item.get('name'),unique_id=unique_id,attributes=item)
