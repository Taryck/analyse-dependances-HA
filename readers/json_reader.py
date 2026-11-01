import json

def read_json(path):
    with path.open(encoding='utf-8') as f: return json.load(f)
