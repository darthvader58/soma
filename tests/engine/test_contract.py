from copy import deepcopy
import json
from pathlib import Path

import pytest

from soma import plan_delivery
from soma.validation import (
    ScenarioValidationError, data_volume_bytes, load_json, load_scenario,
    scenario_sha256, schema_registry, validate_document, validate_scenario,
)


ROOT = Path(__file__).resolve().parents[2]


def test_all_schemas_are_valid_and_local():
    schemas, _ = schema_registry()
    assert {"scenario", "result", "contact", "allocation", "state", "common"} == set(schemas)


@pytest.mark.parametrize("name", ["synthetic-direct", "synthetic-relay"])
def test_standalone_scenario_and_contacts(name):
    scenario = load_scenario(ROOT / "fixtures" / name / "scenario.json")
    assert data_volume_bytes(scenario["data_volume"]) == 104_857_600
    for contact in load_json(ROOT / "fixtures" / name / "contacts.json"):
        validate_document(contact, "contact")
    for allocation in load_json(ROOT / "fixtures" / name / "expected.json")["allocations"]:
        validate_document(allocation, "allocation")


def test_omitted_storage_limit_fails_then_explicit_limit_passes(relay_scenario):
    capacity = relay_scenario["profiles"]["relays"][0].pop("storage_capacity_bytes")
    with pytest.raises(ScenarioValidationError, match="storage_capacity_bytes"):
        validate_scenario(relay_scenario)
    relay_scenario["profiles"]["relays"][0]["storage_capacity_bytes"] = capacity
    validate_scenario(relay_scenario)


@pytest.mark.parametrize("field", [
    "run_version", "lander", "data_ready_utc", "data_volume", "deadline_utc",
    "analysis_horizon", "hardware_profile_ref", "relay_refs", "station_refs",
    "route_families", "rate_method", "pointing_assumption", "service_assumption_label",
])
def test_required_scenario_fields_are_not_defaulted(relay_scenario, field):
    del relay_scenario[field]
    with pytest.raises(ScenarioValidationError, match=field):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("field", [
    "frame", "reference_radius_m", "elevation_datum", "antenna_height_m", "panel_height_m",
])
def test_required_location_metadata(relay_scenario, field):
    del relay_scenario["lander"][field]
    with pytest.raises(ScenarioValidationError, match=field):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("volume", [100, {"value": 100}, {"value": 100, "unit": "MB"}, {"value": True, "unit": "MiB"}])
def test_volume_requires_explicit_supported_units(relay_scenario, volume):
    relay_scenario["data_volume"] = volume
    with pytest.raises(ScenarioValidationError):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("coordinates", [(91, 0), (-89, 180), (0, 0), (-89, -181)])
def test_unsupported_coordinates(relay_scenario, coordinates):
    relay_scenario["lander"]["latitude_deg"], relay_scenario["lander"]["longitude_deg_east"] = coordinates
    with pytest.raises(ScenarioValidationError):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("epoch", ["2026-11-14T08:50:00", "2026-02-30T08:50:00Z", "2026-11-14T08:50:00-00:00"])
def test_invalid_or_unqualified_dates(relay_scenario, epoch):
    relay_scenario["data_ready_utc"] = epoch
    with pytest.raises(ScenarioValidationError):
        validate_scenario(relay_scenario)


def test_unsupported_date_domain(relay_scenario):
    relay_scenario["analysis_horizon"]["start_utc"] = "2026-11-13T08:50:00Z"
    with pytest.raises(ScenarioValidationError, match="Unsupported dates"):
        validate_scenario(relay_scenario)


def test_deadline_is_inside_horizon(relay_scenario):
    relay_scenario["deadline_utc"] = "2026-11-14T11:00:00Z"
    with pytest.raises(ScenarioValidationError, match="horizon"):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("reference", ["hardware_profile_ref", "relay_refs", "station_refs"])
def test_profile_references_must_resolve(relay_scenario, reference):
    relay_scenario[reference] = "missing" if reference == "hardware_profile_ref" else ["missing"]
    with pytest.raises(ScenarioValidationError, match="resolve"):
        validate_scenario(relay_scenario)


def test_invalid_battery_state_rejected(relay_scenario):
    battery = relay_scenario["profiles"]["hardware"][0]["battery"]
    battery["initial_energy_wh"] = battery["capacity_wh"] + 1
    with pytest.raises(ScenarioValidationError, match="Battery"):
        validate_scenario(relay_scenario)


def test_earth_and_lunar_frames_cannot_be_swapped(relay_scenario):
    relay_scenario["profiles"]["stations"][0]["frame"] = "MOON_ME_DE421"
    with pytest.raises(ScenarioValidationError):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numbers_rejected(relay_scenario, value):
    relay_scenario["lander"]["elevation_m"] = value
    with pytest.raises(ScenarioValidationError, match="finite"):
        validate_scenario(relay_scenario)


@pytest.mark.parametrize("text", ['{"id": 1, "id": 2}', '{"x": NaN}', '{"x": Infinity}', '{"x": 1e999}'])
def test_nonstandard_json_rejected(tmp_path, text):
    path = tmp_path / "invalid.json"
    path.write_text(text)
    with pytest.raises(ScenarioValidationError):
        document = load_json(path)
        validate_document(document, "scenario")


def test_inputs_are_detached_and_run_is_deterministic(relay_scenario):
    relay_scenario["lander"]["latitude_deg"] = -88.5
    original = deepcopy(relay_scenario)
    result = plan_delivery(relay_scenario)
    assert result == plan_delivery(relay_scenario)
    assert relay_scenario == original
    assert result["scenario_sha256"] == scenario_sha256(relay_scenario)
    result["provenance"]["input_provenance"][0]["description"] = "changed"
    assert relay_scenario == original
    snapshot = validate_scenario(relay_scenario)
    snapshot["lander"]["panel_height_m"] += 1
    assert relay_scenario == original


def test_unsupported_coverage_does_not_invent_results(relay_scenario):
    relay_scenario["lander"]["latitude_deg"] = -88.5
    result = plan_delivery(relay_scenario)
    validate_document(result, "result")
    assert result["status"] == "unknown"
    assert result["solver_status"] == "unresolved"
    assert result["model_fidelity"] == "not_implemented"
    assert result["delivered_bytes"] is None
    assert result["final_byte_arrival_utc"] is None
    for field in ("contacts", "allocations", "storage_intervals", "energy_history", "buffer_history"):
        assert result[field] == []
    assert result["provenance"]["implementation_status"] == "not_implemented"


def test_unimplemented_result_cannot_claim_feasibility(relay_scenario):
    relay_scenario["lander"]["latitude_deg"] = -88.5
    result = plan_delivery(relay_scenario)
    result["status"] = "feasible_under_assumptions"
    with pytest.raises(ScenarioValidationError):
        validate_document(result, "result")


def test_unresolved_solver_cannot_claim_proven_infeasibility(relay_scenario):
    relay_scenario["lander"]["latitude_deg"] = -88.5
    result = plan_delivery(relay_scenario)
    result.update(status="infeasible_in_model", model_fidelity="assumed_rate_simulation")
    with pytest.raises(ScenarioValidationError):
        validate_document(result, "result")


def test_contact_must_use_source_transmit_epochs():
    contact = load_json(ROOT / "fixtures/synthetic-relay/contacts.json")[0]
    contact["timing_convention"] = "receiver_arrival_epochs"
    with pytest.raises(ScenarioValidationError):
        validate_document(contact, "contact")


@pytest.mark.parametrize("epoch", ["2026-02-30T08:50:00Z", "2026-11-14T08:50:00-00:00"])
def test_contact_date_format_is_enforced_without_optional_dependencies(epoch):
    contact = load_json(ROOT / "fixtures/synthetic-relay/contacts.json")[0]
    contact["source_transmit_window"]["start_utc"] = epoch
    with pytest.raises(ScenarioValidationError):
        validate_document(contact, "contact")


def test_changed_input_changes_hash(relay_scenario):
    old_hash = scenario_sha256(relay_scenario)
    relay_scenario["lander"]["antenna_height_m"] += 1
    assert old_hash != scenario_sha256(relay_scenario)
    reordered = json.loads(json.dumps(relay_scenario, sort_keys=True))
    assert scenario_sha256(reordered) == scenario_sha256(relay_scenario)


def test_hash_treats_equivalent_json_numbers_consistently():
    assert scenario_sha256({"height": 1}) == scenario_sha256({"height": 1.0})
    assert scenario_sha256({"value": -0.0}) == scenario_sha256({"value": 0})
    with pytest.raises(ScenarioValidationError, match="safe range"):
        scenario_sha256({"value": 9_007_199_254_740_992})


def test_cross_language_canonical_hash_vectors():
    vectors = load_json(ROOT / "fixtures/hash-vectors.json")
    for vector in vectors:
        assert scenario_sha256(vector["input"]) == vector["sha256"]


@pytest.mark.parametrize("scale,epoch,representation,valid", [
    ("UTC", "2026-11-14T08:50:00Z", "rfc3339", True),
    ("UTC", "not-a-time", "rfc3339", False),
    ("UTC", 0, "rfc3339", False),
    ("TDB", 0, "seconds_past_j2000_tdb", True),
    ("TDB", "2026-11-14T08:50:00Z", "seconds_past_j2000_tdb", False),
    ("TDB", 0, "rfc3339", False),
])
def test_state_epoch_representation_matches_time_scale(scale, epoch, representation, valid):
    state = {
        "target": "synthetic-relay", "origin": "MOON", "frame": "J2000",
        "epoch": epoch, "epoch_format": representation, "time_scale": scale,
        "position": [1, 2, 3], "position_unit": "m", "provenance_label": "synthetic test only",
    }
    if valid:
        validate_document(state, "state")
    else:
        with pytest.raises(ScenarioValidationError):
            validate_document(state, "state")
