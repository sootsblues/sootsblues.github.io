#!/usr/bin/env python3
"""Check that the Pages CMS settings (.pages.yml) describe every field in content/.

Pages CMS only shows the fields listed in .pages.yml. If a content file has a field the
settings don't list, students can't see or edit it. So whenever you add a field to build.py,
add it to .pages.yml too and run:

    pip install pyyaml
    python3 tools/check_editor_config.py
"""
import copy, json, os, sys

try:
    import yaml
except ImportError:
    sys.exit("This check needs PyYAML. Install it with: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = yaml.safe_load(open(os.path.join(ROOT, ".pages.yml"), encoding="utf-8"))
COMPONENTS = config.get("components") or {}
errors = []

def resolve(field):
    """Fill in `component:` references the way Pages CMS does."""
    field = copy.deepcopy(field)
    name = field.get("component")
    if name:
        if name not in COMPONENTS:
            errors.append(f".pages.yml: unknown component {name!r}")
            return field
        base = copy.deepcopy(COMPONENTS[name])
        base.update({k: v for k, v in field.items() if k != "component"})
        base["type"] = COMPONENTS[name].get("type", "object")
        field = base
    if field.get("fields") and not field.get("type"):
        field["type"] = "object"
    if "fields" in field:
        field["fields"] = [resolve(f) for f in field["fields"]]
    if "blocks" in field:
        field["blocks"] = [resolve(b) for b in field["blocks"]]
    return field

def check_value(value, field, where):
    if value is None:  # an emptied field; the build treats it as empty
        return
    if field.get("list"):
        if not isinstance(value, list):
            errors.append(f"{where}: should be a list")
            return
        for i, v in enumerate(value):
            check_single(v, field, f"{where}[{i}]")
    else:
        check_single(value, field, where)

def check_single(value, field, where):
    t = field.get("type")
    if value is None:
        return
    if t == "object":
        if not isinstance(value, dict):
            errors.append(f"{where}: should be a group of fields")
            return
        check_fields(value, field.get("fields") or [], where)
    elif t == "block":
        key = field.get("blockKey", "_block")
        blocks = {b["name"]: b for b in field.get("blocks") or []}
        if not isinstance(value, dict):
            errors.append(f"{where}: should be a section")
            return
        kind = value.get(key)
        if kind not in blocks:
            errors.append(f"{where}: section kind {kind!r} is not listed under {field['name']!r} in .pages.yml")
            return
        check_fields({k: v for k, v in value.items() if k != key}, blocks[kind].get("fields") or [], f"{where} ({kind})")
    elif isinstance(value, (dict, list)):
        errors.append(f"{where}: is a {type(value).__name__}, but .pages.yml calls it {t}")

def check_fields(data, fields, where):
    known = {f["name"]: f for f in fields}
    for k, v in data.items():
        if k not in known:
            errors.append(f"{where}: field {k!r} is not in .pages.yml, so Pages CMS would not show it")
        else:
            check_value(v, known[k], f"{where}.{k}")

def entries(items):
    for e in items:
        if e.get("type") == "group":
            yield from entries(e.get("items") or [])
        else:
            yield e

checked = set()
for e in entries(config.get("content") or []):
    fields = [resolve(f) for f in e.get("fields") or []]
    if e["type"] == "file":
        paths = [e["path"]]
    else:
        folder = os.path.join(ROOT, e["path"])
        paths = [os.path.join(e["path"], n) for n in sorted(os.listdir(folder))
                 if n.endswith(".json") and n not in (e.get("exclude") or [])]
    for p in paths:
        checked.add(os.path.normpath(p))
        check_fields(json.load(open(os.path.join(ROOT, p), encoding="utf-8")), fields, p)

for folder in ("content", "content/pages"):
    for n in sorted(os.listdir(os.path.join(ROOT, folder))):
        p = os.path.normpath(os.path.join(folder, n))
        if n.endswith(".json") and p not in checked:
            errors.append(f"{p}: no entry in .pages.yml covers this file, so Pages CMS would not show it")

if errors:
    print("\n".join(errors))
    sys.exit(f"\n{len(errors)} problem(s) between .pages.yml and content/")
print(f"OK: .pages.yml covers every field in {len(checked)} content files")
