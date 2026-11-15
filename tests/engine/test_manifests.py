"""Check that Phase 1 provenance cannot masquerade as acquired terrain."""

import json
from datetime import datetime
from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[2] / "data" / "datasets.manifest.json"


def test_manifest_separates_synthetic_validation_domain_from_terrain():
    manifest = json.loads(MANIFEST.read_text())
    datasets = manifest["datasets"]
    assert len({item["id"] for item in datasets}) == len(datasets)
    synthetic = next(item for item in datasets if item["id"] == "synthetic-contract-v1")
    assert synthetic["input_class"] == "synthetic"
    assert synthetic["status"] == "synthetic_fixture_only"
    assert synthetic["latitude_bounds_deg"][0] >= -90
    assert synthetic["latitude_bounds_deg"][0] < synthetic["latitude_bounds_deg"][1] <= 90
    assert synthetic["longitude_bounds_deg_east"] == [-180, 180]
    start, end = (datetime.fromisoformat(synthetic["coverage"][key].replace("Z", "+00:00"))
                  for key in ("start_utc", "end_utc"))
    assert start.tzinfo is not None and end > start
    assert synthetic["reference_radius_m"] == 1737400
    assert synthetic["source_urls"] == []


def test_no_manifest_entry_claims_acquired_scientific_data():
    datasets = json.loads(MANIFEST.read_text())["datasets"]
    for dataset in datasets:
        assert dataset["files"] == []
        assert dataset["numerical_terrain_available"] is False
        assert dataset["ephemeris_available"] is False
        assert dataset["missing_terrain_policy"] == "unknown"
        assert dataset["frame"] == "MOON_ME_DE421"
        assert set(dataset["observer_heights"]) == {"antenna_height_m", "panel_height_m"}
    planned = [dataset for dataset in datasets if dataset["input_class"] == "published"]
    assert planned
    for dataset in planned:
        assert dataset["status"] == "planned_not_downloaded"
        assert dataset["sha256"] is None
        assert dataset["coverage"] is None
        assert dataset["latitude_bounds_deg"] is None
        assert dataset["longitude_bounds_deg_east"] is None
        assert all(url.startswith("https://pgda.gsfc.nasa.gov/") for url in dataset["source_urls"])
        assert "count_mask" in dataset["required_products"]
        assert "interpolated_elevation_fill" in dataset["required_products"]
