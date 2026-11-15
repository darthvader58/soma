"""Completion follows checked evidence, with public hosting kept separate."""

import hashlib
import json
from pathlib import Path
import shutil

from soma.verification.completion import verify_phase6


ROOT = Path(__file__).resolve().parents[2]


def evidence_copy(tmp_path):
    manifest = json.loads((ROOT/'data/phase6-evidence.manifest.json').read_text())
    paths = {binding['path'] for binding in manifest['files']}
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'data').glob('*.manifest.json'))
    for name in paths:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return manifest


def test_recorded_phase6_passes_without_claiming_public_deployment_approval():
    report = verify_phase6(ROOT)
    assert report['phase6_complete'], report['errors']
    assert report['phase7_prerequisite_met']
    assert not report['phase7_started']
    assert not report['public_deployment_authorized']
    evidence = json.loads((ROOT/'data/phase6-evidence.manifest.json').read_text())
    assert not evidence['public_deployment']['corrected_stream_permission_established']


def test_claimed_completion_cannot_hide_a_modified_archive(tmp_path):
    manifest = evidence_copy(tmp_path)
    name = 'fixtures/phase-6/demo/relay-later/run.zip'
    archive = tmp_path/name
    archive.write_bytes(archive.read_bytes()+b'altered after review')
    manifest['phase6_complete'] = True
    (tmp_path/'data/phase6-evidence.manifest.json').write_text(json.dumps(manifest))
    report = verify_phase6(tmp_path)
    assert not report['phase6_complete']
    assert any(error['check'] == 'evidence:'+name for error in report['errors'])


def test_rehashed_receipt_cannot_turn_agent_review_into_a_human_study(tmp_path):
    manifest = evidence_copy(tmp_path)
    name = 'fixtures/phase-6/independent-review.json'
    path = tmp_path/name
    receipt = json.loads(path.read_text())
    receipt['actor']['human_usability_study'] = True
    path.write_text(json.dumps(receipt))
    for binding in manifest['files']:
        if binding['path'] == name:
            binding.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           size_bytes=path.stat().st_size)
    (tmp_path/'data/phase6-evidence.manifest.json').write_text(json.dumps(manifest))
    report = verify_phase6(tmp_path)
    assert not report['phase6_complete']
    assert any(error['check'] == 'review_actor_labeled_honestly' for error in report['errors'])
