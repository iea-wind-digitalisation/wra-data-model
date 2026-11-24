"""Generate the Pydantic data model from the IEA Wind WRA Data Model JSON Schema.

The model is produced by `datamodel-code-generator` and is not edited by hand. Two
constraints expressed in the JSON Schema cannot be emitted by the generator, so they are
applied here as deterministic post-generation patches:

1. `uniqueItems` on arrays, which the generator silently drops. The schema requires
   duplicate items to fail validation rather than be quietly accepted.
2. `description` and `title` on properties that are a bare `$ref` carrying a default. The
   generator omits both for that shape.
3. `SCHEMA_VERSION`, taken from the schema's own `$version` key. The generator translates
   only `properties` and `definitions`, so schema-level metadata is not carried across.

Each patch asserts that it changed at least one site. If a generator upgrade moves or
removes a site, generation fails loudly instead of silently producing a weaker model.

Run from this directory with `poetry run poe generate`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
SCHEMA = REPO_ROOT / "schema" / "iea43_wra_data_model.schema.json"
OUTPUT = HERE / "wra_data_model_pydantic" / "model.py"

# Pinned generator flags. Changing any of these changes the committed model, so the CI
# sync check will fail until the model is regenerated and reviewed.
CODEGEN_FLAGS = [
    "--input-file-type",
    "jsonschema",
    "--output-model-type",
    "pydantic_v2.BaseModel",
    "--target-python-version",
    "3.11",
    "--use-annotated",
    "--use-standard-collections",
    "--use-union-operator",
    "--use-schema-description",
    "--use-field-description",
    # The WRA Data Model carries timestamps without a UTC offset, because the offset is a
    # separate `offset_from_utc_hrs` field. The generator's default of AwareDatetime would
    # reject every timestamp in the demo data.
    "--output-datetime-class",
    "datetime",
    # Inline single-value definitions such as `notes` and `date_from` so they are plain
    # str/datetime values rather than wrapper objects requiring `.root` to read.
    "--collapse-root-models",
    "--set-default-enum-member",
    # Keep output byte-identical between runs so the sync check is meaningful.
    "--disable-timestamp",
]

UNIQUE_LIST_HELPER = '''

T = TypeVar("T")


def _validate_unique_list(value: list[T]) -> list[T]:
    """Reject arrays whose items are not unique, as required by uniqueItems in the schema."""
    seen: set[str] = set()
    for item in value:
        key = item.model_dump_json() if isinstance(item, BaseModel) else repr(item)
        if key in seen:
            raise PydanticCustomError("unique_list", "List items must be unique")
        seen.add(key)
    return value


UniqueList = Annotated[list[T], AfterValidator(_validate_unique_list)]
'''


def load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def unique_item_properties(schema: dict) -> set[str]:
    """Return the names of every property whose array declares uniqueItems true."""
    names: set[str] = set()

    def walk(node: object, parent: str | None = None) -> None:
        if isinstance(node, dict):
            if node.get("uniqueItems") is True and parent:
                names.add(parent)
            for key, value in node.items():
                walk(value, key)
        elif isinstance(node, list):
            for value in node:
                walk(value, parent)

    walk(schema)
    return names


def ref_descriptions(schema: dict, wanted: set[str]) -> dict[str, tuple[str, str]]:
    """Resolve the title and description of the named properties through any ref."""
    definitions = schema["definitions"]
    resolved: dict[str, tuple[str, str]] = {}

    def resolve(node: dict) -> dict:
        while isinstance(node, dict) and "$ref" in node:
            node = definitions[node["$ref"].split("/")[-1]]
        return node

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    for name, prop in value.items():
                        if name in wanted and name not in resolved:
                            target = resolve(prop)
                            resolved[name] = (
                                target.get("title", ""),
                                target.get("description", ""),
                            )
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return resolved


def patch_unique_lists(source: str, names: set[str]) -> str:
    """Wrap the annotation of every uniqueItems array in UniqueList."""
    patched = 0
    unmatched: list[str] = []
    for name in sorted(names):
        # A property whose name collides with a Pydantic attribute is emitted by the
        # generator with a trailing underscore and an alias, e.g. `model_config` becomes
        # `model_config_`. Try both spellings.
        for candidate in (name, f"{name}_"):
            pattern = re.compile(rf"^(    {re.escape(candidate)}: Annotated\[\s*)list\[", re.MULTILINE)
            source, count = pattern.subn(r"\1UniqueList[", source)
            patched += count
            if count:
                break
        else:
            unmatched.append(name)

    if unmatched:
        raise SystemExit(
            "uniqueItems patch could not find these array fields in the generated model, so "
            "duplicate items would be silently accepted: " + ", ".join(unmatched)
        )

    source = source.replace(
        "from pydantic import BaseModel, ConfigDict, Field",
        "from pydantic import AfterValidator, BaseModel, ConfigDict, Field\n"
        "from pydantic_core import PydanticCustomError",
    )
    source = source.replace("from typing import Annotated", "from typing import Annotated, TypeVar")

    first_class = source.index("\nclass ")
    source = source[:first_class] + UNIQUE_LIST_HELPER + source[first_class:]
    print(f"  uniqueItems: wrapped {patched} of {len(names)} array field(s)")
    return source


def patch_schema_version(source: str, version: str) -> str:
    """Record the schema version the model was generated from, as a module constant.

    The code generator only translates `properties` and `definitions` into Python, so the
    schema's own `$version` key is not carried across. Downstream code needs it to report a
    mismatch between the model and a data model file declaring a different version.
    """
    anchor = "from pydantic_core import PydanticCustomError\n"
    if anchor not in source:
        raise SystemExit("schema version patch could not find the import block")
    constant = (
        anchor
        + "\n"
        + "# The version of the WRA Data Model JSON Schema this model was generated from, taken\n"
        + '# from the schema\'s own "$version" key. It is updated when the schema version is\n'
        + "# raised at release and the model regenerated.\n"
        + f'SCHEMA_VERSION = "{version}"\n'
    )
    source = source.replace(anchor, constant, 1)
    print(f"  schema version: recorded SCHEMA_VERSION = {version}")
    return source


def sync_package_version(schema_version: str) -> None:
    """Align the package version in pyproject.toml with the schema version.

    The package and the schema describe the same thing, so they carry one version rather
    than two. The schema version also encodes the release month, as in `1.4.0-2025.06`,
    which is not a valid Python package version, so the package takes the `MAJOR.MINOR.PATCH`
    part and the full value is available to code as `SCHEMA_VERSION`.
    """
    package_version = schema_version.split("-", 1)[0]
    pyproject = HERE / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")

    pattern = re.compile(r'^(name = "wra-data-model-pydantic"\nversion = ")([^"]*)(")', re.MULTILINE)
    match = pattern.search(content)
    if match is None:
        raise SystemExit("could not find the package version in pyproject.toml")

    if match.group(2) != package_version:
        content = pattern.sub(rf"\g<1>{package_version}\g<3>", content, count=1)
        pyproject.write_text(content, encoding="utf-8")
        print(f"  package version: raised to {package_version} to match the schema")
    else:
        print(f"  package version: already {package_version}")


def patch_ref_descriptions(source: str, descriptions: dict[str, tuple[str, str]]) -> str:
    """Restore title and description on bare ref fields that carry a default."""
    patched = 0
    for name, (title, description) in sorted(descriptions.items()):
        pattern = re.compile(rf"^    {re.escape(name)}: ([A-Z][A-Za-z0-9]*) \| None = (.+)$", re.MULTILINE)

        def replace(
            match: re.Match[str],
            name: str = name,
            title: str = title,
            description: str = description,
        ) -> str:
            type_name, default = match.group(1), match.group(2)
            return (
                f"    {name}: Annotated[\n"
                f"        {type_name} | None, Field(title={json.dumps(title)})\n"
                f"    ] = {default}\n"
                f'    """\n'
                f"    {description}\n"
                f'    """'
            )

        source, count = pattern.subn(replace, source)
        if count:
            print(f"  descriptions: {name} patched at {count} site(s)")
        patched += count

    if patched == 0:
        raise SystemExit("description patch matched nothing - generator output has changed shape")
    return source


def main() -> int:
    schema = load_schema()

    print("Generating model from", SCHEMA.relative_to(REPO_ROOT))
    # Invoke the tools as modules of the running interpreter rather than as bare console
    # scripts, so generation does not depend on the virtual environment being on PATH.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(SCHEMA),
            *CODEGEN_FLAGS,
            "--output",
            str(OUTPUT),
        ],
        check=True,
    )

    source = OUTPUT.read_text(encoding="utf-8")
    print("Applying post-generation patches:")
    source = patch_unique_lists(source, unique_item_properties(schema))

    schema_version = schema.get("$version")
    if not schema_version:
        raise SystemExit('the JSON Schema has no "$version" key to record in the model')
    source = patch_schema_version(source, schema_version)
    sync_package_version(schema_version)

    bare_ref_fields = set(re.findall(r"^    ([a-z_0-9]+): [A-Z][A-Za-z0-9]* \| None = .+$", source, re.MULTILINE))
    source = patch_ref_descriptions(source, ref_descriptions(schema, bare_ref_fields))

    # A few schema descriptions end in a space, which lands inside a generated docstring.
    # Ruff will not strip it without --unsafe-fixes, so normalise it here instead.
    source = "\n".join(line.rstrip() for line in source.splitlines()) + "\n"
    OUTPUT.write_text(source, encoding="utf-8")

    subprocess.run([sys.executable, "-m", "ruff", "format", str(OUTPUT)], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", str(OUTPUT)], check=True)
    print("Wrote", OUTPUT.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
