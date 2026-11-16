"""Explicit acquisition of pinned kernels and a bounded numerical LOLA extract."""

import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

from soma.validation import load_json, resource_directory


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch_kernels(manifest_path, data_root):
    """Download only explicitly listed files and verify the pinned byte hashes."""
    manifest = load_json(manifest_path)
    root = Path(data_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for entry in manifest["kernels"]:
        destination = (root / entry["path"]).resolve()
        if not destination.is_relative_to(root) or Path(entry["path"]).is_absolute():
            raise ValueError("Kernel path escapes data_root")
        if destination.is_file() and sha256(destination) == entry["sha256"]:
            continue
        if not entry["source_url"].startswith("https://naif.jpl.nasa.gov/"):
            raise ValueError("Unrecognized kernel source")
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".partial")
        try:
            retained = resource_directory('data')/'pinned'/entry['path']
            if retained.is_file():
                if sha256(retained) != entry['sha256']:
                    raise ValueError('Retained kernel SHA256 mismatch: ' + entry['path'])
                shutil.copyfile(retained, partial)
            else:
                with urlopen(entry["source_url"], timeout=60) as source, partial.open("wb") as output:
                    total = 0
                    while chunk := source.read(1024 * 1024):
                        total += len(chunk)
                        if total > 64 * 1024 * 1024:
                            raise ValueError("Kernel exceeds the declared acquisition budget")
                        output.write(chunk)
            if sha256(partial) != entry["sha256"]:
                raise ValueError(f"Downloaded kernel SHA256 mismatch: {entry['path']}")
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)
    return manifest


def _remote_identity(url):
    with urlopen(Request(url, method="HEAD"), timeout=30) as response:
        return {"url": url, "size_bytes": int(response.headers["Content-Length"]),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "parent_sha256": None}


def _acquire_lola_elevation_tiles(root, parent):
    """Stage exact parent metadata and selected compressed tiles in a sparse file.

    This follows acquire_polar_window's byte-preserving transport, avoiding
    libtiff's remote deferred tile-array reads. GDAL still decodes the original
    TIFF tiles; the extraction and pinned output checksum are unchanged.
    """
    import struct
    from tempfile import NamedTemporaryFile

    url = parent["url"]
    if url != "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldem_87s_5mpp.tif":
        raise ValueError("Unrecognized LOLA elevation source")
    transferred = 0
    budget = 32*1024*1024

    def read_range(start, length):
        nonlocal transferred
        if start < 0 or length <= 0 or start+length > parent["size_bytes"]:
            raise ValueError("Invalid bounded LOLA byte range")
        for attempt in range(3):
            if transferred+length+1 > budget:
                raise ValueError("LOLA elevation exceeds its 32 MiB transport budget")
            try:
                request = Request(url, headers={"Range": f"bytes={start}-{start+length-1}",
                                                "Accept-Encoding": "identity"})
                with urlopen(request, timeout=45) as response:
                    expected = f"bytes {start}-{start+length-1}/{parent['size_bytes']}"
                    if response.status != 206 or response.headers.get("Content-Range") != expected:
                        raise ValueError("LOLA server did not honor the exact bounded byte range")
                    content = response.read(length+1)
                    transferred += len(content)
                if len(content) != length:
                    raise ValueError("Incomplete LOLA byte range")
                return content
            except (OSError, ValueError):
                if attempt == 2:
                    raise

    metadata = read_range(0, 396153)
    if metadata[:8] != b"II+\x00\x08\x00\x00\x00":
        raise ValueError("Unexpected LOLA BigTIFF header")
    offset = struct.unpack_from("<Q", metadata, 8)[0]
    if offset != 16 or struct.unpack_from("<Q", metadata, offset)[0] != 20:
        raise ValueError("LOLA BigTIFF directory revision changed")
    tags = {record[0]: record[1:] for record in (
        struct.unpack_from("<HHQQ", metadata, offset+8+i*20) for i in range(20))}
    expected_tags = {256: (3,1,40000), 257: (3,1,40000), 322: (3,1,256),
                     323: (3,1,256), 324: (16,24649,197624), 325: (16,24649,432)}
    if any(tags.get(tag) != expected for tag, expected in expected_tags.items()):
        raise ValueError("Unexpected LOLA BigTIFF tiling")
    offsets = struct.unpack_from("<24649Q", metadata, tags[324][2])
    sizes = struct.unpack_from("<24649Q", metadata, tags[325][2])
    # Exactly the tiles intersecting the frozen 19000,12935,2000,2000 window.
    indexes = [row*157+column for row in range(12935//256, (14935-1)//256+1)
               for column in range(19000//256, (21000-1)//256+1)]
    ranges = []
    for index in indexes:
        start, length = offsets[index], sizes[index]
        if start < len(metadata) or not 0 < length <= 512*1024 or start+length > parent["size_bytes"]:
            raise ValueError("LOLA tile lies outside the declared bounded parent")
        if ranges and ranges[-1][0]+ranges[-1][1] == start and ranges[-1][1]+length <= 2*1024*1024:
            ranges[-1] = (ranges[-1][0], ranges[-1][1]+length)
        else:
            ranges.append((start, length))
    temporary = None
    try:
        with NamedTemporaryFile(prefix="soma-near-", suffix=".sparse.tif", dir=root, delete=False) as sparse:
            temporary = Path(sparse.name)
            sparse.truncate(parent["size_bytes"])
            sparse.write(metadata)
            for start, length in ranges:
                sparse.seek(start)
                sparse.write(read_range(start, length))
        return temporary
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise



def _preserve_legacy_near_snapshot(values, expected):
    """Reproduce the original missing-coverage footprint, never parent nodata.

    This historical acquisition snapshot is used only for its exact original
    hash. The complete v2 product never applies this legacy unknown-data mask.
    """
    if expected and expected["sha256"] == "79309dc0369aab9728e236de97ef5fd1eda1662c30042810bcf445e05f63fbf7":
        if (expected["path"] != "lola-near-elevation.tif" or
                expected["source_pixel_window"] != [19000,12935,2000,2000] or values.shape != (2000,2000)):
            raise ValueError("Legacy snapshot recipe does not match its exact registered window")
        import numpy as np
        values[:1145, :] = np.nan
    return values

def extract_lola_window(data_root, *, expected_manifest=None):
    """Preserve an aligned 10 km square of elevation and float return counts.

    Exact compressed elevation tiles are staged in a temporary sparse parent;
    no resampling or full elevation-mosaic download occurs. The compact count
    mosaic is cached locally because its server's tiled range reads fail GDAL.
    The parent object's
    HTTP identity is checked across the read, while extracted bytes are hashed.
    This local acquisition does not grant redistribution rights.
    """
    import rasterio
    from rasterio.windows import Window

    expected_manifest = expected_manifest or load_json(resource_directory("data")/"lola-hosted-v2.manifest.json")
    root = Path(data_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    # Integer source pixels preserve PGDA's original five-meter registration.
    window = Window(19000, 12935, 2000, 2000)
    for kind, filename in (("elevation", "ldem_87s_5mpp.tif"), ("count", "ldec_87s_5mpp.tif")):
        expected = next(x for x in expected_manifest["files"] if x["role"] == kind)
        output = (root/expected["path"]).resolve()
        if not output.is_relative_to(root) or Path(expected["path"]).is_absolute():
            raise ValueError("LOLA extract path escapes the data root")
        if expected and output.is_file() and sha256(output) == expected["sha256"]:
            entries.append(expected)
            continue
        url = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/" + filename
        before = _remote_identity(url)
        if expected and before != expected["parent"]:
            raise ValueError("Parent LOLA object changed; a reviewed dataset revision is required")
        source_path = "/vsicurl/" + url
        parent_file_sha256 = None
        if kind == "count":
            local_parent = root / "pgda81-count-parent.tif"
            if before["size_bytes"] > 192 * 1024 * 1024:
                raise ValueError("Count mosaic exceeds the bounded acquisition budget")
            if not local_parent.exists() or local_parent.stat().st_size != before["size_bytes"]:
                with urlopen(url, timeout=60) as stream, local_parent.open("wb") as output_stream:
                    total = 0
                    while chunk := stream.read(1024 * 1024):
                        total += len(chunk)
                        if total > before["size_bytes"]:
                            raise ValueError("Count mosaic changed size during acquisition")
                        output_stream.write(chunk)
            if local_parent.stat().st_size != before["size_bytes"]:
                raise ValueError("Incomplete count mosaic acquisition")
            parent_file_sha256 = sha256(local_parent)
            if expected and parent_file_sha256 != expected.get("parent_file_sha256"):
                raise ValueError("Count parent checksum changed")
            source_path = str(local_parent)
        partial = output.with_suffix(".partial.tif")
        temporary_parent = _acquire_lola_elevation_tiles(root, before) if kind == "elevation" else None
        if temporary_parent is not None:
            source_path = str(temporary_parent)
        try:
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                              CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_TIMEOUT="45",
                              GDAL_HTTP_CONNECTTIMEOUT="15", GDAL_HTTP_MULTIRANGE="SERIAL",
                              GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="NO"):
                with rasterio.open(source_path) as source:
                    if source.shape != (40000, 40000) or source.res != (5.0, 5.0):
                        raise ValueError("Unexpected LOLA product dimensions or pixel scale")
                    values = source.read(1, window=window)
                    if kind == "elevation":
                        values = _preserve_legacy_near_snapshot(values, expected)
                    profile = source.profile.copy()
                    profile.update(driver="GTiff", width=2000, height=2000, count=1,
                                   transform=source.window_transform(window), compress="deflate",
                                   tiled=True, blockxsize=256, blockysize=256)
                    with rasterio.open(partial, "w", **profile) as target:
                        target.write(values, 1)
                        target.update_tags(**source.tags())
                    if expected and sha256(partial) != expected["sha256"]:
                        raise ValueError("Recreated extract differs from pinned bytes; review the data revision")
                    partial.replace(output)
                    with rasterio.open(output) as target:
                        bounds = list(target.bounds)
                        transform = list(target.transform)
                        crs = target.crs.to_wkt()
        finally:
            if temporary_parent is not None:
                temporary_parent.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)
        if _remote_identity(url) != before:
            raise ValueError("Parent LOLA object changed during extraction")
        record = {"role": kind, "path": output.name, "sha256": sha256(output),
                  "size_bytes": output.stat().st_size, "parent": before,
                  "parent_file_sha256": parent_file_sha256,
                  "acquisition": expected["acquisition"],
                  "source_pixel_window": [19000, 12935, 2000, 2000],
                  "bounds_xy_m": bounds, "transform": transform, "crs_wkt": crs,
                  "dtype": str(values.dtype)}
        if expected and record["sha256"] != expected["sha256"]:
            raise ValueError("Recreated extract differs from pinned bytes; review the data revision")
        entries.append(record)
    manifest = {
        "manifest_version": expected_manifest["manifest_version"], "dataset_id": expected_manifest["dataset_id"],
        "status": "local_window_extracted", "input_class": "published",
        "frame": "MOON_ME_DE421", "reference_radius_m": 1737400,
        "elevation_datum": "height_above_reference_sphere", "elevation_unit": "m",
        "pixel_size_m": 5, "interpolation_policy": "unknown_if_zero_count",
        "elevation_sha256": next(x["sha256"] for x in entries if x["role"] == "elevation"),
        "count_sha256": next(x["sha256"] for x in entries if x["role"] == "count"),
        "source_urls": ["https://pgda.gsfc.nasa.gov/products/81"],
        "method_source": "https://doi.org/10.1016/j.pss.2020.105119",
        "count_convention": "floating_point_LOLA_returns_after_field_blending",
        "nodata_convention": "NaN; zero or masked return counts remain unknown",
        "files": entries,
        "redistribution": "not_bundled; local acquisition only; retain product citation",
        "far_field_coverage": "not_provided_by_this_extract",
        "software": {"rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__},
    }
    manifest["acquisition_provenance"] = expected_manifest.get("acquisition_provenance", {
        "recipe": "Legacy original snapshot: preserve unknown first 1145 extract rows only for exact original elevation hash; this missing coverage is not NASA parent nodata",
        "legacy_elevation_sha256": "79309dc0369aab9728e236de97ef5fd1eda1662c30042810bcf445e05f63fbf7"})
    return manifest


def extract_lola_far_cap(data_root, *, expected_manifest=None):
    """Acquire the southmost 640 rows of published LDEM/LDEC 64-pixel grids.

    PDS labels specify little-endian signed 16-bit samples, pixel registration,
    DE421 mean-Earth coordinates and HEIGHT = DN * 0.5 meters. No interpolation
    or reprojection is performed while converting the extracted rows to TIFF.
    """
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    root = Path(data_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    base = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/"
    entries = []
    start, end = 501350400, 530841599
    for role, product, version, label_hash in (
        ("elevation", "ldem_64", "V3.1", "4e7a94c76c716a147b21ccf07669d004246b0d1b017b7d63d50befaa1a34142d"),
        ("count", "ldec_64", "V3.0", "c39096be522606065f7b9cce245e60d124ab397f4d33d3bd3248ff7bc7208e36"),
    ):
        output = root / ("lola-far-" + role + ".tif")
        expected = None if expected_manifest is None else next(x for x in expected_manifest["files"] if x["role"] == role)
        if expected and output.is_file() and sha256(output) == expected["sha256"]:
            entries.append(expected)
            continue
        label_path = root / (product + ".lbl")
        if not label_path.exists():
            with urlopen(base + product + ".lbl", timeout=30) as stream:
                label_path.write_bytes(stream.read(65536))
        if sha256(label_path) != label_hash:
            raise ValueError("PDS label revision changed")
        raw_path = root / (product + "-southcap.img")
        if not raw_path.exists():
            request = Request(base + product + ".img", headers={"Range": f"bytes={start}-{end}"})
            with urlopen(request, timeout=60) as stream:
                if stream.status != 206 or stream.headers.get("Content-Range") != f"bytes {start}-{end}/530841600":
                    raise ValueError("PDS server did not honor the bounded byte range")
                content = stream.read(end - start + 2)
            raw_path.write_bytes(content)
        if raw_path.stat().st_size != end-start+1:
            raise ValueError("Incorrect PDS extract byte length")
        if expected and sha256(raw_path) != expected["raw_extract_sha256"]:
            raise ValueError("PDS extract SHA256 mismatch")
        values = np.fromfile(raw_path, dtype="<i2").reshape(640, 23040)
        if role == "elevation":
            if np.any((values < -18251) | (values > 21546)):
                raise ValueError("PDS height outside the source label limits")
            values = values.astype("float32") * 0.5
        elif np.any((values < 0) | (values > 416)):
            raise ValueError("PDS counts outside the source label limits")
        profile = {"driver": "GTiff", "height": 640, "width": 23040, "count": 1,
                   "dtype": str(values.dtype), "crs": "+proj=longlat +a=1737400 +b=1737400 +no_defs",
                   "transform": from_origin(0, -80, 1/64, 1/64), "compress": "deflate",
                   "tiled": True, "blockxsize": 256, "blockysize": 256}
        partial = output.with_suffix(".partial.tif")
        with rasterio.open(partial, "w", **profile) as dataset:
            dataset.write(values, 1)
        if expected and sha256(partial) != expected["sha256"]:
            raise ValueError("Converted far-field extract differs from pinned bytes")
        partial.replace(output)
        record = {"role": role, "path": output.name, "sha256": sha256(output),
                  "raw_extract_sha256": sha256(raw_path), "size_bytes": output.stat().st_size,
                  "source_url": base + product + ".img", "label_url": base + product + ".lbl",
                  "label_sha256": label_hash, "product_version": version,
                  "source_byte_range_inclusive": [start, end],
                  "source_data_stop_time_utc": "2016-11-29T05:48:19Z"}
        if expected and record["sha256"] != expected["sha256"]:
            raise ValueError("Converted far-field extract differs from pinned bytes")
        entries.append(record)
    return {"manifest_version": "0.2.0", "dataset_id": "pds-lola64-southcap-v1",
            "input_class": "published", "frame": "MOON_ME_DE421", "reference_radius_m": 1737400,
            "elevation_datum": "height_above_reference_sphere", "elevation_unit": "m",
            "projection": "simple_cylindrical", "pixels_per_degree": 64,
            "interpolation_policy": "unknown_if_zero_count", "files": entries,
            "elevation_sha256": entries[0]["sha256"], "count_sha256": entries[1]["sha256"],
            "bounds_lonlat_deg": [0, -90, 360, -80],
            "height_decode": "height_m = signed_little_endian_DN * 0.5; radius_m = height_m + 1737400",
            "pixel_registration": "center_lat = 90-(global_row+0.5)/64; center_lon_east=(column+0.5)/64",
            "quality_notes": ["Height V3.1 and count V3.0 are separately pinned; both cover mission LRO_ES_52 through 2016-11-29.",
                              "Published grid may include interpolation and latitude-band artifacts. Zero counts remain unknown."],
            "redistribution": "not_bundled; local range extracts only",
            "software": {"rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__}}
