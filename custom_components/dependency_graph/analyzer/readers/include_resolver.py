"""Résolution de !include, en conservant la provenance des déclarations.

Le marqueur fichier_d_origine est une clé YAML ordinaire, lisible par PyYAML.
Il est ajouté aux objets inclus (pas aux sous-dictionnaires d'actions).
"""
from pathlib import Path
import yaml

ORIGIN = 'fichier_d_origine'


def load_config(root):
    root = Path(root).resolve()
    active = []

    def load(path):
        path = path.resolve()
        if path in active:
            raise ValueError('Include circulaire : ' + ' -> '.join(map(str, active + [path])))
        if not path.is_relative_to(root):
            raise ValueError(f'Include hors configuration : {path}')
        active.append(path)
        try:
            class Loader(yaml.SafeLoader):
                pass

            def include(loader, node):
                target = (path.parent / loader.construct_scalar(node)).resolve()
                result = load(target)
                source = target.relative_to(root).as_posix()
                # Une seule métadonnée par !include, au niveau de la section.
                # Le contenu garde exactement sa structure initiale sous "contenu".
                return {ORIGIN: source, 'contenu': result}

            def ignored(loader, suffix, node):
                loader.construct_scalar(node)
                return {}

            Loader.add_constructor('!include', include)
            Loader.add_constructor('!secret', lambda loader, node: '!secret ' + loader.construct_scalar(node))
            Loader.add_multi_constructor('!include_dir_', ignored)
            with path.open(encoding='utf-8') as stream:
                return yaml.load(stream, Loader=Loader)
        finally:
            active.pop()

    return load(root / 'configuration.yaml')
