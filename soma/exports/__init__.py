"""Deterministic, structured exports of the authoritative engine run."""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
import csv
import hashlib
import io
from importlib import metadata
import json
import platform
import zipfile

from soma import __version__
from soma.time import parse_utc
from soma.validation import scenario_sha256, validate_document
from soma.exports.display import display_data, renderer_registration


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def summary(run):
    result = run["result"]
    metrics = {"route_family": None, "route_nodes": None, "mean_relay_wait_s": None,
               "lander_communications_energy_wh": None, "minimum_stored_energy_wh": None,
               "minimum_margin_above_reserve_wh": None}
    replay = run.get("validation")
    if result["status"] == "feasible_under_assumptions" and isinstance(replay, dict) and replay.get("passed") is True:
        scenario = run["scenario"]
        lander = scenario["lander"]["id"]
        contacts = {c["contact_id"]: c for c in result["contacts"]}
        records = [(a, contacts[a["contact_id"]]) for a in result["allocations"]]
        relays = sorted({node for _, c in records for node in (c["sender"], c["receiver"]) if node in scenario["relay_refs"]})
        stations = sorted({c["receiver"] for _, c in records if c["receiver"] in scenario["station_refs"]})
        metrics["route_family"] = "single_lunar_relay" if relays else "direct_to_earth"
        metrics["route_nodes"] = [lander, *relays, *stations]
        weighted_wait, forwarded_bytes = 0., 0
        for outgoing, contact in records:
            if contact["sender"] not in relays:
                continue
            incoming = next(a for a, c in records if c["receiver"] == contact["sender"]
                            and (a["chunk_id"], a["byte_offset"], a["byte_length"]) ==
                            (outgoing["chunk_id"], outgoing["byte_offset"], outgoing["byte_length"]))
            wait = (parse_utc(outgoing["source_transmit_interval"]["start_utc"]) - parse_utc(incoming["byte_available_utc"])).total_seconds()
            weighted_wait += outgoing["byte_length"] * wait
            forwarded_bytes += outgoing["byte_length"]
        metrics["mean_relay_wait_s"] = weighted_wait / forwarded_bytes if forwarded_bytes else 0.
        hardware = next(p for p in scenario["profiles"]["hardware"] if p["id"] == scenario["hardware_profile_ref"])
        metrics["lander_communications_energy_wh"] = _lander_radio_energy_wh(scenario, records)
        history = [p["stored_energy_wh"] for p in replay.get("energy_history", []) if p["node_id"] == lander]
        if history and all(value is not None for value in history):
            minimum = min(history)
            metrics["minimum_stored_energy_wh"] = minimum
            metrics["minimum_margin_above_reserve_wh"] = minimum - hardware["battery"]["reserve_wh"]
    return deepcopy({key: result[key] for key in (
        "scenario_id", "scenario_sha256", "status", "solver_status", "model_fidelity",
        "delivered_bytes", "final_byte_arrival_utc", "assumptions", "warnings",
    )} | {"artifact_type": "soma_run_summary", "format_version": "0.4.0",
          "limiting_reason": result["provenance"]["reason"], **metrics,
          "replay": replay, "details": run.get("details", {})})


def _lander_radio_energy_wh(scenario, records):
    lander = scenario["lander"]["id"]
    hardware = next(p for p in scenario["profiles"]["hardware"] if p["id"] == scenario["hardware_profile_ref"])
    terminals = {t["id"]: t for t in hardware["terminals"]}
    occupancy = {}
    def duration(seconds):
        return timedelta(microseconds=int((Decimal(str(seconds)) * 1000000).to_integral_value(rounding=ROUND_CEILING)))
    for allocation, contact in records:
        for direction, node, terminal_key, interval_key in (
            ("tx", contact["sender"], "sender_terminal_id", "source_transmit_interval"),
            ("rx", contact["receiver"], "receiver_terminal_id", "receiver_occupancy_interval"),
        ):
            if node != lander:
                continue
            terminal = terminals[contact[terminal_key]]
            interval = allocation[interval_key]
            start = parse_utc(interval["start_utc"]) - duration(terminal["acquisition_s"])
            end = parse_utc(interval["end_utc"]) + duration(terminal["teardown_s"])
            occupancy.setdefault((terminal["id"], direction), []).append((start, end))
    energy = 0.
    for (identifier, direction), intervals in occupancy.items():
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        energy += sum((end-start).total_seconds() for start, end in merged) * terminals[identifier][f"{direction}_electrical_w"] / 3600
    return energy


def display_payload(run, display=None):
    """Preserve exact epochs and the registration status of this run."""
    result = run["result"]
    registration = (display or display_data(run))['registration']
    payload = [{"id": "document", "version": "1.0", "name": "SOMA planning result"}, {
        "id": "soma-run", "properties": {
            "scenario_sha256": result["scenario_sha256"],
            "registration_status": registration['status'],
            "map_registration_passed": registration['release_gate']['map_registration_passed'],
            "model_fidelity": result["model_fidelity"],
            "allocations_json": json.dumps(result["allocations"], sort_keys=True, allow_nan=False),
            "warnings_json": json.dumps(result["warnings"], ensure_ascii=False),
        },
    }]
    display = display or display_data(run)
    for index, state in enumerate(display.get('renderer_states', [])):
        # An instant packet cannot extend a sampled trajectory between epochs.
        payload.append({'id':f"{state['target']}-sample-{index}",
            'availability':state['epoch']+'/'+state['epoch'],
            'position':{'referenceFrame':'FIXED','cartesian':state['position']},
            'properties':{'source_frame':state['source_frame'],'renderer_frame':state['frame'],
                'origin':state['origin'],'position_unit':state['position_unit'],
                'epoch_utc':state['epoch'],'provenance_label':state['provenance_label'],
                'transform_ref':state['transform_ref']}})
    return payload


def _csv(headers, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def explanation(run, display=None):
    result = run["result"]
    lines = ["# SOMA delivery plan", "", f"Outcome: {result['status']}.",
             f"Solver: {result['solver_status']}. Model: {result['model_fidelity']}.",
             "This is a planning model under declared assumptions.",
             f"Delivered bytes: {result['delivered_bytes'] if result['delivered_bytes'] is not None else 'unknown'}.",
             f"Final byte arrival UTC: {result['final_byte_arrival_utc'] or 'unknown'}.", ""]
    contacts = {contact["contact_id"]: contact for contact in result["contacts"]}
    for allocation in result["allocations"]:
        contact = contacts[allocation["contact_id"]]
        tx, rx = allocation["source_transmit_interval"], allocation["receiver_occupancy_interval"]
        lines.append(f"- {allocation['chunk_id']}: {allocation['byte_length']} bytes from {contact['sender']} to {contact['receiver']} via {contact['contact_id']}; source transmit {tx['start_utc']} to {tx['end_utc']}; receiver occupancy {rx['start_utc']} to {rx['end_utc']}; bytes available {allocation['byte_available_utc']}.")
    for storage in result["storage_intervals"]:
        interval = storage["interval"]
        lines.append(f"- Storage: {storage['node_id']} holds {storage['byte_length']} bytes of {storage['chunk_id']} from {interval['start_utc']} to {interval['end_utc']}.")
    for label in ("assumptions", "warnings"):
        lines.extend(["", label.capitalize() + ":", ""])
        lines.extend("- " + value for value in result[label])
    registration = (display or display_data(run))['registration']
    lines.extend(["", "Planning details: " + json.dumps(run.get("details", {}), sort_keys=True, ensure_ascii=False), "",
                  f"Renderer registration: {registration['status']}; map gate passed for this site: {registration['release_gate']['map_registration_passed']}.",
                  "Registration applies only to the corrected representation within its certified region. Missing spacecraft states remain unknown. Schedule epochs are unchanged.", ""])
    return "\n".join(lines).encode("utf-8")


def _software_versions():
    versions = {"soma": __version__, "python": platform.python_version()}
    for package in ("pulp", "spiceypy", "rasterio", "numpy", "fastapi", "uvicorn", "jsonschema", "rfc8785"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def create_run_package(run):
    """Return byte-stable ZIP, with checksums for every member except manifest."""
    run = deepcopy(run)
    scenario, result = run["scenario"], run["result"]
    validate_document(result, "result")
    if scenario_sha256(scenario) != result["scenario_sha256"]:
        raise ValueError("Result scenario hash does not match the exported scenario")
    display = display_data(run)
    files = {"scenario.json": json_bytes(scenario), "result.json": json_bytes(result),
             "summary.json": json_bytes(summary(run)), "display.czml": json_bytes(display_payload(run, display)),
             "display-data.json": json_bytes(display),
             "renderer-registration.json": json_bytes(display['registration']),
             "explanation.md": explanation(run, display)}
    if display.get('renderer_conversion') is not None:
        files['renderer-conversion.json'] = json_bytes(display['renderer_conversion'])
    if "analysis_inputs" in run:
        files["analysis-inputs.json"] = json_bytes(run["analysis_inputs"])
    if "validation" in run:
        files["replay.json"] = json_bytes(run["validation"])
    files["contacts.csv"] = _csv([
        "contact_id", "sender", "receiver", "sender_terminal_id", "receiver_terminal_id", "source_transmit_start_utc", "source_transmit_end_utc", "payload_rate_bits_per_second", "available_capacity_bits", "one_way_delay_seconds", "rate_method", "service_provenance", "quality_flags_json"],
        [[c["contact_id"], c["sender"], c["receiver"], c["sender_terminal_id"], c["receiver_terminal_id"], c["source_transmit_window"]["start_utc"], c["source_transmit_window"]["end_utc"], c["payload_rate_bps"], c["available_capacity_bits"], c["one_way_delay"]["seconds"], c["rate_method"], c["service_provenance"], json.dumps(c["quality_flags"])] for c in result["contacts"]])
    contacts = {c["contact_id"]: c for c in result["contacts"]}
    files["schedule.csv"] = _csv(["allocation_id", "chunk_id", "byte_offset_bytes", "byte_length_bytes", "contact_id", "sender", "receiver", "source_transmit_start_utc", "source_transmit_end_utc", "receiver_occupancy_start_utc", "receiver_occupancy_end_utc", "byte_available_utc"],
        [[a["allocation_id"], a["chunk_id"], a["byte_offset"], a["byte_length"], a["contact_id"], contacts[a["contact_id"]]["sender"], contacts[a["contact_id"]]["receiver"], a["source_transmit_interval"]["start_utc"], a["source_transmit_interval"]["end_utc"], a["receiver_occupancy_interval"]["start_utc"], a["receiver_occupancy_interval"]["end_utc"], a["byte_available_utc"]] for a in result["allocations"]])
    files["energy.csv"] = _csv(["node_id", "epoch_utc", "stored_energy_wh"], [[v["node_id"], v["epoch_utc"], v["stored_energy_wh"]] for v in result["energy_history"]])
    files["buffer-history.csv"] = _csv(["node_id", "epoch_utc", "stored_bytes"], [[v["node_id"], v["epoch_utc"], v["stored_bytes"]] for v in result["buffer_history"]])
    files["run-manifest.json"] = json_bytes({
        "format_version": "1", "scenario_sha256": result["scenario_sha256"],
        "software_versions": _software_versions() | run.get("details", {}).get("software", {}).get("versions", {}),
        "csv_unknown_representation": "empty field; never zero", "time_convention": "source transmit UTC; receiver occupancy and availability exported separately",
        "assumptions": result["assumptions"], "warnings": result["warnings"],
        "provenance": result["provenance"], "details": run.get("details", {}),
        "files": {name: {"sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)} for name, content in sorted(files.items())},
    })
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return output.getvalue()
