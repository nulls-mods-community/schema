# This script generates JSON schema files from CSV files located in specified folders.
# Each CSV file should have the first row as column names and the second row as data types
# (int, float, str, bool). The script creates a corresponding .schema.json file for each CSV file.

import csv
import json
from pathlib import Path

CSV_FOLDERS = ["csv_logic", "csv_client", "localization"]
BASE_DIR = Path(__file__).parent
SCHEMAS_DIR = BASE_DIR / "schemas"
SCHEMAS_DIR.mkdir(exist_ok=True)

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
        properties[col] = {"type": json_type}

    # Use first column values as examples for propertyNames
    property_names_examples = [row[0] for row in example_rows if row and row[0]]

    # TODO: add array values support later.
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": properties,
        # "required": list(properties.keys()),
        "propertyNames": {
            "type": "string",
            "examples": property_names_examples
        },
        "minProperties": 1
    }


def main():
    for folder in CSV_FOLDERS:
        folder_path = BASE_DIR / folder
        folder_output = SCHEMAS_DIR / folder
        folder_output.mkdir(exist_ok=True)

        if not folder_path.exists():
            continue
        for csv_file in folder_path.glob("*.csv"):
            schema = csv_to_schema(csv_file)
            schema_file = csv_file.with_suffix(".schema.json")
            schema_path = folder_output / schema_file.name
            with schema_path.open("w", encoding="utf-8") as f:
                json.dump(schema, f, indent=4)
            print(f"Generated schema: {schema_path}")


if __name__ == "__main__":
    main()
