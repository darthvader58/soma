"""Sampled lunar horizons and finite segment terrain tests.

Method reference: Barker et al. (2021), section 5,
https://doi.org/10.1016/j.pss.2020.105119. SOMA uses Cartesian terrain vectors
and configurable nested sampling, without adopting that paper's site results.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import numpy as np

from soma.geometry import local_basis, surface_position
from .dem import DATUM, FRAME, RADIUS_M, DEM

ALGORITHM_VERSION = "cartesian-sampled-horizon-1"


@dataclass(frozen=True)
class HorizonSite:
    latitude_deg: float
    longitude_deg_east: float
    elevation_m: float
    height_m: float
    pole_reference_meridian_deg_east: float
    frame: str
    reference_radius_m: float
    elevation_datum: str

    def __post_init__(self):
        surface_position(self.latitude_deg, self.longitude_deg_east, self.reference_radius_m, self.elevation_m)
        if self.frame != FRAME or self.elevation_datum != DATUM or self.reference_radius_m != RADIUS_M:
            raise ValueError("Unsupported horizon reference surface")
        if not math.isfinite(self.height_m) or self.height_m < 0:
            raise ValueError("Observer height must be finite and nonnegative")
        local_basis(self.latitude_deg, self.longitude_deg_east, self.pole_reference_meridian_deg_east)


@dataclass(frozen=True)
class HorizonSampling:
    azimuth_step_deg: float
    near_step_m: float
    far_step_m: float
    near_extent_m: float
    extents_m: tuple[float, ...]
    convergence_tolerance_deg: float
    required_max_extent_m: float

    def __post_init__(self):
        object.__setattr__(self, "extents_m", tuple(self.extents_m))
        positive = (self.azimuth_step_deg, self.near_step_m, self.far_step_m,
                    self.near_extent_m, self.required_max_extent_m, *self.extents_m)
        if any(not math.isfinite(x) or x <= 0 for x in positive):
            raise ValueError("Sampling distances and angles must be positive and finite")
        if self.azimuth_step_deg > 180 or not math.isclose(360/self.azimuth_step_deg, round(360/self.azimuth_step_deg)):
            raise ValueError("Azimuth step must divide 360 and be at most 180 degrees")
        if len(self.extents_m) < 2 or any(b <= a for a, b in zip(self.extents_m, self.extents_m[1:])):
            raise ValueError("Convergence requires at least two increasing extents")
        if self.extents_m[0] < self.near_extent_m or self.extents_m[-1] < self.required_max_extent_m:
            raise ValueError("Extent sequence must cover near terrain and the declared required maximum")
        if self.extents_m[-1] >= math.pi * RADIUS_M:
            raise ValueError("Horizon rays must remain shorter than a lunar half circumference")
        if not math.isfinite(self.convergence_tolerance_deg) or self.convergence_tolerance_deg < 0:
            raise ValueError("Convergence tolerance must be finite and nonnegative")
        radial_count = math.ceil(self.near_extent_m/self.near_step_m) + math.ceil(
            max(0, self.extents_m[-1]-self.near_extent_m)/self.far_step_m) + len(self.extents_m)+1
        if round(360/self.azimuth_step_deg)*radial_count > 2_000_000:
            raise ValueError("Horizon sampling exceeds the bounded two-million-point workload")


@dataclass(frozen=True)
class HorizonBand:
    azimuth_deg: float
    elevation_deg: float | None
    sampled_lower_bound_deg: float | None
    unknown_samples: int
    quality_flags: tuple[str, ...]


@dataclass(frozen=True)
class HorizonProfile:
    cache_key: str
    site: HorizonSite
    sampling: HorizonSampling
    bands: tuple[HorizonBand, ...]
    converged: bool
    maximum_change_deg: float | None
    algorithm_version: str = ALGORITHM_VERSION
    classification_scope: str = "sampled_distant_target_horizon_not_finite_spacecraft"

    def to_dict(self):
        return asdict(self)


def horizon_cache_key(dem: DEM, site: HorizonSite, sampling: HorizonSampling):
    if (dem.frame, dem.reference_radius_m, dem.elevation_datum) != (
            site.frame, site.reference_radius_m, site.elevation_datum):
        raise ValueError("DEM and observer reference surfaces differ")
    if not dem.source_hashes or any(len(h) != 64 for h in dem.source_hashes):
        raise ValueError("Every DEM must supply complete SHA256 identities")
    content = {"site": asdict(site), "sampling": asdict(sampling),
               "source_hashes": dem.source_hashes, "algorithm_version": ALGORITHM_VERSION}
    return hashlib.sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _lat_lon(point):
    radius = float(np.linalg.norm(point))
    if radius == 0:
        raise ValueError("Lunar center has no surface coordinates")
    return math.degrees(math.asin(np.clip(point[2]/radius, -1, 1))), (
        math.degrees(math.atan2(point[1], point[0])) + 180) % 360 - 180


def _distances(sampling):
    near = np.arange(sampling.near_step_m, sampling.near_extent_m, sampling.near_step_m)
    far = np.arange(sampling.near_extent_m, sampling.extents_m[-1], sampling.far_step_m)
    return sorted(set(float(d) for d in (*near, *far, *sampling.extents_m, sampling.near_extent_m)))


class HorizonCache:
    """Run-local immutable records; no cache can overwrite another input identity."""

    def __init__(self):
        self._profiles = {}

    def get(self, key):
        return self._profiles.get(key)

    def put(self, profile):
        existing = self._profiles.get(profile.cache_key)
        if existing is not None and existing != profile:
            raise ValueError("Nondeterministic horizon for the same cache identity")
        self._profiles[profile.cache_key] = profile


def build_horizon(dem: DEM, site: HorizonSite, sampling: HorizonSampling, *, cache=None):
    key = horizon_cache_key(dem, site, sampling)
    if cache is not None and cache.get(key) is not None:
        return cache.get(key)
    basis = local_basis(site.latitude_deg, site.longitude_deg_east, site.pole_reference_meridian_deg_east)
    observer = surface_position(site.latitude_deg, site.longitude_deg_east,
                                site.reference_radius_m, site.elevation_m + site.height_m)
    distances = _distances(sampling)
    bands, changes = [], []
    for azimuth in np.arange(0, 360, sampling.azimuth_step_deg):
        a = math.radians(azimuth)
        tangent = basis[0]*math.sin(a) + basis[1]*math.cos(a)
        angles, unknown = [], 0
        flags = {"sampled_horizon", "no_atmospheric_refraction"}
        for distance in distances:
            arc = distance/site.reference_radius_m
            direction = basis[2]*math.cos(arc) + tangent*math.sin(arc)
            lat, lon = _lat_lon(direction)
            sample = dem.sample(lat, lon)
            flags.update(sample.quality_flags)
            if sample.elevation_m is None:
                unknown += 1
                continue
            terrain = surface_position(lat, lon, site.reference_radius_m, sample.elevation_m)
            east, north, up = basis @ (terrain-observer)
            angles.append((distance, math.degrees(math.atan2(up, math.hypot(east, north)))))
        lower = max((value for _, value in angles), default=None)
        if unknown or lower is None:
            bands.append(HorizonBand(float(azimuth), None, lower, unknown, tuple(sorted(flags | {"unknown_horizon"}))))
            continue
        per_extent = [max(value for distance, value in angles if distance <= extent)
                      for extent in sampling.extents_m]
        changes.append(abs(per_extent[-1]-per_extent[-2]))
        bands.append(HorizonBand(float(azimuth), lower, lower, 0, tuple(sorted(flags))))
    converged = len(changes) == len(bands) and max(changes) <= sampling.convergence_tolerance_deg
    profile = HorizonProfile(key, site, sampling, tuple(bands), converged,
                             max(changes) if len(changes) == len(bands) else None)
    if cache is not None:
        cache.put(profile)
    return profile


@dataclass(frozen=True)
class SegmentVisibility:
    status: str
    reason: str
    minimum_sampled_clearance_m: float | None
    tested_range_m: float
    sample_count: int
    quality_flags: tuple[str, ...]


def finite_segment_visibility(dem: DEM, observer_m, target_m, *, frame: str,
                              step_m: float, clearance_m: float, body_radius_m: float,
                              max_samples: int = 100000):
    """Test only the segment, including endpoints, in a declared common frame.

    ``body_radius_m`` is an explicitly declared conservative solid-body radius,
    NOT automatically the reference sphere (LOLA elevations can be negative).
    Clear means clear under the recorded finite sampling, not RF link closure.
    """
    if frame != dem.frame or frame != FRAME:
        raise ValueError("Segment and terrain frames must match MOON_ME_DE421")
    start, stop = np.asarray(observer_m, dtype=float), np.asarray(target_m, dtype=float)
    if start.shape != (3,) or stop.shape != (3,) or not np.all(np.isfinite([start, stop])):
        raise ValueError("Segment endpoints require three finite Moon-centered meters")
    if not math.isfinite(step_m) or step_m <= 0 or not math.isfinite(clearance_m) or clearance_m < 0:
        raise ValueError("Require positive finite step and nonnegative clearance")
    if not math.isfinite(body_radius_m) or not 0 < body_radius_m <= dem.reference_radius_m:
        raise ValueError("Declare a positive conservative solid-body radius no larger than reference sphere")
    vector = stop-start
    length = float(np.linalg.norm(vector))
    if length < 1e-6:
        return SegmentVisibility("unknown", "degenerate_segment", None, length, 0, ("unresolved_geometry",))
    fraction = float(np.clip(-np.dot(start, vector)/np.dot(vector, vector), 0, 1))
    if np.linalg.norm(start+fraction*vector) < body_radius_m:
        return SegmentVisibility("blocked", "solid_body_intersection", None, length, 0, ("declared_body_radius",))
    intervals = math.ceil(length/step_m)
    if intervals+1 > max_samples:
        return SegmentVisibility("unknown", "sampling_budget_exceeded", None, length, 0, ("unresolved_geometry",))
    minimum, unknown, flags = math.inf, False, {"finite_segment", "sampled_terrain_clearance", "same_epoch_geometry"}
    for index, t in enumerate(np.linspace(0, 1, intervals+1)):
        point = start+t*vector
        lat, lon = _lat_lon(point)
        sample = dem.sample(lat, lon)
        flags.update(sample.quality_flags)
        if sample.elevation_m is None:
            unknown = True
            continue
        gap = float(np.linalg.norm(point))-dem.reference_radius_m-sample.elevation_m
        minimum = min(minimum, gap)
        if gap < -clearance_m:
            return SegmentVisibility("blocked", "sampled_terrain_intersection", minimum, length,
                                     index+1, tuple(sorted(flags)))
        if gap <= clearance_m:
            unknown = True
            flags.add("grazing_or_below_clearance_margin")
    status = "unknown" if unknown else "clear"
    return SegmentVisibility(status, "missing_terrain_or_unresolved_clearance" if unknown else "clear_under_sampling",
                             None if minimum == math.inf else minimum, length, intervals+1, tuple(sorted(flags)))
