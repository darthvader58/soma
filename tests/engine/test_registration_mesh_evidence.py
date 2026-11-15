import json
import math
from pathlib import Path

import pytest

from soma.geometry.registration_calibration import radial_triangle_hit


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/registration"


def load(name):
    return json.loads((FIXTURES/name).read_text())


def test_cpu_intersections_explain_mesh_samples_without_approving_registration():
    capture = load("inner-polar-cpu-intersections.json")
    assert not capture["registration_passed"]
    assert len(capture["controls"]) == 4
    for control in capture["controls"]:
        assert len(control["hits"]) == 1
        hit = control["hits"][0]
        position = radial_triangle_hit(control["direction_position_m"], hit["triangle_world_m"])
        assert math.dist(position, hit["cpu_position_m"]) < 1e-6
        assert math.dist(position, control["gpu_position_m"]) < 0.06
        # CPU/GPU agreement diagnoses sampling; the source mismatch still exists.
        assert math.hypot(*position)-1737400-control["source_height_m"] > 500


@pytest.mark.parametrize("prefix,expected_unknown", [("inner-polar", 80), ("inner-polar-5m", 324)])
def test_zero_count_polar_samples_remain_unknown_in_recorded_diagnostics(prefix, expected_unknown):
    reference = load(prefix+"-reference.json")
    rows = {r["id"]:r for r in load(prefix+"-radial-differences.json")["samples"]}
    unknown = 0
    for sample in reference["samples"]:
        missing = any(p["count"] <= 0 for p in sample["native_contributors"])
        if missing:
            unknown += 1
            assert sample["reference_height_m"] is None
            assert rows[sample["id"]]["radial_difference_m"] is None
        else:
            height = sum(p["height_dn"]*.5*p["weight"] for p in sample["native_contributors"])
            assert sample["reference_height_m"] == pytest.approx(height)
        assert rows[sample["id"]]["horizontal_landmark_residual_m"] is None
    assert unknown == expected_unknown


def test_positive_count_five_meter_samples_reproduce_the_measured_difference():
    reference = load("inner-polar-5m-positive-reference.json")
    observed = {r["id"]:r for r in load("inner-polar-5m-positive-capture.json")["probes"]}
    diagnostic = load("inner-polar-5m-positive-differences.json")
    assert not diagnostic["registration_passed"]
    assert len(reference["samples"]) == 4
    expected = {r["id"]:r for r in diagnostic["samples"]}
    for sample in reference["samples"]:
        assert sample["count"] > 0
        assert sample["reference_height_m"] == sample["native_dn"]*.5
        measured_height = math.hypot(*observed[sample["id"]]["renderer_position_m"])-1737400
        difference = measured_height-sample["reference_height_m"]
        assert expected[sample["id"]]["radial_difference_m"] == pytest.approx(difference)
        assert difference > 500
        assert expected[sample["id"]]["horizontal_landmark_residual_m"] is None
