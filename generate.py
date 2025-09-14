# This script generates JSON schema files from CSV files located in specified folders.
# Each CSV file should have the first row as column names and the second row as data types
# (int, float, str, bool). The script creates a corresponding .schema.json file for each CSV file.

import csv
import json
from pathlib import Path

CSV_FOLDERS = ["csv_logic", "csv_client", "localization"]
BASE_DIR = Path(__file__).parent
SCHEMAS_DIR = BASE_DIR / "schemas"
ENHANCED_SCHEMAS_DIR = BASE_DIR / "enhanced_schemas"

PATCH_WHITELIST_UPDATE_KEYS = {"properties"}
PATCH_WHITELIST_SET_KEYS = {"defaultSnippets", "description"}

TYPE_MAP = {
    "int": "integer",
    "float": "number",
    "str": "string",
    "bool": "boolean"
}

def csv_to_schema(csv_path: Path) -> dict:
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
                    "examples": property_names_examples
                },
                "additionalProperties": {"$ref": "#/definitions/entry"},
                "minProperties": 1
            }, 
            "entry": {  # TODO: maybe renamt to csv singular variant
                "type": "object", 
                "properties": properties, 
                "additionalProperties": False, 
                "minProperties": 1
            }
        },
        "$ref": "#/definitions/entries"
    }


def merge_schemas(generated: dict, patch: dict) -> dict:
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
            if key in generated and isinstance(generated[key], dict) and isinstance(value, dict):
                generated[key].update(value)
            else:
                generated[key] = value
        if key in PATCH_WHITELIST_SET_KEYS:
            generated[key] = value

    return generated


def try_enhance(generated: dict, schema_file: Path, enhanced_path: Path) -> dict:
    patch_path = enhanced_path / schema_file.name
    print(f"Looking for patch: {patch_path}")
    if patch_path.exists():
        with patch_path.open("r", encoding="utf-8") as pf:
            patch_schema = json.load(pf)
        return merge_schemas(generated, patch_schema)

    return generated


def main():
    generated = {}

    for folder in CSV_FOLDERS:
        folder_path = BASE_DIR / folder
        folder_output = SCHEMAS_DIR / folder
        folder_output.mkdir(exist_ok=True)

        enhanced_path = ENHANCED_SCHEMAS_DIR / folder

        if not folder_path.exists():
            continue
        for csv_file in folder_path.glob("*.csv"):
            schema = csv_to_schema(csv_file)

            schema_file = csv_file.with_suffix(".schema.json")

            schema = try_enhance(schema, schema_file, enhanced_path)

            schema_path = folder_output / schema_file.name
            with schema_path.open("w", encoding="utf-8") as f:
                json.dump(schema, f, indent=4)
            print(f"Generated schema: {schema_path}")

            # Note: using relative path with forward slashes for cross-platform compatibility. Windows \\ in $ref causes issues.
            generated[csv_file.stem] = {"$ref": f"{schema_path.relative_to(SCHEMAS_DIR).as_posix()}#/definitions/entries"}
    
    all_schema = {"$schema": "http://json-schema.org/draft-07/schema#", "properties": generated}
    
    all_schema_path = SCHEMAS_DIR / "all.schema.json"

    all_schema = try_enhance(all_schema, all_schema_path, ENHANCED_SCHEMAS_DIR)
    with all_schema_path.open("w", encoding="utf-8") as f:
        json.dump(all_schema, f, indent=4)


if __name__ == "__main__":
    main()
