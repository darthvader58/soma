"""Analytic spherical geometry checks independent of SPICE."""
import math
import numpy as np
import pytest
from soma.geometry import SurfacePoint, local_basis, surface_position, vector_direction, segment_intersects_sphere


def test_lunar_axes_heights_and_cartesian_roundtrip():
    np.testing.assert_allclose(surface_position(0, 0, 1737400, 25), [1737425, 0, 0])
    np.testing.assert_allclose(surface_position(0, 90, 1737400), [0, 1737400, 0], atol=1e-8)
    np.testing.assert_allclose(surface_position(-90, 119, 1737400), [0, 0, -1737400], atol=0)
    point = SurfacePoint(-83, 154, 'MOON_ME_DE421', 1737400, -100, 4, 1, 0)
    recovered = SurfacePoint.from_cartesian(point.position_m(), reference_radius_m=1737400)
    assert recovered.latitude_deg == pytest.approx(-83)
    assert recovered.longitude_deg_east == pytest.approx(154)
    assert recovered.elevation_m == pytest.approx(-100)
    assert np.linalg.norm(point.position_m(4)-point.position_m(1)) == pytest.approx(3)


@pytest.mark.parametrize('lat', [-90, 90])
def test_exact_pole_basis_uses_declared_meridian(lat):
    basis = local_basis(lat, 120, 0)
    np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=1e-15)
    np.testing.assert_allclose(basis[0], [0, 1, 0])
    np.testing.assert_allclose(basis[2], [0, 0, math.copysign(1, lat)])
    np.testing.assert_allclose(np.cross(basis[0], basis[1]), basis[2])
    np.testing.assert_allclose(local_basis(lat, -10, 0), basis)


def test_enu_azimuth_elevation_and_range_are_not_earth_defaults():
    basis = local_basis(0, 0)
    assert vector_direction([0, 1000, 0], basis)['azimuth_deg'] == pytest.approx(90)
    assert vector_direction([1000, 0, 1000], basis)['elevation_deg'] == pytest.approx(45)
    assert vector_direction([1000, 0, 1000], basis)['range_m'] == pytest.approx(math.sqrt(2)*1000)


@pytest.mark.parametrize('args', [(91, 0, 1737400), (0, 180, 1737400), (0, 0, -1), (0, float('nan'), 1737400)])
def test_unsupported_coordinates_fail(args):
    with pytest.raises(ValueError):
        surface_position(*args)


def test_finite_segment_body_occultation_and_tangency():
    assert not segment_intersects_sphere([2, 0, 0], [3, 0, 0], 1)
    assert not segment_intersects_sphere([2, 0, 0], [1.5, 0, 0], 1)
    assert segment_intersects_sphere([2, 0, 0], [-2, 0, 0], 1)
    assert segment_intersects_sphere([-2, 1, 0], [2, 1, 0], 1)
    assert not segment_intersects_sphere([1, 0, 0], [2, 0, 0], 1)
    assert segment_intersects_sphere([1, 0, 0], [-2, 0, 0], 1)
    assert segment_intersects_sphere([1, 0, 0], [2, 0, 0], 1, clearance_m=.01)
