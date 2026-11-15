"""Numerical, count-aware LOLA access; no renderer-derived elevations."""

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Protocol

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.windows import Window

FRAME = "MOON_ME_DE421"
RADIUS_M = 1737400.0
DATUM = "height_above_reference_sphere"
POLAR_CRS = CRS.from_proj4(
    "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 "
    "+a=1737400 +b=1737400 +units=m +no_defs"
)


@dataclass(frozen=True)
class TerrainSample:
    elevation_m: float | None
    quality_flags: tuple[str, ...]
    count: float | None = None
    source_id: str = ""


class DEM(Protocol):
    frame: str
    reference_radius_m: float
    elevation_datum: str
    source_hashes: tuple[str, ...]

    def sample(self, latitude_deg: float, longitude_deg_east: float) -> TerrainSample: ...


def _coordinates(latitude_deg, longitude_deg_east):
    if not (math.isfinite(latitude_deg) and math.isfinite(longitude_deg_east)):
        raise ValueError("Terrain coordinates must be finite")
    if not -90 <= latitude_deg <= 90 or not -180 <= longitude_deg_east < 180:
        raise ValueError("Expected planetocentric latitude [-90,90], east longitude [-180,180)")


def _sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _supported_polar_crs(crs):
    if not crs.is_projected or crs.coordinate_operation is None:
        return False
    if not (crs.ellipsoid.semi_major_metre == RADIUS_M == crs.ellipsoid.semi_minor_metre):
        return False
    if crs.prime_meridian.longitude != 0 or any(a.unit_conversion_factor != 1 for a in crs.axis_info):
        return False
    operation = crs.coordinate_operation
    parameters = {p.name: p.value for p in operation.params}
    # GeoTIFF round trips normalize k=1 at the pole to variant B, lat_ts=-90.
    supported = {
        "Polar Stereographic (variant A)": {
            "Latitude of natural origin": -90, "Longitude of natural origin": 0,
            "Scale factor at natural origin": 1, "False easting": 0, "False northing": 0},
        "Polar Stereographic (variant B)": {
            "Latitude of standard parallel": -90, "Longitude of origin": 0,
            "False easting": 0, "False northing": 0},
    }
    return parameters == supported.get(operation.method_name)


class RasterDEM:
    """Aligned south-pole elevation/count files in the DE421 ME realization.

    Metadata carries frame information absent from a generic spherical TIFF CRS.
    Zero-count interpolated product pixels stay unknown, even if elevation is finite.
    Every contributing bilinear pixel must have a positive measured return count.
    """

    frame = FRAME
    reference_radius_m = RADIUS_M
    elevation_datum = DATUM

    def __init__(self, elevation_path, count_path, metadata: dict):
        required = {
            "frame": FRAME, "reference_radius_m": RADIUS_M,
            "elevation_datum": DATUM, "elevation_unit": "m",
            "interpolation_policy": "unknown_if_zero_count",
        }
        for name, value in required.items():
            if metadata.get(name) != value:
                raise ValueError(f"Unsupported or missing DEM metadata: {name}; expected {value!r}")
        pixel_size = metadata.get("pixel_size_m")
        if isinstance(pixel_size, bool) or not isinstance(pixel_size, (int, float)) or not math.isfinite(pixel_size) or pixel_size <= 0:
            raise ValueError("Declare a positive finite pixel_size_m; no resampling is implicit")
        hashes = (_sha256(elevation_path), _sha256(count_path))
        if hashes != (metadata.get("elevation_sha256"), metadata.get("count_sha256")):
            raise ValueError("DEM checksum mismatch")
        self.source_hashes = hashes
        self.source_id = str(metadata.get("dataset_id", hashes[0]))
        self._elevation = rasterio.open(elevation_path)
        try:
            self._counts = rasterio.open(count_path)
            for ds in (self._elevation, self._counts):
                if ds.count != 1 or ds.crs is None:
                    raise ValueError("DEM must have one band and an explicit lunar CRS")
                crs = CRS.from_user_input(ds.crs)
                if not _supported_polar_crs(crs):
                    raise ValueError("Unsupported CRS: require 1737400 m spherical south-polar stereographic")
                if ds.transform.b != 0 or ds.transform.d != 0 or ds.res != (pixel_size, pixel_size):
                    raise ValueError("Require declared unrotated grid resolution; reprojection is not implicit")
                if ds.scales != (1.0,) or ds.offsets != (0.0,):
                    raise ValueError("Scaled raster values require explicit preprocessing")
            a, b = self._elevation, self._counts
            if (a.width, a.height, a.transform, a.crs) != (b.width, b.height, b.transform, b.crs):
                raise ValueError("Elevation and count grids are not aligned")
            self._project = Transformer.from_crs(POLAR_CRS.geodetic_crs, POLAR_CRS, always_xy=True)
        except Exception:
            self.close()
            raise

    def close(self):
        self._elevation.close()
        if hasattr(self, "_counts"):
            self._counts.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def sample(self, latitude_deg, longitude_deg_east):
        _coordinates(latitude_deg, longitude_deg_east)
        x, y = self._project.transform(longitude_deg_east, latitude_deg)
        col, row = ~self._elevation.transform @ (x, y)
        col, row = col - 0.5, row - 0.5
        # Remove numerical noise when querying a pixel center, notably the pole.
        if abs(col - round(col)) < 1e-8:
            col = float(round(col))
        if abs(row - round(row)) < 1e-8:
            row = float(round(row))
        c0, r0 = math.floor(col), math.floor(row)
        contributors = [(r0+dr, c0+dc, (1-abs(row-(r0+dr)))*(1-abs(col-(c0+dc))))
                        for dr in (0, 1) for dc in (0, 1)]
        contributors = [(r, c, w) for r, c, w in contributors if w > 0]
        if any(r < 0 or c < 0 or r >= self._elevation.height or c >= self._elevation.width
               for r, c, _ in contributors):
            return TerrainSample(None, ("outside_coverage",), source_id=self.source_id)
        window = Window(c0, r0, min(2, self._elevation.width-c0), min(2, self._elevation.height-r0))
        heights = self._elevation.read(1, window=window, masked=True)
        counts = self._counts.read(1, window=window, masked=True)
        height, count = 0.0, 0.0
        for r, c, weight in contributors:
            h, n = heights[r-r0, c-c0], counts[r-r0, c-c0]
            if np.ma.is_masked(h) or np.ma.is_masked(n) or not np.isfinite(h) or not np.isfinite(n):
                return TerrainSample(None, ("nodata",), source_id=self.source_id)
            if n <= 0:
                return TerrainSample(None, ("zero_count_interpolated_fill_unknown",), float(n), self.source_id)
            height += weight * float(h)
            count += weight * float(n)
        flag = "bilinear_from_positive_count_pixels" if len(contributors) > 1 else "positive_count_pixel"
        return TerrainSample(height, (flag,), count, self.source_id)


class SyntheticDEM:
    """Analytic test surface. Its supplied identifier must describe all function inputs."""

    frame = FRAME
    reference_radius_m = RADIUS_M
    elevation_datum = DATUM

    def __init__(self, elevation_function, *, identifier: str):
        if not identifier:
            raise ValueError("Synthetic terrain requires an explicit identity")
        self._function = elevation_function
        self.source_hashes = (hashlib.sha256(("synthetic:" + identifier).encode()).hexdigest(),)
        self.source_id = "synthetic:" + identifier

    def sample(self, latitude_deg, longitude_deg_east):
        _coordinates(latitude_deg, longitude_deg_east)
        value = self._function(latitude_deg, longitude_deg_east)
        if value is None or not math.isfinite(value):
            return TerrainSample(None, ("synthetic", "missing_terrain"), source_id=self.source_id)
        return TerrainSample(float(value), ("synthetic",), source_id=self.source_id)


class GeographicRasterDEM:
    """Native PDS cylindrical grid, decoded to meters without reprojection.

    A full 360-degree grid wraps longitude during interpolation. The polar
    half-pixel outside the center-coordinate hull remains unknown; there is no
    measured pole row to extrapolate. Frame realization comes from the pinned
    PDS label in the manifest, not the generic spherical GeoTIFF CRS name.
    """

    frame = FRAME
    reference_radius_m = RADIUS_M
    elevation_datum = DATUM

    def __init__(self, elevation_path, count_path, metadata: dict):
        required = {
            "frame": FRAME, "reference_radius_m": RADIUS_M,
            "elevation_datum": DATUM, "elevation_unit": "m",
            "projection": "simple_cylindrical",
            "interpolation_policy": "unknown_if_zero_count",
        }
        for field, expected in required.items():
            if metadata.get(field) != expected:
                raise ValueError(f"Unsupported or missing geographic DEM metadata: {field}")
        ppd = metadata.get("pixels_per_degree")
        if isinstance(ppd, bool) or not isinstance(ppd, (int, float)) or not math.isfinite(ppd) or ppd <= 0:
            raise ValueError("Require explicit positive pixels_per_degree")
        hashes = (_sha256(elevation_path), _sha256(count_path))
        if hashes != (metadata.get("elevation_sha256"), metadata.get("count_sha256")):
            raise ValueError("DEM checksum mismatch")
        self.source_hashes = hashes
        self.source_id = str(metadata.get("dataset_id", hashes[0]))
        self._elevation = rasterio.open(elevation_path)
        try:
            self._counts = rasterio.open(count_path)
            for ds in (self._elevation, self._counts):
                if ds.count != 1 or ds.crs is None:
                    raise ValueError("Geographic DEM requires one band and an explicit lunar CRS")
                crs = CRS.from_user_input(ds.crs)
                if (not crs.is_geographic or crs.ellipsoid.semi_major_metre != RADIUS_M
                        or crs.ellipsoid.semi_minor_metre != RADIUS_M
                        or crs.prime_meridian.longitude != 0
                        or any(not math.isclose(a.unit_conversion_factor, math.pi/180) for a in crs.axis_info)):
                    raise ValueError("Geographic DEM requires 1737400 m lunar sphere and degree coordinates")
                if ds.scales != (1.0,) or ds.offsets != (0.0,):
                    raise ValueError("Decode height scale explicitly before opening geographic DEM")
                t = ds.transform
                if (t.b != 0 or t.d != 0 or not math.isclose(t.a, 1/ppd)
                        or not math.isclose(t.e, -1/ppd) or t.c != 0
                        or not math.isclose(ds.width/ppd, 360)):
                    raise ValueError("Require north-up full 0..360 longitude grid at declared pixels_per_degree")
                bounds = metadata.get("bounds_lonlat_deg")
                if (not isinstance(bounds, (list, tuple)) or len(bounds) != 4
                        or not np.allclose(ds.bounds, bounds, rtol=0, atol=1e-9)
                        or ds.bounds.bottom < -90 or ds.bounds.top > 90):
                    raise ValueError("Geographic bounds must match the declared native grid")
            a, b = self._elevation, self._counts
            if (a.width, a.height, a.transform, a.crs) != (b.width, b.height, b.transform, b.crs):
                raise ValueError("Elevation and count grids are not aligned")
        except Exception:
            self.close()
            raise

    def close(self):
        self._elevation.close()
        if hasattr(self, "_counts"):
            self._counts.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def sample(self, latitude_deg, longitude_deg_east):
        _coordinates(latitude_deg, longitude_deg_east)
        col, row = ~self._elevation.transform @ (longitude_deg_east % 360, latitude_deg)
        col, row = col - 0.5, row - 0.5
        if abs(row-round(row)) < 1e-8:
            row = float(round(row))
        if abs(col-round(col)) < 1e-8:
            col = float(round(col))
        r0, c0 = math.floor(row), math.floor(col)
        contributors = [(r0+dr, (c0+dc) % self._elevation.width,
                         (1-abs(row-(r0+dr)))*(1-abs(col-(c0+dc))))
                        for dr in (0, 1) for dc in (0, 1)]
        contributors = [(r, c, w) for r, c, w in contributors if w > 0]
        if any(r < 0 or r >= self._elevation.height for r, _, _ in contributors):
            flag = "pole_extrapolation_not_supported" if abs(latitude_deg) == 90 else "outside_coverage"
            return TerrainSample(None, (flag,), source_id=self.source_id)
        height, count = 0.0, 0.0
        for r, c, weight in contributors:
            window = Window(c, r, 1, 1)
            h = self._elevation.read(1, window=window, masked=True)[0, 0]
            n = self._counts.read(1, window=window, masked=True)[0, 0]
            if np.ma.is_masked(h) or np.ma.is_masked(n) or not np.isfinite(h) or not np.isfinite(n):
                return TerrainSample(None, ("nodata",), source_id=self.source_id)
            if n <= 0:
                return TerrainSample(None, ("zero_count_interpolated_fill_unknown",), float(n), self.source_id)
            height += weight*float(h)
            count += weight*float(n)
        flags = ("bilinear_from_positive_count_pixels", "periodic_longitude") if len(contributors) > 1 else ("positive_count_pixel",)
        return TerrainSample(height, flags, count, self.source_id)


class CompositeDEM:
    """Use detailed near coverage and an explicitly supplied coarse far source.

    Only outside-coverage samples may fall through. A hole or zero count in the
    detailed source cannot silently become a clear sample from a coarse source.
    """

    def __init__(self, *sources: DEM):
        if not sources:
            raise ValueError("At least one terrain source is required")
        self._sources = sources
        first = sources[0]
        self.frame, self.reference_radius_m, self.elevation_datum = (
            first.frame, first.reference_radius_m, first.elevation_datum)
        for source in sources:
            if (source.frame, source.reference_radius_m, source.elevation_datum) != (
                    self.frame, self.reference_radius_m, self.elevation_datum):
                raise ValueError("Composite DEM frame, radius and datum must match")
        self.source_hashes = tuple(h for source in sources for h in source.source_hashes)

    def sample(self, latitude_deg, longitude_deg_east):
        for source in self._sources:
            sample = source.sample(latitude_deg, longitude_deg_east)
            if "outside_coverage" not in sample.quality_flags:
                return sample
        return TerrainSample(None, ("outside_coverage",))
