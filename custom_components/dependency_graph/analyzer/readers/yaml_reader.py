from pathlib import Path
import yaml
from .include_resolver import load_config

def build_global(root, output_path=None):
    data = load_config(root)
    output = Path(output_path) if output_path else Path(__file__).resolve().parents[1] / 'global_configuration.yaml'
    output.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False),encoding='utf-8')
    # Relecture effective avec PyYAML du fichier assemblé.
    return yaml.safe_load(output.read_text(encoding='utf-8'))
