# Pydantic Data Model

A [Pydantic](https://docs.pydantic.dev/latest/) implementation of the _IEA Wind WRA Data Model_, generated from [`schema/iea43_wra_data_model.schema.json`](../../schema/iea43_wra_data_model.schema.json).

It validates and parses JSON data files that follow the _WRA Data Model_, and gives an object-oriented way to work with that data in Python, including code completion and type checking in modern IDEs.

**Python 3.11 or later is required.** The model uses `StrEnum`, built-in generics and the `X | None` union operator, none of which are available earlier, and Pydantic v2 itself requires 3.9 or later. Importing the model on an older interpreter fails with `ImportError: cannot import name 'StrEnum' from 'enum'`.

## Usage

```python
import json

from wra_data_model_pydantic.model import IeaWindResourceAssessmentDataModel

with open("demo_data/iea43_wra_data_model.json") as f:
    wra_data_model = IeaWindResourceAssessmentDataModel.model_validate(json.load(f))

print(wra_data_model.measurement_location[0].name)
```

A worked example is in the [load_demo_schema_to_model.ipynb](../load_demo_schema_to_model.ipynb) notebook.

## Schema version

The package version matches the version of the JSON Schema it was generated from, so there is one version number rather than two. The schema version also encodes the release month, as in `1.4.0-2025.06`, which is not a valid Python package version, so the package carries the `MAJOR.MINOR.PATCH` part and the full value is available as a constant:

```python
from wra_data_model_pydantic.model import SCHEMA_VERSION

SCHEMA_VERSION  # '1.4.0-2025.06'
```

When checking a data file against the model, compare the `MAJOR.MINOR.PATCH` part rather than the whole string. The trailing `YYYY.MM` records when a version was released and carries no compatibility meaning, so two files that differ only in that suffix are the same version of the standard.

```python
def schema_version_of(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("-", 1)[0].split("."))

file_version = schema_version_of(wra_data_model.version)
model_version = schema_version_of(SCHEMA_VERSION)

if file_version[0] != model_version[0]:
    raise ValueError(f"file is major version {file_version[0]}, model implements {model_version[0]}")
```

A differing major version means the file and the model are incompatible. A differing minor or patch version is usually safe, because changes within a major version have so far been additive, though a file from a newer version may contain values this model does not know about.

Note that the schema version is raised at release rather than on each change, so between releases the constant reports the last released version while the model may already contain newer fields.

## Environment

Dependencies are managed with [Poetry](https://python-poetry.org/). Run from this directory:

```bash
poetry install
```

The model itself depends only on Pydantic. The example notebook additionally needs pandas and a Jupyter kernel, which are in an optional group:

```bash
poetry install --with notebook
```

## The model is generated, not hand-written

`wra_data_model_pydantic/model.py` is produced by [datamodel-code-generator](https://docs.pydantic.dev/latest/integrations/datamodel_code_generator/) and **must not be edited by hand**. Any manual edit is silently reverted the next time the model is regenerated, and the CI sync check will fail.

To regenerate after a change to the JSON Schema:

```bash
poetry run poe generate
```

The generator flags are pinned in [generate_model.py](generate_model.py). `datamodel-code-generator` and `ruff` are pinned to exact versions in `pyproject.toml`, because both determine the bytes of the generated file: the generator produces it and `ruff format` normalises it. Upgrade either deliberately, regenerate, and review the resulting diff.

### Post-generation patches

Two constraints in the JSON Schema cannot be expressed by the generator, so `generate_model.py` applies them afterwards. Both are applied automatically; neither requires manual intervention.

1. **`uniqueItems` on arrays.** The generator drops these silently, which would let a document containing duplicate items validate successfully. Each affected array is wrapped in a `UniqueList` annotation that rejects duplicates. The script fails if it cannot find every array the schema marks as unique, so a generator upgrade cannot quietly weaken this.
2. **`description` and `title` on a bare `$ref` carrying a default.** The generator omits both for that shape, which affects six fields including `height_reference_id` and `orientation_reference_id`. The text is read from the schema rather than duplicated here, so it cannot drift.

### Notable generator settings

- `--output-datetime-class datetime` — the generator's default of `AwareDatetime` rejects every timestamp in the demo data. The _WRA Data Model_ carries timestamps without a UTC offset because the offset is a separate `offset_from_utc_hrs` field.
- `--collapse-root-models` — single-value definitions such as `notes` and `date_from` become plain `str` and `datetime` values. Without this they become wrapper objects requiring `.root` to read the value.
- `--disable-timestamp` — keeps output byte-identical between runs so the sync check is meaningful.

Two lint exemptions are configured in `pyproject.toml` for the generated file: long docstring lines (`E501`), which are specification descriptions, and mixed-case enum members (`N815`), which are vendor names taken verbatim from the schema. A mypy override covers statistic types such as `count` that shadow same-named `str` methods when emitted as `StrEnum` members.

## Tests

```bash
poetry run poe test
```

The suite validates every file in [demo_data](../../demo_data) against the model, and checks that duplicate array items and malformed `classification` values are rejected rather than silently accepted.

## Keeping the model in sync with the schema

The committed model is the file users import, so it is regenerated and committed as part of any schema change rather than built on demand. The 'Python Model Build, Lint, and Test' pipeline does not produce it: on every relevant pull request the pipeline regenerates a copy of its own, purely to compare against the committed one, and fails if the two differ. A change to the JSON Schema that is not carried into the model therefore cannot pass review. See [contributing.md](../../contributing.md) for the wider schema-change checklist.
