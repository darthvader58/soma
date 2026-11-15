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


def unresolved():
    return validate_renderer_registration(json.loads((ROOT/'fixtures/registration/unresolved-registration-v0.1.json').read_text()))


def test_archived_raw_registration_preserves_unknowns_and_blocks_release():
    evidence = unresolved()
    assert evidence['source_frame'] == 'MOON_ME_DE421'
    assert evidence['renderer_frame'] is None
    assert evidence['transform_column_major'] is None
    assert evidence['tolerance_m'] is None
    assert registration_release_gate(evidence)['overlays_allowed'] is False
    assert len(evidence['landmarks']) >= 4
    assert all(p['residual_m'] is None for p in evidence['landmarks'])
    evidence['release_gate']['overlays_allowed'] = True
    assert unresolved()['release_gate']['overlays_allowed'] is False


@pytest.mark.parametrize('field,value', [
    ('renderer_frame', 'IAU_MOON'),
    ('transform_column_major', [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),
    ('status', 'registered'), ('tolerance_m', 5), ('origin', 'EARTH'),
    ('position_unit', 'km'),
])
def test_unresolved_metadata_cannot_be_promoted_by_defaults(field, value):
    evidence = unresolved()
    evidence[field] = value
    with pytest.raises(ValueError):
        validate_renderer_registration(evidence)


def test_algebraic_positions_are_not_independent_residuals():
    evidence = unresolved()
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
    evidence = unresolved()
    evidence['landmarks'][1] = deepcopy(evidence['landmarks'][0])
    with pytest.raises(ValueError, match='distinct'):
        validate_renderer_registration(evidence)
    evidence = unresolved()
    evidence['landmarks'][0]['catalog_reference_position_m'][0] += 1
    with pytest.raises(ValueError, match='inconsistent'):
        validate_renderer_registration(evidence)


@pytest.mark.parametrize('lat,lon,radius', [(True,0,1), (0,0,float('nan')), (91,0,1), (0,180,1), (0,0,0)])
def test_catalog_sphere_rejects_invalid_inputs(lat, lon, radius):
    with pytest.raises(ValueError):
        catalog_reference_position_m(lat,lon,radius)


def test_evidence_hash_mismatch_is_not_accepted(tmp_path):
    manifest = unresolved()
    for ref in [manifest['source_manifest_ref'], *(b['path'] for b in manifest['source_bindings'])]:
        (tmp_path/ref).write_bytes((ROOT/'data'/ref).read_bytes())
    target = tmp_path/'renderer-registration.manifest.json'
    target.write_text(json.dumps(manifest))
    assert load_renderer_registration(target)['release_gate']['overlays_allowed'] is False
    (tmp_path/manifest['source_manifest_ref']).write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        load_renderer_registration(target)


def test_release_boolean_cannot_override_missing_science():
    manifest = unresolved()
    manifest['release_gate']['overlays_allowed'] = True
    with pytest.raises(ValueError, match='block'):
        registration_release_gate(manifest)


def test_corrected_scene_requires_measured_features_and_site_scope():
    from soma.geometry.registration import renderer_registration_for_site
    evidence=load_renderer_registration()
    assert evidence['version']=='0.2.0'
    assert evidence['representation']=='engine_corrected_mesh'
    assert evidence['release_gate']['map_registration_passed']
    assert all(0<p['residual_m']<.3 for p in evidence['landmarks'])
    inside=renderer_registration_for_site({'latitude_deg':-89,'longitude_deg_east':0})
    outside=renderer_registration_for_site({'latitude_deg':0,'longitude_deg_east':0})
    assert registration_release_gate(inside)['overlays_allowed']
    assert not registration_release_gate(outside)['overlays_allowed']
    inside['landmarks'][0]['residual_m']=0
    with pytest.raises(ValueError,match='residual'):
        validate_renderer_registration(inside)


def test_packaged_evidence_loads_without_frontend_or_fixture_directories(tmp_path):
    import shutil
    data = tmp_path/'data'
    data.mkdir()
    for path in (ROOT/'data').glob('*.manifest.json'):
        shutil.copyfile(path, data/path.name)
    loaded = load_renderer_registration(data/'renderer-registration.manifest.json')
    assert loaded['release_gate']['map_registration_passed']
    assert not (tmp_path/'web').exists()
    assert not (tmp_path/'fixtures').exists()


def test_rehashed_conversion_cannot_reuse_measurements_of_different_parameters(tmp_path):
    import hashlib
    import shutil
    data = tmp_path/'data'
    data.mkdir()
    for path in (ROOT/'data').glob('*.manifest.json'):
        shutil.copyfile(path, data/path.name)
    target = data/'renderer-registration.manifest.json'
    certificate = json.loads(target.read_text())
    conversion_path = data/certificate['conversion_manifest_ref']
    conversion = json.loads(conversion_path.read_text())
    conversion['semimajor_m'] += 20
    conversion_path.write_text(json.dumps(conversion))
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    certificate['conversion_manifest_sha256'] = digest(conversion_path)
    evidence_path = data/certificate['evidence_manifest_ref']
    evidence = json.loads(evidence_path.read_text())
    for binding in evidence['files']:
        if binding['path'] == 'data/'+conversion_path.name:
            binding['sha256'] = digest(conversion_path)
    evidence_path.write_text(json.dumps(evidence))
    for binding in certificate['source_bindings']:
        if binding['path'] in (conversion_path.name,evidence_path.name):
            binding['sha256'] = digest(data/binding['path'])
    target.write_text(json.dumps(certificate))
    with pytest.raises(ValueError, match='measured scene|Measured scene'):
        load_renderer_registration(target)
