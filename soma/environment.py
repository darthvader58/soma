"""Versioned illumination/power/contact diagnostics, without a delivery solver."""

from copy import deepcopy
import hashlib
import json
import math
from types import SimpleNamespace

import numpy as np

from soma.diagnostics import _epochs, _horizon_classification
from soma.geometry import SurfacePoint, vector_direction
from soma.illumination import solar_disk_visibility
from soma.links import assess_contact
from soma.power import fixed_panel_power, integrate_battery
from soma.time import parse_utc
from soma.validation import scenario_sha256, validate_document, validate_scenario


GENERATION_MODEL = "left_sample_piecewise_constant_assumption"


def _validated_geometry(report):
    report = deepcopy(report)
    if report.get("artifact_type") != "soma_geometry_diagnostic" or report.get("artifact_version") != "0.2.0":
        raise ValueError("Require a version 0.2.0 geometry diagnostic")
    scenario = validate_scenario(report["scenario"])
    if report["scenario_sha256"] != scenario_sha256(scenario):
        raise ValueError("Geometry scenario hash mismatch")
    point = report["analysis_point"]
    for key, value in scenario["lander"].items():
        if key != "elevation_m" and point.get(key) != value:
            raise ValueError(f"Resolved analysis point differs from declared {key}")
    site = SurfacePoint.from_lander(point)
    if (report["frame"], report["origin"], report["position_unit"], report["time_scale"]) != (site.frame, "MOON", "m", "UTC"):
        raise ValueError("Geometry frame, origin, units or time scale mismatch")
    for role in ("antenna", "panel"):
        horizon_site = report["horizons"][role]["site"]
        for key in ("latitude_deg", "longitude_deg_east", "elevation_m", "frame", "reference_radius_m", "elevation_datum", "pole_reference_meridian_deg_east"):
            if horizon_site[key] != point[key]:
                raise ValueError(f"{role} horizon site mismatch: {key}")
        if horizon_site["height_m"] != point[role+"_height_m"]:
            raise ValueError(f"{role} horizon observer height mismatch")
    return report, scenario, site


def environment_diagnostic(geometry_report, *, generation_time_model, candidates=(),
                           samples=512, max_samples=8192, tolerance=0.005):
    """Consume pinned geometry and explicit interval-wide contact evidence.

    Solar values are sampled instants. Battery replay treats each left sample
    as constant until the next sample by an explicit, non-validated assumption.
    It does not establish continuous physical power bounds or select a schedule.
    """
    if generation_time_model != GENERATION_MODEL:
        raise ValueError(f"Generation time model must explicitly be {GENERATION_MODEL}")
    source, scenario, site = _validated_geometry(geometry_report)
    tracks = {}
    for track in source["tracks"]:
        if track["target"] in tracks:
            raise ValueError("Duplicate target tracks")
        tracks[track["target"]] = track
    if not {"SUN", "EARTH"}.issubset(tracks):
        raise ValueError("Both Sun and Earth states are required for eclipse masking")
    epochs = [item["epoch_utc"] for item in tracks["SUN"]["samples"]]
    if len(epochs) < 2 or len(epochs) > 10001:
        raise ValueError("Require two to 10001 aligned geometry samples")
    if len(epochs)*max_samples > 4_000_000:
        raise ValueError("Solar time/disk sampling exceeds the bounded four-million-ray workload")
    times = [parse_utc(epoch) for epoch in epochs]
    if any(b <= a for a, b in zip(times, times[1:])) or times[0] != parse_utc(scenario["analysis_horizon"]["start_utc"]) or times[-1] != parse_utc(scenario["analysis_horizon"]["end_utc"]):
        raise ValueError("Geometry samples must cover the declared horizon chronologically")
    for track in tracks.values():
        if [item["epoch_utc"] for item in track["samples"]] != epochs:
            raise ValueError("All geometry tracks must share identical sample epochs")
        for epoch, record in zip(epochs, track["samples"]):
            state = record["state"]
            validate_document(state, "state")
            if (state["target"], state["frame"], state["origin"], state["position_unit"], state["time_scale"], state["epoch"]) != (track["target"], site.frame, "MOON", "m", "UTC", epoch):
                raise ValueError("Geometry state identity, epoch, frame or units mismatch")
    hardware = next(p for p in scenario["profiles"]["hardware"] if p["id"] == scenario["hardware_profile_ref"])
    solar, power, display_tracks = [], [], []
    for index, epoch in enumerate(epochs):
        observer = site.position_m(site.panel_height_m)
        sun = site.local_basis() @ (np.array(tracks["SUN"]["samples"][index]["state"]["position"])-observer)
        earth = site.local_basis() @ (np.array(tracks["EARTH"]["samples"][index]["state"]["position"])-observer)
        visibility = solar_disk_visibility(sun, earth, horizon=source["horizons"]["panel"],
                                          samples=samples, max_samples=max_samples, tolerance=tolerance)
        solar.append({"epoch_utc": epoch, **visibility})
        power.append({"epoch_utc": epoch, **fixed_panel_power(hardware["panel"], sun, visibility["visible_fraction"])})
    for track in tracks.values():
        for role in ("panel", "antenna"):
            records = []
            for epoch, sample in zip(epochs, track["samples"]):
                vector = np.array(sample["state"]["position"])-site.position_m(getattr(site, role+"_height_m"))
                direction = vector_direction(vector, site.local_basis())
                if track["target"] in ("SUN", "EARTH"):
                    status, reason = _horizon_classification(SimpleNamespace(**{
                        "converged": source["horizons"][role]["converged"],
                        "bands": [SimpleNamespace(**b) for b in source["horizons"][role]["bands"]],
                        "sampling": SimpleNamespace(**source["horizons"][role]["sampling"]),
                    }), direction["azimuth_deg"], direction["elevation_deg"], 0.1)
                else:
                    status, reason = "unknown", "finite_endpoint_link_not_assessed_by_distant_horizon"
                records.append({**sample, "direction": direction, "classification": status, "classification_reason": reason})
            display_tracks.append({**track, "observer_role": role, "observer_height_m": getattr(site, role+"_height_m"), "samples": records})
    bins = [{"start_utc": a["epoch_utc"], "end_utc": b["epoch_utc"], "generation_w": a["generated_power_w"],
             "incremental_load_w": 0, "power_model": "piecewise_constant"} for a, b in zip(power, power[1:])]
    battery = integrate_battery(hardware["battery"], bins, base_load_w=hardware["base_load_w"])
    profiles = {scenario["lander"]["id"]: hardware}
    profiles.update({p["id"]: p for p in scenario["profiles"]["relays"] if p["id"] in scenario["relay_refs"]})
    profiles.update({p["id"]: p for p in scenario["profiles"]["stations"] if p["id"] in scenario["station_refs"]})
    opportunities, contacts, decisions, occupancy = [], [], [], []
    for candidate in candidates:
        if candidate["sender"] not in profiles or candidate["receiver"] not in profiles:
            raise ValueError("Contact endpoint is not enabled in this scenario")
        start, end = (parse_utc(candidate["source_transmit_window"][k]) for k in ("start_utc", "end_utc"))
        if start < times[0] or end > times[-1]:
            raise ValueError("Candidate extends outside the analysis horizon")
        assessment = assess_contact(candidate, profiles[candidate["sender"]], profiles[candidate["receiver"]], guard_s=0)
        opportunities.append(assessment["opportunity"])
        for contact in assessment["contacts"]:
            validate_document(contact, "contact")
        contacts.extend(assessment["contacts"])
        occupancy.extend(assessment["endpoint_occupancy"])
        decisions.append({"candidate_id": candidate["contact_id"], **assessment["decision"]})
    if not opportunities:
        for target in scenario["station_refs"]+scenario["relay_refs"]:
            decisions.append({"candidate_id": target, "status": "unknown", "reasons": ["sampled_geometry_is_not_interval_wide_contact_evidence"]})
    return {
        "artifact_type": "soma_environment_diagnostic", "artifact_version": "0.3.0",
        "scenario": scenario, "scenario_id": scenario["scenario_id"], "scenario_sha256": scenario_sha256(scenario),
        "analysis_point": source["analysis_point"], "analysis_horizon": scenario["analysis_horizon"],
        "frame": site.frame, "origin": "MOON", "position_unit": "m", "time_scale": "UTC",
        "horizons": source["horizons"], "tracks": display_tracks, "solar_samples": solar,
        "power_samples": power, "battery": battery, "opportunities": opportunities,
        "contacts": contacts, "contact_decisions": decisions, "endpoint_occupancy": occupancy,
        "assumptions": [generation_time_model, "Battery diagnostic includes base load only; no radio schedule was selected.",
                        "Fixed-panel center-ray projection times sampled uniform solar disk fraction.",
                        "Spherical opaque Earth eclipse mask combined with terrain on the same solar samples.",
                        "Contact event guard is explicitly zero for this diagnostic; not an operational margin."],
        "warnings": ["Environment diagnostics are not a delivery result or an energy-constrained selected schedule.",
                     "Sampled generation is held constant by assumption; interior variation is not physically bounded.",
                     "Unknown terrain or disk convergence produces unknown power and stored energy.",
                     "Usable contacts still require scheduling, conflicts, finite buffers and replay validation.",
                     *["Source geometry: "+warning for warning in source.get("warnings", [])]],
        "provenance": {**source["provenance"], "geometry_artifact_sha256": hashlib.sha256(json.dumps(source, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                       "geometry_digest_convention": "sha256_of_python_sorted_json_utf8_default_separators_not_scenario_JCS"},
    }


def synthetic_environment_fixture(scenario, contact_inputs):
    """Explicit invented sky and skyline used only to check algorithms and UI."""
    scenario = validate_scenario(scenario)
    site = SurfacePoint.from_lander(scenario["lander"])
    epochs = _epochs(parse_utc(scenario["analysis_horizon"]["start_utc"]), parse_utc(scenario["analysis_horizon"]["end_utc"]), 300)
    horizons = {}
    for role, level in (("panel", 0.2), ("antenna", 0.0)):
        definition = {"input_class": "synthetic", "role": role, "elevation_deg": level, "azimuth_step_deg": 30}
        horizons[role] = {"site": {k: v for k, v in scenario["lander"].items() if k in ("latitude_deg", "longitude_deg_east", "elevation_m", "pole_reference_meridian_deg_east", "frame", "reference_radius_m", "elevation_datum")},
                          "sampling": {"azimuth_step_deg": 30}, "converged": True,
                          "cache_key": hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest(),
                          "algorithm_version": "synthetic_uniform_skyline_input_v1",
                          "bands": [{"azimuth_deg": a, "elevation_deg": level, "sampled_lower_bound_deg": level,
                                     "unknown_samples": 0, "quality_flags": ["synthetic_skyline_not_a_measured_DEM"]} for a in range(0, 360, 30)]}
        horizons[role]["site"]["height_m"] = getattr(site, role+"_height_m")
    tracks = []
    targets = [("SUN", "panel", "synthetic_sun_direction_not_ephemeris", 149597870700.0, 90, None),
               ("EARTH", "antenna", "Earth_center_not_a_ground_station_synthetic_direction", 380000000.0, 270, 8)]
    targets += [(s, "antenna", "synthetic_configured_station_direction_not_ephemeris", 380000000.0, 270, 7) for s in scenario["station_refs"]]
    for target, role, definition, distance, azimuth, elevation in targets:
        records = []
        for index, epoch in enumerate(epochs):
            el = -0.4+1.2*index/(len(epochs)-1) if elevation is None else elevation
            az, angle = math.radians(azimuth), math.radians(el)
            enu = distance*np.array([math.cos(angle)*math.sin(az), math.cos(angle)*math.cos(az), math.sin(angle)])
            position = site.position_m(getattr(site, role+"_height_m"))+site.local_basis().T@enu
            state = {"target": target, "origin": "MOON", "frame": site.frame, "epoch": epoch, "epoch_format": "rfc3339", "time_scale": "UTC",
                     "position": position.tolist(), "position_unit": "m", "provenance_label": definition}
            records.append({"epoch_utc": epoch, "state": state, "direction": vector_direction(position-site.position_m(getattr(site, role+"_height_m")), site.local_basis()),
                            "classification": "unknown", "classification_reason": "synthetic_direction_input"})
        tracks.append({"target": target, "target_definition": definition, "observer_role": role, "samples": records})
    source = {"artifact_type": "soma_geometry_diagnostic", "artifact_version": "0.2.0", "scenario": scenario, "scenario_sha256": scenario_sha256(scenario),
              "analysis_point": deepcopy(scenario["lander"]), "frame": site.frame, "origin": "MOON", "position_unit": "m", "time_scale": "UTC",
              "horizons": horizons, "tracks": tracks, "warnings": ["All sky directions and skylines in this fixture are invented inputs, not lunar predictions."],
              "provenance": {"input_class": "synthetic", "geometry": {"kind": "synthetic_direction_fixture_not_trajectory"},
                             "terrain": [{"id": "synthetic_uniform_skyline_input_v1", "sha256": hashlib.sha256(json.dumps(horizons, sort_keys=True).encode()).hexdigest()}]}}
    candidates = []
    fields = ("contact_id", "sender", "receiver", "sender_terminal_id", "receiver_terminal_id", "source_transmit_window", "mode_id", "rate_method", "payload_rate_bps", "one_way_delay", "quality_flags")
    for contact in contact_inputs:
        candidate = {key: deepcopy(contact[key]) for key in fields}
        candidate.update(geometry_status="clear_under_sampling", geometry_reason="synthetic_interval_geometry_assumption",
                         geometry_evidence={"scope": "interval_wide", "coverage": deepcopy(contact["source_transmit_window"]), "source_transmit_window": deepcopy(contact["source_transmit_window"]),
                                            "input_class": "synthetic", "method": "declared_fixture_assumption_not_computed_geometry"},
                         pointing_assumption=scenario["pointing_assumption"], service_assumption_label=scenario["service_assumption_label"], input_class="synthetic")
        candidates.append(candidate)
    if candidates:
        blocked = deepcopy(candidates[0]); blocked.update(contact_id="synthetic-blocked-interval", geometry_status="blocked", geometry_reason="synthetic_terrain_blockage")
        unknown = deepcopy(candidates[0]); unknown.update(contact_id="synthetic-unknown-interval", geometry_status="unknown", geometry_reason="synthetic_missing_terrain_coverage")
        candidates.extend((blocked, unknown))
    return environment_diagnostic(source, generation_time_model=GENERATION_MODEL, candidates=candidates)
