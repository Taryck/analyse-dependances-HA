"""Inventaire et dépendances des dashboards Lovelace (lecture seule).

Les dashboards sont des sources fonctionnelles distinctes dans le graphe.
Les structures générées par stratégie ne permettent pas de connaître
statiquement toutes les entités affichées.
"""
import json
import re
from pathlib import Path
import yaml

from .dependencies.all_objects import ENTITY, references

# En dehors des champs explicitement structurés, la recherche est réservée
# aux templates (Jinja et JS des custom cards) pour limiter les faux positifs.
ENTITY_TOKEN = re.compile(r"(?<![a-zA-Z0-9_])([a-z_][a-z0-9_]*\.[a-z0-9_]+)(?![a-zA-Z0-9_])", re.I)
TEMPLATE_HINT = re.compile(r"{{|{%|\[\[\[|\bstates\s*\[|\bhass\.states\b")
SINGLE_KEYS = {
    "entity", "entity_id", "camera_entity", "camera_image_entity",
    "weather", "sun_entity", "person", "sensor", "source",
    "target_entity", "active_entity", "inactive_entity",
}
LIST_KEYS = {"entities", "entity_ids", "exclude_entities"}
SKIP_KEYS = {"icon", "url", "image", "image_url", "navigation_path", "tap_action",
             "hold_action", "double_tap_action"}
STORAGE_PREFIX = "lovelace."


def _read_json(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("data", payload)


def _read_dashboard_yaml(path, root, active=None):
    """Lit les includes Lovelace sans jamais écrire dans la configuration."""
    path, root = Path(path).resolve(), Path(root).resolve()
    active = [] if active is None else active
    if not path.is_relative_to(root):
        raise ValueError("Include Lovelace hors répertoire config")
    if path in active:
        raise ValueError("Include Lovelace circulaire")
    active.append(path)
    try:
        class Loader(yaml.SafeLoader):
            pass

        def include(loader, node):
            target = (path.parent / loader.construct_scalar(node)).resolve()
            return _read_dashboard_yaml(target, root, active)

        def directory(loader, suffix, node):
            folder = (path.parent / loader.construct_scalar(node)).resolve()
            if not folder.is_relative_to(root):
                raise ValueError("Répertoire Lovelace hors configuration")
            docs = [_read_dashboard_yaml(p, root, active)
                    for p in sorted(folder.glob("*.yaml")) if p.is_file()]
            if suffix == "merge_list":
                return [value for doc in docs if isinstance(doc, list) for value in doc]
            if suffix == "merge_named":
                merged = {}
                for doc in docs:
                    if isinstance(doc, dict):
                        merged.update(doc)
                return merged
            if suffix == "named":
                return {p.stem: _read_dashboard_yaml(p, root, active)
                        for p in sorted(folder.glob("*.yaml")) if p.is_file()}
            return docs

        Loader.add_constructor("!include", include)
        Loader.add_constructor("!secret", lambda loader, node: None)
        Loader.add_multi_constructor("!include_dir_", directory)
        return yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)
    finally:
        active.pop()


def _extract(value, key):
    if not isinstance(value, str):
        return []
    refs = list(references(value, key))
    if key in SINGLE_KEYS or key in LIST_KEYS:
        for match in ENTITY_TOKEN.finditer(value):
            token = match.group(1)
            if ENTITY.fullmatch(token):
                refs.append((token, "dashboard"))
    elif TEMPLATE_HINT.search(value):
        for match in ENTITY_TOKEN.finditer(value):
            token = match.group(1)
            if ENTITY.fullmatch(token):
                refs.append((token, "dashboard_template"))
    return list(dict.fromkeys(refs))


def _links(db, source, filename, config):
    count = 0
    def walk(value, path, key=None):
        nonlocal count
        if isinstance(value, dict):
            for k, child in value.items():
                # Les actions peuvent contenir des cibles entity_id :
                # ne PAS ignorer les sous-arbres tap_action / hold_action.
                if k in {"icon", "url", "image", "image_url", "navigation_path"}:
                    continue
                walk(child, f"{path}.{k}" if path else str(k), str(k))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", key)
        elif isinstance(value, str):
            for target, kind in _extract(value, key):
                cur = db.db.execute(
                    "INSERT OR IGNORE INTO dependencies "
                    "(source_id,target_id,source_file,yaml_path,reference_type) "
                    "VALUES (?,?,?,?,?)",
                    (source, target, filename, path, kind))
                count += cur.rowcount
    walk(config, "")
    return count


def scan_dashboards(root, db, global_path):
    """Ajoute les dashboards comme objets et leurs liens dans dependencies."""
    root = Path(root)
    storage = root / ".storage"
    metadata = {}
    metadata_path = storage / "lovelace_dashboards"
    if metadata_path.is_file():
        try:
            data = _read_json(metadata_path)
            for row in data.get("items", []):
                if isinstance(row, dict):
                    metadata[str(row.get("url_path") or "lovelace")] = row
        except (ValueError, OSError) as exc:
            db.error(str(metadata_path), str(exc))

    configs = {}
    for path in sorted(storage.glob("lovelace*")):
        if not path.is_file() or path.name in {"lovelace_dashboards", "lovelace_resources"}:
            continue
        if path.name != "lovelace" and not path.name.startswith(STORAGE_PREFIX):
            continue
        slug = path.name[len(STORAGE_PREFIX):] if path.name.startswith(STORAGE_PREFIX) else "lovelace"
        try:
            data = _read_json(path)
            config = data.get("config")
            if isinstance(config, dict):
                configs[slug] = (config, path.name, "storage")
        except (ValueError, OSError) as exc:
            db.error(path.name, str(exc))

    # Les fichiers YAML des tableaux déclarés dans configuration.yaml.
    try:
        global_data = yaml.safe_load(Path(global_path).read_text(encoding="utf-8")) or {}
        lovelace = global_data.get("lovelace") or {}
        if isinstance(lovelace, dict) and "contenu" in lovelace:
            lovelace = lovelace["contenu"]
        dashboards = lovelace.get("dashboards", {}) if isinstance(lovelace, dict) else {}
        for slug, spec in dashboards.items():
            if not isinstance(spec, dict) or spec.get("mode") != "yaml" or not spec.get("filename"):
                continue
            try:
                filename = spec["filename"]
                config = _read_dashboard_yaml(root / filename, root)
                if isinstance(config, dict):
                    configs[str(slug)] = (config, filename, "yaml")
                metadata[str(slug)] = {**metadata.get(str(slug), {}), **spec}
            except (ValueError, OSError, yaml.YAMLError) as exc:
                db.error(str(spec["filename"]), str(exc))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        db.error(str(global_path), str(exc))

    count = 0
    for slug, (config, filename, mode) in configs.items():
        details = metadata.get(slug, {})
        source = f"dashboard.{slug}"
        views = config.get("views") or []
        view_titles = {
            str(i): view.get("title") or view.get("path") or f"Vue {i+1}"
            for i, view in enumerate(views) if isinstance(view, dict)
        }
        attrs = {
            "url_path": slug, "mode": mode, "view_titles": view_titles,
            "strategy": config.get("strategy"),
        }
        db.add({
            "object_id": source, "domain": "dashboard", "object_type": "dashboard",
            "source_type": mode, "source_file": filename,
            "name": details.get("title") or config.get("title") or slug,
            "attributes": attrs,
        })
        count += _links(db, source, filename, config)
    return count
