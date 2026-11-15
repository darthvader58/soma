"""DE421 geometry in an isolated, restored SPICE kernel pool.

Frame definitions follow NAIF moon_080317.tf (frame 31007 relative to
31006); Earth ITRF93 requires a high precision binary Earth PCK. All
geometric directions use same-epoch NONE corrections, not apparent light.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import threading
import numpy as np

from soma.time import parse_utc, format_utc
from soma.time.spice import utc_to_et
from .surface import angles, finite, vector_direction

_LOCK = threading.RLock()
_ACTIVE = False


def _pool_snapshot(spice):
    kernels = [spice.kdata(i, "ALL") for i in range(spice.ktotal("ALL"))]
    variables = {}
    try:
        names = spice.gnpool("*", 0, 100000)
    except spice.utils.exceptions.NotFoundError:
        names = []
    for name in names:
        count, kind = spice.dtpool(name)
        values = spice.gcpool(name, 0, count, 10000) if kind == "C" else spice.gdpool(name, 0, count)
        variables[name] = (kind, values)
    return kernels, variables


def _restore(spice, snapshot):
    kernels, variables = snapshot
    spice.kclear()
    for filename, kind, source, handle in kernels:
        if not source:
            spice.furnsh(filename)
    for name, (kind, values) in variables.items():
        (spice.pcpool if kind == "C" else spice.pdpool)(name, values)


class SpiceGeometry:
    """Context-scoped DE421 provider; no SPICE calls outside its owning thread.

    The process lock serializes SOMA contexts. External callers must not mutate
    SPICE while a context is active. Preexisting kernels and injected pool values
    are restored, including when loading or coverage checks fail.
    """
    def __init__(self, manifest, data_root):
        self.manifest = deepcopy(manifest)
        self.data_root = Path(data_root).resolve()
        self.active = False
        if manifest.get("frame") != "MOON_ME_DE421" or manifest.get("ephemeris") != "DE421":
            raise ValueError("only the explicitly matched MOON_ME_DE421 / DE421 set is supported")
        self.coverage = self.manifest["coverage"]
        self.start = parse_utc(self.coverage["start_utc"])
        self.end = parse_utc(self.coverage["end_utc"])
        if self.start >= self.end:
            raise ValueError("kernel manifest coverage must have positive duration")
        self.paths = {}
        allowed = {"leap_seconds", "planetary_ephemeris", "lunar_frame", "lunar_orientation", "earth_orientation"}
        for item in self.manifest["kernels"]:
            role = item["role"]
            if role not in allowed or role in self.paths:
                raise ValueError("unsupported or duplicate kernel role")
            path = (self.data_root / item["path"]).resolve()
            if Path(item["path"]).is_absolute() or not path.is_relative_to(self.data_root):
                raise ValueError("kernel paths must remain beneath data_root")
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"missing kernel or SHA256 mismatch: {role}")
            self.paths[role] = str(path)
        if not {"leap_seconds", "planetary_ephemeris", "lunar_frame", "lunar_orientation"} <= self.paths.keys():
            raise ValueError("kernel manifest is missing a matched required role")

    def __enter__(self):
        global _ACTIVE
        import spiceypy as spice
        _LOCK.acquire()
        if _ACTIVE:
            _LOCK.release()
            raise RuntimeError("nested SPICE contexts are not supported")
        _ACTIVE = True
        self.owner = threading.get_ident()
        self.spice = spice
        self.snapshot = None
        try:
            self.snapshot = _pool_snapshot(spice)
            spice.kclear()
            for item in self.manifest["kernels"]:
                path = self.paths[item["role"]]
                if hashlib.sha256(Path(path).read_bytes()).hexdigest() != item["sha256"]:
                    raise ValueError("kernel SHA256 changed after manifest validation")
                spice.furnsh(path)
            self.active = True
            self._preflight()
            return self
        except BaseException:
            self.active = False
            try:
                if self.snapshot is not None:
                    _restore(spice, self.snapshot)
            finally:
                _ACTIVE = False
                _LOCK.release()
            raise

    def __exit__(self, exc_type, exc, traceback):
        global _ACTIVE
        self._check_active()
        try:
            _restore(self.spice, self.snapshot)
        finally:
            self.active = False
            _ACTIVE = False
            _LOCK.release()

    def _check_active(self):
        if not self.active or threading.get_ident() != self.owner:
            raise RuntimeError("SPICE geometry requires its active owning context")

    def _epoch(self, utc):
        self._check_active()
        value = parse_utc(utc)
        if not self.start <= value <= self.end:
            raise ValueError("epoch outside declared and verified kernel coverage")
        return utc_to_et(utc)

    def _covers(self, window, start, end):
        return any(a <= start and end <= b for a,b in
                   (self.spice.wnfetd(window, i) for i in range(self.spice.wncard(window))))

    def _preflight(self):
        spice = self.spice
        start, end = utc_to_et(self.coverage["start_utc"]), utc_to_et(self.coverage["end_utc"])
        if spice.namfrm("MOON_ME_DE421") != 31007 or spice.namfrm("MOON_PA_DE421") != 31006:
            raise ValueError("lunar FK is not the documented DE421 realization")
        if spice.gcpool("TKFRAME_31007_RELATIVE", 0, 1)[0] != "MOON_PA_DE421":
            raise ValueError("DE421 mean-Earth frame must derive from DE421 principal axes")
        if list(spice.gdpool("TKFRAME_31007_ANGLES", 0, 3)) != [67.92, 78.56, .30]:
            raise ValueError("unsupported DE421 mean-Earth registration")
        pck = self.paths["lunar_orientation"]
        frames = spice.utils.support_types.SPICEINT_CELL(100)
        spice.pckfrm(pck, frames)
        if 31006 not in frames or not self._covers(spice.pckcov(pck, 31006), start, end):
            raise ValueError("actual lunar binary PCK does not cover the interval in DE421")
        if "earth_orientation" in self.paths:
            earth_pck = self.paths["earth_orientation"]
            earth_frames = spice.utils.support_types.SPICEINT_CELL(100)
            spice.pckfrm(earth_pck, earth_frames)
            if 3000 not in earth_frames or not self._covers(spice.pckcov(earth_pck, 3000), start, end):
                raise ValueError("actual Earth binary PCK does not cover the complete ITRF93 interval")
        spk = self.paths["planetary_ephemeris"]
        objects = set(spice.spkobj(spk))
        for body in (3, 10, 301, 399):
            if body not in objects or not self._covers(spice.spkcov(spk, body), start, end):
                raise ValueError(f"actual SPK coverage missing required body {body}")
        # DE ephemerides declare their development number as a kernel-pool value
        # only in some distributions. DAF comments are checked for the selected DE.
        handle = spice.dafopr(spk)
        try:
            comments = []
            done = False
            while not done:
                count, lines, done = spice.dafec(handle, 1000, 1000)
                comments.extend(lines[:count])
            text = " ".join(comments).upper().replace("-", "").replace(" ", "")
            if "DE421" not in text:
                raise ValueError("SPK comments do not identify the selected DE421 ephemeris")
        finally:
            spice.dafcls(handle)
        for et in (start, end):
            spice.pxform("J2000", "MOON_ME_DE421", et)
            for body in ("SUN", "EARTH"):
                spice.spkezr(body, et, "MOON_ME_DE421", "NONE", "MOON")
            if "earth_orientation" in self.paths:
                spice.pxform("ITRF93", "MOON_ME_DE421", et)
        self.provenance = {"frame": "MOON_ME_DE421", "ephemeris": "DE421",
                           "aberration": "NONE", "geometry_model": "same_epoch_geometric",
                           "verified_coverage": deepcopy(self.coverage),
                           "kernels": deepcopy(self.manifest["kernels"]),
                           "spice_toolkit_version": spice.tkvrsn("TOOLKIT")}

    def state(self, target, utc, frame="MOON_ME_DE421", origin="MOON", aberration="NONE"):
        if frame not in ("MOON_ME_DE421", "J2000") or origin != "MOON" or aberration != "NONE":
            raise ValueError("baseline state requires Moon origin, explicit DE421/J2000 axes and NONE aberration")
        et = self._epoch(utc)
        state, _ = self.spice.spkezr(str(target), et, frame, aberration, origin)
        return {"target": str(target), "origin": origin, "frame": frame,
                "epoch": format_utc(parse_utc(utc)), "epoch_format": "rfc3339", "time_scale": "UTC",
                "position": (np.asarray(state[:3])*1000).tolist(), "position_unit": "m",
                "provenance_label": "published_DE421_SPICE_same_epoch_geometric_NONE"}

    def direction(self, surface, target, utc, height_m=0):
        record = self.state(target, utc, frame=surface.frame)
        result = vector_direction(np.asarray(record["position"])-surface.position_m(height_m), surface.local_basis())
        return {**result, "target": str(target), "epoch_utc": record["epoch"], "frame": surface.frame,
                "origin": "surface_observer", "observer_height_m": height_m, "aberration": "NONE",
                "geometry_model": "same_epoch_geometric"}

    def station_state(self, station, utc, frame="MOON_ME_DE421"):
        et = self._epoch(utc)
        if "earth_orientation" not in self.paths:
            raise ValueError("ITRF93 station geometry requires high precision Earth binary PCK")
        if station["frame"] != "ITRF93" or station["reference_ellipsoid"] != "WGS84" or frame not in ("MOON_ME_DE421", "J2000"):
            raise ValueError("station requires ITRF93 / WGS84 and explicit supported output frame")
        angles(station["latitude_deg"], station["longitude_deg_east"])
        finite(station["height_m"])
        lat, lon = np.radians([station["latitude_deg"], station["longitude_deg_east"]])
        p = self.spice.georec(lon, lat, station["height_m"]/1000, 6378.137, 1/298.257223563)
        offset = self.spice.pxform("ITRF93", frame, et) @ p * 1000
        earth = self.state("EARTH", utc, frame=frame)
        return {**earth, "target": station["id"], "position": (np.asarray(earth["position"])+offset).tolist(),
                "provenance_label": f"{station['input_class']}_station_WGS84_ITRF93_published_DE421_same_epoch_NONE"}

    def transform_position(self, position_m, utc, from_frame="J2000", to_frame="MOON_ME_DE421"):
        if from_frame not in ("J2000", "MOON_ME_DE421") or to_frame not in ("J2000", "MOON_ME_DE421"):
            raise ValueError("unsupported lunar frame transform")
        p = np.asarray(position_m, dtype=float)
        if p.shape != (3,) or not np.isfinite(p).all():
            raise ValueError("transform requires finite meter three-vector")
        return self.spice.pxform(from_frame, to_frame, self._epoch(utc)) @ p
