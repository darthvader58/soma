"""Delivery boundary; standalone diagnostics do not constitute a delivery plan."""

from soma import __version__
from soma.validation import scenario_sha256, validate_document, validate_scenario


def plan_delivery(scenario: dict) -> dict:
    """Return an auditable unknown result rather than a fabricated schedule."""
    snapshot = validate_scenario(scenario)
    result = {
        "run_version": snapshot["run_version"],
        "scenario_id": snapshot["scenario_id"],
        "scenario_sha256": scenario_sha256(snapshot),
        "status": "unknown",
        "solver_status": "unresolved",
        "model_fidelity": "not_implemented",
        "assumptions": [
            "Rate method: " + snapshot["rate_method"],
            "Pointing: " + snapshot["pointing_assumption"],
            "Service: " + snapshot["service_assumption_label"],
            "Synthetic fixture inputs do not establish lunar visibility or link closure.",
        ],
        "warnings": [
            "The integrated delivery-planning pipeline, energy-constrained optimization "
            "and independent schedule replay are not implemented. "
            "Standalone Phase 2 geometry and Phase 3 illumination, power and contact diagnostics "
            "do not establish delivery feasibility.",
            "No feasibility or delivery metrics have been calculated.",
        ],
        "contacts": [],
        "allocations": [],
        "storage_intervals": [],
        "energy_history": [],
        "buffer_history": [],
        "delivered_bytes": None,
        "final_byte_arrival_utc": None,
        "provenance": {
            "engine_version": __version__,
            "implementation_status": "not_implemented",
            "reason": "The delivery planner has not selected or validated a schedule. Geometry, illumination, power and contact diagnostics are separate artifacts.",
            "kernel_manifest_ref": None,
            "dataset_manifest_ref": snapshot["dataset_manifest_ref"],
            "source_urls": sorted({
                url for entry in snapshot["input_provenance"] for url in entry["source_urls"]
            }),
            "input_provenance": snapshot["input_provenance"],
        },
    }
    validate_document(result, "result")
    return result
