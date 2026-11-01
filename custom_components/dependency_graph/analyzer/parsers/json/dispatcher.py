from ...readers.json_reader import read_json
from .entity_registry_parser import EntityRegistryParser
from .registry_parser import RegistryParser,REGISTRIES
from .helper_parser import HelperJsonParser,HELPERS
from .config_entries_parser import ConfigEntriesParser

def parse_storage(root,db,verbose=False):
    storage=root/'.storage'
    for filename in ('core.entity_registry','core.config_entries','core.device_registry',*REGISTRIES,*HELPERS):
        path=storage/filename
        if not path.is_file():
            if verbose: print(f'[ABSENT] {path}')
            continue
        try:
            payload=read_json(path)
            if filename=='core.entity_registry': EntityRegistryParser(db).parse(payload,filename)
            elif filename=='core.config_entries': ConfigEntriesParser(db).parse(payload,filename)
            elif filename=='core.device_registry':
                db.device_areas = {d.get('id'):d.get('area_id') for d in payload.get('data',{}).get('devices',[]) if isinstance(d,dict)}
            elif filename in REGISTRIES: RegistryParser(db).parse(payload,filename)
            else: HelperJsonParser(db).parse(payload,filename)
            if verbose: print(f'[LU] {path}')
        except Exception as exc: db.error(str(path),str(exc))
