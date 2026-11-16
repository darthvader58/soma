from copy import deepcopy
import json

import pytest

import soma.datasets as datasets
from soma.validation import load_json, resource_directory


def test_retained_earth_orientation_reproduces_pinned_bytes_without_network(tmp_path, monkeypatch):
    manifest = load_json(resource_directory('data')/'de421-phase2.manifest.json')
    entry = next(item for item in manifest['kernels'] if item['role'] == 'earth_orientation')
    manifest['kernels'] = [entry]
    path = tmp_path/'manifest.json'
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(datasets, 'urlopen', lambda *a, **k: pytest.fail('Retained source required a network download'))
    datasets.fetch_kernels(path, tmp_path/'acquired')
    result = tmp_path/'acquired'/entry['path']
    assert result.stat().st_size == entry['size_bytes']
    assert datasets.sha256(result) == entry['sha256']

    bad = deepcopy(manifest)
    bad['kernels'][0]['sha256'] = '0'*64
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match='Retained kernel SHA256 mismatch'):
        datasets.fetch_kernels(path, tmp_path/'wrong-hash')
