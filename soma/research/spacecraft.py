"""Pinned local reconstructed SPKs; no network access or implicit spacecraft."""
from copy import deepcopy
import hashlib
from pathlib import Path

from soma.time import parse_utc
from soma.time.spice import utc_to_et
from soma.validation import load_json, resource_directory
from .validation import StudyValidationError


def spacecraft_manifest():
    path = resource_directory("data") / "research-lro.manifest.json"
    if not path.is_file():
        return None
    return load_json(path)


def verify_spacecraft(manifest, data_root):
    """Verify the source identity and bytes before a SPK is loaded."""
    required = {"id", "name", "input_class", "naif_id", "path", "sha256", "size_bytes",
                "source_url", "coverage", "frame", "origin"}
    if not required <= manifest.keys():
        raise StudyValidationError("spacecraft source manifest is incomplete")
    if (manifest["input_class"] != "reconstructed_ephemeris" or manifest["naif_id"] != -85
            or manifest["frame"] != "J2000" or manifest["origin"] != "MOON"):
        raise StudyValidationError("unsupported spacecraft source semantics")
    root = Path(data_root).resolve()
    path = (root / manifest["path"]).resolve()
    if Path(manifest["path"]).is_absolute() or not path.is_relative_to(root):
        raise StudyValidationError("spacecraft path must remain beneath data_root")
    if not path.is_file() or path.stat().st_size != manifest["size_bytes"]:
        raise StudyValidationError("spacecraft SPK is missing or has an incorrect size")
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != manifest["sha256"]:
        raise StudyValidationError("spacecraft SPK SHA256 mismatch")
    return path


def coverage_records(spice, window):
    return [{"start_tdb_s": float(a), "end_tdb_s": float(b),
             "start_utc": spice.et2utc(a, "ISOC", 6) + "Z",
             "end_utc": spice.et2utc(b, "ISOC", 6) + "Z"}
            for a, b in (spice.wnfetd(window, i) for i in range(spice.wncard(window)))]


def load_spacecraft(geometry, manifest, data_root, start_utc, end_utc):
    """Preflight complete binary coverage inside the caller's isolated pool."""
    geometry._check_active()
    path = verify_spacecraft(manifest, data_root)
    start, end = utc_to_et(start_utc), utc_to_et(end_utc)
    declared = manifest["coverage"]
    if not (parse_utc(declared["start_utc"]) <= parse_utc(start_utc)
            and parse_utc(end_utc) <= parse_utc(declared["end_utc"])):
        raise StudyValidationError("requested interval exceeds the spacecraft source's declared coverage")
    spice = geometry.spice
    if manifest["naif_id"] not in spice.spkobj(str(path)):
        raise StudyValidationError("spacecraft NAIF ID absent from actual SPK")
    window = spice.spkcov(str(path), manifest["naif_id"])
    if not geometry._covers(window, start, end):
        raise StudyValidationError("actual spacecraft SPK coverage has a gap or does not cover the interval")
    spice.furnsh(str(path))
    for epoch in (start, end):
        spice.spkezr(str(manifest["naif_id"]), epoch, "MOON_ME_DE421", "NONE", "MOON")
    return {"manifest": deepcopy(manifest), "actual_coverage": coverage_records(spice, window)}
