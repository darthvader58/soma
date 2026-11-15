"""Bounded trajectories; interpolation and synthetic dynamics stay labeled."""
from copy import deepcopy
import bisect
import math
from types import MappingProxyType
import numpy as np
from soma.time import parse_utc, format_utc
from .surface import finite


def _record(target, epoch, frame, position, label):
    return {"target": target, "origin": "MOON", "frame": frame,
            "epoch": epoch, "epoch_format": "rfc3339" if isinstance(epoch, str) else "seconds_past_j2000_tdb",
            "time_scale": "UTC" if isinstance(epoch, str) else "TDB",
            "position": np.asarray(position).tolist(), "position_unit": "m", "provenance_label": label}


class StateHistory:
    """Documented JSON state history, not an OEM parser.

    Metadata requires origin, frame, time_scale, position_unit, velocity_unit,
    interpolation='linear', max_gap_s, coverage, target, provenance_label.
    Samples contain epoch, position, velocity. Positions are piecewise linear;
    reported velocities are interpolated separately, not used as derivatives.
    UTC uses aware RFC3339; TDB uses numeric seconds past J2000 and numeric
    coverage start/end. No extrapolation or interpolation through large gaps.
    """
    def __init__(self, metadata, samples, *, utc_to_et=None):
        self.metadata = deepcopy(metadata)
        m = self.metadata
        self.converter = utc_to_et
        if m.get("kind", "documented_state_history") != "documented_state_history":
            raise ValueError("unsupported trajectory import; only documented_state_history is accepted")
        if m["origin"] != "MOON" or m["frame"] not in ("J2000", "MOON_ME_DE421"):
            raise ValueError("state history must declare Moon origin and supported explicit axes")
        if m["time_scale"] not in ("UTC", "TDB") or m["interpolation"] != "linear":
            raise ValueError("unsupported time scale or interpolation; libration/Kepler import is not implemented")
        if m["time_scale"] == "UTC" and not callable(utc_to_et):
            raise ValueError("UTC state histories require a kernel-backed UTC-to-TDB converter")
        if (m["position_unit"], m["velocity_unit"]) not in (("m", "m/s"), ("km", "km/s")):
            raise ValueError("state position and velocity units must be explicit and consistent")
        if not isinstance(m["provenance_label"], str) or not m["provenance_label"]:
            raise ValueError("state history requires provenance")
        finite(m["max_gap_s"])
        if m["max_gap_s"] <= 0:
            raise ValueError("state-history max gap must be positive")
        if len(samples) < 2:
            raise ValueError("state history requires at least two samples")
        self.epochs = [self._epoch(x["epoch"]) for x in samples]
        if any(a >= b for a,b in zip(self.epochs, self.epochs[1:])):
            raise ValueError("state history epochs must increase strictly")
        self.positions = np.asarray([x["position"] for x in samples], dtype=float)
        self.velocities = np.asarray([x["velocity"] for x in samples], dtype=float)
        if self.positions.shape != (len(samples), 3) or self.velocities.shape != (len(samples), 3) or not np.isfinite(self.positions).all() or not np.isfinite(self.velocities).all():
            raise ValueError("state histories require finite position and velocity three-vectors")
        factor = 1000 if m["position_unit"] == "km" else 1
        self.positions *= factor
        self.velocities *= factor
        self.positions.flags.writeable = False
        self.velocities.flags.writeable = False
        coverage = m["coverage"]
        keys = ("start_utc", "end_utc") if m["time_scale"] == "UTC" else ("start_tdb_s", "end_tdb_s")
        self.start, self.end = [self._epoch(coverage[k]) for k in keys]
        if self.start >= self.end or self.start < self.epochs[0] or self.end > self.epochs[-1]:
            raise ValueError("declared history coverage must be bounded by samples")
        m["coverage"] = MappingProxyType(m["coverage"])
        self.metadata = MappingProxyType(m)
        self.epochs = tuple(self.epochs)

    def _epoch(self, value):
        if self.metadata["time_scale"] == "UTC":
            return float(self.converter(format_utc(parse_utc(value))))
        finite(value)
        return float(value)

    def state(self, epoch):
        t = self._epoch(epoch)
        if not self.start <= t <= self.end:
            raise ValueError("epoch outside state-history coverage")
        i = bisect.bisect_left(self.epochs, t)
        if i < len(self.epochs) and self.epochs[i] == t:
            p = self.positions[i]
        else:
            a,b = self.epochs[i-1:i+1]
            if b-a > self.metadata["max_gap_s"]:
                raise ValueError("state-history interpolation crosses a declared gap")
            f = (t-a)/(b-a)
            p = self.positions[i-1]*(1-f) + self.positions[i]*f
        exported = format_utc(parse_utc(epoch)) if self.metadata["time_scale"] == "UTC" else float(epoch)
        return _record(self.metadata["target"], exported, self.metadata["frame"], p,
                       self.metadata["provenance_label"]+"; documented_state_history_linear_position_interpolation")


class SyntheticTwoBodyLunarPreset:
    """Short-arc elliptical conic, never an operational or libration orbit.

    Elements are about Moon-centered J2000 axes, not a Moon-equator plane.
    GM, reference radius and all elements are explicitly supplied. SPICE conics
    uses km/s, with a local elapsed TDB-second epoch. UTC queries require a
    caller's active kernel-backed utc_to_et converter (including LSK).
    """
    label = "synthetic_two_body_lunar_preset"

    def __init__(self, *, target, epoch_utc, coverage, gm_m3_s2, reference_radius_m,
                 semimajor_axis_m, eccentricity, inclination_deg, ascending_node_deg,
                 argument_periapsis_deg, mean_anomaly_deg, utc_to_et):
        finite(gm_m3_s2, reference_radius_m, semimajor_axis_m, eccentricity, inclination_deg,
               ascending_node_deg, argument_periapsis_deg, mean_anomaly_deg)
        if gm_m3_s2 <= 0 or reference_radius_m <= 0 or not 0 <= eccentricity < 1 or not 0 <= inclination_deg <= 180 or semimajor_axis_m*(1-eccentricity) <= reference_radius_m:
            raise ValueError("synthetic lunar ellipse must be bounded and remain above its reference sphere")
        self.target = target
        self.epoch_utc = format_utc(parse_utc(epoch_utc))
        self.start = parse_utc(coverage["start_utc"])
        self.end = parse_utc(coverage["end_utc"])
        if not self.start <= parse_utc(epoch_utc) <= self.end or self.start >= self.end or (self.end-self.start).total_seconds() > 7*86400:
            raise ValueError("synthetic coverage must include epoch and span at most seven days")
        self.converter = utc_to_et
        self.epoch_et = self.converter(self.epoch_utc)
        self.elements = [semimajor_axis_m*(1-eccentricity)/1000, eccentricity,
                         *np.radians([inclination_deg, ascending_node_deg, argument_periapsis_deg, mean_anomaly_deg]),
                         0, gm_m3_s2/1e9]
        self.period_s = 2*math.pi*math.sqrt(semimajor_axis_m**3/gm_m3_s2)
        self.provenance = {"label": self.label, "origin": "MOON", "frame": "J2000",
                           "gm_m3_s2": gm_m3_s2, "reference_radius_m": reference_radius_m,
                           "omitted_forces": ["lunar_nonspherical_gravity", "Earth_and_Sun_third_body", "radiation_pressure"],
                           "coverage": deepcopy(coverage)}

    def state(self, utc):
        import spiceypy as spice
        t = parse_utc(utc)
        if not self.start <= t <= self.end:
            raise ValueError("epoch outside synthetic short-arc coverage")
        state = spice.conics(self.elements, self.converter(utc)-self.epoch_et)
        return _record(self.target, format_utc(t), "J2000", state[:3]*1000, self.label)
