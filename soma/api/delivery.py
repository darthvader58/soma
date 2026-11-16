"""Bounded, synchronous delivery planning with native replay and exact exports."""
from copy import deepcopy
import asyncio
import base64
import gzip
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

from fastapi import APIRouter, HTTPException, Request, Response

from soma.api.native import preload_hosted_libraries
from soma.api.processes import start_private_interpreter, stop_private_interpreter
from soma.time import parse_utc
from soma.validation import (ScenarioValidationError, _check_json_values, _reject_constant,
                             _unique_keys, data_volume_bytes, load_json, resource_directory,
                             scenario_sha256, validate_document, validate_scenario, physical_dataset_manifest)
from soma.api.research_jobs import _atomic_write, configure_numerical_threads, encode

API_VERSION = "1.0.0"
LIMITS = {
    "max_duration_s": 21600, "max_data_volume_bytes": 67108864, "max_chunks": 4,
    "min_bin_s": 60, "max_bin_s": 300, "max_solver_time_s": 10,
    "max_stations": 3, "max_relays": 1, "max_request_bytes": 128000,
    "max_response_wire_bytes": 4000000, "max_response_decoded_bytes": 16000000,
    "max_export_zip_bytes": 16000000, "max_worker_seconds": 240,
    "worker_address_space_bytes": 1536 * 1024 * 1024,
    "worker_tree_rss_bytes": 1024 * 1024 * 1024,
}
HOSTED_MODEL_ID = "physical-lola-de421-v2"
DEFAULT_OPTIONS = {"chunk_bytes": 16777216, "bin_s": 60, "time_limit_s": 10}
SOURCE_MANIFESTS = ("de421-phase2.manifest.json", "lola-hosted-v2.manifest.json",
                    "lola-far-hosted-v2.manifest.json", "physical-polar-hosted-v2.manifest.json")


class DeliverySourceError(RuntimeError):
    """Required local scientific data or executable solver is unavailable."""


def _data_root(value):
    return Path(value or os.environ.get("SOMA_DELIVERY_DATA_ROOT") or os.environ.get("SOMA_DATA_ROOT")
                or os.environ.get("SOMA_RESEARCH_DATA_ROOT") or "/private/tmp/soma-phase2-data").resolve()


def scenario_template():
    """Declared educational inputs; no expected outcome or contact is stored."""
    window = {"start_utc": "2026-11-24T08:00:00Z", "end_utc": "2026-11-24T14:00:00Z"}
    label = "Assumed finite educational service; no operator allocation"

    def service():
        return {"label": label, "input_class": "assumed", "windows": [deepcopy(window)]}

    def terminal(identifier, modes):
        return {"id": identifier, "band": "SYNTHETIC_X_band", "duplex": "half_duplex",
                "mode_ids": modes, "acquisition_s": 0, "teardown_s": 0,
                "tx_electrical_w": 20, "rx_electrical_w": 5}

    hardware = {"id": "assumed-lander-v1", "input_class": "assumed", "storage_capacity_bytes": 209715200,
                "base_load_w": 5, "battery": {"capacity_wh": 100, "initial_energy_wh": 80,
                    "reserve_wh": 10, "max_charge_w": 50, "max_discharge_w": 100,
                    "charge_efficiency": 0.9, "discharge_efficiency": 0.9},
                "panel": {"kind": "fixed", "area_m2": 1, "normal_local_enu": [0, 0, 1],
                    "efficiency": 0.2, "lumped_derating": 0.8, "irradiance_at_1au_w_m2": 1361},
                "terminals": [terminal("lander-radio", ["synthetic-direct-256k", "synthetic-uplink-2m"])],
                "service": service()}
    relay = {"id": "synthetic-lunar-relay", "input_class": "synthetic", "behavior": "store_and_forward",
             "storage_capacity_bytes": 104857600, "processing_delay_s": 0,
             "trajectory": {"kind": "synthetic_two_body_lunar_preset", "reference": "soma-polar-200km-v1",
                 "origin": "MOON", "frame": "J2000", "time_scale": "UTC", "position_unit": "m",
                 "coverage": deepcopy(window)},
             "terminals": [terminal("relay-radio", ["synthetic-uplink-2m", "synthetic-downlink-10m"])],
             "service": service(), "power_assumption_label":
                 "SYNTHETIC external relay power assumed sufficient only during declared service; no relay battery model"}
    stations = []
    for identifier, lat, lon in (("educational-americas", 35, -117), ("educational-europe", 40, -4),
                                  ("educational-australia", -35, 149)):
        stations.append({"id": identifier, "input_class": "assumed", "latitude_deg": lat,
            "longitude_deg_east": lon, "height_m": 0, "frame": "ITRF93", "reference_ellipsoid": "WGS84",
            "minimum_elevation_deg": 10, "storage_capacity_bytes": 209715200,
            "terminals": [terminal("station-radio", ["synthetic-direct-256k", "synthetic-downlink-10m"])],
            "service": service()})
    return validate_scenario({"run_version": "0.1.0", "scenario_id": "user-lunar-delivery",
        "analysis_mode": "terrain_ephemeris", "dataset_manifest_ref": HOSTED_MODEL_ID,
        "lander": {"id": "polar-lander", "latitude_deg": -89.03093035536243,
            "longitude_deg_east": 1.389336784014743, "frame": "MOON_ME_DE421", "reference_radius_m": 1737400,
            "elevation_datum": "height_above_reference_sphere", "elevation_m": 0,
            "antenna_height_m": 2, "panel_height_m": 1, "pole_reference_meridian_deg_east": 0},
        "data_ready_utc": window["start_utc"], "data_volume": {"value": 16, "unit": "MiB"},
        "deadline_utc": window["end_utc"], "analysis_horizon": deepcopy(window),
        "hardware_profile_ref": hardware["id"], "relay_refs": [relay["id"]],
        "station_refs": [station["id"] for station in stations],
        "route_families": ["direct_to_earth", "single_lunar_relay"], "rate_method": "assumed_net_rate",
        "pointing_assumption": "ideal_pointing", "service_assumption_label": label,
        "profiles": {"hardware": [hardware], "relays": [relay], "stations": stations},
        "input_provenance": [
            {"scope": "terrain and celestial geometry", "input_class": "published",
             "description": "Pinned numerical LOLA near/far/polar grids and matched DE421 SPICE. Actual ground elevation is resolved by Python, with interpolation and missing-data quality retained.",
             "source_urls": ["https://pgda.gsfc.nasa.gov/products/81", "https://naif.jpl.nasa.gov/naif/spiceconcept.html"]},
            {"scope": "hardware, rates, pointing and service", "input_class": "assumed",
             "description": "Educational hardware, assumed net payload rates, ideal pointing and finite service. Rounded geographic station proxies are not actual DSN antenna coordinates or booked service.", "source_urls": []},
            {"scope": "lunar relay trajectory", "input_class": "synthetic",
             "description": "synthetic_two_body_lunar_preset soma-polar-200km-v1, not an operational frozen orbit, libration orbit, LRO relay or publicly available relay service.", "source_urls": []}]})


def validate_delivery_request(document):
    _check_json_values(document)
    if not isinstance(document, dict) or not {"scenario"} <= document.keys() <= {"scenario", "options"}:
        raise ValueError("Delivery request requires scenario and optional options")
    scenario = validate_scenario(document["scenario"])
    if scenario["analysis_mode"] != "terrain_ephemeris":
        raise ValueError("Hosted delivery requires the declared terrain_ephemeris provider")
    if scenario["rate_method"] != "assumed_net_rate" or scenario["pointing_assumption"] != "ideal_pointing":
        raise ValueError("Hosted physical delivery supports assumed_net_rate and explicit ideal_pointing only")
    options = deepcopy(document.get("options", {}))
    if not isinstance(options, dict) or set(options) - DEFAULT_OPTIONS.keys():
        raise ValueError("Unsupported scheduler option")
    options = DEFAULT_OPTIONS | options
    if type(options["chunk_bytes"]) is not int or options["chunk_bytes"] <= 0:
        raise ValueError("chunk_bytes must be a positive integer")
    for name in ("bin_s", "time_limit_s"):
        if type(options[name]) not in (int, float) or not math.isfinite(options[name]):
            raise ValueError(name + " must be finite numeric")
    if not LIMITS["min_bin_s"] <= options["bin_s"] <= LIMITS["max_bin_s"]:
        raise ValueError("bin_s is outside the hosted 60 to 300 second budget")
    if not 0 <= options["time_limit_s"] <= LIMITS["max_solver_time_s"]:
        raise ValueError("time_limit_s is outside the hosted zero to ten second solver budget")
    volume = data_volume_bytes(scenario["data_volume"])
    if volume > LIMITS["max_data_volume_bytes"] or math.ceil(volume/options["chunk_bytes"]) > LIMITS["max_chunks"]:
        raise ValueError("Delivery request exceeds the 64 MiB or four-chunk budget")
    profiles = scenario["profiles"]
    if len(profiles["hardware"]) != 1 or len(profiles["relays"]) > 1 or len(profiles["stations"]) > 3:
        raise ValueError("Hosted delivery permits one hardware profile, at most one lunar relay and three stations")
    for profile in [*profiles["hardware"], *profiles["relays"], *profiles["stations"]]:
        if len(profile["terminals"]) > 2 or any(len(t["mode_ids"]) > 3 for t in profile["terminals"]):
            raise ValueError("Hosted terminal/mode budget exceeded")
        if len(profile["service"]["windows"]) > 8:
            raise ValueError("Hosted service calendar permits at most eight windows per node")
    # Reject unsupported provider inputs before terrain horizons consume the worker budget.
    from soma.physical import RELAY_REFERENCE, _terminal_pairs
    model, _ = physical_dataset_manifest(HOSTED_MODEL_ID)
    start, end = [parse_utc(scenario["analysis_horizon"][key]) for key in ("start_utc", "end_utc")]
    if (scenario["dataset_manifest_ref"] != HOSTED_MODEL_ID or not 0 < (end-start).total_seconds() <= LIMITS["max_duration_s"]
            or start < parse_utc(model["coverage"]["start_utc"]) or end > parse_utc(model["coverage"]["end_utc"])):
        raise ValueError("Unsupported physical model or analysis coverage")
    site = scenario["lander"]
    if not (model["latitude_bounds_deg"][0] <= site["latitude_deg"] <= model["latitude_bounds_deg"][1]
            and model["longitude_bounds_deg_east"][0] <= site["longitude_deg_east"] <= model["longitude_bounds_deg_east"][1]):
        raise ValueError("Site is outside the hosted numerical terrain region")
    nodes = [site["id"], *[p["id"] for p in profiles["relays"]+profiles["stations"]]]
    if any(node.upper() in {"SUN", "EARTH"} for node in nodes):
        raise ValueError("SUN and EARTH are reserved celestial state identifiers")
    for station in profiles["stations"]:
        if station["height_m"] < 0:
            raise ValueError("Physical stations require nonnegative WGS84 ellipsoid height")
    for relay in profiles["relays"]:
        trajectory = relay["trajectory"]
        if tuple(trajectory[key] for key in ("kind", "reference", "origin", "frame", "time_scale", "position_unit")) != (
                "synthetic_two_body_lunar_preset", RELAY_REFERENCE, "MOON", "J2000", "UTC", "m"):
            raise ValueError("Unsupported hosted synthetic relay trajectory")
        left, right = [parse_utc(trajectory["coverage"][key]) for key in ("start_utc", "end_utc")]
        if not left <= start < end <= right or (right-left).total_seconds() > 7*86400:
            raise ValueError("Synthetic relay coverage must contain the run and span at most seven days")
    hardware = profiles["hardware"][0]
    for station in profiles["stations"]:
        _terminal_pairs(hardware, station)
    for relay in profiles["relays"]:
        _terminal_pairs(hardware, relay)
        for station in profiles["stations"]:
            _terminal_pairs(relay, station)
    return {"scenario": scenario, "options": options}


def source_entries():
    directory = resource_directory("data")
    result = []
    for name in SOURCE_MANIFESTS:
        manifest = load_json(directory/name)
        for entry in manifest.get("kernels", manifest.get("files", [])):
            result.append({**deepcopy(entry), "manifest_ref": name})
    return result


def _verified_sources(data_root):
    root = _data_root(data_root)
    records = []
    for entry in source_entries():
        path = (root/entry["path"]).resolve()
        if Path(entry["path"]).is_absolute() or not path.is_relative_to(root):
            raise DeliverySourceError("Scientific source path escapes the data directory")
        if not path.is_file() or path.stat().st_size != entry["size_bytes"]:
            raise DeliverySourceError("Required delivery source is missing or has an incorrect size")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != entry["sha256"]:
            raise DeliverySourceError("Required delivery source failed SHA256 verification")
        records.append({key: entry[key] for key in ("path", "sha256", "size_bytes", "manifest_ref")})
    return records


def solver_identity(*, smoke=False):
    import pulp
    if pulp.__version__ != "3.3.2":
        raise DeliverySourceError("Hosted delivery requires the pinned PuLP 3.3.2 solver interface")
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=2, threads=1, options=["randomSeed 1"])
    if not solver.available():
        raise DeliverySourceError("Pinned CBC executable is unavailable")
    path = Path(solver.path).resolve()
    license_file = path.parent/"coin-license.txt"
    if not license_file.is_file():
        raise DeliverySourceError("CBC license text is missing")
    if smoke:
        model = pulp.LpProblem("soma_hosted_cbc_probe", pulp.LpMinimize)
        x = pulp.LpVariable("probe_x", lowBound=0, cat="Integer")
        model += x
        model += x >= 1
        model.solve(solver)
        if model.status != pulp.LpStatusOptimal or x.value() != 1:
            raise DeliverySourceError("CBC executable failed its integer-program smoke test")
    return {"provider": "PuLP/CBC", "pulp_version": pulp.__version__,
            "executable_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "license_sha256": hashlib.sha256(license_file.read_bytes()).hexdigest(),
            "available": True, "integer_smoke_test": "passed" if smoke else "not_run"}


def _library_capabilities():
    rows = [
        ("geometry_time", "Lunar geometry and time", "soma.geometry", ["soma.time"],
         ["SpiceGeometry", "SurfacePoint"], "/api/research/analyze", True,
         "Matched DE421 same-epoch geometric states; explicit coverage and time conventions.", "/docs/reference/geometry-time"),
        ("trajectories", "Spacecraft trajectories", "soma.geometry.trajectories", [],
         ["StateHistory", "SyntheticTwoBodyLunarPreset"], "/api/research/analyze", True,
         "Geometry endpoint exposes the pinned reconstructed LRO source; delivery uses only its explicitly synthetic lunar preset, not LRO relay service.", "/docs/reference/trajectories"),
        ("terrain_horizons", "Numerical terrain and horizons", "soma.terrain", ["soma.terrain.physical"],
         ["build_horizon", "finite_segment_visibility", "resolve_terrain_site"], "/api/research/delivery/analyze", True,
         "Regional numerical LOLA terrain in the bounded delivery pipeline; no global terrain-visibility HTTP operation.", "/docs/reference/terrain"),
        ("illumination_power", "Illumination and power", "soma.illumination", ["soma.power"],
         ["solar_disk_visibility", "fixed_panel_power", "integrate_battery"], "/api/research/delivery/analyze", True,
         "Finite-disk terrain/Earth masks and declared panel/battery models inside bounded delivery; no thermal-survival claim.", "/docs/reference/illumination-power"),
        ("links_rf", "Links and RF models", "soma.links", ["soma.links.budget"],
         ["assess_contact", "evaluate_geometry", "link_budget"], None, False,
         "Link helpers exist in Python. Hosted physical delivery uses assumed net rates; a complete RF link budget is not integrated.", "/docs/reference/communications"),
        ("scheduling_replay", "Delivery scheduling and replay", "soma.schedule", ["soma.engine", "soma.schedule.replay"],
         ["plan_delivery", "plan_run", "replay_schedule"], "/api/research/delivery/analyze", True,
         "Finite direct/one-lunar-relay families with independent replay; a feasible incumbent is distinct from proven optimality.", "/docs/reference/scheduling"),
        ("exports", "Validation and exports", "soma.exports", ["soma.validation"],
         ["create_run_package", "summary", "validate_scenario"], "/api/research/delivery/analyze", True,
         "The same calculation returns an exact native ZIP with replay inputs; no durable serverless run store.", "/docs/reference/validation-exports"),
    ]
    return [dict(zip(("id", "label", "python_module", "related_python_modules", "python_functions",
                      "http_operation", "interactive", "limitation", "docs_path"), row)) for row in rows]


def delivery_capabilities(*, data_root):
    data_root = _data_root(data_root)
    model, _ = physical_dataset_manifest(HOSTED_MODEL_ID)
    result = {"delivery_api_version": API_VERSION, "ready": False, "service_mode": "serverless",
        "async_available": False, "persistence": "none", "limits": deepcopy(LIMITS),
        "coverage": {"frame": model["frame"], "reference_radius_m": model["reference_radius_m"],
            "latitude_bounds_deg": model["latitude_bounds_deg"], "longitude_bounds_deg_east": model["longitude_bounds_deg_east"],
            **model["coverage"]}, "scenario_template": scenario_template(),
        "supported": {"rate_methods": ["assumed_net_rate"], "pointing_assumptions": ["ideal_pointing"],
            "route_families": ["direct_to_earth", "single_lunar_relay"], "relay_trajectory_refs": ["soma-polar-200km-v1"]},
        "assumptions": model["limitations"], "sources": [], "solver": {"available": False},
        "library_capabilities": _library_capabilities(),
        "transport": {"response": "HTTP gzip when accepted; identity response only if it fits the wire budget",
            "export_encoding": "gzip+base64", "export_sha256_scope": "exact uncompressed native ZIP bytes"},
        "cancellation": "Disconnect stops waiting; the worker is stopped at its hard deadline. No durable cancellation/job claim."}
    try:
        result["sources"] = _verified_sources(data_root)
        from soma.geometry import SpiceGeometry
        manifest = load_json(resource_directory("data")/"de421-phase2.manifest.json")
        manifest["coverage"] = {"start_utc": model["coverage"]["start_utc"], "end_utc": model["coverage"]["end_utc"]}
        with SpiceGeometry(manifest, data_root) as geometry:
            result["verified_kernel_coverage"] = deepcopy(geometry.provenance["verified_coverage"])
        from soma.terrain.dem import RasterDEM, GeographicRasterDEM
        for name, cls in ((SOURCE_MANIFESTS[1], RasterDEM), (SOURCE_MANIFESTS[2], GeographicRasterDEM),
                          (SOURCE_MANIFESTS[3], RasterDEM)):
            source = load_json(resource_directory("data")/name)
            files = {entry["role"]: Path(data_root)/entry["path"] for entry in source["files"]}
            with cls(files["elevation"], files["count"], source):
                pass
        result["solver"] = solver_identity(smoke=True)
        result["ready"] = True
    except Exception as error:
        result["unavailable_reason"] = "Delivery dependencies or pinned scientific sources are not ready ("+type(error).__name__+")"
    return result


def calculate_delivery(document, *, data_root):
    """Run only in the owning private interpreter; never fetch data here."""
    request = validate_delivery_request(document)
    _verified_sources(data_root)
    solver_identity(smoke=False)
    os.environ["SOMA_DATA_ROOT"] = str(_data_root(data_root))
    from soma.engine import plan_run
    from soma.exports import create_run_package, summary
    run = plan_run(request["scenario"], options=request["options"])
    package = create_run_package(run)
    if len(package) > LIMITS["max_export_zip_bytes"]:
        raise OverflowError("Native ZIP exceeds the hosted export budget")
    payload = {"delivery_api_version": API_VERSION, "scenario_sha256": run["result"]["scenario_sha256"],
        "scenario": run["scenario"], "options": request["options"], "result": run["result"],
        "summary": summary(run), "display": delivery_display(run, data_root=data_root),
        "environment": run["analysis_inputs"].get("environment"), "replay": run["validation"],
        "export": {"encoding": "gzip+base64", "media_type": "application/zip",
            "sha256": hashlib.sha256(package).hexdigest(), "size_bytes": len(package),
            "bytes_base64": base64.b64encode(gzip.compress(package, mtime=0)).decode("ascii")}}
    return payload


def delivery_display(run, *, data_root):
    """Additional Python states for the hosted viewer; native run/export stays intact."""
    from datetime import timedelta
    from soma.exports.display import display_data
    from soma.geometry import SpiceGeometry
    from soma.geometry.surface import SurfacePoint
    from soma.physical import _relay, _state
    from soma.time import format_utc
    payload = display_data(run)
    scenario = run["scenario"]
    site = SurfacePoint.from_lander(run["analysis_inputs"]["environment"]["analysis_point"])
    start, end = [parse_utc(scenario["analysis_horizon"][key]) for key in ("start_utc", "end_utc")]
    epochs = {format_utc(start), format_utc(end)}
    cursor = start
    while cursor < end:
        epochs.add(format_utc(cursor))
        cursor += timedelta(seconds=60)
    for allocation in run["result"]["allocations"]:
        epochs.add(allocation["byte_available_utc"])
        for key in ("source_transmit_interval", "receiver_occupancy_interval"):
            epochs.update(allocation[key].values())
    epochs = sorted(epochs, key=parse_utc)
    manifest = load_json(resource_directory("data")/"de421-phase2.manifest.json")
    manifest["coverage"] = {"start_utc": epochs[0], "end_utc": epochs[-1]}
    states = []
    matrix = payload["registration"].get("transform_column_major")
    overlays_allowed = matrix is not None and payload["registration"]["release_gate"]["overlays_allowed"]
    earth_body = {
        "body_id": "EARTH", "reference_ellipsoid": "WGS84",
        "radii_m": [6378137, 6378137, 6356752.314245179],
        "body_fixed_frame": "ITRF93", "renderer_frame": payload["registration"]["renderer_frame"],
        "center_state_target": "EARTH", "center_origin": "MOON",
        "position_unit": "m", "time_scale": "UTC", "rotation_layout": "row_major",
        "rotation_unit": "dimensionless", "orientation_samples": [],
        "status": "available" if overlays_allowed else "unknown",
        "provenance": {"scope": "Hosted display only; native ZIP and scientific result unchanged",
            "method": "Matched Earth binary PCK: ITRF93 to MOON_ME_DE421 at each exact display epoch, premultiplied by registered engine-to-renderer rotation; translation excluded",
            "ellipsoid": "WGS84 terrestrial reference ellipsoid, independent of the lunar reference sphere",
            "interpolation": "none_unknown_between_samples"}}
    if not overlays_allowed:
        earth_body["unavailable_reason"] = "renderer_registration_blocks_earth_orientation"
    with SpiceGeometry(manifest, _data_root(data_root)) as geometry:
        presets = {p["id"]: _relay(geometry, scenario, p, site) for p in scenario["profiles"]["relays"]
                   if p["id"] in scenario["relay_refs"]}
        for epoch in epochs:
            if overlays_allowed:
                body_to_engine = geometry.spice.pxform("ITRF93", "MOON_ME_DE421", geometry._epoch(epoch))
                rotation = [sum(matrix[k*4+row]*body_to_engine[k, column] for k in range(3))
                            for row in range(3) for column in range(3)]
                earth_body["orientation_samples"].append({"epoch_utc": epoch,
                    "rotation_body_fixed_to_renderer_row_major": rotation})
            states.append(_state(scenario["lander"]["id"], epoch, site.position_m(site.antenna_height_m),
                                 "published_LOLA_resolved_site_explicit_antenna_height"))
            states.append({**geometry.state("EARTH", epoch), "epoch": epoch})
            states.extend({**geometry.station_state(p, epoch), "epoch": epoch}
                          for p in scenario["profiles"]["stations"] if p["id"] in scenario["station_refs"])
            for node, preset in presets.items():
                states.append(_state(node, epoch, geometry.transform_position(preset.state(epoch)["position"], epoch), preset.label))
    payload["earth_body"] = earth_body
    payload["states"] = states
    payload["state_status"] = "stored_samples"
    payload["state_unavailable_reasons"] = []
    payload["sample_epochs_utc"] = epochs
    payload["additional_states_provenance"] = {
        "scope": "Hosted display adapter only; native ZIP and replay inputs unchanged",
        "method": "Same matched SPICE, terrain-resolved antenna and synthetic relay model; 60-second samples plus exact allocation epochs",
        "interpolation": "none_unknown_between_samples"}
    matrix = payload["registration"].get("transform_column_major")
    payload["renderer_states"] = []
    if matrix is not None and payload["registration"]["release_gate"]["overlays_allowed"]:
        for state in states:
            position = state["position"]
            transformed = [sum(matrix[column*4+row]*position[column] for column in range(3))+matrix[12+row] for row in range(3)]
            payload["renderer_states"].append({**deepcopy(state), "position": transformed,
                "source_frame": state["frame"], "frame": payload["registration"]["renderer_frame"],
                "transform_ref": "renderer-registration.json", "transform_epoch_utc": state["epoch"]})
    return payload


def _linux_tree_rss(process_group):
    if not sys.platform.startswith("linux"):
        return None
    total = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry/"stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) != process_group:
                continue
            for line in (entry/"status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1])*1024
                    break
        except (OSError, ValueError, IndexError):
            continue
    return total


def _worker(control_path):
    configure_numerical_threads()
    control = load_json(control_path)
    directory = Path(control_path).parent
    try:
        preload_hosted_libraries()
        if sys.platform.startswith("linux"):
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (LIMITS["worker_address_space_bytes"],)*2)
            resource.setrlimit(resource.RLIMIT_CPU, (LIMITS["max_worker_seconds"],)*2)
        runner = calculate_delivery
        if control.get("runner") is not None:
            runner = importlib.import_module(control["runner"]["module"])
            for name in control["runner"]["qualname"].split("."):
                runner = getattr(runner, name)
        payload = runner(control["document"], data_root=control["data_root"])
        content = encode(payload)
        if len(content) > LIMITS["max_response_decoded_bytes"]:
            raise OverflowError("Decoded delivery result exceeds the hosted response budget")
        _atomic_write(directory/"result.json", content)
    except BaseException as error:
        status = 503
        detail = "Delivery computation is unavailable; inspect source readiness and declared model coverage"
        if isinstance(error, OverflowError):
            status, detail = 413, "Delivery result exceeds the hosted response/export budget; reduce duration or network size"
        elif isinstance(error, (ValueError, ScenarioValidationError)):
            status, detail = 422, "Delivery input cannot be evaluated under the declared bounded physical model"
        _atomic_write(directory/"error.json", encode({"status": status, "detail": detail, "error_type": type(error).__name__}))


def run_delivery_sync(document, *, data_root, runner=None, timeout_s=None):
    configure_numerical_threads()
    request = validate_delivery_request(document)
    reference = None
    if runner is not None:
        if "<" in runner.__qualname__ or runner.__module__ == "__main__":
            raise ValueError("Trusted delivery runner must be an importable module-level callable")
        reference = {"module": runner.__module__, "qualname": runner.__qualname__}
    timeout = LIMITS["max_worker_seconds"] if timeout_s is None else timeout_s
    if not 0 < timeout <= LIMITS["max_worker_seconds"]:
        raise ValueError("Delivery worker timeout exceeds its budget")
    with tempfile.TemporaryDirectory(prefix="soma-delivery-") as directory:
        control = Path(directory)/"input.json"
        _atomic_write(control, encode({"document": request, "data_root": str(_data_root(data_root)), "runner": reference}))
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(str(p or os.getcwd()) for p in sys.path)
        process = start_private_interpreter([sys.executable, "-m", "soma.api.delivery", str(control)], env=environment)
        started = time.monotonic()
        peak_rss = 0
        try:
            while process.poll() is None:
                if time.monotonic()-started > timeout:
                    _stop_delivery_process(process)
                    raise HTTPException(504, "Delivery worker exceeded its hard time budget")
                rss = _linux_tree_rss(process.pid)
                if rss is not None:
                    peak_rss = max(peak_rss, rss)
                    if rss > LIMITS["worker_tree_rss_bytes"]:
                        _stop_delivery_process(process)
                        raise HTTPException(503, "Delivery worker and solver exceeded their combined memory budget")
                time.sleep(0.1)
            failure = Path(directory)/"error.json"
            if failure.is_file():
                error = load_json(failure)
                raise HTTPException(error["status"], error["detail"])
            output = Path(directory)/"result.json"
            if process.returncode != 0 or not output.is_file():
                raise HTTPException(503, "Delivery worker exited without a complete result")
            if output.stat().st_size > LIMITS["max_response_decoded_bytes"]:
                raise HTTPException(413, "Decoded delivery response exceeds its budget")
            content = output.read_bytes()
            payload = json.loads(content)
            if (payload.get("scenario") != request["scenario"] or payload.get("scenario_sha256") != scenario_sha256(request["scenario"])
                    or payload.get("options") != request["options"]):
                raise HTTPException(503, "Delivery result does not match its submitted inputs")
            validate_document(payload["result"], "result")
            if payload["result"]["scenario_sha256"] != payload["scenario_sha256"]:
                raise HTTPException(503, "Delivery result hash mismatch")
            return content
        finally:
            _stop_delivery_process(process)


def _stop_delivery_process(process):
    stop_private_interpreter(process)

def _accepts_gzip(value):
    qualities = {}
    for item in value.lower().split(","):
        encoding, *parameters = [part.strip() for part in item.split(";")]
        quality = 1.0
        for parameter in parameters:
            if parameter.startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        if not math.isfinite(quality) or not 0 <= quality <= 1:
            quality = 0.0
        qualities[encoding] = quality
    return qualities.get("gzip", qualities.get("*", 0)) > 0


def delivery_router(*, data_root, runner=None, capabilities_provider=None, timeout_s=None):
    router = APIRouter(prefix="/research/delivery", tags=["delivery"])
    slot = threading.BoundedSemaphore(1)
    inflight = set()

    def calculate_and_release(document):
        # The thread owns the slot until the actual subprocess finishes, even
        # if its asyncio waiter is canceled during disconnect or shutdown.
        try:
            return run_delivery_sync(document, data_root=data_root, runner=runner, timeout_s=timeout_s)
        finally:
            slot.release()

    def finished(task):
        inflight.discard(task)
        if not task.cancelled():
            task.exception()  # Observe failures when a disconnected waiter cannot receive them.

    @router.get("/capabilities")
    def capabilities():
        provider = capabilities_provider or delivery_capabilities
        return provider(data_root=data_root)

    @router.post("/analyze")
    async def analyze(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > LIMITS["max_request_bytes"]:
                raise HTTPException(413, "Delivery request exceeds its 128000-byte budget")
        try:
            document = json.loads(body, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
            document = validate_delivery_request(document)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise HTTPException(422, str(error)[:2000]) from error
        if not slot.acquire(blocking=False):
            raise HTTPException(429, "One delivery computation is already active", headers={"Retry-After": "3"})
        try:
            task = asyncio.create_task(asyncio.to_thread(calculate_and_release, document))
        except BaseException:
            slot.release()
            raise
        inflight.add(task)
        task.add_done_callback(finished)
        content = await asyncio.shield(task)
        headers = {"Cache-Control": "private, no-store", "Vary": "Accept-Encoding"}
        if _accepts_gzip(request.headers.get("accept-encoding", "")):
            content = gzip.compress(content, mtime=0)
            headers["Content-Encoding"] = "gzip"
        if len(content) > LIMITS["max_response_wire_bytes"]:
            raise HTTPException(413, "Delivery response requires HTTP gzip or a smaller declared workload")
        return Response(content, media_type="application/json", headers=headers)

    return router


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected a parent-created delivery control file")
    _worker(sys.argv[1])
