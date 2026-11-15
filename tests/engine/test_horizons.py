"""Analytic lunar sphere and ridge cases independent of ephemeris inputs."""

from dataclasses import replace
import math

import numpy as np
import pytest

from soma.geometry import surface_position
from soma.terrain import (
    HorizonCache, HorizonSampling, HorizonSite, SyntheticDEM, build_horizon,
    finite_segment_visibility, horizon_cache_key,
)
from soma.terrain.dem import DATUM, FRAME, RADIUS_M


SITE = HorizonSite(0, 0, 0, 2, 0, FRAME, RADIUS_M, DATUM)
SAMPLING = HorizonSampling(90, 5, 20, 100, (1000, 2000), 0.01, 2000)


def test_spherical_horizon_agrees_with_analytic_tangent_dip():
    sampling = replace(SAMPLING, extents_m=(4000, 8000), required_max_extent_m=8000)
    profile = build_horizon(SyntheticDEM(lambda lat, lon: 0, identifier="flat"), SITE, sampling)
    expected = -math.degrees(math.acos(RADIUS_M/(RADIUS_M+SITE.height_m)))
    assert profile.converged
    assert all(b.elevation_deg == pytest.approx(expected, abs=0.0001) for b in profile.bands)


def test_ridge_raises_east_horizon_and_higher_equipment_reduces_it():
    dem = SyntheticDEM(lambda lat, lon: 20 if 0.003 < lon < 0.004 and abs(lat) < 0.001 else 0,
                       identifier="20m-east-ridge-lon003-004")
    low = build_horizon(dem, SITE, SAMPLING)
    high = build_horizon(dem, replace(SITE, height_m=30), SAMPLING)
    assert low.bands[1].elevation_deg > 5
    assert low.bands[0].elevation_deg < 0
    assert high.bands[1].elevation_deg < low.bands[1].elevation_deg
    assert high.cache_key != low.cache_key


def test_missing_ray_sample_invalidates_horizon_and_convergence():
    dem = SyntheticDEM(lambda lat, lon: None if lon > 0.002 else 0, identifier="east-gap")
    profile = build_horizon(dem, SITE, SAMPLING)
    assert not profile.converged
    assert profile.bands[1].elevation_deg is None
    assert profile.bands[1].sampled_lower_bound_deg is not None


def test_small_tile_does_not_converge_by_ignoring_far_terrain():
    dem = SyntheticDEM(lambda lat, lon: 0 if abs(lat) < 0.01 and abs(lon) < 0.01 else None,
                       identifier="small-tile")
    profile = build_horizon(dem, SITE, SAMPLING)
    assert not profile.converged
    assert all(b.elevation_deg is None for b in profile.bands)


def test_cache_tracks_sampling_and_source_identity_and_is_immutable():
    dem = SyntheticDEM(lambda lat, lon: 0, identifier="flat")
    cache = HorizonCache()
    profile = build_horizon(dem, SITE, SAMPLING, cache=cache)
    assert build_horizon(dem, SITE, SAMPLING, cache=cache) is profile
    assert horizon_cache_key(dem, SITE, replace(SAMPLING, far_step_m=10)) != profile.cache_key
    other = SyntheticDEM(lambda lat, lon: 1, identifier="one")
    assert horizon_cache_key(other, SITE, SAMPLING) != profile.cache_key
    with pytest.raises(ValueError, match="Nondeterministic"):
        cache.put(replace(profile, converged=not profile.converged))


@pytest.mark.parametrize("latitude,longitude", [(-90, 0), (-89.99, 179.999), (90, -180)])
def test_poles_and_dateline_have_finite_horizons(latitude, longitude):
    profile = build_horizon(SyntheticDEM(lambda lat, lon: 0, identifier="flat"),
                            replace(SITE, latitude_deg=latitude, longitude_deg_east=longitude), SAMPLING)
    assert all(math.isfinite(b.elevation_deg) for b in profile.bands)


def test_ridge_beyond_spacecraft_does_not_block_finite_segment():
    dem = SyntheticDEM(lambda lat, lon: 100 if 0.01 < lon < 0.02 else 0,
                       identifier="100m-ridge-beyond-target")
    observer = surface_position(0, 0, RADIUS_M, 2)
    target = surface_position(0, 0.005, RADIUS_M, 30)
    result = finite_segment_visibility(dem, observer, target, frame=FRAME, step_m=2,
                                       clearance_m=0.1, body_radius_m=RADIUS_M)
    assert result.status == "clear"
    horizon = build_horizon(dem, SITE, SAMPLING)
    assert horizon.bands[1].elevation_deg > 5


def test_segment_checks_body_and_missing_terrain_separately():
    missing = SyntheticDEM(lambda lat, lon: None, identifier="missing")
    start = surface_position(0, 0, RADIUS_M, 10)
    kwargs = dict(frame=FRAME, step_m=10, clearance_m=0.1, body_radius_m=RADIUS_M-12000)
    assert finite_segment_visibility(missing, start, start+np.array([100, 0, 0]), **kwargs).status == "unknown"
    assert finite_segment_visibility(missing, start, -start, **kwargs).reason == "solid_body_intersection"
    assert finite_segment_visibility(missing, start, start, **kwargs).status == "unknown"


def test_a_near_ridge_blocks_and_a_grazing_ray_is_not_validated_clear():
    dem = SyntheticDEM(lambda lat, lon: 50 if 0.002 < lon < 0.004 else 0,
                       identifier="50m-near-ridge")
    start = surface_position(0, 0, RADIUS_M, 2)
    target = surface_position(0, 0.005, RADIUS_M, 10)
    result = finite_segment_visibility(dem, start, target, frame=FRAME, step_m=2,
                                       clearance_m=0.1, body_radius_m=RADIUS_M)
    assert result.status == "blocked"
    flat = SyntheticDEM(lambda lat, lon: 0, identifier="flat")
    grazing = finite_segment_visibility(flat, surface_position(0, 0, RADIUS_M),
                                        surface_position(0, 0, RADIUS_M, 10), frame=FRAME,
                                        step_m=1, clearance_m=0.1, body_radius_m=RADIUS_M)
    assert grazing.status == "unknown"
