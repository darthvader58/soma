"""Missing registration evidence must never authorize lunar overlays."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from soma.geometry.registration import (
    catalog_reference_position_m, load_renderer_registration,
    registration_release_gate, validate_renderer_registration,
)


ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_registration_preserves_unknowns_and_blocks_release():
    evidence = load_renderer_registration()
    assert evidence['source_frame'] == 'MOON_ME_DE421'
    assert evidence['renderer_frame'] is None
    assert evidence['transform_column_major'] is None
    assert evidence['tolerance_m'] is None
    assert registration_release_gate(evidence)['overlays_allowed'] is False
    assert len(evidence['landmarks']) >= 4
    assert all(p['residual_m'] is None for p in evidence['landmarks'])
    evidence['release_gate']['overlays_allowed'] = True
    assert load_renderer_registration()['release_gate']['overlays_allowed'] is False


@pytest.mark.parametrize('field,value', [
    ('renderer_frame', 'IAU_MOON'),
    ('transform_column_major', [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),
    ('status', 'registered'), ('tolerance_m', 5), ('origin', 'EARTH'),
    ('position_unit', 'km'),
])
def test_unresolved_metadata_cannot_be_promoted_by_defaults(field, value):
    evidence = load_renderer_registration()
    evidence[field] = value
    with pytest.raises(ValueError):
        validate_renderer_registration(evidence)


def test_algebraic_positions_are_not_independent_residuals():
    evidence = load_renderer_registration()
    for p in evidence['landmarks']:
        # Independent inverse check of the stored spherical catalog construction.
        x, y, z = p['catalog_reference_position_m']
        assert math.sqrt(x*x+y*y+z*z) == pytest.approx(1737400)
        assert math.degrees(math.atan2(z, math.hypot(x,y))) == pytest.approx(p['catalog_coordinates']['latitude_deg'])
        assert math.degrees(math.atan2(y,x)) == pytest.approx(p['catalog_coordinates']['longitude_deg_east'])
    evidence['landmarks'][0]['residual_m'] = 0
    with pytest.raises(ValueError, match='unmeasured'):
        validate_renderer_registration(evidence)


def test_duplicate_landmarks_and_invented_catalog_positions_fail():
    evidence = load_renderer_registration()
    evidence['landmarks'][1] = deepcopy(evidence['landmarks'][0])
    with pytest.raises(ValueError, match='distinct'):
        validate_renderer_registration(evidence)
    evidence = load_renderer_registration()
    evidence['landmarks'][0]['catalog_reference_position_m'][0] += 1
    with pytest.raises(ValueError, match='inconsistent'):
        validate_renderer_registration(evidence)


@pytest.mark.parametrize('lat,lon,radius', [(True,0,1), (0,0,float('nan')), (91,0,1), (0,180,1), (0,0,0)])
def test_catalog_sphere_rejects_invalid_inputs(lat, lon, radius):
    with pytest.raises(ValueError):
        catalog_reference_position_m(lat,lon,radius)


def test_evidence_hash_mismatch_is_not_accepted(tmp_path):
    manifest = load_renderer_registration()
    for ref in [manifest['source_manifest_ref'], *(b['path'] for b in manifest['source_bindings'])]:
        (tmp_path/ref).write_bytes((ROOT/'data'/ref).read_bytes())
    target = tmp_path/'renderer-registration.manifest.json'
    target.write_text(json.dumps(manifest))
    assert load_renderer_registration(target)['release_gate']['overlays_allowed'] is False
    (tmp_path/manifest['source_manifest_ref']).write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        load_renderer_registration(target)


def test_release_boolean_cannot_override_missing_science():
    manifest = load_renderer_registration()
    manifest['release_gate']['overlays_allowed'] = True
    with pytest.raises(ValueError, match='block'):
        registration_release_gate(manifest)
