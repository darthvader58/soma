"""Raster tests use synthetic pixels, not a claim of physical LOLA coverage."""

import hashlib

import numpy as np
import pytest
from pyproj import Transformer
import rasterio
from rasterio.transform import from_origin

from soma.terrain import CompositeDEM, GeographicRasterDEM, RasterDEM, SyntheticDEM, TerrainSample
from soma.terrain.dem import DATUM, FRAME, POLAR_CRS, RADIUS_M


def write_pair(tmp_path, *, counts=None, elevation=None, count_transform=None, crs=POLAR_CRS):
    elevation = np.array([[0, 10, 20], [30, 40, 50], [60, 70, 80]], dtype="float32") if elevation is None else elevation
    counts = np.full((3, 3), 1.5, dtype="float32") if counts is None else counts
    transform = from_origin(-7.5, 7.5, 5, 5)
    paths = [tmp_path / "height.tif", tmp_path / "counts.tif"]
    for index, (path, values) in enumerate(zip(paths, (elevation, counts))):
        with rasterio.open(path, "w", driver="GTiff", width=3, height=3, count=1,
                           dtype="float32", crs=crs, transform=count_transform if index and count_transform else transform,
                           nodata=-9999) as output:
            output.write(values, 1)
    metadata = {"frame": FRAME, "reference_radius_m": RADIUS_M, "elevation_datum": DATUM,
                "elevation_unit": "m", "pixel_size_m": 5,
                "interpolation_policy": "unknown_if_zero_count",
                "elevation_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
                "count_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest()}
    return paths, metadata


def latlon(x, y):
    lon, lat = Transformer.from_crs(POLAR_CRS, POLAR_CRS.geodetic_crs, always_xy=True).transform(x, y)
    return lat, (lon+180) % 360-180


def test_bilinear_is_hand_computable_and_counts_remain_fractional(tmp_path):
    paths, metadata = write_pair(tmp_path)
    with RasterDEM(*paths, metadata) as dem:
        sample = dem.sample(*latlon(-2.5, 2.5))
        assert sample.elevation_m == pytest.approx((0+10+30+40)/4, abs=0.0003)
        assert sample.count == pytest.approx(1.5)
        assert dem.sample(-90, 0).elevation_m == 40
        assert dem.sample(-90, -180).elevation_m == 40
        assert dem.sample(*latlon(20, 20)).elevation_m is None


@pytest.mark.parametrize("kind", ["zero_count", "count_nodata", "height_nodata", "nan"])
def test_any_unknown_bilinear_contributor_stays_unknown(tmp_path, kind):
    heights = np.arange(9, dtype="float32").reshape(3, 3)
    counts = np.ones((3, 3), dtype="float32")
    if kind == "zero_count":
        counts[0, 0] = 0
    elif kind == "count_nodata":
        counts[0, 0] = -9999
    elif kind == "height_nodata":
        heights[0, 0] = -9999
    else:
        heights[0, 0] = np.nan
    paths, metadata = write_pair(tmp_path, counts=counts, elevation=heights)
    with RasterDEM(*paths, metadata) as dem:
        assert dem.sample(*latlon(-2.5, 2.5)).elevation_m is None
        assert dem.sample(-90, 0).elevation_m == 4


@pytest.mark.parametrize("field,value", [("frame", "IAU_MOON"), ("reference_radius_m", 6378137),
                                        ("elevation_unit", "km"), ("count_sha256", "0"*64)])
def test_rejects_mismatched_metadata(tmp_path, field, value):
    paths, metadata = write_pair(tmp_path)
    metadata[field] = value
    with pytest.raises(ValueError):
        RasterDEM(*paths, metadata)


def test_does_not_resample_shifted_count_grid(tmp_path):
    paths, metadata = write_pair(tmp_path, count_transform=from_origin(-2.5, 7.5, 5, 5))
    with pytest.raises(ValueError, match="not aligned"):
        RasterDEM(*paths, metadata)


def test_does_not_reproject_earth_coordinates(tmp_path):
    paths, metadata = write_pair(tmp_path, crs="EPSG:3857")
    with pytest.raises(ValueError, match="Unsupported CRS"):
        RasterDEM(*paths, metadata)


def test_composite_cannot_hide_a_missing_fine_sample():
    fine = SyntheticDEM(lambda lat, lon: None, identifier="missing")
    coarse = SyntheticDEM(lambda lat, lon: 0, identifier="flat")
    assert CompositeDEM(fine, coarse).sample(-89, 0).elevation_m is None


def geographic_pair(tmp_path, *, missing_seam=False, crs=None):
    heights = np.broadcast_to(np.arange(360, dtype="float32"), (3, 360)).copy()
    counts = np.full((3, 360), 2, dtype="int32")
    if missing_seam:
        counts[1, 359] = 0
    paths = [tmp_path/"geographic-height.tif", tmp_path/"geographic-count.tif"]
    lunar_crs = "+proj=longlat +a=1737400 +b=1737400 +no_defs"
    for path, values in zip(paths, (heights, counts)):
        with rasterio.open(path, "w", driver="GTiff", width=360, height=3, count=1,
                           dtype=values.dtype, crs=crs or lunar_crs,
                           transform=from_origin(0, -87, 1, 1)) as output:
            output.write(values, 1)
    metadata = {"frame": FRAME, "reference_radius_m": RADIUS_M, "elevation_datum": DATUM,
                "elevation_unit": "m", "projection": "simple_cylindrical",
                "pixels_per_degree": 1, "bounds_lonlat_deg": [0, -90, 360, -87],
                "interpolation_policy": "unknown_if_zero_count",
                "elevation_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
                "count_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest()}
    return paths, metadata


def test_native_geographic_bilinear_wraps_meridian_and_negative_longitudes(tmp_path):
    paths, metadata = geographic_pair(tmp_path)
    with GeographicRasterDEM(*paths, metadata) as dem:
        # Zero degrees is halfway between native centers 359.5 and 0.5.
        assert dem.sample(-88.5, 0).elevation_m == 179.5
        assert dem.sample(-88.5, -0.25).elevation_m == 269.25
        assert dem.sample(-88.5, 0.25).elevation_m == 89.75
        assert dem.sample(-88.5, -180).elevation_m == 179.5
        assert dem.sample(-88.5, -179.5).elevation_m == 180
        assert dem.sample(-89.5, 10.5).elevation_m == 10


def test_geographic_pole_and_latitude_outside_center_hull_remain_unknown(tmp_path):
    paths, metadata = geographic_pair(tmp_path)
    with GeographicRasterDEM(*paths, metadata) as dem:
        for lon in (0, 90, -180):
            pole = dem.sample(-90, lon)
            assert pole.elevation_m is None
            assert "pole_extrapolation_not_supported" in pole.quality_flags
        assert dem.sample(-86, 0).elevation_m is None


def test_geographic_zero_count_across_periodic_seam_remains_unknown(tmp_path):
    paths, metadata = geographic_pair(tmp_path, missing_seam=True)
    with GeographicRasterDEM(*paths, metadata) as dem:
        assert dem.sample(-88.5, 0).elevation_m is None
        assert dem.sample(-88.5, 0.5).elevation_m == 0


@pytest.mark.parametrize("field,value", [("frame", "IAU_MOON"), ("pixels_per_degree", 2),
                                        ("bounds_lonlat_deg", [0, -90, 360, -80])])
def test_geographic_metadata_cannot_change_grid_or_frame(tmp_path, field, value):
    paths, metadata = geographic_pair(tmp_path)
    metadata[field] = value
    with pytest.raises(ValueError):
        GeographicRasterDEM(*paths, metadata)


def test_geographic_rejects_terrestrial_crs(tmp_path):
    paths, metadata = geographic_pair(tmp_path, crs="EPSG:4326")
    with pytest.raises(ValueError, match="lunar sphere"):
        GeographicRasterDEM(*paths, metadata)


def test_composite_falls_through_coverage_edge_but_preserves_a_hole():
    class Near(SyntheticDEM):
        def sample(self, lat, lon):
            return TerrainSample(None, ("outside_coverage",)) if lon > 0 else super().sample(lat, lon)
    near = Near(lambda lat, lon: None, identifier="near-gap")
    far = SyntheticDEM(lambda lat, lon: 12, identifier="far-twelve")
    composite = CompositeDEM(near, far)
    assert composite.sample(-89, 1).elevation_m == 12
    assert composite.sample(-89, -1).elevation_m is None
