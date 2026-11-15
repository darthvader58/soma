"""Synthetic surfaces and CPU intersections for renderer instrument checks."""

import math


def _vector(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or not all(type(x) in (int, float) and math.isfinite(x) for x in value)):
        raise ValueError("Require a finite Cartesian meter vector")
    return tuple(value)


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(value):
    vector = _vector(value)
    length = math.hypot(*vector)
    if length == 0:
        raise ValueError("A ray direction cannot be zero")
    return tuple(x/length for x in vector)


def planar_surfaces(request, *, reference_radius_m=1737400, height_m=-1000, half_width_m=1000):
    """Generate explicitly synthetic planes normal to the requested radial rays.

    The center intersection has radius R + height exactly. Corner heights differ
    because the surface is planar. No real terrain or registration is inferred.
    """
    if (request.get("source_frame") != "MOON_ME_DE421"
            or request.get("candidate_bridge") != "identity_for_measurement_only"
            or request.get("format_version") != "0.1.0"):
        raise ValueError("Require an explicit unregistered diagnostic request")
    for value in (reference_radius_m, height_m, half_width_m):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Calibration dimensions require finite meters")
    if reference_radius_m <= 0 or reference_radius_m+height_m <= 0 or not 0 < half_width_m <= 10000:
        raise ValueError("Invalid calibration surface dimensions")
    probes = request.get("probes")
    if not isinstance(probes, list) or not 1 <= len(probes) <= 32:
        raise ValueError("Calibration requires 1 to 32 probes")
    identifiers, positions, indices, centers = set(), [], [], []
    for probe in probes:
        identifier = probe.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError("Calibration probes require distinct identifiers")
        identifiers.add(identifier)
        radial = _unit(probe.get("position_m"))
        axis = min(((1, 0, 0), (0, 1, 0), (0, 0, 1)), key=lambda a: abs(_dot(a, radial)))
        east = _unit(_cross(axis, radial))
        north = _cross(radial, east)
        center = [(reference_radius_m+height_m)*v for v in radial]
        start = len(positions)//3
        for e, n in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            positions.extend(center[i]+half_width_m*(e*east[i]+n*north[i]) for i in range(3))
        indices.extend(start+i for i in (0, 1, 2, 0, 2, 3))
        centers.append({"id": identifier, "expected_position_m": center})
    return {"artifact_type": "synthetic_calibration_planes", "format_version": "0.1.0",
            "origin": "MOON", "source_frame": "MOON_ME_DE421", "position_unit": "m",
            "reference_radius_m": reference_radius_m, "expected_height_m": height_m,
            "half_width_m": half_width_m, "positions": positions, "indices": indices,
            "centers": centers, "input_class": "synthetic", "registration_passed": False}


def radial_triangle_hit(direction, vertices):
    """Intersect a Moon-center radial ray with one observed world-space triangle.

    This CPU calculation diagnoses mesh sampling. Its output is not an
    independent terrain landmark or a coordinate-frame registration verdict.
    """
    ray = _unit(direction)
    if not isinstance(vertices, (list, tuple)) or len(vertices) != 3:
        raise ValueError("Require exactly three triangle vertices")
    a, b, c = map(_vector, vertices)
    e1 = tuple(b[i]-a[i] for i in range(3))
    e2 = tuple(c[i]-a[i] for i in range(3))
    h = _cross(ray, e2)
    determinant = _dot(e1, h)
    if abs(determinant) <= 1e-12*math.hypot(*e1)*math.hypot(*e2):
        return None
    inv = 1/determinant
    offset = tuple(-x for x in a)
    u = inv*_dot(offset, h)
    q = _cross(offset, e1)
    v = inv*_dot(ray, q)
    distance = inv*_dot(e2, q)
    if min(u, v) < -1e-9 or u+v > 1+1e-9 or distance <= 0:
        return None
    return [distance*x for x in ray]
