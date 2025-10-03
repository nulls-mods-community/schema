#!/usr/bin/env bash

# This script generates JSON schema files from CSV files located in specified folders.
# Each CSV file should have the first row as column names and the second row as data types
# (int, float, str, bool). The script creates a corresponding .schema.json file for each CSV file.

from collections import deque
import csv
import json
from pathlib import Path
from typing import Any, TypeAlias

CSV_DIRECTORY_NAME = "csv"
GENERATED_DIRECTORY_NAME = "generated"
ENHANCED_DIRECTORY_NAME = "enhanced_schemas"

PATCH_WHITELIST_UPDATE_KEYS = {"properties", "definitions"}
PATCH_WHITELIST_SET_KEYS = {"defaultSnippets", "description"}

TYPE_MAP = {"int": "integer", "float": "number", "str": "string", "bool": "boolean"}

Schema: TypeAlias = dict[str, Any]


def _csv_to_schema(csv_path: Path) -> Schema:
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        columns = next(reader)
        types = next(reader)
        example_rows = [row for row in reader]

    first_column = True
    properties = {}
    for col, typ in zip(columns, types):
        if first_column:
            first_column = False
            # First column is used as propertyNames, so we skip it here
            continue

        json_type = TYPE_MAP.get(typ.strip().lower(), "string")
        properties[col] = {"type": [json_type, "null"]}

    # Use first column values as examples for propertyNames
    property_names_examples = [row[0] for row in example_rows if row and row[0]]

    # TODO: add array values support later.
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        # Note: using $definitions to be compatible with Draft 7 tooling.
        "definitions": {
            "entries": {  # TODO: maybe rename to csv plural variant
                "type": "object",
                "propertyNames": {
                    "type": "string",
                    "examples": property_names_examples,
                },
                "additionalProperties": {"$ref": "#/definitions/entry"},
                "minProperties": 1,
            },
            "entry": {  # TODO: maybe rename to csv singular variant
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
                "minProperties": 1,
            },
        },
        "$ref": "#/definitions/entries",
    }


def _update_dict(original: dict, updates: dict) -> dict:
    if original is None:
        return updates
    
    if updates is None:
        return original

    intersected_keys: set[str] = set(original.keys()) & set(updates.keys())
    if len(intersected_keys) > 0:
        raise ValueError("Keys intersected, couldn't solve the conflict")
    
    original.update(updates)
    return original


def _merge_schemas(schema: Schema, second_schema: Schema) -> Schema:
    gen_props = (schema.get("additionalProperties", None) or {}).get("properties", {})
    patch_props = (second_schema.get("additionalProperties", None) or {}).get("properties", {})
    for prop, patch_data in patch_props.items():
        if prop in gen_props:
            gen_props[prop].update(patch_data)
        else:
            print(f"Adding new property from patch: {prop}")
            gen_props[prop] = patch_data

    if gen_props:
        schema["additionalProperties"]["properties"] = gen_props

    # Merge other top-level keys if needed (optional)
    for key, value in second_schema.items():
        if key in PATCH_WHITELIST_UPDATE_KEYS:
            if (
                key in schema
                and isinstance(schema[key], dict)
                and isinstance(value, dict)
            ):
                if "$schema" in value and key == "properties":
                    del value["$schema"]

                _update_dict(schema[key], value)
            elif (
                key in schema
                and isinstance(schema[key], list)
                and isinstance(value, list)
            ):
                schema[key].extend(value)
            else:
                schema[key] = value
        if key in PATCH_WHITELIST_SET_KEYS:
            schema[key] = value

    return schema


def _try_enhance(generated: Schema, enhanced_schema_path: Path) -> dict:
    if enhanced_schema_path.exists():
        print(f"Found enhancement for schema: {enhanced_schema_path}")
        with enhanced_schema_path.open("r", encoding="utf-8") as pf:
            patch_schema = json.load(pf)
        return _merge_schemas(generated, patch_schema)

    return generated


def _flatten_schemas(base_path: Path, *schemas: Schema) -> Schema:
    """Used for flattening the allOf notation within the schema."""

    result = {}
    for schema in schemas:
        if "$ref" in schema:
            ref_file, ref_fragment = _parse_ref(schema["$ref"])
            ref_path = base_path / Path(ref_file)
            with ref_path.open("r", encoding="utf-8") as pf:
                ref_schema = json.load(pf)

            ref_schema = _fix_refs(ref_schema, base_path, ref_path.absolute().parent)

            if ref_fragment is not None:
                result["definitions"] = _update_dict(result.get("definitions", None), ref_schema.get("definitions", None))

                for key in ref_fragment.lstrip("/").split("/"):
                    ref_schema = ref_schema[key]
            schema = ref_schema
            
        result = _merge_schemas(result, schema)
    
    return result


def _parse_ref(ref: str) -> tuple[str, str | None]:
    """Parses a $ref string into a file path and an optional fragment."""
    if "#" in ref:
        ref_file, ref_fragment = ref.split("#")
    else:
        ref_file, ref_fragment = ref, None

    return ref_file, ref_fragment


def _fix_refs(original_schema: Schema, base_path: Path, relative_path: Path) -> Schema:
    """Fixes paths in $ref directive using BFS through the schema."""

    schemas: deque[Schema] = deque()
    schemas.append(original_schema)

    while schemas:
        schema = schemas.popleft()
        for property in schema.get("properties", {}).values():
            if "$ref" not in property:
                continue
            
            ref_file, ref_fragment = _parse_ref(property["$ref"])
            
            # For local references like "#definitions/def1"
            if not ref_file:
                continue

            ref_file: Path = relative_path / ref_file
            
            relative_to_base = ref_file.relative_to(base_path).as_posix()
            if ref_fragment is not None:
                property["$ref"] = f"{relative_to_base}#{ref_fragment}"
            else:
                property["$ref"] = relative_to_base
        
        for definition in schema.get("definitions", {}).values():
            schemas.append(definition)

    return original_schema


def generate(
    csv_directory: Path,
    generated_directory: Path,
    enhanced_directory: Path | None = None,
) -> None:
    generated = {}

    for csv_file in csv_directory.glob("**/*.csv"):
        relative_path = csv_file.relative_to(csv_directory).with_suffix(".schema.json")

        schema_path = generated_directory / relative_path
        schema_path.parent.mkdir(parents=True, exist_ok=True)

        schema = _csv_to_schema(csv_file)
        if enhanced_directory is not None:
            schema = _try_enhance(schema, enhanced_directory / relative_path)

        with schema_path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, indent=4)
        print(f"Generated schema: {schema_path}")

        # Note: using relative path with forward slashes for cross-platform compatibility. Windows \\ in $ref causes issues.
        generated[csv_file.stem] = {"$ref": f"{relative_path.as_posix()}"}

    all_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "properties": generated,
    }

    all_schema_path = generated_directory / "patches.schema.json"

    if enhanced_directory is not None:
        all_schema = _try_enhance(
            all_schema, enhanced_directory / "patches.schema.json"
        )

    with all_schema_path.open("w", encoding="utf-8") as f:
        json.dump(all_schema, f, indent=4)


def generate_flatten_schema(base_schema: Path, generated_directory: Path) -> Path:
    schema_path = base_schema
    with schema_path.open("r", encoding="utf-8") as pf:
        schema = json.load(pf)
    
    all_of: list[Schema] = schema.get("allOf", [])
    schema = _merge_schemas(schema, _flatten_schemas(base_schema.parent, *all_of))
    del schema["allOf"]
    schema["additionalProperties"] = False
    
    flatten_schema_path = generated_directory / base_schema.name
    with flatten_schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=4)
    
    return flatten_schema_path


def _main() -> None:
    base = Path(__file__).parent
    csv_directory = base / CSV_DIRECTORY_NAME
    generated_directory = base / GENERATED_DIRECTORY_NAME
    enhanced_directory = base / ENHANCED_DIRECTORY_NAME

    generate(csv_directory, generated_directory, enhanced_directory)

    flatten_schema_path = generate_flatten_schema(base / "schema.json", generated_directory)
    print(f"{flatten_schema_path.as_posix()} was generated")

    flatten_schema_path = generate_flatten_schema(base / "feature.schema.json", generated_directory)
    print(f"{flatten_schema_path.as_posix()} was generated")


if __name__ == "__main__":
    _main()
