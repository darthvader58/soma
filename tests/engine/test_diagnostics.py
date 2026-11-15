"""Phase 2 artifacts must not imply contacts, power, or a complete skyline."""

from types import SimpleNamespace

from soma.diagnostics import _epochs, _horizon_classification, sampled_intervals
from soma.terrain import HorizonSampling
from soma.time import parse_utc
import pytest


def test_unknown_or_unconverged_horizon_cannot_make_clear_geometry():
    profile = SimpleNamespace(converged=False, bands=[SimpleNamespace(elevation_deg=0)],
                              sampling=SimpleNamespace(azimuth_step_deg=180))
    assert _horizon_classification(profile, 0, 45, .1)[0] == "unknown"


def test_neighbor_disagreement_is_unknown_rather_than_a_spurious_block():
    profile = SimpleNamespace(converged=True,
                              bands=[SimpleNamespace(elevation_deg=0), SimpleNamespace(elevation_deg=10)],
                              sampling=SimpleNamespace(azimuth_step_deg=180))
    assert _horizon_classification(profile, 90, 5, .1)[0] == "unknown"
    assert _horizon_classification(profile, 90, 11, .1)[0] == "clear"
    assert _horizon_classification(profile, 90, -1, .1)[0] == "blocked"


def test_geometric_intervals_preserve_unknown_transitions_and_sampling_limits():
    records = [{"epoch_utc": f"2026-11-14T09:0{i}:00Z", "classification": status,
                "classification_reason": "sampled_test"}
               for i, status in enumerate(("blocked", "blocked", "clear"))]
    intervals = sampled_intervals(records, 60)
    assert intervals[0]["classification"] == "blocked"
    assert intervals[1]["classification"] == "unknown"
    assert all(item["boundary_uncertainty_s"] == 60 for item in intervals)
    assert all("payload_rate_bps" not in item for item in intervals)


def test_uniform_unknown_keeps_the_specific_limiting_reason():
    records = [{"epoch_utc": epoch, "classification": "unknown", "classification_reason": "station_segment_not_assessed"}
               for epoch in ("2026-11-14T09:00:00Z", "2026-11-14T09:01:00Z")]
    assert sampled_intervals(records, 60)[0]["reason"] == "station_segment_not_assessed"


def test_sampling_budget_and_utc_resolution_fail_explicitly():
    with pytest.raises(ValueError, match="bounded"):
        HorizonSampling(1e-6, 1, 1, 5000, (10000, 20000), .01, 20000)
    start = parse_utc("2026-11-14T09:00:00Z")
    end = parse_utc("2026-11-14T09:00:00.000001Z")
    with pytest.raises(ValueError, match="microseconds"):
        _epochs(start, end, 1e-10)
