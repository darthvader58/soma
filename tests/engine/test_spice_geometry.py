"""Live checks require externally acquired, hash-pinned NAIF kernels."""
import copy
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import pytest
from soma.geometry import SpiceGeometry, SurfacePoint
from soma.time.spice import utc_to_et


@pytest.fixture
def live_manifest():
    root = Path(os.environ.get('SOMA_PHASE2_DATA_ROOT', '/private/tmp/soma-phase2-data'))
    names = {'leap_seconds':'naif0012.tls','planetary_ephemeris':'de421.bsp',
             'lunar_frame':'moon_080317.tf','lunar_orientation':'moon_pa_de421_1900-2050.bpc',
             'earth_orientation':'earth_000101_270208_261113.bpc'}
    if any(not (root/name).is_file() for name in names.values()):
        pytest.skip('externally downloaded NAIF kernel bundle absent; set SOMA_PHASE2_DATA_ROOT')
    manifest = {'frame':'MOON_ME_DE421','ephemeris':'DE421',
                'coverage':{'start_utc':'2008-03-17T20:10:00Z','end_utc':'2026-11-15T00:00:00Z'},
                'kernels':[{'role':role,'path':name,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()}
                           for role,name in names.items()]}
    return manifest, root


def test_naif_published_de421_earth_vector_and_strict_utc(live_manifest):
    manifest, root = live_manifest
    with SpiceGeometry(manifest, root) as geometry:
        # Independent published reference from NAIF moon_080317.tf program output,
        # not a second invocation of SOMA or SpiceyPy.
        state = geometry.state('EARTH', '2008-03-17T20:10:00Z')
        np.testing.assert_allclose(state['position'], [379892825,33510118,-12661527.8], atol=.6, rtol=0)
        assert state['position_unit'] == 'm'
        assert utc_to_et('2026-11-14T00:00:00Z') == utc_to_et('2026-11-13T17:00:00-07:00')
        with pytest.raises(ValueError):
            geometry.state('SUN', '2026-11-14T00:00:00')
        with pytest.raises(ValueError, match='coverage'):
            geometry.state('SUN', '2100-01-01T00:00:00Z')
        with pytest.raises(ValueError):
            geometry.state('SUN', '2026-11-14T00:00:00Z', frame='IAU_MOON')


def test_pool_restoration_on_success_nested_rejection_and_failure(live_manifest):
    import spiceypy as spice
    manifest, root = live_manifest
    spice.pdpool('SOMA_TEST_EXTERNAL_NUMERIC', [12.5, 7])
    spice.pcpool('SOMA_TEST_EXTERNAL_TEXT', ['external user value'])
    before = [spice.kdata(i,'ALL') for i in range(spice.ktotal('ALL'))]
    try:
        with SpiceGeometry(manifest, root):
            assert spice.ktotal('ALL') == 5
            with pytest.raises(RuntimeError, match='nested'):
                with SpiceGeometry(manifest, root):
                    pass
        assert [spice.kdata(i,'ALL')[:3] for i in range(spice.ktotal('ALL'))] == [x[:3] for x in before]
        np.testing.assert_allclose(spice.gdpool('SOMA_TEST_EXTERNAL_NUMERIC',0,2), [12.5,7])
        assert spice.gcpool('SOMA_TEST_EXTERNAL_TEXT',0,1)[0] == 'external user value'
        broken = copy.deepcopy(manifest)
        broken['coverage']['end_utc'] = '2100-01-01T00:00:00Z'
        with pytest.raises(ValueError, match='PCK'):
            with SpiceGeometry(broken, root):
                pass
        np.testing.assert_allclose(spice.gdpool('SOMA_TEST_EXTERNAL_NUMERIC',0,2), [12.5,7])
    finally:
        spice.dvpool('SOMA_TEST_EXTERNAL_NUMERIC')
        spice.dvpool('SOMA_TEST_EXTERNAL_TEXT')


def test_checksum_and_frame_mismatch_fail_before_pool_mutation(live_manifest):
    manifest, root = live_manifest
    bad = copy.deepcopy(manifest)
    bad['kernels'][0]['sha256'] = '0'*64
    with pytest.raises(ValueError, match='SHA256'):
        SpiceGeometry(bad, root)
    bad = copy.deepcopy(manifest)
    bad['frame'] = 'MOON_ME'
    with pytest.raises(ValueError, match='matched'):
        SpiceGeometry(bad, root)


def test_external_manifest_edit_cannot_change_context_coverage(live_manifest):
    manifest, root = live_manifest
    geometry = SpiceGeometry(manifest, root)
    manifest['coverage']['end_utc'] = '2100-01-01T00:00:00Z'
    with geometry:
        assert geometry.state('SUN', '2026-11-14T09:00:00Z')['frame'] == 'MOON_ME_DE421'
        assert geometry.provenance['verified_coverage']['end_utc'] == '2026-11-15T00:00:00Z'


def test_station_translation_and_missing_earth_orientation(live_manifest):
    manifest, root = live_manifest
    station = {'id':'educational-proxy','input_class':'assumed','latitude_deg':0,'longitude_deg_east':0,
               'height_m':0,'frame':'ITRF93','reference_ellipsoid':'WGS84'}
    utc = '2026-11-14T00:00:00Z'
    with SpiceGeometry(manifest, root) as geometry:
        earth = np.array(geometry.state('EARTH',utc)['position'])
        actual = np.array(geometry.station_state(station,utc)['position'])
        assert np.linalg.norm(actual-earth) == pytest.approx(6378137, abs=1e-6)
        surface = SurfacePoint(-89,0,'MOON_ME_DE421',1737400,0,4,1,0)
        direction = geometry.direction(surface,'SUN',utc,height_m=surface.panel_height_m)
        assert direction['range_m'] > 1e11
        assert direction['observer_height_m'] == 1
        assert direction['aberration'] == 'NONE'
    manifest['kernels'] = [x for x in manifest['kernels'] if x['role'] != 'earth_orientation']
    with SpiceGeometry(manifest, root) as geometry:
        with pytest.raises(ValueError, match='Earth binary PCK'):
            geometry.station_state(station,utc)
