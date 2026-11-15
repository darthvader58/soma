from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

import pytest

from soma.geometry.registration_calibration import planar_surfaces, radial_triangle_hit


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/registration"


def load(name):
    return json.loads((FIXTURES/name).read_text())


def test_planes_intersect_the_declared_centers_even_at_the_pole():
    request = {"format_version": "0.1.0", "source_frame": "MOON_ME_DE421",
               "candidate_bridge": "identity_for_measurement_only", "probes": [
                   {"id": "pole", "position_m": [0, 0, -1737400]},
                   {"id": "oblique", "position_m": [500000, 700000, -1500000]}]}
    planes = planar_surfaces(request)
    for i, probe in enumerate(request["probes"]):
        corners = [planes["positions"][3*j:3*j+3] for j in range(i*4, i*4+4)]
        hit = radial_triangle_hit(probe["position_m"], corners[:3])
        assert math.dist(hit, planes["centers"][i]["expected_position_m"]) < 1e-6
        assert math.hypot(*hit) == pytest.approx(1736400, abs=1e-6)
        assert math.hypot(*corners[0]) > math.hypot(*hit)
    assert not planes["registration_passed"]


@pytest.mark.parametrize("problem", ["false_bridge", "duplicate", "zero_direction", "nonfinite", "invalid_width"])
def test_calibration_rejects_misattributed_or_invalid_geometry(problem):
    request = deepcopy(load("four-polar-probes.json"))
    kwargs = {}
    if problem == "false_bridge": request["candidate_bridge"] = "registered"
    if problem == "duplicate": request["probes"].append(request["probes"][0])
    if problem == "zero_direction": request["probes"][0]["position_m"] = [0, 0, 0]
    if problem == "nonfinite": request["probes"][0]["position_m"][0] = math.nan
    if problem == "invalid_width": kwargs["half_width_m"] = -1
    with pytest.raises(ValueError):
        planar_surfaces(request, **kwargs)


def test_triangle_intersection_rejects_misses_and_degenerate_surfaces():
    assert radial_triangle_hit([0, 0, 1], [[-1, -1, 10], [1, -1, 10], [0, 1, 10]]) == [0, 0, 10]
    assert radial_triangle_hit([0, 0, -1], [[-1, -1, 10], [1, -1, 10], [0, 1, 10]]) is None
    assert radial_triangle_hit([0, 0, 1], [[1, 1, 10], [2, 1, 10], [2, 2, 10]]) is None
    assert radial_triangle_hit([0, 0, 1], [[1, 1, 10]]*3) is None


def test_recorded_sampler_calibration_is_synthetic_and_asserted():
    capture = load("instrument-calibration.json")
    assert capture["status"] == "completed"
    assert capture["asset_id"] is None
    assert capture["registration_status"] == "not_evaluated"
    assertions = capture["interception"]
    assert assertions["module_requests"] == assertions["factory_matches"] == assertions["token_matches"] == 1
    assert assertions["runtime_marker"] and assertions["blocked_requests"] == 0
    assert capture["page_errors"] == capture["console_errors"] == 0
    assert capture["provenance"]["request_sha256"] == hashlib.sha256((FIXTURES/"four-polar-probes.json").read_bytes()).hexdigest()
    assert capture["provenance"]["planes_sha256"] == hashlib.sha256((FIXTURES/"calibration-planes.json").read_bytes()).hexdigest()
    expected = {x["id"]:x["expected_position_m"] for x in capture["synthetic_geometry"]["centers"]}
    for probe in capture["measurement"]["probes"]:
        assert probe["status"] == "measured"
        assert math.dist(probe["renderer_position_m"], expected[probe["id"]]) < 0.01


