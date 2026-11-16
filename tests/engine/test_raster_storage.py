"""Hosted containers preserve exact sample bits and reject scientific/container drift."""
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from soma.datasets import (CANONICAL_RASTER_ENCODING, canonical_raster_profile,
                           raster_sample_identity, sha256, verify_raster_artifact)
from soma.validation import load_json, resource_directory


def test_canonical_encoding_is_explicit_and_legacy_profile_stays_unchanged(tmp_path):
    bits = np.array([0, 0x80000000, 0x7fc00001, 0x3f800000], dtype='<u4')
    values = bits.view('<f4').reshape(1,4)
    profile = {'driver': 'GTiff', 'width': 4, 'height': 1, 'count': 1,
               'dtype': 'float32', 'transform': from_origin(0,0,5,5),
               'compress': 'deflate', 'tiled': True, 'blockxsize': 256, 'blockysize': 256}
    assert canonical_raster_profile(profile, {}) == profile
    entry = {'storage_encoding': CANONICAL_RASTER_ENCODING}
    canonical = canonical_raster_profile(profile, entry)
    paths = [tmp_path/'first.tif', tmp_path/'second.tif']
    for path in paths:
        with rasterio.open(path, 'w', **canonical) as target:
            target.write(values, 1)
        assert path.read_bytes()[:4] == b'II*\x00'
        with rasterio.open(path) as source:
            assert source.compression is None
            assert source.block_shapes == [(1,4)]
            assert source.read(1).tobytes() == values.tobytes()
    assert paths[0].read_bytes() == paths[1].read_bytes()
    expected = {**raster_sample_identity(values), 'sha256': sha256(paths[0]), 'size_bytes': paths[0].stat().st_size}
    verify_raster_artifact(paths[1], values, canonical, expected)
    altered = values.copy()
    altered[0,3] = 2
    with pytest.raises(ValueError, match='Decoded terrain samples differ'):
        verify_raster_artifact(paths[1], altered, canonical, expected)
    with rasterio.open(paths[1], 'r+') as source:
        source.update_tags(unexpected='container mutation')
    with pytest.raises(ValueError, match='Raster encoding differs'):
        verify_raster_artifact(paths[1], values, canonical, expected)


def test_all_available_hosted_containers_match_pinned_samples_and_original_georeferencing():
    root = Path(__file__).resolve().parents[2]/'api'/'_data'
    manifests = ['lola-hosted-v2.manifest.json','lola-far-hosted-v2.manifest.json','physical-polar-hosted-v2.manifest.json']
    sources = ['lola-near-elevation-v2.tif','lola-near-count.tif', 'lola-far-elevation.tif',
               'lola-far-count.tif','lola-pole-elevation.tif','lola-pole-count.tif']
    entries = [entry for name in manifests for entry in load_json(resource_directory('data')/name)['files']]
    if any(not (root/name).is_file() for name in sources+[entry['path'] for entry in entries]):
        pytest.skip('Scientific source files are acquired separately')
    for original_name, entry in zip(sources, entries):
        path = root/entry['path']
        with rasterio.open(root/original_name) as original, rasterio.open(path) as canonical:
            before, after = original.read(1), canonical.read(1)
            assert before.tobytes() == after.tobytes()
            assert original.transform == canonical.transform
            assert original.crs == canonical.crs
            assert canonical.compression is None
            assert canonical.block_shapes == [(1,canonical.width)]
            verify_raster_artifact(path, after, canonical.profile, entry)


def test_available_raw_far_sources_reconstruct_exact_canonical_containers(tmp_path):
    import shutil
    from soma.datasets import extract_lola_far_cap
    cache = Path('/private/tmp/soma-phase2-data')
    names = ('ldec_64-southcap.img','ldec_64.lbl','ldem_64-southcap.img','ldem_64.lbl')
    if any(not (cache/name).is_file() for name in names):
        pytest.skip('Published raw PDS range extracts are acquired separately')
    for name in names:
        shutil.copyfile(cache/name, tmp_path/name)
    expected = load_json(resource_directory('data')/'lola-far-hosted-v2.manifest.json')
    report = extract_lola_far_cap(tmp_path, expected_manifest=expected)
    assert [entry['sha256'] for entry in report['files']] == [entry['sha256'] for entry in expected['files']]
