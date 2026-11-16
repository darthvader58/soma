"""Native DE421 geometry studies with source preflight and isolated kernels."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path

import numpy as np

from soma import __version__
from soma.geometry import SpiceGeometry, SurfacePoint
from soma.geometry.surface import vector_direction
from soma.time.spice import utc_to_et
from soma.validation import load_json, resource_directory, scenario_sha256, validate_document
from .spacecraft import coverage_records, load_spacecraft, spacecraft_manifest, verify_spacecraft
from .validation import (REQUEST_BUDGETS, StudyValidationError, study_epochs,
                         study_sha256, validate_study)


class StudyCancelled(RuntimeError):
    """Cancellation interrupted a study before a completed result existed."""


LIMITATIONS = [
    "Reference-sphere geometry uses declared site elevation; no numerical terrain was sampled.",
    "Terrain visibility, solar disk fraction, eclipses, power and usable contacts were not evaluated.",
    "Above the spherical horizontal does not establish terrain-clear access or station service.",
    "Same-epoch geometric NONE states are not apparent light-time-corrected directions.",
    "Before 1972, dates use SPICE's extended UTC convention; historical civil UTC is not reconstructed.",
    "Discrete sampled extrema are not continuous-time extrema; no event search or convergence study was performed.",
    "Moon-fixed velocity is the derivative in rotating MOON_ME_DE421 axes, not inertial velocity.",
    "Source frame consistency does not establish global registration to a rendered terrain mesh.",
    "Archived spacecraft geometry grants no communications relay service, pointing or instrument footprint.",
]


def _data_root(data_root):
    return Path(data_root or os.environ.get("SOMA_RESEARCH_DATA_ROOT")
                or os.environ.get("SOMA_DATA_ROOT") or os.environ.get("SOMA_PHASE2_DATA_ROOT")
                or "/private/tmp/soma-phase2-data")


def _manifest(interval=None):
    path = resource_directory("data") / "de421-phase2.manifest.json"
    source = load_json(path)
    effective = deepcopy(source)
    effective["kernels"] = [item for item in source["kernels"] if item["role"] != "earth_orientation"]
    effective.pop("earth_orientation_quality", None)
    effective["coverage_scope"] = "request_interval_preflighted_against_actual_SPICE_binaries"
    if interval is not None:
        effective["coverage"] = {key: interval[key] for key in ("start_utc", "end_utc")}
    return effective, hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_coverage(geometry):
    spice = geometry.spice
    windows = []
    records = {}
    for body in (3, 10, 301, 399):
        window = spice.spkcov(geometry.paths["planetary_ephemeris"], body)
        records[f"planetary_ephemeris:{body}"] = coverage_records(spice, window)
        windows.append(window)
    window = spice.pckcov(geometry.paths["lunar_orientation"], 31006)
    records["lunar_orientation:31006"] = coverage_records(spice, window)
    windows.append(window)
    common = windows[0]
    for window in windows[1:]:
        common = spice.wnintd(common, window)
    records["matched_intersection"] = coverage_records(spice, common)
    return records


def runtime_capabilities(*, data_root=None):
    """Inspect local hash-pinned sources and actual binary coverage, without fetching.

    Deployment adapters add their supported synchronous/asynchronous service mode.
    Unavailable spacecraft remains listed separately from core body readiness.
    """
    root = _data_root(data_root)
    result = {
        "ready": False, "frame": "MOON_ME_DE421", "reference_radius_m": 1737400,
        "coverage": None, "actual_coverage": {}, "spacecraft": [],
        "limits": {"max_sites": 8, "max_epochs": 2000, "max_site_epoch_pairs": 5000,
                   "max_duration_days": 31, "min_step_s": 10},
        "request_budgets": deepcopy(REQUEST_BUDGETS),
        "limitations": list(LIMITATIONS), "provider": "soma.research.SpiceGeometry/DE421",
    }
    try:
        manifest, digest = _manifest()
        with SpiceGeometry(manifest, root) as geometry:
            actual = _actual_coverage(geometry)
            common = actual["matched_intersection"]
            result.update(ready=bool(common), actual_coverage=actual, kernel_manifest_sha256=digest)
            if len(common) == 1:
                result["coverage"] = {key: common[0][key] for key in ("start_utc", "end_utc")}
            source = spacecraft_manifest()
            if source is not None:
                profile = {key: source[key] for key in ("id", "name", "input_class", "coverage", "source_url")}
                profile["available"] = False
                try:
                    load = load_spacecraft(geometry, source, root, **source["coverage"])
                    profile["actual_coverage"] = load["actual_coverage"]
                    profile["available"] = True
                except (ValueError, OSError) as exc:
                    profile["unavailable_reason"] = str(exc)
                result["spacecraft"].append(profile)
    except (ValueError, OSError, ImportError) as exc:
        result["unavailable_reason"] = str(exc)
    return result


def _canceled(event):
    if event is not None and event.is_set():
        raise StudyCancelled("geometry study canceled")


def _state(geometry, target, epoch):
    et = utc_to_et(epoch)
    state, _ = geometry.spice.spkezr(str(target), et, "MOON_ME_DE421", "NONE", "MOON")
    state = np.asarray(state, dtype=float) * 1000
    if state.shape != (6,) or not np.isfinite(state).all():
        raise ValueError("SPICE returned a non-finite or malformed six-dimensional state")
    return {"epoch_utc": epoch, "position_m": state[:3].tolist(), "velocity_m_s": state[3:].tolist()}


def _direction(position, surface, height):
    direction = vector_direction(np.asarray(position) - surface.position_m(height), surface.local_basis())
    return {"azimuth_deg": direction["azimuth_deg"], "elevation_deg": direction["elevation_deg"],
            "range_m": direction["range_m"], "direction_moon_fixed": direction["unit_vector_fixed"]}


def analyze_study(request, *, data_root=None, progress=None, cancel_event=None):
    """Evaluate bounded native SPICE states and site-relative Sun/Earth samples.

    Uses local files only. ``progress`` receives stage/count dictionaries. A
    cancellation event raises StudyCancelled and kernel-pool state is restored.
    The final sample always includes the requested end epoch. No interpolation
    or event classification is performed, and no synthetic spacecraft is added.
    """
    _canceled(cancel_event)
    request = validate_study(request)
    epochs = study_epochs(request)
    root = _data_root(data_root)

    def report(stage, completed=0):
        _canceled(cancel_event)
        if progress is not None:
            progress({"stage": stage, "completed_epochs": completed, "total_epochs": len(epochs)})
        _canceled(cancel_event)

    report("source_preflight")
    manifest, manifest_hash = _manifest(request["time"])
    source = spacecraft_manifest() if request["spacecraft_refs"] else None
    if request["spacecraft_refs"] and (source is None or request["spacecraft_refs"] != [source["id"]]):
        raise StudyValidationError("spacecraft reference is not a configured public reconstructed source")
    if source is not None:
        verify_spacecraft(source, root)
    try:
        with SpiceGeometry(manifest, root) as geometry:
            actual_coverage = _actual_coverage(geometry)
            sources = []
            spacecraft = []
            if source is not None:
                loaded = load_spacecraft(geometry, source, root, request["time"]["start_utc"], request["time"]["end_utc"])
                sources.append({"manifest_sha256": scenario_sha256(source), "manifest_hash_method": "RFC8785_SHA256", **loaded})
                spacecraft.append({"id": source["id"], "name": source["name"],
                                   "input_class": source["input_class"], "source_ref": source["id"], "samples": []})
            sites = []
            surfaces = []
            for site in request["sites"]:
                surface = SurfacePoint(site["latitude_deg"], site["longitude_deg_east"], request["frame"],
                                       request["reference_radius_m"], site["elevation_m"],
                                       site["antenna_height_m"], site["panel_height_m"], 0)
                surfaces.append(surface)
                sites.append({**site, "position_m": surface.position_m().tolist(),
                              "antenna_position_m": surface.position_m(surface.antenna_height_m).tolist(),
                              "panel_position_m": surface.position_m(surface.panel_height_m).tolist(),
                              "samples": [], "quality": {
                                  "surface_model": "reference_sphere", "elevation_datum": "declared_height_above_reference_sphere",
                                  "terrain_visibility": "not_evaluated", "solar_disk_fraction": "not_evaluated",
                                  "power": "not_evaluated", "usable_contacts": "not_evaluated",
                                  "pole_reference_meridian_deg_east": 0, "sampling": "discrete_epochs_no_event_detection"}})
            bodies = [{"id": "SUN", "samples": []}, {"id": "EARTH", "samples": []}]
            report("geometry")
            for index, epoch in enumerate(epochs):
                _canceled(cancel_event)
                for body in bodies:
                    body["samples"].append(_state(geometry, body["id"], epoch))
                for item in spacecraft:
                    item["samples"].append(_state(geometry, source["naif_id"], epoch))
                for site, surface in zip(sites, surfaces):
                    site["samples"].append({"epoch_utc": epoch,
                        "sun": _direction(bodies[0]["samples"][-1]["position_m"], surface, surface.panel_height_m),
                        "earth": _direction(bodies[1]["samples"][-1]["position_m"], surface, surface.antenna_height_m)})
                if index % 25 == 0 or index == len(epochs) - 1:
                    report("geometry", index + 1)
            for site in sites:
                site["summary"] = {f"{body}_elevation_{bound}_deg": operation(sample[body]["elevation_deg"] for sample in site["samples"])
                                   for body in ("sun", "earth") for bound, operation in (("min", min), ("max", max))}
            provenance = {"provider": "soma.research.SpiceGeometry/DE421", "software_version": __version__,
                "spiceypy_version": geometry.spice.__version__, "spice_toolkit_version": geometry.spice.tkvrsn("TOOLKIT"),
                "kernel_manifest_sha256": manifest_hash, "effective_kernel_manifest_sha256": scenario_sha256(manifest),
                "kernels": deepcopy(manifest["kernels"]), "aberration": "NONE", "geometry_model": "same_epoch_geometric",
                "verified_coverage": deepcopy(manifest["coverage"]), "actual_coverage": actual_coverage,
                "spacecraft_sources": sources,
                "assumptions": ["Site elevations and equipment heights are declared inputs above a reference sphere.",
                                "Sun observer is panel height; Earth-center observer is antenna height.",
                                "At either geographic pole, local east/north use reference meridian 0 degrees east.",
                                "UTC uses the pinned NAIF leap-second kernel; future leap seconds beyond its publication are unknown.",
                                "Before 1972, dates use SPICE's extended UTC convention; historical civil UTC is not reconstructed.",
                                "The requested end epoch is sampled even when the final interval is shorter than step_s."]}
    except StudyCancelled:
        raise
    except ValueError as exc:
        raise StudyValidationError(str(exc)) from exc
    report("result_validation", len(epochs))
    result = {"study_version": request["study_version"], "analysis_type": "geometry", "study_sha256": study_sha256(request),
              "status": "completed", "request": request, "frame": request["frame"], "origin": "MOON",
              "reference_radius_m": request["reference_radius_m"], "epochs_utc": epochs,
              "sites": sites, "bodies": bodies, "spacecraft": spacecraft, "provenance": provenance,
              "limitations": list(LIMITATIONS)}
    validate_document(result, "study-result")
    _canceled(cancel_event)
    return result
