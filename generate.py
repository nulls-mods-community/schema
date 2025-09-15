#!/usr/bin/env bash

# This script generates JSON schema files from CSV files located in specified folders.
# Each CSV file should have the first row as column names and the second row as data types
# (int, float, str, bool). The script creates a corresponding .schema.json file for each CSV file.

import csv
import json
from pathlib import Path

CSV_DIRECTORY_NAME = "csv"
GENERATED_DIRECTORY_NAME = "generated"
ENHANCED_DIRECTORY_NAME = "enhanced_schemas"

PATCH_WHITELIST_UPDATE_KEYS = {"properties"}
PATCH_WHITELIST_SET_KEYS = {"defaultSnippets", "description"}

TYPE_MAP = {"int": "integer", "float": "number", "str": "string", "bool": "boolean"}


def _csv_to_schema(csv_path: Path) -> dict:
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


def _merge_schemas(generated: dict, patch: dict) -> dict:
    gen_props = generated.get("additionalProperties", {}).get("properties", {})
    patch_props = patch.get("additionalProperties", {}).get("properties", {})
    for prop, patch_data in patch_props.items():
        if prop in gen_props:
            gen_props[prop].update(patch_data)
        else:
            print(f"Adding new property from patch: {prop}")
            gen_props[prop] = patch_data

    if gen_props:
        generated["additionalProperties"]["properties"] = gen_props

    # Merge other top-level keys if needed (optional)
    for key, value in patch.items():
        if key in PATCH_WHITELIST_UPDATE_KEYS:
            if (
                key in generated
                and isinstance(generated[key], dict)
                and isinstance(value, dict)
            ):
                generated[key].update(value)
            else:
                generated[key] = value
        if key in PATCH_WHITELIST_SET_KEYS:
            generated[key] = value

    return generated


def _try_enhance(generated: dict, enhanced_schema_path: Path) -> dict:
    if enhanced_schema_path.exists():
        print(f"Found enhancement for schema: {enhanced_schema_path}")
        with enhanced_schema_path.open("r", encoding="utf-8") as pf:
            patch_schema = json.load(pf)
        return _merge_schemas(generated, patch_schema)

    return generated


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


def _main() -> None:
    base = Path(__file__).parent
    csv_directory = base / CSV_DIRECTORY_NAME
    generated_directory = base / GENERATED_DIRECTORY_NAME
    enhanced_directory = base / ENHANCED_DIRECTORY_NAME

    generate(csv_directory, generated_directory, enhanced_directory)


if __name__ == "__main__":
    _main()
