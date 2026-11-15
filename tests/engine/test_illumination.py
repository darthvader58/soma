"""Synthetic angular geometry, independent disk segment and shared-mask checks."""
import math
import pytest
from soma.illumination import solar_disk_visibility

SUN_DISTANCE = 149597870700.0


def horizon(elevation=0, height=1, converged=True):
    return {"converged": converged, "site": {"height_m": height}, "bands": [
        {"azimuth_deg": a, "elevation_deg": elevation} for a in range(0,360,10)]}


def vector(elevation, distance=SUN_DISTANCE):
    angle = math.radians(elevation)
    return [0, distance*math.cos(angle), distance*math.sin(angle)]


def visibility(elevation=0, **kwargs):
    return solar_disk_visibility(vector(elevation), [3.8e8,0,0], horizon=horizon(),
                                 horizon_margin_deg=0, **kwargs)


def test_partial_sun_matches_independent_flat_disk_segment():
    radius = math.degrees(math.asin(695700000/SUN_DISTANCE))
    # Geometric area above a line through a disk at one-half radius offset.
    expected = 1-(math.acos(0.5)-0.5*math.sqrt(0.75))/math.pi
    result = visibility(radius/2, samples=2048, max_samples=16384, tolerance=0.002)
    assert result["visible_fraction"] == pytest.approx(expected, abs=0.003)
    assert result["converged"]


def test_clear_dark_and_missing_horizon():
    assert visibility(10)["visible_fraction"] == 1
    assert visibility(-10)["visible_fraction"] == 0
    result = solar_disk_visibility(vector(10), [3.8e8,0,0], horizon=horizon(None))
    assert result["visible_fraction"] is None
    assert (result["lower_bound"], result["upper_bound"]) == (0,1)
    result = solar_disk_visibility(vector(10), [3.8e8,0,0], horizon=horizon(converged=False))
    assert result["status"] == "unknown"


def test_observer_heights_remain_separate_inputs():
    panel = solar_disk_visibility(vector(1), [3.8e8,0,0], horizon=horizon(2,1))
    antenna = solar_disk_visibility(vector(1), [3.8e8,0,0], horizon=horizon(0,3))
    assert panel["visible_fraction"] == 0
    assert antenna["visible_fraction"] == 1
    assert (panel["observer_height_m"], antenna["observer_height_m"]) == (1,3)


def test_earth_and_terrain_masks_overlap_without_double_subtraction():
    result = solar_disk_visibility(vector(0), vector(0,3.8e8), horizon=horizon(), horizon_margin_deg=0)
    counts = result["mask_counts"]
    assert counts["both_blocked"] > 0
    assert counts["earth_blocked"] == result["samples"]
    assert result["visible_fraction"] == 0
    # Replacing unknown terrain cannot revive any ray already blocked by Earth.
    assert solar_disk_visibility(vector(0), vector(0,3.8e8), horizon=horizon(None))["visible_fraction"] == 0


def test_earth_behind_sun_does_not_mask():
    result = solar_disk_visibility(vector(10), vector(10,2*SUN_DISTANCE), horizon=horizon())
    assert result["visible_fraction"] == 1
    assert result["mask_counts"]["earth_blocked"] == 0


def test_partial_eclipse_shared_disk_union():
    # Synthetic equal-angular-radius Earth offset below Sun so terrain overlaps it.
    radius = math.asin(695700000/SUN_DISTANCE)
    earth_distance = 6378137/math.sin(radius)
    result = solar_disk_visibility(vector(0), vector(-math.degrees(radius)/2,earth_distance),
                                  horizon=horizon(), horizon_margin_deg=0,
                                  samples=2048,max_samples=16384)
    counts = result["mask_counts"]
    assert 0 < counts["both_blocked"] < counts["earth_blocked"]
    union = counts["terrain_blocked"]+counts["earth_blocked"]-counts["both_blocked"]
    assert result["visible_fraction"] == pytest.approx(1-union/result["samples"])
