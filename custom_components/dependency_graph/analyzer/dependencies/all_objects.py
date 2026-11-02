"""Dépendances statiques : YAML analysé, commentaires exclus; Template UI JSON."""
import json
import re
from pathlib import Path
import yaml
ENTITY = re.compile(r'^[a-z_][a-z0-9_]*\.[a-z0-9_]+$',re.I)
JINJA_COMMENT = re.compile(r'{#.*?#}',re.S)
JINJA_BLOCK = re.compile(r'({{.*?}}|{%.*?%})', re.S)
JINJA_REF = re.compile(r"(?:states|is_state|is_state_attr|state_attr|has_value|expand)\s*\(\s*['\"]([a-z_][a-z0-9_]*\.[a-z0-9_]+)['\"]",re.I)
# Variables Jinja affectées à un identifiant d'entité littéral.
# On ne crée un lien que si la variable est ensuite utilisée comme référence
# d'état (states[var], is_state(var, ...), state_attr(var, ...)).
JINJA_SET = re.compile(r"{%\s*set\s+([a-z_][a-z0-9_]*)\s*=\s*['\\"]([a-z_][a-z0-9_]*\.[a-z0-9_]+)['\\"]\s*%}", re.I)
JINJA_VARIABLE_USE = re.compile(r"(?:states\s*\[\s*{v}\s*\]|(?:is_state|is_state_attr|state_attr|has_value|expand|states)\s*\(\s*{v}\s*[,\)])", re.I)
JINJA_DOT = re.compile(r'\bstates\.([a-z_][a-z0-9_]*)\.([a-z0-9_]+)',re.I)
DIRECT = {'entity_id','entity','source','above','below','at'}
SKIP = {'fichier_d_origine','alias','description','name','icon','action','service','trigger','condition','device_id','area_id','label_id','domain','platform','unique_id','id'}

def references(value,key):
    if not isinstance(value,str):return []
    if key in DIRECT and ENTITY.fullmatch(value.strip()):return [(value.strip(),'direct')]
    if '{{' not in value and '{%' not in value:return []
    # Ne garder que les blocs exécutables, sans les commentaires Jinja.
    value=' '.join(JINJA_BLOCK.findall(JINJA_COMMENT.sub('',value)))
    refs=[(m.group(1),'jinja') for m in JINJA_REF.finditer(value)]
    # Exemple : {% set s = 'binary_sensor.ballon_250_en_marche' %}
    #           {{ states[s].last_changed }} ou {% if is_state(s, 'on') %}.
    # Une simple chaîne affectée à une variable non utilisée ne constitue
    # pas une dépendance : vérifier une utilisation fonctionnelle.
    for match in JINJA_SET.finditer(value):
        variable, entity_id = match.groups()
        use = JINJA_VARIABLE_USE.pattern.format(v=re.escape(variable))
        if re.search(use, value[match.end():], re.I):
            refs.append((entity_id, 'jinja'))
    refs += [(m.group(1)+'.'+m.group(2),'jinja') for m in JINJA_DOT.finditer(value)]
    return list(dict.fromkeys(refs))

def scan_all(root,db,global_path=None):
    path=Path(global_path) if global_path else Path(__file__).resolve().parents[1]/'global_configuration.yaml'
    data=yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    db.db.execute('DELETE FROM dependencies')
    count=0
    def walk(value,source,filename,location,key=None):
        nonlocal count
        if isinstance(value,dict):
            for k,v in value.items():
                if k not in SKIP:walk(v,source,filename,location+'.'+str(k),k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,source,filename,f'{location}[{i}]',key)
        else:
            for target,kind in references(value,key):
                cur=db.db.execute('INSERT OR IGNORE INTO dependencies (source_id,target_id,source_file,yaml_path,reference_type) VALUES (?,?,?,?,?)',(source,target,filename,location,kind))
                count+=cur.rowcount
    def canonical(domain,uid,fallback):
        row=db.db.execute('SELECT entity_id FROM objects WHERE domain=? AND (unique_id=? OR config_id=?) AND entity_id IS NOT NULL LIMIT 1',(domain,str(uid),str(uid))).fetchone()
        return row['entity_id'] if row else fallback
    for section,content in data.items():
        if not isinstance(content,(dict,list)):continue
        filename='configuration.yaml'
        if isinstance(content,dict) and 'contenu' in content:
            filename=content.get('fichier_d_origine') or filename
            content=content['contenu']
        if section=='automation' and isinstance(content,list):
            for i,item in enumerate(content):
                if isinstance(item,dict):
                    uid=item.get('id')
                    walk(item,canonical('automation',uid,f'automation_config.{uid}'),filename,f'automation[{i}]')
        elif section=='template' and isinstance(content,list):
            for i,block in enumerate(content):
                if not isinstance(block,dict):continue
                for domain,items in block.items():
                    if domain not in ('sensor','binary_sensor','switch','number','select','button','text','cover','light') or not isinstance(items,list):continue
                    for j,item in enumerate(items):
                        if not isinstance(item,dict):continue
                        uid=item.get('unique_id')
                        if not uid:continue
                        source=canonical(domain,uid,f'template_{domain}.{uid}')
                        walk({k:v for k,v in block.items() if k not in ('sensor','binary_sensor','switch','number','select','button','text','cover','light')},source,filename,f'template[{i}].shared')
                        walk(item,source,filename,f'template[{i}].{domain}[{j}]')
        elif section in ('script','scene') and isinstance(content,dict):
            for key,item in content.items():
                if isinstance(item,dict):walk(item,f'{section}.{key}',filename,f'{section}.{key}')
    # Parcourir toutes les entrées de configuration, pas seulement Template.
    # Une entrée filter, par exemple, contient son capteur source dans options.
    # Plusieurs entités peuvent partager la même entrée : chaque entité doit
    # recevoir les références qui la concernent, sans dupliquer les objets.
    for row in list(db.db.execute("SELECT * FROM objects WHERE object_type='config_entry'")):
        attrs = json.loads(row['attributes'] or '{}')
        entry_id = attrs.get('entry_id')
        if not entry_id:
            continue
        entities = list(db.db.execute(
            "SELECT entity_id FROM objects WHERE entity_id IS NOT NULL "
            "AND json_extract(attributes,'$.config_entry_id')=?", (entry_id,)
        ))
        sources = [entity['entity_id'] for entity in entities] or [row['object_id']]
        for source in sources:
            # Les champs options et data peuvent tous deux contenir des entités.
            # Le parcours existant extrait les identifiants directs et Jinja.
            # Il ignore les champs de gestion non fonctionnels du registre.
            for section in ('options', 'data'):
                walk(attrs.get(section) or {}, source, 'core.config_entries',
                     f'config_entry.{entry_id}.{section}')
    db.commit()
    return count
