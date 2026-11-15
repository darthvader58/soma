"""Verify that the handoff identifies the exact local inputs it describes."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_handoff_file_checksums_and_review_status():
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())
    assert manifest["scientific_analysis_performed"] is True
    assert manifest["analysis_scope"] == "synthetic_assumed_rate_delivery_runs_through_phase_5"
    assert manifest["schema_review"]["status"] == "phase_1_interface_review_completed"
    assert manifest["schema_review"]["review_type"] == "automated_agent_review"
    assert manifest["schema_review"]["human_developer_b_approval"] is False
    files = manifest["files"]
    paths = {entry["path"] for entry in files}
    assert len(paths) == len(files)
    assert "schemas/scenario.schema.json" in paths
    assert "data/datasets.manifest.json" in paths
    for family in ("synthetic-direct", "synthetic-relay"):
        for name in ("scenario.json", "contacts.json", "expected.json"):
            assert f"fixtures/{family}/{name}" in paths
    for entry in files:
        assert hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
