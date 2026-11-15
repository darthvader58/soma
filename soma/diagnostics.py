"""Phase 2 geometric diagnostics, deliberately separate from delivery results."""

from contextlib import ExitStack
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import numpy as np

from soma.geometry import SurfacePoint, SpiceGeometry, SyntheticTwoBodyLunarPreset, vector_direction
from soma.terrain import CompositeDEM, RasterDEM, HorizonSampling, HorizonSite, build_horizon, finite_segment_visibility
from soma.time import format_utc, parse_utc
from soma.time.spice import utc_to_et
from soma.validation import load_json, load_scenario, scenario_sha256, validate_document


def _terrain_file(root, manifest, role):
    entry = next(item for item in manifest["files"] if item["role"] == role)
    path = (Path(root).resolve() / entry["path"]).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Terrain path escapes data root")
    return path


def open_terrain(stack, root, near_manifest, far_manifest=None):
    near = stack.enter_context(RasterDEM(_terrain_file(root, near_manifest, "elevation"),
                                         _terrain_file(root, near_manifest, "count"), near_manifest))
    if far_manifest is None:
        return near
    from soma.terrain import GeographicRasterDEM
    far = stack.enter_context(GeographicRasterDEM(_terrain_file(root, far_manifest, "elevation"),
                                                 _terrain_file(root, far_manifest, "count"), far_manifest))
    return CompositeDEM(near, far)


def _epochs(start, end, step_s):
    if not np.isfinite(step_s) or step_s < 1e-6 or not np.isclose(step_s*1e6, round(step_s*1e6), rtol=0, atol=1e-6):
        raise ValueError("Sample step must be finite and a positive whole number of microseconds")
    if (end-start).total_seconds()/step_s > 10000:
        raise ValueError("Diagnostic time sampling exceeds the bounded workload")
    result = []
    current = start
    while current < end:
        result.append(format_utc(current))
        current += timedelta(seconds=step_s)
    result.append(format_utc(end))
    return result


def _horizon_classification(profile, azimuth, elevation, margin_deg):
    if not profile.converged:
        return "unknown", "horizon_missing_data_or_extent_not_converged"
    bands = profile.bands
    step = profile.sampling.azimuth_step_deg
    left = int((azimuth % 360)/step) % len(bands)
    right = (left+1) % len(bands)
    levels = (bands[left].elevation_deg, bands[right].elevation_deg)
    if any(value is None for value in levels):
        return "unknown", "unknown_horizon_azimuth"
    # Neighbor disagreement is unresolved, rather than projecting a ridge from
    # one sampled azimuth into its neighbor. Unsampled features remain a limit.
    if elevation > max(levels)+margin_deg:
        return "clear", "above_both_sampled_horizon_neighbors"
    if elevation < min(levels)-margin_deg:
        return "blocked", "below_both_sampled_horizon_neighbors"
    return "unknown", "between_horizon_neighbors_or_within_margin"


def sampled_intervals(samples, step_s):
    """Group adjacent samples; bounds carry sampling uncertainty, never contact capacity."""
    intervals = []
    for a, b in zip(samples, samples[1:]):
        status = a["classification"] if a["classification"] == b["classification"] else "unknown"
        reason = a["classification_reason"] if a["classification"] == b["classification"] and a["classification_reason"] == b["classification_reason"] else "unknown_coverage_or_transition_within_sample_bin"
        record = {"start_utc": a["epoch_utc"], "end_utc": b["epoch_utc"],
                  "classification": status, "reason": reason,
                  "boundary_uncertainty_s": min(step_s, (parse_utc(b["epoch_utc"])-parse_utc(a["epoch_utc"])).total_seconds())}
        if intervals and all(intervals[-1][key] == record[key] for key in ("classification", "reason", "boundary_uncertainty_s")):
            intervals[-1]["end_utc"] = record["end_utc"]
        else:
            intervals.append(record)
    return intervals


def geometry_diagnostic(scenario, *, data_root, kernel_manifest, near_manifest, far_manifest=None,
                        sample_step_s=300, azimuth_step_deg=30, required_extent_m=200000,
                        include_synthetic_relay=False):
    """Compute body-consistent directions and quality-aware sampled horizons.

    This diagnostic does not evaluate solar disk fraction, power, usable radio
    contacts, resource scheduling, or delivery feasibility.
    """
    from soma.validation import validate_scenario
    scenario = validate_scenario(scenario)
    if required_extent_m < 10000:
        raise ValueError("Two horizon extents must include the five-kilometer near field; require at least 10000 m")
    sampling = HorizonSampling(azimuth_step_deg, 5, 240, 5000,
                               (required_extent_m/2, required_extent_m), .01, required_extent_m)
    start = parse_utc(scenario["analysis_horizon"]["start_utc"])
    end = parse_utc(scenario["analysis_horizon"]["end_utc"])
    epochs = _epochs(start, end, sample_step_s)
    margin = .1
    with ExitStack() as stack:
        dem = open_terrain(stack, data_root, near_manifest, far_manifest)
        sample = dem.sample(scenario["lander"]["latitude_deg"], scenario["lander"]["longitude_deg_east"])
        if sample.elevation_m is None:
            raise ValueError("Selected site has unknown measured terrain; no analysis point can be resolved")
        resolved = {**scenario["lander"], "elevation_m": sample.elevation_m}
        site = SurfacePoint.from_lander(resolved)
        profiles = {}
        for role, height in (("antenna", site.antenna_height_m), ("panel", site.panel_height_m)):
            horizon_site = HorizonSite(site.latitude_deg, site.longitude_deg_east, site.elevation_m, height,
                                       site.pole_reference_meridian_deg_east, site.frame,
                                       site.reference_radius_m, site.elevation_datum)
            profiles[role] = build_horizon(dem, horizon_site, sampling)
        geometry = stack.enter_context(SpiceGeometry(kernel_manifest, data_root))
        tracks = []
        for target, role in (("SUN", "panel"), ("EARTH", "antenna")):
            height = getattr(site, role+"_height_m")
            records = []
            for epoch in epochs:
                state = geometry.state(target, epoch)
                validate_document(state, "state")
                direction = geometry.direction(site, target, epoch, height_m=height)
                status, reason = _horizon_classification(profiles[role], direction["azimuth_deg"], direction["elevation_deg"], margin)
                records.append({"epoch_utc": epoch, "state": state, "direction": direction,
                                "classification": status, "classification_reason": reason})
            tracks.append({"target": target, "target_definition": "Sun_center_not_solar_disk" if target == "SUN" else "Earth_center_not_a_ground_station",
                           "observer_role": role, "observer_height_m": height, "samples": records,
                           "geometric_intervals": sampled_intervals(records, sample_step_s)})
        for station_id in scenario["station_refs"]:
            station = next(x for x in scenario["profiles"]["stations"] if x["id"] == station_id)
            records = []
            for epoch in epochs:
                state = geometry.station_state(station, epoch)
                validate_document(state, "state")
                direction = vector_direction(np.array(state["position"])-site.position_m(site.antenna_height_m), site.local_basis())
                records.append({"epoch_utc": epoch, "state": state, "direction": direction,
                                "classification": "unknown", "classification_reason": "station_endpoint_and_full_segment_opportunity_not_assessed"})
            tracks.append({"target": station_id, "target_definition": station["input_class"]+"_configured_WGS84_ITRF93_ground_station",
                           "observer_role": "antenna", "observer_height_m": site.antenna_height_m, "samples": records,
                           "geometric_intervals": sampled_intervals(records, sample_step_s)})
        if include_synthetic_relay:
            preset = SyntheticTwoBodyLunarPreset(target="diagnostic-synthetic-relay", epoch_utc=epochs[0],
                coverage=scenario["analysis_horizon"], gm_m3_s2=4.902800066e12, reference_radius_m=site.reference_radius_m,
                semimajor_axis_m=site.reference_radius_m+200000, eccentricity=.01, inclination_deg=90,
                ascending_node_deg=0, argument_periapsis_deg=0, mean_anomaly_deg=0, utc_to_et=utc_to_et)
            records = []
            for epoch in epochs:
                inertial = preset.state(epoch)
                position = geometry.transform_position(inertial["position"], epoch)
                state = {**inertial, "frame": site.frame, "position": position.tolist(),
                         "provenance_label": preset.label+"; transformed_to_MOON_ME_DE421"}
                validate_document(state, "state")
                segment = finite_segment_visibility(dem, site.position_m(site.antenna_height_m), position,
                              frame=site.frame, step_m=250, clearance_m=1, body_radius_m=1720000, max_samples=20000)
                records.append({"epoch_utc": epoch, "state": state,
                                "direction": vector_direction(position-site.position_m(site.antenna_height_m), site.local_basis()),
                                "classification": segment.status, "classification_reason": segment.reason,
                                "segment_test": asdict(segment)})
            tracks.append({"target": "diagnostic-synthetic-relay", "target_definition": preset.label,
                           "not_scenario_relay_ephemeris": True, "observer_role": "antenna",
                           "observer_height_m": site.antenna_height_m, "trajectory_assumptions": preset.provenance,
                           "segment_parameters": {"step_m": 250, "clearance_m": 1, "body_radius_m": 1720000,
                                                  "body_radius_input_class": "assumed_conservative_inner_sphere", "max_samples": 20000},
                           "samples": records, "geometric_intervals": sampled_intervals(records, sample_step_s)})
        report = {
            "artifact_type": "soma_geometry_diagnostic", "artifact_version": "0.2.0",
            "scenario": scenario,
            "scenario_id": scenario["scenario_id"], "scenario_sha256": scenario_sha256(scenario),
            "analysis_horizon": scenario["analysis_horizon"], "analysis_point": resolved,
            "requested_elevation_m": scenario["lander"]["elevation_m"],
            "elevation_resolution": {"source": sample.source_id, "count": sample.count, "quality_flags": sample.quality_flags},
            "frame": site.frame, "origin": "MOON", "position_unit": "m", "time_scale": "UTC",
            "azimuth_convention": "east_of_north_deg; pole_uses_declared_reference_meridian",
            "horizons": {key: value.to_dict() for key, value in profiles.items()}, "tracks": tracks,
            "numerics": {"time_step_s": sample_step_s, "horizon_margin_deg": margin,
                         "interval_method": "adjacent_sample_classification_not_refined_events",
                         "interval_interior_verification": "not_proved; opportunities_shorter_than_step_may_be_missed"},
            "provenance": {"geometry": geometry.provenance, "terrain": [near_manifest]+([far_manifest] if far_manifest else [])},
            "warnings": ["Geometric diagnostics are not usable contacts or a delivery result.",
                         "Sun center classification is not solar visible fraction, illumination energy, or power.",
                         "Earth center is not any specific station. Station positions do not establish station visibility or service.",
                         "Same-epoch NONE geometry omits transmission light-time corrections; no delivery times are computed.",
                         "Extent convergence does not prove angular or radial sampling completeness; unresolved horizons stay unknown.",
                         "Renderer registration is absent. No map overlays are released by this diagnostic."],
        }
    return report
