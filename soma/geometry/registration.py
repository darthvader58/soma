"""Versioned, fail-closed handoff for Moon-centered renderer registration.

This version records an unresolved asset frame. It deliberately cannot authorize
an affine transform or turn a reference-sphere coordinate into a terrain control.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sysconfig


MANIFEST_NAME = "renderer-registration.manifest.json"


def _data_directory():
    local = Path(__file__).resolve().parents[2] / "data"
    if (local / MANIFEST_NAME).is_file():
        return local
    return Path(sysconfig.get_path("data")) / "share" / "soma" / "data"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def catalog_reference_position_m(latitude_deg, longitude_deg_east, reference_radius_m):
    """Algebraic sphere candidate, not a DE421 or Cesium landmark position.

    Input catalog angles are evaluated on a declared sphere (where graphic and
    centric latitude coincide). Origin is MOON, units m, epoch/time scale are
    not applicable to this static catalog construction. No terrain height or
    control-network transformation is inferred.
    """
    if not all(_number(v) for v in (latitude_deg, longitude_deg_east, reference_radius_m)):
        raise ValueError("catalog sphere requires finite numeric values")
    if not -90 <= latitude_deg <= 90 or not -180 <= longitude_deg_east < 180 or reference_radius_m <= 0:
        raise ValueError("invalid catalog sphere coordinates")
    lat, lon = math.radians(latitude_deg), math.radians(longitude_deg_east)
    c = 0.0 if abs(latitude_deg) == 90 else math.cos(lat)
    return [reference_radius_m*c*math.cos(lon), reference_radius_m*c*math.sin(lon), reference_radius_m*math.sin(lat)]


def validate_renderer_registration(manifest):
    """Validate the unresolved v0.1.0 artifact; never grant overlay release.

    Asset registration approval needs a separately reviewed artifact version.
    Rejecting an invented identity here avoids treating structural validity as
    scientific evidence. No dynamic state transformation is implemented.
    """
    required = {"version", "authority", "status", "source_frame", "renderer_frame", "asset_id",
                "origin", "position_unit", "epoch", "time_scale", "transform_column_major",
                "transform_meaning", "source_manifest_ref", "source_manifest_sha256", "source_bindings",
                "tolerance_m", "tolerance_justification", "landmarks", "distribution_review", "release_gate"}
    if not isinstance(manifest, dict) or not required <= manifest.keys():
        raise ValueError("registration artifact is missing required metadata")
    expected = {"version": "0.1.0", "authority": "soma_engine", "status": "blocked_pending_asset_registration",
                "source_frame": "MOON_ME_DE421", "asset_id": 2684829, "origin": "MOON", "position_unit": "m",
                "renderer_frame": None, "epoch": None, "time_scale": "not_applicable_static_catalog",
                "transform_column_major": None, "tolerance_m": None}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("unresolved registration cannot assert a frame, transform, tolerance or release")
    digest = manifest["source_manifest_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("source manifest requires a SHA-256 digest")
    landmarks = manifest["landmarks"]
    if not isinstance(landmarks, list) or len(landmarks) < 4:
        raise ValueError("at least four candidate landmarks are required")
    ids = set()
    for point in landmarks:
        if not isinstance(point, dict) or not {"id", "source_ref", "catalog_coordinates", "catalog_reference_position_m", "analysis_position_m", "renderer_position_m", "residual_m"} <= point.keys():
            raise ValueError("landmark metadata is incomplete")
        if not isinstance(point["id"], str) or not point["id"] or point["id"] in ids:
            raise ValueError("landmarks require distinct IDs")
        ids.add(point["id"])
        if any(point[key] is not None for key in ("analysis_position_m", "renderer_position_m", "residual_m")):
            raise ValueError("unmeasured landmark positions and asset residuals must remain null")
        catalog = point["catalog_coordinates"]
        candidate = catalog_reference_position_m(catalog["latitude_deg"], catalog["longitude_deg_east"], catalog["reference_radius_m"])
        actual = point["catalog_reference_position_m"]
        if not isinstance(actual, list) or len(actual) != 3 or not all(_number(v) for v in actual) or math.dist(candidate, actual) > 1e-6:
            raise ValueError("catalog sphere Cartesian construction is inconsistent")
    review = manifest["distribution_review"]
    gate = manifest["release_gate"]
    if review.get("accepted") is not False or gate.get("overlays_allowed") is not False or not gate.get("blockers"):
        raise ValueError("unresolved registration must block overlays and retain blockers")
    return deepcopy(manifest)


def load_renderer_registration(path=None):
    """Load immutable-by-copy evidence and verify pinned local source bindings."""
    path = Path(path) if path is not None else _data_directory() / MANIFEST_NAME
    manifest = validate_renderer_registration(json.loads(path.read_text()))
    references = [{"path": manifest["source_manifest_ref"], "sha256": manifest["source_manifest_sha256"]}, *manifest["source_bindings"]]
    for ref in references:
        name = ref["path"]
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("registration source bindings must be sibling manifest names")
        if hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError(f"registration source checksum mismatch: {name}")
    return manifest


def registration_release_gate(manifest=None):
    """Return the explicit blocked gate without changing the scientific result."""
    checked = load_renderer_registration() if manifest is None else validate_renderer_registration(manifest)
    return deepcopy(checked["release_gate"])
