"""Real-file checks remain separate from synthetic numerical regression tests."""

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from soma.diagnostics import geometry_diagnostic
from soma.geometry import SurfacePoint
from soma.geometry_verification import verify_geometry
from soma.validation import load_json, load_scenario, validate_document

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def real_data():
    directory = Path(os.environ.get("SOMA_PHASE2_DATA_ROOT", "/private/tmp/soma-phase2-data"))
    manifests = [load_json(ROOT / "data" / name) for name in (
        "de421-phase2.manifest.json", "lola-phase2.manifest.json", "lola-far-phase2.manifest.json")]
    entries = manifests[0]["kernels"] + manifests[1]["files"] + manifests[2]["files"]
    if any(not (directory / entry["path"]).is_file() for entry in entries):
        pytest.skip("Externally acquired Phase 2 data absent; run fetch-geometry-data and set SOMA_PHASE2_DATA_ROOT")
    return directory, manifests


def test_independent_ephemeris_and_rotation_readers_pass(real_data):
    directory, manifests = real_data
    report = verify_geometry(directory, manifests[0])
    assert report["passed"]
    assert len(report["checks"]) == 6
    assert "not independent validation" in report["scope"]


def test_real_dem_control_point_and_honest_diagnostic(real_data):
    directory, manifests = real_data
    scenario = load_scenario(ROOT / "fixtures/synthetic-relay/scenario.json")
    scenario["lander"].update(latitude_deg=-89.03093035536243, longitude_deg_east=1.389336784014743)
    report = geometry_diagnostic(scenario, data_root=directory, kernel_manifest=manifests[0],
        near_manifest=manifests[1], far_manifest=manifests[2], sample_step_s=2250, azimuth_step_deg=90,
        include_synthetic_relay=True)
    assert report["analysis_point"]["elevation_m"] == pytest.approx(-301.98974609375)
    assert report["elevation_resolution"]["count"] == pytest.approx(1)
    # Independent inverse stereographic control point from the pinned source
    # grid (x=712.5,y=29377.5 m); this is not renderer registration.
    radius, x, y = 1737400, 712.5, 29377.5
    colatitude = 2*np.arctan(np.hypot(x, y)/(2*radius))
    longitude = np.arctan2(x, y)
    r = radius-301.98974609375
    expected = r*np.array([np.sin(colatitude)*np.cos(longitude), np.sin(colatitude)*np.sin(longitude), -np.cos(colatitude)])
    np.testing.assert_allclose(SurfacePoint.from_lander(report["analysis_point"]).position_m(), expected, atol=1e-6, rtol=0)
    assert report["frame"] == "MOON_ME_DE421"
    assert report["scenario"]["data_volume"] == {"value": 100, "unit": "MiB"}
    for role, expected_height in (("panel", 1), ("antenna", 2)):
        horizon = report["horizons"][role]
        assert horizon["site"]["height_m"] == expected_height
        assert not horizon["converged"]
        assert all(band["elevation_deg"] is None for band in horizon["bands"])
    for track in report["tracks"]:
        for sample in track["samples"]:
            validate_document(sample["state"], "state")
        if track["target"] in ("SUN", "EARTH", "synthetic-earth-station"):
            assert all(sample["classification"] == "unknown" for sample in track["samples"])
    assert "contacts" not in report and "delivered_bytes" not in report
    json.dumps(report, allow_nan=False)


def test_unobserved_original_fixture_site_fails_without_being_moved(real_data):
    directory, _ = real_data
    completed = subprocess.run([sys.executable, "-m", "soma", "geometry",
        str(ROOT / "fixtures/synthetic-relay/scenario.json"), "--data-root", str(directory)],
        cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "unknown measured terrain" in completed.stderr
    assert "Traceback" not in completed.stderr
