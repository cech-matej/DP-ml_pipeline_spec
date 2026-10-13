"""Validate YAML configs against independently maintained schemas in schemas/config/."""

from pathlib import Path
import argparse, sys, yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "config"
DEFAULT_CONFIG_DIR = ROOT / "config"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="YAML files or directories; defaults to config/")
    args = parser.parse_args()
    schema_by_root = {}

    for path in sorted(SCHEMA_DIR.glob("*.schema.yaml")):
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
        root_key = schema.get("x-config-root-key")

        if not root_key:
            print(f"ERROR {path}: missing x-config-root-key", file=sys.stderr)
            return 2
        
        if root_key in schema_by_root:
            print(f"ERROR duplicate schema root key: {root_key}", file=sys.stderr)
            return 2

        schema_by_root[root_key] = (path, schema)
    
    if not schema_by_root:
        print(f"ERROR no schemas found in {SCHEMA_DIR}", file=sys.stderr)
        return 2

    inputs = [Path(p) for p in args.paths] if args.paths else [DEFAULT_CONFIG_DIR]
    files=[]

    for item in inputs:
        if item.is_dir():
            files.extend(p for p in item.rglob("*.yaml") if p.is_file())
        elif item.is_file():
            files.append(item)
        else:
            print(f"ERROR path does not exist: {item}", file=sys.stderr)
            return 2

    failed=0
    for file in sorted(set(files)):
        try:
            data=yaml.safe_load(file.read_text(encoding="utf-8"))

        except Exception as exc:
            print(f"FAIL {file}: YAML parse error: {exc}")
            failed+=1
            continue

        if not isinstance(data, dict):
            print(f"FAIL {file}: document must be a YAML mapping")
            failed+=1
            continue

        # Choose the schema whose required top-level fields best match the document.
        # This is schema-driven: some configs (for example a phase manifest) may
        # legitimately contain a nested/adjacent section named like another config root.
        ranked=[]

        for key, (schema_path, schema) in schema_by_root.items():
            required=set(schema.get("required", []))

            if key in data:
                ranked.append((len(required.intersection(data)), key, schema_path, schema))

        if not ranked:
            print(f"FAIL {file}: no discovered schema root key matches document keys {list(data)}")
            failed+=1
            continue

        ranked.sort(reverse=True, key=lambda item: item[0])

        if len(ranked)>1 and ranked[0][0]==ranked[1][0]:
            print(f"FAIL {file}: ambiguous schema match between {ranked[0][1]} and {ranked[1][1]}")
            failed+=1
            continue

        _, key, schema_path, schema=ranked[0]

        errors=sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(map(str,e.absolute_path)))

        # For versioned artefacts, enforce that directory vN agrees with the
        # version field inside the corresponding root object. The check is generic.
        version_dir = file.parent.name if file.parent.name.startswith("v") and file.parent.name[1:].isdigit() else None

        if version_dir and isinstance(data.get(key), dict):
            body_version = data[key].get("version")

            if body_version is None:
                errors.append(ValidationError(f"versioned path {version_dir} requires {key}.version"))

            elif str(body_version) != version_dir[1:]:
                errors.append(ValidationError(f"path version {version_dir} does not match {key}.version={body_version}"))

        if errors:
            failed += 1

            for err in errors:
                loc=".".join(map(str,err.absolute_path)) or "<root>"
                print(f"FAIL {file} [{schema_path.name}] {loc}: {err.message}")

        else:
            print(f"OK   {file} [{schema_path.name}]")

    print(f"\nValidated {len(set(files))} file(s); failures: {failed}")

    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
