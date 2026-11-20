import copy
import json
import os

import pytest
from pydantic import ValidationError

from wra_data_model_pydantic.model import IeaWindResourceAssessmentDataModel

# The repository root, three levels up from this file (tools/pydantic_model/tests).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEMO_DATA_DIR = os.path.join(REPO_ROOT, "demo_data")


def get_demo_data_files() -> list[str]:
    return [
        os.path.join(DEMO_DATA_DIR, file_name) for file_name in os.listdir(DEMO_DATA_DIR) if file_name.endswith(".json")
    ]


def load_demo_document() -> dict:
    with open(os.path.join(DEMO_DATA_DIR, "iea43_wra_data_model.json")) as f:
        return json.load(f)


def test_demo_data_files_are_discovered() -> None:
    """Guard against an empty parametrisation, which would otherwise report as a pass."""
    assert len(get_demo_data_files()) > 0


@pytest.mark.parametrize("file_path", get_demo_data_files())
def test_demo_data_validates(file_path: str) -> None:
    with open(file_path) as f:
        data = json.load(f)
    wra_data_model = IeaWindResourceAssessmentDataModel.model_validate(data)
    assert wra_data_model is not None


def test_duplicate_items_in_a_unique_array_are_rejected() -> None:
    """The schema marks `measurement_point` as uniqueItems, so duplicates must not validate."""
    data = load_demo_document()
    measurement_points = data["measurement_location"][0]["measurement_point"]
    measurement_points.append(copy.deepcopy(measurement_points[0]))

    with pytest.raises(ValidationError, match="List items must be unique"):
        IeaWindResourceAssessmentDataModel.model_validate(data)


def test_distinct_items_in_a_unique_array_are_accepted() -> None:
    """Positive control for the uniqueness check: near-identical but distinct items are valid."""
    data = load_demo_document()
    measurement_points = data["measurement_location"][0]["measurement_point"]
    duplicate = copy.deepcopy(measurement_points[0])
    duplicate["name"] = f"{duplicate['name']}_distinct_copy"
    measurement_points.append(duplicate)

    assert IeaWindResourceAssessmentDataModel.model_validate(data) is not None


def test_invalid_classification_is_rejected() -> None:
    """`classification` carries a regex pattern in the schema, e.g. 1.2A."""
    data = load_demo_document()
    for measurement_point in data["measurement_location"][0]["measurement_point"]:
        for sensor in measurement_point.get("sensor") or []:
            sensor["classification"] = "1.2X"

            with pytest.raises(ValidationError, match="String should match pattern"):
                IeaWindResourceAssessmentDataModel.model_validate(data)
            return

    pytest.fail("no sensor found in the demo data to exercise the classification pattern")


def test_valid_classification_is_accepted() -> None:
    """Positive control for the classification pattern, including the two-digit class index."""
    data = load_demo_document()
    for measurement_point in data["measurement_location"][0]["measurement_point"]:
        for sensor in measurement_point.get("sensor") or []:
            sensor["classification"] = "10.32S"

            assert IeaWindResourceAssessmentDataModel.model_validate(data) is not None
            return

    pytest.fail("no sensor found in the demo data to exercise the classification pattern")
