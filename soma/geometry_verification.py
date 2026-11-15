"""Independent readers check the implementation, not the underlying JPL data."""

from pathlib import Path
from importlib.metadata import version
from contextlib import ExitStack

import numpy as np

from soma.geometry import SpiceGeometry, SurfacePoint
from soma.time.spice import utc_to_et


def _open_reference(paths):
    from skyfield.api import PlanetaryConstants, load, load_file
    resources = ExitStack()
    try:
        ephemeris = load_file(str(paths["planetary_ephemeris"]))
        resources.callback(ephemeris.close)
        constants = PlanetaryConstants()
        with paths["lunar_frame"].open("rb") as stream:
            constants.read_text(stream)
        binary_stream = resources.enter_context(paths["lunar_orientation"].open("rb"))
        constants.read_binary(binary_stream)
        frame = constants.build_frame_named("MOON_ME_DE421")
        return resources, ephemeris, frame, load.timescale(builtin=True)
    except BaseException:
        resources.close()
        raise


def verify_geometry(data_root, manifest):
    """Compare SpiceyPy states/rotations with Skyfield's independent readers."""
    paths = {entry["role"]: Path(data_root) / entry["path"] for entry in manifest["kernels"]}
    resources, ephemeris, frame, timescale = _open_reference(paths)
    epochs = ["2026-11-14T08:50:00Z", "2026-11-14T09:30:00Z", "2026-11-14T10:05:00Z"]
    site = SurfacePoint(-89, 0, "MOON_ME_DE421", 1737400, 0, 2, 1, 0)
    checks = []
    try:
        with SpiceGeometry(manifest, data_root) as geometry:
            for epoch in epochs:
                et = utc_to_et(epoch)
                # Split JD avoids losing microseconds by adding small fractions
                # to a 2.4-million-day floating-point Julian date.
                time = timescale.tdb_jd(2451545.0, et/86400.0)
                rotation = frame.rotation_at(time)
                # Skyfield 1.55's rotation_at passes a single-float JD to its
                # PCK reader. Compare rotations at that same quantized epoch.
                rotation_et = (float(time.tdb)-2451545.0)*86400.0
                rotation_reference = geometry.spice.pxform("J2000", "MOON_ME_DE421", rotation_et)
                rotation_error = float(np.max(np.abs(rotation-rotation_reference)))
                for target in ("SUN", "EARTH"):
                    inertial = (ephemeris[target.lower()]-ephemeris["moon"]).at(time).position.m
                    actual_inertial = np.asarray(geometry.state(target, epoch, frame="J2000")["position"])
                    inertial_error = float(np.linalg.norm(inertial-actual_inertial))
                    reference = rotation @ inertial
                    actual = np.asarray(geometry.state(target, epoch)["position"])
                    residual = float(np.linalg.norm(reference-actual))
                    role_height = 1 if target == "SUN" else 2
                    vector = reference-site.position_m(role_height)
                    # Independent elementary spherical ENU at lon=0, lat=-89.
                    lat = np.deg2rad(-89)
                    e = vector[1]
                    n = -np.sin(lat)*vector[0]+np.cos(lat)*vector[2]
                    u = np.cos(lat)*vector[0]+np.sin(lat)*vector[2]
                    reference_elevation = float(np.rad2deg(np.arctan2(u, np.hypot(e, n))))
                    actual_direction = geometry.direction(site, target, epoch, role_height)
                    angle_error = abs(reference_elevation-actual_direction["elevation_deg"])
                    checks.append({"epoch_utc": epoch, "target": target,
                                   "fixed_position_raw_residual_m": residual,
                                   "inertial_position_residual_m": inertial_error,
                                   "rotation_epoch_quantization_s": rotation_et-et,
                                   "matched_epoch_rotation_max_element_residual": rotation_error,
                                   "elevation_residual_deg": angle_error,
                                   "inertial_position_tolerance_m": .01,
                                   "rotation_element_tolerance": 1e-10, "elevation_tolerance_deg": 1e-7,
                                   "passed": inertial_error <= .01 and rotation_error <= 1e-10 and angle_error <= 1e-7})
    finally:
        resources.close()
    return {"artifact_type": "soma_geometry_independent_verification", "artifact_version": "0.2.0",
            "passed": all(item["passed"] for item in checks), "checks": checks,
            "method": "SpiceyPy/CSPICE versus Skyfield/jplephem SPK and binary-PCK readers, plus independent ENU arithmetic",
            "frame": "MOON_ME_DE421", "ephemeris": "DE421", "aberration": "NONE",
            "scope": "Implementation and frame handling, not independent validation of the shared JPL ephemeris or terrain",
            "reference_precision_note": "Skyfield 1.55 rotation_at uses a single-float TDB Julian date. Raw fixed-vector differences include that time quantization; rotations are additionally checked at matching quantized epochs. SPK inertial comparisons retain split-JD precision.",
            "tolerance_scope": "Conservative floating-point implementation comparisons, not physical ephemeris uncertainty or registration accuracy",
            "reader_versions": {name: version(name) for name in ("skyfield", "jplephem", "spiceypy", "numpy")},
            "provenance": {"kernels": manifest["kernels"]}}
