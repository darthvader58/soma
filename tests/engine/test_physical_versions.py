"""Explicit physical revisions must never fall back to a legacy terrain file."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from soma.api.delivery import scenario_template, validate_delivery_request
from soma.datasets import _preserve_legacy_near_snapshot, sha256
from soma.validation import (ScenarioValidationError, load_json,
                             physical_dataset_manifest, resource_directory, validate_scenario)


def test_explicit_revision_registry_and_hosted_boundary():
    v1, p1 = physical_dataset_manifest('physical-lola-de421-v1')
    v2, p2 = physical_dataset_manifest('physical-lola-de421-v2')
    assert p1 != p2 and v1['near_manifest_ref'] != v2['near_manifest_ref']
    from soma.api.delivery import SOURCE_MANIFESTS
    assert SOURCE_MANIFESTS[1] == v2['near_manifest_ref']
    scenario = scenario_template()
    assert scenario['dataset_manifest_ref'] == v2['id']
    validate_delivery_request({'scenario': scenario})
    scenario['dataset_manifest_ref'] = v1['id']
    validate_scenario(scenario)
    with pytest.raises(ValueError):
        validate_delivery_request({'scenario': scenario})
    for reference in ('physical-lola-de421-v3', '../physical-hosted-v2.manifest.json', 'synthetic-contract-v1'):
        with pytest.raises(ScenarioValidationError):
            physical_dataset_manifest(reference)


def test_legacy_unknown_mask_is_exact_hash_specific_and_v2_never_masks():
    old = load_json(resource_directory('data')/'lola-phase2.manifest.json')['files'][0]
    new = load_json(resource_directory('data')/'lola-hosted-v2.manifest.json')['files'][0]
    values = np.ones((2000,2000), dtype=np.float32)
    legacy = _preserve_legacy_near_snapshot(values.copy(), old)
    assert np.isnan(legacy[:1145]).all() and np.isfinite(legacy[1145:]).all()
    assert np.isfinite(_preserve_legacy_near_snapshot(values.copy(), new)).all()
    invalid = deepcopy(old)
    invalid['source_pixel_window'][0] += 1
    with pytest.raises(ValueError):
        _preserve_legacy_near_snapshot(values, invalid)


def test_missing_v2_source_does_not_use_present_legacy_file(tmp_path):
    from soma.terrain.physical import open_physical_dem
    (tmp_path/'lola-near-elevation.tif').write_bytes(b'legacy-source-must-not-be-read')
    near = load_json(resource_directory('data')/'lola-hosted-v2.manifest.json')
    far = load_json(resource_directory('data')/'lola-far-phase2.manifest.json')
    with pytest.raises((FileNotFoundError, ValueError, OSError)):
        open_physical_dem(tmp_path, near, far, policy='published_grid')
    assert not (tmp_path/'lola-near-elevation-v2-canonical.tif').exists()


def test_available_original_and_complete_sources_have_exact_hashes_and_footprints():
    import rasterio
    root = Path(__file__).resolve().parents[2]/'api'/'_data'
    old = load_json(resource_directory('data')/'lola-phase2.manifest.json')
    new = load_json(resource_directory('data')/'lola-hosted-v2.manifest.json')
    if any(not (root/entry['path']).is_file() for manifest in (old,new) for entry in manifest['files']):
        pytest.skip('Pinned scientific files are acquired separately')
    for manifest in (old,new):
        for entry in manifest['files']:
            assert (root/entry['path']).stat().st_size == entry['size_bytes']
            assert sha256(root/entry['path']) == entry['sha256']
    with rasterio.open(root/old['files'][0]['path']) as a, rasterio.open(root/new['files'][0]['path']) as b:
        legacy, complete = a.read(1), b.read(1)
    assert np.isfinite(legacy).sum() == 1710000
    assert np.isfinite(complete).sum() == 4000000
    np.testing.assert_array_equal(legacy[1145:], complete[1145:])
    for key in ('parent', 'parent_file_sha256', 'source_pixel_window', 'bounds_xy_m', 'transform', 'dtype'):
        assert old['files'][1][key] == new['files'][1][key]
    assert new['files'][1]['sample_sha256'] == 'a95c40e058e3da32a2b1b27d73d64490075ef594548c9b72e6eb8f325aaf162e'
