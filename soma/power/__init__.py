"""Fixed-panel direct sunlight and event-aligned electrical battery replay."""

import math
from soma.illumination import _vector
from soma.time import parse_utc, format_utc

AU_M = 149597870700.0
__all__ = ["fixed_panel_power", "integrate_battery"]


def _number(value, name, *, positive=False, upper=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0 or (positive and value == 0) or (upper is not None and value > upper):
        raise ValueError(f"{name} is outside the supported range")
    return float(value)


def fixed_panel_power(panel_profile, sun_vector_enu_m, visible_fraction):
    """Center-direction projected area times direct uniform-disk visibility.

    The center-ray projection is explicitly an approximation near edge-on
    incidence; it does not integrate incidence separately over the visible disk.
    """
    if panel_profile["kind"] != "fixed":
        raise ValueError("Only fixed panels supported; tracker limits and overhead are unimplemented")
    normal, length = _vector(panel_profile["normal_local_enu"])
    if not math.isclose(length, 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Panel normal must be an explicit unit ENU vector")
    sun, distance = _vector(sun_vector_enu_m)
    area = _number(panel_profile["area_m2"], "area_m2")
    efficiency = _number(panel_profile["efficiency"], "efficiency", upper=1)
    derating = _number(panel_profile["lumped_derating"], "lumped_derating", upper=1)
    irradiance = _number(panel_profile["irradiance_at_1au_w_m2"], "irradiance_at_1au_w_m2", positive=True)*(AU_M/distance)**2
    cosine = max(0.0, float(normal @ (sun/distance)))
    fraction = None if visible_fraction is None else _number(visible_fraction, "visible_fraction", upper=1)
    power = None if fraction is None else irradiance*area*efficiency*derating*cosine*fraction
    return {"generated_power_w": power, "status": "unknown" if power is None else "evaluated_under_assumptions",
            "normal_local_enu": normal.tolist(), "irradiance_w_m2": irradiance,
            "sun_distance_m": distance, "reference_distance_m": AU_M,
            "projected_area_m2": area*cosine, "visible_fraction": fraction,
            "efficiency": efficiency, "lumped_derating": derating,
            "method": "inverse_square_irradiance_fixed_panel_center_direction_projection",
            "limitations": ["temperature and self-shadowing unmodeled", "uniform-disk fraction times center-ray projection"]}


def integrate_battery(profile, bins, *, base_load_w):
    """Replay strictly piecewise constant electrical bus power, in chronological bins.

    Charge and discharge limits are bus-side watts. A monotone constant-power
    interval has extrema at its ends, so checking both ends also checks its
    interior. Every change must be supplied as a bin boundary. A violated trace
    remains a counterfactual demand trajectory, never an executable schedule.
    """
    base = _number(base_load_w, "base_load_w", positive=True)
    capacity = _number(profile["capacity_wh"], "capacity_wh", positive=True)
    energy = _number(profile["initial_energy_wh"], "initial_energy_wh", upper=capacity)
    reserve = _number(profile["reserve_wh"], "reserve_wh", upper=capacity)
    max_charge = _number(profile["max_charge_w"], "max_charge_w")
    max_discharge = _number(profile["max_discharge_w"], "max_discharge_w")
    charge_eff = _number(profile["charge_efficiency"], "charge_efficiency", positive=True, upper=1)
    discharge_eff = _number(profile["discharge_efficiency"], "discharge_efficiency", positive=True, upper=1)
    samples, intervals, violations = [], [], []
    previous_end, unknown = None, False
    if energy < reserve:
        violations.append({"bin_index": 0, "reason": "initial_reserve_violation",
                           "stored_energy_wh": energy, "reserve_wh": reserve})
    bins = list(bins)
    if not bins or len(bins) > 100000:
        raise ValueError("Require one to 100000 explicit constant-power bins")
    for index, item in enumerate(bins):
        if set(item)-{"start_utc", "end_utc", "generation_w", "incremental_load_w", "power_model"}:
            raise ValueError("Unsupported bin fields; split every internal power change")
        if item.get("power_model", "piecewise_constant") != "piecewise_constant":
            raise ValueError("Only exact piecewise_constant bins supported; split changes at event times")
        start, end = parse_utc(item["start_utc"]), parse_utc(item["end_utc"])
        if end <= start or (previous_end is not None and start != previous_end):
            raise ValueError("Battery bins must be positive, chronological and contiguous")
        previous_end = end
        hours = (end-start).total_seconds()/3600
        generation = item["generation_w"]
        if generation is not None:
            generation = _number(generation, "generation_w")
        demand = base+_number(item["incremental_load_w"], "incremental_load_w")
        initial = energy
        if not samples:
            samples.append({"epoch_utc": format_utc(start), "stored_energy_wh": initial})
        if generation is None or energy is None:
            unknown, energy = True, None
            charge = discharge = spill = None
        else:
            surplus = generation-demand
            charge, discharge, spill = 0.0, 0.0, 0.0
            if surplus >= 0:
                charge = min(surplus, max_charge)
                stored = min(capacity-energy, charge*hours*charge_eff)
                energy += stored
                # Includes curtailment from charge rate and full capacity.
                spill = surplus*hours-stored/charge_eff
                charge = stored/(hours*charge_eff)
            else:
                discharge = -surplus
                energy -= discharge*hours/discharge_eff
                if discharge > max_discharge+1e-10:
                    violations.append({"bin_index": index, "reason": "instantaneous_discharge_power_exceeded",
                                       "required_bus_w": discharge, "limit_bus_w": max_discharge})
            if min(initial, energy) < reserve-1e-10:
                violations.append({"bin_index": index, "reason": "reserve_violation",
                                   "minimum_stored_energy_wh": min(initial, energy), "reserve_wh": reserve})
        intervals.append({"start_utc": format_utc(start), "end_utc": format_utc(end),
                          "start_energy_wh": initial, "end_energy_wh": energy,
                          "generation_w": generation, "electrical_load_w": demand,
                          "charge_bus_w": charge, "discharge_bus_w": discharge,
                          "charge_bus_w_definition": "bin_average_after_capacity_curtailment",
                          "spilled_bus_energy_wh": spill})
        samples.append({"epoch_utc": format_utc(end), "stored_energy_wh": energy})
    return {"status": "violated" if violations else "unknown" if unknown else "satisfied_under_piecewise_constant_assumptions",
            "samples": samples, "intervals": intervals, "violations": violations,
            "base_load_w": base, "power_limit_convention": "bus_side_watts",
            "method": "signed_net_bus_power_exact_constant_bin_integration",
            "interior_check": "monotone_energy_extrema_at_both_bounds; every_power_change_requires_split",
            "limitations": ["no scheduler or schedule-feasibility claim", "unknown generation propagates unknown stored energy"]}
