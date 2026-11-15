"""Direct sunlight under sampled lunar horizons and a spherical Earth mask."""

import math
import numpy as np

__all__ = ["solar_disk_visibility"]


def _vector(value):
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)) or not math.isfinite(float(np.linalg.norm(vector))) or np.linalg.norm(vector) == 0:
        raise ValueError("Require a nonzero finite local ENU vector in meters")
    return vector, float(np.linalg.norm(vector))


def solar_disk_visibility(sun_vector_enu_m, earth_vector_enu_m, *, horizon,
                          sun_radius_m=695700000.0, earth_radius_m=6378137.0,
                          horizon_margin_deg=0.1, samples=512, max_samples=8192,
                          tolerance=0.005):
    """Uniform projected disk quadrature, refined by doubling the sample count.

    Bounds concern unknown terrain at sampled rays, not a rigorous quadrature or
    DEM error bound. Adjacent horizon bands are linearly interpolated; either
    missing endpoint makes the ray unknown. Extent nonconvergence makes all
    terrain rays unknown. Earth and terrain mask the very same disk samples.
    """
    sun, distance = _vector(sun_vector_enu_m)
    earth, earth_distance = _vector(earth_vector_enu_m)
    if not all(math.isfinite(x) and x > 0 for x in (sun_radius_m, earth_radius_m)):
        raise ValueError("Body radii must be positive finite meters")
    if distance <= sun_radius_m or earth_distance <= earth_radius_m:
        raise ValueError("Observer must be outside both bodies")
    if not math.isfinite(horizon_margin_deg) or horizon_margin_deg < 0:
        raise ValueError("Horizon margin must be finite and nonnegative")
    if (isinstance(samples, bool) or not isinstance(samples, int) or samples < 64
            or not isinstance(max_samples, int) or max_samples < 2*samples or max_samples > 131072):
        raise ValueError("Require 64 <= samples, 2*samples <= max_samples <= 131072")
    if not math.isfinite(tolerance) or not 0 < tolerance < 1:
        raise ValueError("Convergence tolerance must be between zero and one")
    bands = sorted(horizon["bands"], key=lambda band: band["azimuth_deg"])
    az = np.asarray([b["azimuth_deg"] for b in bands], dtype=float)
    elevations = [b["elevation_deg"] for b in bands]
    if len(bands) < 2 or not np.all(np.isfinite(az)) or az[0] < 0 or az[-1] >= 360 or np.any(np.diff(az) <= 0):
        raise ValueError("Horizon requires unique ascending azimuths spanning [0,360)")
    if any(e is not None and (not math.isfinite(e) or not -90 <= e <= 90) for e in elevations):
        raise ValueError("Horizon elevations must be finite degrees or None")
    if not isinstance(horizon.get("converged"), bool):
        raise ValueError("Horizon must declare extent convergence")
    direction = sun/distance
    axis = np.eye(3)[int(np.argmin(np.abs(direction)))]
    tangent = np.cross(direction, axis)
    tangent /= np.linalg.norm(tangent)
    other = np.cross(direction, tangent)
    angular_radius = math.asin(sun_radius_m/distance)
    earth_unit = earth/earth_distance
    earth_cos = math.sqrt(1-(earth_radius_m/earth_distance)**2)
    previous, history = None, []
    n, converged = samples, False
    while True:
        indices = np.arange(n)
        radius = np.sqrt((indices+0.5)/n)*math.sin(angular_radius)
        phase = indices*(math.pi*(3-math.sqrt(5)))
        rays = (np.sqrt(1-radius**2)[:, None]*direction
                + (radius*np.cos(phase))[:, None]*tangent
                + (radius*np.sin(phase))[:, None]*other)
        sample_az = np.degrees(np.arctan2(rays[:, 0], rays[:, 1])) % 360
        sample_el = np.degrees(np.arcsin(np.clip(rays[:, 2], -1, 1)))
        right = np.searchsorted(az, sample_az, side="right") % len(az)
        left = (right-1) % len(az)
        known = np.array([elevations[l] is not None and elevations[r] is not None
                          for l, r in zip(left, right)]) & horizon["converged"]
        width = (az[right]-az[left]) % 360
        weight = ((sample_az-az[left]) % 360)/width
        values = np.array([np.nan if e is None else e for e in elevations])
        skyline = values[left]*(1-weight)+values[right]*weight+horizon_margin_deg
        terrain_blocked = known & (sample_el <= skyline)
        # For every ray, compare its near intersections with the Earth and Sun
        # spheres, rather than treating a target behind the Sun as an eclipse.
        earth_dot = rays @ earth_unit
        in_earth_disk = earth_dot >= earth_cos
        earth_near = earth_distance*earth_dot-np.sqrt(np.maximum(
            0, earth_radius_m**2-earth_distance**2*(1-earth_dot**2)))
        sun_dot = rays @ direction
        sun_near = distance*sun_dot-np.sqrt(np.maximum(
            0, sun_radius_m**2-distance**2*(1-sun_dot**2)))
        earth_blocked = in_earth_disk & (earth_near > 0) & (earth_near < sun_near)
        clear = known & ~terrain_blocked & ~earth_blocked
        unresolved = ~known & ~earth_blocked
        bounds = (float(np.mean(clear)), float(np.mean(clear | unresolved)))
        history.append({"samples": n, "lower_bound": bounds[0], "upper_bound": bounds[1]})
        if previous is not None and max(abs(a-b) for a,b in zip(bounds, previous)) <= tolerance:
            converged = True
            break
        if n == max_samples:
            break
        previous = bounds
        n = min(n*2, max_samples)
    known_fraction = not np.any(unresolved)
    return {"visible_fraction": bounds[0] if known_fraction and converged else None,
            "lower_bound": bounds[0], "upper_bound": bounds[1],
            "status": "evaluated_under_sampling" if known_fraction and converged else "unknown",
            "method": "uniform_projected_disk_golden_angle_same_ray_masks_v1",
            "converged": converged, "horizon_converged": horizon["converged"],
            "sampling_history": history, "samples": n, "tolerance": tolerance,
            "bounds_scope": "unknown_terrain_on_sampled_rays_not_quadrature_error",
            "horizon_interpolation": "periodic_linear_between_adjacent_azimuth_bands",
            "horizon_margin_deg": horizon_margin_deg,
            "observer_height_m": horizon.get("site", {}).get("height_m"),
            "sun_direction_enu": direction.tolist(), "sun_range_m": distance,
            "sun_angular_radius_deg": math.degrees(angular_radius),
            "earth_range_m": earth_distance,
            "earth_angular_radius_deg": math.degrees(math.asin(earth_radius_m/earth_distance)),
            "sun_radius_m": sun_radius_m, "earth_radius_m": earth_radius_m,
            "mask_counts": {"terrain_blocked": int(np.sum(terrain_blocked)),
                            "earth_blocked": int(np.sum(earth_blocked)),
                            "both_blocked": int(np.sum(terrain_blocked & earth_blocked)),
                            "unknown_unmasked": int(np.sum(unresolved)),
                            "visible": int(np.sum(clear))},
            "limitations": ["spherical Earth without atmosphere", "uniform solar brightness; no limb darkening",
                            "sampled horizon interpolation cannot resolve omitted terrain features"]}
