"""Published-grid policy tests; fabricated grids remain synthetic test inputs."""
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from rasterio.transform import from_origin

from soma.terrain.dem import DATUM, FRAME, RADIUS_M, SyntheticDEM
from soma.terrain.horizons import HorizonSampling, HorizonSite, build_horizon
from soma.terrain.physical import (COARSE, INTERPOLATED, UNKNOWN, PhysicalDEM,
                                   _MemoryGrid, _profile, open_physical_dem)
from soma.validation import load_json


class Band:
    def __init__(self, values, transform):
        self.values, self.transform = values, transform
    def read(self, *args, **kwargs):
        return self.values


def grid(values, counts):
    heights = np.ma.masked_invalid(np.array(values,dtype=float))
    counts = np.ma.masked_invalid(np.array(counts,dtype=float))
    transform = from_origin(-180, 90, 120, 60)
    source = SimpleNamespace(source_id='synthetic-test-grid',_elevation=Band(heights,transform),
                             _counts=Band(counts,transform))
    return _MemoryGrid(source,geographic=True)


def test_published_interpolation_is_explicit_and_strict_mode_remains_unknown():
    source = grid(np.full((3,3),42),np.zeros((3,3)))
    heights,counts,flags = source.sample_many(np.array([0]),np.array([0]),'published_grid')
    assert heights[0] == 42 and counts[0] == 0
    assert flags[0] & INTERPOLATED and not flags[0] & UNKNOWN
    heights,_,flags = source.sample_many(np.array([0]),np.array([0]),'strict_measurements')
    assert np.isnan(heights[0]) and flags[0] & UNKNOWN


def test_nan_is_unknown_even_in_published_grid_and_coarse_downgrade_is_labeled():
    missing = grid(np.full((3,3),np.nan),np.ones((3,3)))
    valid = grid(np.full((3,3),17),np.ones((3,3)))
    dem = PhysicalDEM(missing,valid,policy='published_grid',source_hashes=('a'*64,))
    sample = dem.sample(0,0)
    assert sample.elevation_m == 17
    assert 'explicit_coarse_resolution_downgrade' in sample.quality_flags
    unknown = PhysicalDEM(missing,missing,policy='published_grid',source_hashes=('b'*64,)).sample(0,0)
    assert unknown.elevation_m is None
    assert 'missing_terrain_unknown' in unknown.quality_flags


class SampledSyntheticDEM(SyntheticDEM):
    policy = 'strict_measurements'
    def sample_many(self,lat,lon,*,policy=None):
        samples = [self.sample(float(a),float(b)) for a,b in zip(lat,lon)]
        return (np.array([np.nan if s.elevation_m is None else s.elevation_m for s in samples]),
                np.ones(len(samples)),np.array([UNKNOWN if s.elevation_m is None else 0 for s in samples],dtype=np.uint8))


def test_vector_horizon_matches_separate_scalar_implementation_and_cache_height_identity():
    dem = SampledSyntheticDEM(lambda lat,lon:300 if lon>0 else 0,identifier='synthetic-east-step-300m')
    sampling = HorizonSampling(30,20,100,100,(1000,2000),.01,2000)
    site = HorizonSite(-89,0,0,2,0,FRAME,RADIUS_M,DATUM)
    vector,quality = _profile(dem,site,sampling)
    reference = build_horizon(dem,site,sampling)
    np.testing.assert_allclose([b.elevation_deg for b in vector.bands],
                               [b.elevation_deg for b in reference.bands],atol=1e-7,rtol=0)
    assert vector.converged == reference.converged
    taller,_ = _profile(dem,HorizonSite(-89,0,0,20,0,FRAME,RADIUS_M,DATUM),sampling)
    assert vector.cache_key != taller.cache_key
    again,quality_again = _profile(dem,site,sampling)
    assert again == vector and quality_again == quality
    assert quality['unknown_samples'] == 0


def test_missing_sample_makes_horizon_unknown_not_clear():
    dem = SampledSyntheticDEM(lambda lat,lon:None,identifier='synthetic-all-missing')
    site = HorizonSite(-89,0,0,2,0,FRAME,RADIUS_M,DATUM)
    profile,quality = _profile(dem,site,HorizonSampling(90,20,100,100,(1000,2000),.01,2000))
    assert not profile.converged
    assert all(b.elevation_deg is None and b.unknown_samples>0 for b in profile.bands)
    assert quality['unknown_fraction'] == 1


def test_cancellation_stops_horizon_work():
    from threading import Event
    event = Event();event.set()
    dem = SampledSyntheticDEM(lambda lat,lon:0,identifier='synthetic-cancel-flat')
    with pytest.raises(InterruptedError):
        _profile(dem,HorizonSite(-89,0,0,2,0,FRAME,RADIUS_M,DATUM),
                 HorizonSampling(90,20,100,100,(1000,2000),.01,2000),cancel_event=event)


def test_real_grid_control_point_and_independent_scalar_horizon_agree():
    root = Path(os.environ.get('SOMA_DATA_ROOT','/private/tmp/soma-phase2-data'))
    data = Path(__file__).resolve().parents[2]/'data'
    near,far = (load_json(data/n) for n in ('lola-phase2.manifest.json','lola-far-phase2.manifest.json'))
    if any(not (root/e['path']).is_file() for m in (near,far) for e in m['files']):
        pytest.skip('External pinned LOLA files absent')
    dem = open_physical_dem(root,near,far,policy='published_grid')
    try:
        point = dem.sample(-89.03093035536243,1.389336784014743)
        assert point.elevation_m == pytest.approx(-301.98974609375,abs=1e-8)
        sampling = HorizonSampling(90,50,250,500,(1000,2000),.01,2000)
        site = HorizonSite(-89.03093035536243,1.389336784014743,point.elevation_m,2,0,FRAME,RADIUS_M,DATUM)
        fast,_ = _profile(dem,site,sampling)
        scalar = build_horizon(dem,site,sampling)
        np.testing.assert_allclose([b.elevation_deg for b in fast.bands],
                                   [b.elevation_deg for b in scalar.bands],rtol=0,atol=1e-7)
    finally:
        dem.close()


def test_far_field_cap_bound_is_cartesian_and_decreases_beyond_extent():
    from soma.terrain.physical import far_field_envelope
    dem = SampledSyntheticDEM(lambda lat,lon:0,identifier='synthetic-envelope-flat')
    sampling = HorizonSampling(90,100,1000,1000,(100000,200000,250000),.01,250000)
    site = HorizonSite(-89,0,0,2,0,FRAME,RADIUS_M,DATUM)
    profile,_ = _profile(dem,site,sampling)
    evidence = far_field_envelope(profile,maximum_terrain_height_m=12000)
    assert evidence['height_cap_input_class'] == 'assumed'
    assert evidence['omitted_terrain_cannot_raise_sampled_bands_under_cap']
    radius = RADIUS_M+12000
    observer = RADIUS_M+2
    for distance in (250000,300000,1000000):
        point = np.array([radius*np.sin(distance/RADIUS_M),radius*np.cos(distance/RADIUS_M)])
        angle = np.degrees(np.arctan2(point[1]-observer,point[0]))
        assert angle <= evidence['maximum_omitted_elevation_deg']+1e-12


def test_real_release_profile_is_complete_with_polar_patch_and_records_strict_comparison():
    from soma.terrain.physical import DEFAULT_SAMPLING,far_field_envelope
    root = Path(os.environ.get('SOMA_DATA_ROOT','/private/tmp/soma-phase2-data'))
    data = Path(__file__).resolve().parents[2]/'data'
    manifests = [load_json(data/n) for n in ('lola-phase2.manifest.json','lola-far-phase2.manifest.json','physical-polar-window.manifest.json')]
    if any(not (root/e['path']).is_file() for m in manifests for e in m['files']):
        pytest.skip('External pinned LOLA grids and polar patch absent')
    dem = open_physical_dem(root,*manifests[:2],polar_manifest=manifests[2],policy='published_grid')
    try:
        lat,lon = -89.03093035536243,1.389336784014743
        point = dem.sample(lat,lon)
        profile,quality = _profile(dem,HorizonSite(lat,lon,point.elevation_m,2,0,FRAME,RADIUS_M,DATUM),HorizonSampling(**DEFAULT_SAMPLING))
        assert profile.converged and profile.maximum_change_deg == 0
        assert quality['unknown_samples'] == 0 and quality['polar_patch_samples'] > 0
        assert quality['strict_measurements_unknown_samples'] > 0
        assert 0 < quality['interpolated_fraction'] < 1
        assert far_field_envelope(profile,maximum_terrain_height_m=12000)['omitted_terrain_cannot_raise_sampled_bands_under_cap']
    finally:
        dem.close()


def test_negative_count_is_invalid_not_published_interpolation():
    source = grid(np.full((3,3),42),np.full((3,3),-1))
    heights,_,flags = source.sample_many(np.array([0]),np.array([0]),'published_grid')
    assert np.isnan(heights[0]) and flags[0] & UNKNOWN
    assert not flags[0] & INTERPOLATED
