"""Input invariants for the separate geometry-study contract."""
from copy import deepcopy
import hashlib

import pytest
import rfc8785

from soma.research import StudyValidationError, study_sha256, validate_study
from soma.research.validation import study_epochs
from soma.validation import validate_document


@pytest.fixture
def study():
    return {"study_version": "1.0.0", "analysis_type": "geometry", "frame": "MOON_ME_DE421",
            "reference_radius_m": 1737400, "surface_model": "reference_sphere",
            "sites": [{"id": "custom-a", "name": "Research location", "latitude_deg": 14.25,
                       "longitude_deg_east": 51.75, "elevation_m": -123,
                       "antenna_height_m": 3, "panel_height_m": 0.75}],
            "time": {"start_utc": "2024-01-08T00:00:00Z", "end_utc": "2024-01-08T06:00:00Z", "step_s": 900},
            "spacecraft_refs": []}


def test_normalized_snapshot_and_rfc8785_hash(study):
    normalized = validate_study(study)
    assert study_sha256(study) == hashlib.sha256(rfc8785.dumps(normalized)).hexdigest()
    equivalent = deepcopy(study)
    equivalent["time"]["start_utc"] = "2024-01-07T17:00:00-07:00"
    assert study_sha256(equivalent) == study_sha256(study)
    normalized["sites"][0]["latitude_deg"] = 5
    assert study["sites"][0]["latitude_deg"] == 14.25
    assert study_sha256(normalized) != study_sha256(study)


@pytest.mark.parametrize("field,value", [("latitude_deg", 91), ("longitude_deg_east", 180),
    ("latitude_deg", float("nan")), ("panel_height_m", float("inf")),
    ("antenna_height_m", True), ("elevation_m", -1737400), ("panel_height_m", -1)])
def test_invalid_site_inputs_fail(study, field, value):
    study["sites"][0][field] = value
    with pytest.raises(StudyValidationError):
        validate_study(study)


def test_units_frame_unknown_fields_missing_heights_and_unique_ids(study):
    for field, value in (("frame", "IAU_MOON"), ("surface_model", "terrain"), ("reference_radius_m", "1737400m")):
        bad = deepcopy(study)
        bad[field] = value
        with pytest.raises(StudyValidationError):
            validate_study(bad)
    bad = deepcopy(study)
    del bad["sites"][0]["panel_height_m"]
    with pytest.raises(StudyValidationError):
        validate_study(bad)
    bad = deepcopy(study)
    bad["sites"].append(deepcopy(bad["sites"][0]))
    with pytest.raises(StudyValidationError, match="unique"):
        validate_study(bad)
    bad = deepcopy(study)
    bad["time"]["step_unit"] = "minute"
    with pytest.raises(StudyValidationError):
        validate_study(bad)


def test_budget_limits_and_end_epoch(study):
    sparse = deepcopy(study)
    sparse["time"]["step_s"] = 9_000_000_000_000_000
    assert len(study_epochs(validate_study(sparse))) == 2
    study["time"]["end_utc"] = "2024-01-09T00:00:01Z"
    study["time"]["step_s"] = 3600
    validated = validate_study(study)
    epochs = study_epochs(validated)
    assert len(epochs) == 26
    assert epochs[-1] == study["time"]["end_utc"]
    study["time"]["step_s"] = 10
    with pytest.raises(StudyValidationError, match="2000"):
        validate_study(study)
    study["time"] = {"start_utc": "2024-01-01T00:00:00Z", "end_utc": "2024-02-02T00:00:00Z", "step_s": 86400}
    with pytest.raises(StudyValidationError, match="31-day"):
        validate_study(study)
    study["time"] = {"start_utc": "2024-01-01T00:00:00Z", "end_utc": "2024-01-02T00:00:00Z", "step_s": 60}
    study["sites"] = [{**study["sites"][0], "id": str(i)} for i in range(4)]
    with pytest.raises(StudyValidationError, match="5000"):
        validate_study(study)


@pytest.mark.parametrize("epoch", ["2024-01-08T00:00:00", "2024-01-08T00:00:00-00:00", "2024-01-08T00:00:60Z"])
def test_strict_timezone_boundary(study, epoch):
    study["time"]["start_utc"] = epoch
    with pytest.raises(StudyValidationError):
        validate_study(study)


def test_study_schema_is_separate_from_delivery_schema(study):
    validate_document(study, "study")
    with pytest.raises(ValueError):
        validate_document(study, "scenario")


def test_hash_rejects_invalid_unicode(study):
    study["sites"][0]["name"] = "\ud800"
    with pytest.raises(StudyValidationError, match="canonicalized"):
        study_sha256(study)
