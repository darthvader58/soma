"""Planetocentric spherical geometry in meters, without refraction."""
from dataclasses import dataclass, fields
import math
import numpy as np


def finite(*values):
    if not all(isinstance(v, (int, float, np.number)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        raise ValueError("geometry requires finite numeric values")


def angles(latitude_deg, longitude_deg_east):
    finite(latitude_deg, longitude_deg_east)
    if not -90 <= latitude_deg <= 90 or not -180 <= longitude_deg_east < 180:
        raise ValueError("planetocentric latitude or east-positive longitude out of range")


def surface_position(latitude_deg, longitude_deg_east, radius_m, elevation_m=0):
    angles(latitude_deg, longitude_deg_east)
    finite(radius_m, elevation_m)
    if radius_m <= 0 or radius_m + elevation_m <= 0:
        raise ValueError("reference and surface radii must be positive")
    lat, lon = np.radians([latitude_deg, longitude_deg_east])
    c = 0.0 if abs(latitude_deg) == 90 else math.cos(lat)
    return (radius_m + elevation_m) * np.array([c*math.cos(lon), c*math.sin(lon), math.sin(lat)])


def local_basis(latitude_deg, longitude_deg_east, pole_reference_meridian_deg_east=0):
    """Return rows east, north, up; at a pole use the declared meridian."""
    angles(latitude_deg, longitude_deg_east)
    angles(0, pole_reference_meridian_deg_east)
    lon = pole_reference_meridian_deg_east if abs(latitude_deg) == 90 else longitude_deg_east
    lat, lon = np.radians([latitude_deg, lon])
    c = 0.0 if abs(latitude_deg) == 90 else math.cos(lat)
    return np.array([[-math.sin(lon), math.cos(lon), 0],
                     [-math.sin(lat)*math.cos(lon), -math.sin(lat)*math.sin(lon), c],
                     [c*math.cos(lon), c*math.sin(lon), math.sin(lat)]])


@dataclass(frozen=True)
class SurfacePoint:
    latitude_deg: float
    longitude_deg_east: float
    frame: str
    reference_radius_m: float
    elevation_m: float
    antenna_height_m: float
    panel_height_m: float
    pole_reference_meridian_deg_east: float
    elevation_datum: str = "height_above_reference_sphere"

    def __post_init__(self):
        self.position_m()
        angles(0, self.pole_reference_meridian_deg_east)
        finite(self.antenna_height_m, self.panel_height_m)
        if self.frame != "MOON_ME_DE421" or self.elevation_datum != "height_above_reference_sphere":
            raise ValueError("unsupported lunar frame or elevation datum")
        if min(self.antenna_height_m, self.panel_height_m) < 0:
            raise ValueError("equipment heights must be nonnegative")

    @classmethod
    def from_lander(cls, lander):
        return cls(**{f.name: lander[f.name] for f in fields(cls)})

    @classmethod
    def from_cartesian(cls, position_m, *, reference_radius_m, frame="MOON_ME_DE421", antenna_height_m=0, panel_height_m=0, pole_reference_meridian_deg_east=0):
        p = np.asarray(position_m, dtype=float)
        if p.shape != (3,) or not np.isfinite(p).all() or np.linalg.norm(p) == 0:
            raise ValueError("Cartesian position requires three finite coordinates and positive radius")
        r = float(np.linalg.norm(p))
        lat = math.degrees(math.atan2(p[2], math.hypot(p[0], p[1])))
        lon = (math.degrees(math.atan2(p[1], p[0])) + 180) % 360 - 180
        if abs(lat) == 90:
            lon = pole_reference_meridian_deg_east
        return cls(lat, lon, frame, reference_radius_m, r-reference_radius_m, antenna_height_m, panel_height_m, pole_reference_meridian_deg_east)

    def position_m(self, height_m=0):
        finite(height_m)
        if height_m < 0:
            raise ValueError("observer height must be nonnegative")
        return surface_position(self.latitude_deg, self.longitude_deg_east, self.reference_radius_m, self.elevation_m+height_m)

    def local_basis(self):
        return local_basis(self.latitude_deg, self.longitude_deg_east, self.pole_reference_meridian_deg_east)


def vector_direction(vector_fixed_m, basis):
    p = np.asarray(vector_fixed_m, dtype=float)
    if p.shape != (3,) or not np.isfinite(p).all() or np.linalg.norm(p) <= 0:
        raise ValueError("direction requires a nonzero finite three-vector")
    e, n, u = np.asarray(basis) @ p
    distance = float(np.linalg.norm(p))
    return {"azimuth_deg": math.degrees(math.atan2(e, n)) % 360,
            "elevation_deg": math.degrees(math.atan2(u, math.hypot(e, n))),
            "range_m": distance, "unit_vector_fixed": (p/distance).tolist()}


def segment_intersects_sphere(source_m, target_m, radius_m, *, center_m=(0, 0, 0), clearance_m=0, endpoint_tolerance_m=1e-6):
    """Finite segment: interior tangency blocks, surface endpoints may leave.

    Clearance inflates the body and never extends the ray beyond its target.
    Endpoint tolerance only absorbs radial roundoff, not an interior grazing ray.
    """
    finite(radius_m, clearance_m, endpoint_tolerance_m)
    if radius_m <= 0 or clearance_m < 0 or endpoint_tolerance_m < 0:
        raise ValueError("invalid sphere radius, clearance, or tolerance")
    a, b, center = [np.asarray(x, dtype=float) for x in (source_m, target_m, center_m)]
    if any(x.shape != (3,) or not np.isfinite(x).all() for x in (a, b, center)):
        raise ValueError("sphere test requires finite three-vectors")
    a, b = a-center, b-center
    r = radius_m + clearance_m
    d = b-a
    if min(np.linalg.norm(a), np.linalg.norm(b)) < r-endpoint_tolerance_m:
        return True
    if np.linalg.norm(d) == 0:
        raise ValueError("occultation segment has zero length")
    t = float(np.clip(-np.dot(a, d)/np.dot(d, d), 0, 1))
    distance = float(np.linalg.norm(a+t*d))
    if t == 0 or t == 1:
        return bool(distance < r-endpoint_tolerance_m)
    return bool(distance <= r)
