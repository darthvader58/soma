import json
from pathlib import Path
import shutil

from soma.verification.physical_completion import _sampling_source_compatible


def test_legacy_comparison_binds_current_source_and_exact_archived_inputs(tmp_path):
    root = Path(__file__).resolve().parents[2]
    paths = ('soma/physical.py', 'data/physical-source-compatibility.manifest.json',
             'fixtures/physical-south-pole/sampling-verification.json')
    for relative in paths:
        destination = tmp_path/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/relative, destination)
    sampling = json.loads((tmp_path/paths[2]).read_text())
    assert _sampling_source_compatible(tmp_path, sampling)

    report_path = tmp_path/paths[1]
    report = json.loads(report_path.read_text())
    report['comparisons'][0]['current_inputs_sha256'] = '0'*64
    report_path.write_text(json.dumps(report))
    assert not _sampling_source_compatible(tmp_path, sampling)

    shutil.copyfile(root/paths[1], report_path)
    (tmp_path/paths[0]).write_text('changed implementation')
    assert not _sampling_source_compatible(tmp_path, sampling)
