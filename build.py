import json
import shutil
from pathlib import Path

from generate import (
    CSV_DIRECTORY_NAME,
    ENHANCED_DIRECTORY_NAME,
    GENERATED_DIRECTORY_NAME,
    generate,
)

BUILD_DIRECTORY_NAME = "build"


def _minify_schema(schema_path: Path, output_path: Path) -> None:
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, separators=(",", ":"))


def _main() -> None:
    base = Path(__file__).parent

    build_dir = base / BUILD_DIRECTORY_NAME
    shutil.rmtree(build_dir, ignore_errors=True)
    build_dir.unlink(missing_ok=True)

    for schema_file in base.glob("*.schema.json"):
        _minify_schema(schema_file, build_dir / schema_file.relative_to(base))

    temp_build_dir = base / f"{BUILD_DIRECTORY_NAME}_tmp"

    try:
        generate(
            base / CSV_DIRECTORY_NAME,
            temp_build_dir / GENERATED_DIRECTORY_NAME,
            base / ENHANCED_DIRECTORY_NAME,
        )

        for schema_file in temp_build_dir.glob("**/*.schema.json"):
            _minify_schema(
                schema_file, build_dir / schema_file.relative_to(temp_build_dir)
            )
    finally:
        shutil.rmtree(temp_build_dir, ignore_errors=True)
        temp_build_dir.unlink(missing_ok=True)

    print(
        f"✅ Done! The minified schema build is available in the {BUILD_DIRECTORY_NAME}/ directory."
    )


if __name__ == "__main__":
    _main()
