"""Turn interval-wide geometric assessments into assumed-rate contacts.

Endpoint service includes acquisition and teardown; contact timestamps describe
payload transmission only. Resource conflicts and energy remain scheduler duties.
"""

from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import math

import numpy as np

from soma.time import parse_utc, format_utc
from soma.terrain.horizons import finite_segment_visibility
from soma.geometry.surface import segment_intersects_sphere
from .budget import link_budget as evaluate_link_budget


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{name} is outside its supported range")
    return value


def _interval(window):
    start, end = parse_utc(window["start_utc"]), parse_utc(window["end_utc"])
    if end <= start:
        raise ValueError("interval end must follow start")
    return start, end


def _window(start, end):
    return {"start_utc": format_utc(start), "end_utc": format_utc(end)}


def _merged(windows):
    merged = []
    for start, end in sorted(_interval(w) for w in windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _terminal(profile, terminal_id):
    matches = [t for t in profile["terminals"] if t["id"] == terminal_id]
    if len(matches) != 1:
        raise ValueError("terminal must identify exactly one configured terminal")
    terminal = matches[0]
    for field in ("acquisition_s", "teardown_s", "tx_electrical_w", "rx_electrical_w"):
        _number(terminal[field], field)
    if terminal["duplex"] not in ("half_duplex", "full_duplex") or not terminal["band"] or not terminal["mode_ids"]:
        raise ValueError("terminal capabilities must be declared")
    return terminal


def assess_contact(candidate, sender_profile, receiver_profile, *, guard_s, link_budget=None):
    """Assess one interval-wide opportunity with an explicit event guard.

    Geometry must cover the entire proposed interval. ``guard_s`` trims each
    geometric edge once. Endpoint setup/teardown trim each endpoint's service
    separately, with receiver service mapped back by the declared constant delay.
    No geometry interpolation, pointing policy, service, rate, or power is inferred.
    """
    opportunity = deepcopy(candidate)
    result = {"opportunity": opportunity, "contacts": [], "endpoint_occupancy": [],
              "decision": {"status": "unknown", "reasons": []}, "model_fidelity": "unknown"}

    def finish(status, reason):
        result["decision"] = {"status": status, "reasons": [reason]}
        return result

    try:
        guard = timedelta(seconds=_number(guard_s, "guard_s"))
        start, end = _interval(candidate["source_transmit_window"])
        geometry = candidate["geometry_status"]
        if geometry == "blocked":
            return finish("rejected", candidate["geometry_reason"])
        if geometry != "clear_under_sampling":
            return finish("unknown", candidate.get("geometry_reason") or "geometry_unknown")
        if not candidate["geometry_evidence"] or not candidate["geometry_reason"]:
            return finish("unknown", "geometry_evidence_missing")
        evidence = candidate["geometry_evidence"]
        if evidence.get("scope") != "interval_wide":
            return finish("unknown", "interval_wide_geometry_evidence_required")
        coverage_start, coverage_end = _interval(evidence["coverage"])
        if coverage_start > start or coverage_end < end:
            return finish("unknown", "geometry_evidence_does_not_cover_candidate")
        tx = _terminal(sender_profile, candidate["sender_terminal_id"])
        rx = _terminal(receiver_profile, candidate["receiver_terminal_id"])
        if tx["band"] != rx["band"]:
            return finish("rejected", "incompatible_band")
        if any(candidate["mode_id"] not in t["mode_ids"] for t in (tx, rx)):
            return finish("rejected", "incompatible_mode")
        if candidate["pointing_assumption"] != "ideal_pointing":
            return finish("unknown", "nonideal_pointing_not_implemented")
        if candidate["input_class"] not in ("measured", "published", "synthetic", "assumed"):
            raise ValueError("input class must be declared")
        delay = candidate["one_way_delay"]
        seconds = _number(delay["seconds"], "one_way_delay.seconds")
        if delay["model"] not in ("constant_assumed", "disabled_for_synthetic_test"):
            return finish("unknown", "unsupported_delay_model")
        if delay["model"] == "disabled_for_synthetic_test" and (seconds != 0 or candidate["input_class"] != "synthetic"):
            raise ValueError("disabled light time is only a zero-delay synthetic test")
        delay_us = int((Decimal(str(seconds))*1000000).to_integral_value(rounding=ROUND_CEILING))
        delta = timedelta(microseconds=delay_us)
        delay = {**delay, "seconds": delay_us/1000000}
        method = candidate["rate_method"]
        if method == "assumed_net_rate":
            rate = _number(candidate["payload_rate_bps"], "payload_rate_bps", positive=True)
            fidelity = "assumed_rate_simulation"
            performance_flags = ["assumed_net_rate", "link_budget_not_computed"]
        elif method == "link_budget":
            if link_budget is None:
                return finish("unknown", "link_budget_inputs_missing_no_physical_closure_claim")
            if link_budget["mode"]["mode_id"] != candidate["mode_id"]:
                return finish("rejected", "link_budget_mode_mismatch")
            budget_start, budget_end = _interval(link_budget["profile"]["coverage"])
            if budget_start > start or budget_end < end:
                return finish("unknown", "link_budget_range_bound_does_not_cover_interval")
            performance = evaluate_link_budget(link_budget["profile"], link_budget["mode"])
            result["link_budget"] = performance
            if link_budget["profile"]["tx_rf_power_w"] > tx["tx_electrical_w"]:
                return finish("unknown", "radiated_power_exceeds_declared_radio_electrical_draw")
            if performance["status"] != "margin_met_under_declared_assumptions":
                return finish("rejected", "insufficient_link_margin")
            rate = performance["payload_rate_bps"]
            fidelity = "modeled_link_budget"
            performance_flags = ["modeled_link_budget", "margin_met_under_declared_assumptions"]
        else:
            return finish("unknown", "unsupported_rate_method")
        if not candidate["service_assumption_label"]:
            raise ValueError("service assumption label is required")
        services = []
        for profile in (sender_profile, receiver_profile):
            service = profile["service"]
            if not service["label"] or service["input_class"] not in ("synthetic", "assumed", "measured", "published"):
                raise ValueError("service provenance is required")
            services.append(_merged(service["windows"]))
        intervals = []
        for a, b in services[0]:
            for c, d in services[1]:
                left = max(start+guard+timedelta(seconds=max(tx["acquisition_s"], rx["acquisition_s"])), a+timedelta(seconds=tx["acquisition_s"]),
                           c+timedelta(seconds=rx["acquisition_s"])-delta)
                right = min(end-guard-timedelta(seconds=max(tx["teardown_s"], rx["teardown_s"])), b-timedelta(seconds=tx["teardown_s"]),
                            d-timedelta(seconds=rx["teardown_s"])-delta)
                if left < right:
                    intervals.append((left, right))
        for index, (left, right) in enumerate(intervals):
            duration = right-left
            microseconds = (duration.days*86400+duration.seconds)*1000000+duration.microseconds
            bits = int((Decimal(str(rate))*Decimal(microseconds)/Decimal(1000000)).to_integral_value(rounding=ROUND_FLOOR))
            input_flags = [flag for flag in candidate["quality_flags"] if flag not in ("assumed_net_rate", "link_budget_not_computed", "modeled_link_budget")]
            flags = sorted(set(input_flags + performance_flags + [
                           "ideal_pointing", "same_epoch_geometry", "radio_conflicts_and_energy_not_yet_checked",
                           f"input_class_{candidate['input_class']}"]))
            contact_id = candidate["contact_id"] if len(intervals) == 1 else f"{candidate['contact_id']}.{index+1}"
            result["contacts"].append({"contact_id": contact_id, "sender": candidate["sender"],
                "receiver": candidate["receiver"], "sender_terminal_id": tx["id"], "receiver_terminal_id": rx["id"],
                "timing_convention": "source_transmit_epochs", "source_transmit_window": _window(left, right),
                "mode_id": candidate["mode_id"], "rate_method": method, "payload_rate_bps": rate,
                "payload_rate_definition": "net_payload_bits_per_second_overhead_already_applied",
                "available_capacity_bits": bits, "one_way_delay": deepcopy(delay),
                "service_provenance": f"{candidate['service_assumption_label']}; sender: {sender_profile['service']['label']}; receiver: {receiver_profile['service']['label']}",
                "quality_flags": flags})
            result["endpoint_occupancy"].append({"contact_id": contact_id,
                "sender_occupancy_interval": _window(left-timedelta(seconds=tx["acquisition_s"]), right+timedelta(seconds=tx["teardown_s"])),
                "receiver_occupancy_interval": _window(left+delta-timedelta(seconds=rx["acquisition_s"]), right+delta+timedelta(seconds=rx["teardown_s"])),
                "byte_available_utc": format_utc(right+delta), "available_capacity_bytes": bits//8,
                "sender_duplex": tx["duplex"], "receiver_duplex": rx["duplex"],
                "tx_electrical_w": tx["tx_electrical_w"], "rx_electrical_w": rx["rx_electrical_w"]})
        result["model_fidelity"] = fidelity
        return finish("usable_under_assumptions" if intervals else "rejected",
                      ("assumed_rate_no_link_closure_claim" if method == "assumed_net_rate" else "modeled_margin_no_operational_service_claim") if intervals else "no_endpoint_service_after_delay_and_setup")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return finish("unknown", f"invalid_or_missing_contact_input: {error}")


def evaluate_geometry(dem, sender_state, receiver_state, *, step_m, clearance_m,
                      body_radius_m, occulting_spheres, station_normal=None,
                      minimum_elevation_deg=None, occulting_ellipsoids=()):
    """Finite same-epoch lunar segment plus declared spherical body masks.

    Extra body centers and station normal must be transformed by the caller into
    the states' common Moon-centered frame. Station normal is the Earth-ellipsoid
    surface normal, not the Moon-centered station position. Returns one sample,
    never an inferred interval-wide opportunity.
    """
    for key in ("origin", "frame", "epoch", "epoch_format", "time_scale", "position_unit"):
        if sender_state[key] != receiver_state[key]:
            raise ValueError(f"endpoint state {key} differs")
    if sender_state["origin"] != "MOON" or sender_state["position_unit"] != "m":
        raise ValueError("geometry requires Moon-centered meters")
    a, b = np.asarray(sender_state["position"], float), np.asarray(receiver_state["position"], float)
    terrain = asdict(finite_segment_visibility(dem, a, b, frame=sender_state["frame"],
                    step_m=step_m, clearance_m=clearance_m, body_radius_m=body_radius_m))
    v = b-a
    for body in occulting_spheres:
        center = np.asarray(body["center_m"], float)
        radius = _number(body["radius_m"], "body.radius_m", positive=True)
        if center.shape != (3,) or not np.all(np.isfinite(center)):
            raise ValueError("body center requires three finite meters")
        if segment_intersects_sphere(a, b, radius, center_m=center):
            terrain.update(status="blocked", reason=f"{body['id']}_body_intersection")
    for body in occulting_ellipsoids:
        center = np.asarray(body['center_m'], float)
        radii = np.asarray(body['radii_m'], float)
        rotation = np.asarray(body['rotation_common_to_body'], float)
        if (center.shape != (3,) or radii.shape != (3,) or not np.isfinite(center).all()
                or not np.isfinite(radii).all() or np.any(radii <= 0)
                or rotation.shape != (3, 3) or not np.isfinite(rotation).all()
                or not np.allclose(rotation@rotation.T, np.eye(3), atol=1e-12, rtol=0)
                or not math.isclose(float(np.linalg.det(rotation)), 1, abs_tol=1e-12)):
            raise ValueError('Body ellipsoid requires positive radii and an orthonormal frame rotation')
        a_body = (rotation@(a-center))/radii
        b_body = (rotation@(b-center))/radii
        if segment_intersects_sphere(a_body, b_body, 1, endpoint_tolerance_m=1e-12):
            terrain.update(status='blocked', reason=f"{body['id']}_ellipsoid_intersection")
    if (station_normal is None) != (minimum_elevation_deg is None):
        raise ValueError("station elevation requires both normal and limit")
    if station_normal is not None:
        normal = np.asarray(station_normal, float)
        if normal.shape != (3,) or not np.all(np.isfinite(normal)) or not math.isclose(float(np.linalg.norm(normal)), 1, abs_tol=1e-9):
            raise ValueError("station normal must be a unit vector in the common frame")
        if not math.isfinite(minimum_elevation_deg) or not -90 <= minimum_elevation_deg <= 90:
            raise ValueError("invalid station elevation limit")
        if np.linalg.norm(v) == 0:
            return {**terrain, "status": "unknown", "reason": "degenerate_segment"}
        elevation = math.degrees(math.asin(float(np.clip(np.dot(-v/np.linalg.norm(v), normal), -1, 1))))
        terrain["station_elevation_deg"] = elevation
        if elevation < minimum_elevation_deg:
            terrain.update(status="blocked", reason="station_below_minimum_elevation")
    terrain["quality_flags"] = list(terrain["quality_flags"])
    terrain["scope"] = "single_same_epoch_sample_not_interval"
    return terrain
