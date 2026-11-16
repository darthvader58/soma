"""Standalone contract validation, scientific diagnostics and delivery boundary."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from soma.validation import ScenarioValidationError, load_json, load_scenario, resource_directory, scenario_sha256


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soma",
        description="Validate scenarios, plan bounded data delivery, replay schedules, and export auditable runs.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate", "Validate a standalone scenario JSON file"),
        ("plan", "Plan bounded delivery under declared assumptions; unsupported coverage remains unknown"),
        ("run", "Plan once and write the complete auditable run package"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("path", help="Path to scenario JSON")
        if name in ("plan", "run"):
            command.add_argument("--analysis-inputs", help="Versioned analysis JSON bound to the exact scenario hash")
            command.add_argument("--chunk-bytes", type=int)
            command.add_argument("--bin-s", type=float)
            command.add_argument("--time-limit-s", type=float)
        if name == "run":
            command.add_argument("--output-dir", required=True)
    replay = commands.add_parser("replay", help="Independently validate an exported run without invoking the planner")
    replay.add_argument("path", help="Path to run.json")
    environment = commands.add_parser("environment", help="Compute Phase 3 diagnostics from a versioned geometry artifact; no delivery result")
    environment.add_argument("path", help="Path to a Phase 2 geometry diagnostic JSON")
    environment.add_argument("--generation-time-model", required=True, choices=["left_sample_piecewise_constant_assumption"])
    environment.add_argument("--contact-candidates", help="Explicit interval-wide candidates JSON; never inferred from sampled directions")
    example = commands.add_parser("environment-fixture", help="Compute explicitly synthetic Phase 3 algorithm/display fixture")
    example.add_argument("path", help="Path to a synthetic scenario JSON")
    example.add_argument("--contacts", required=True, help="Path to synthetic contact input JSON")
    geometry = commands.add_parser("geometry", help="Write Phase 2 geometric diagnostics; no delivery or usable-contact claim")
    geometry.add_argument("path", help="Path to a standalone scenario JSON")
    geometry.add_argument("--data-root", required=True, help="Directory holding pinned local kernels and numerical terrain")
    geometry.add_argument("--sample-step-s", type=float, default=300)
    geometry.add_argument("--azimuth-step-deg", type=float, default=30)
    geometry.add_argument("--required-extent-m", type=float, default=200000)
    geometry.add_argument("--latitude-deg", type=float, help="Explicit diagnostic site override; never moves an unsupported site silently")
    geometry.add_argument("--longitude-deg-east", type=float, help="Explicit east-positive diagnostic site override")
    geometry.add_argument("--synthetic-relay", action="store_true", help="Explicit diagnostic-only two-body preset, not an operational/scenario relay ephemeris")
    fetch = commands.add_parser("fetch-geometry-data", help="Explicitly acquire pinned kernels and bounded LOLA data extracts")
    fetch.add_argument("--data-root", required=True)
    fetch.add_argument("--kernels-only", action="store_true")
    fetch.add_argument("--physical", action="store_true", help="Also acquire the pinned polar coverage patch for terrain_ephemeris planning")
    verify = commands.add_parser("verify-geometry", help="Compare independent Skyfield and SPICE readers")
    verify.add_argument("--data-root", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("geometry", "verify-geometry", "fetch-geometry-data"):
            directory = resource_directory("data")
            kernel_path = directory / "de421-phase2.manifest.json"
            if args.command == "fetch-geometry-data":
                from soma.datasets import extract_lola_far_cap, extract_lola_window, fetch_kernels
                manifest = fetch_kernels(kernel_path, args.data_root)
                if not args.kernels_only:
                    extract_lola_window(args.data_root, expected_manifest=load_json(directory / "lola-phase2.manifest.json"))
                    extract_lola_far_cap(args.data_root, expected_manifest=load_json(directory / "lola-far-phase2.manifest.json"))
                    if args.physical:
                        from soma.terrain.physical import acquire_polar_window
                        acquire_polar_window(args.data_root)
                output = {"acquired": True, "kernel_manifest_id": manifest["id"], "kernels_only": args.kernels_only}
            elif args.command == "verify-geometry":
                from soma.geometry_verification import verify_geometry
                output = verify_geometry(args.data_root, load_json(kernel_path))
                if not output["passed"]:
                    print(json.dumps(output, indent=2, allow_nan=False))
                    return 1
            else:
                from soma.diagnostics import geometry_diagnostic
                scenario = load_scenario(args.path)
                if (args.latitude_deg is None) != (args.longitude_deg_east is None):
                    raise ValueError("Both latitude and longitude must be supplied for an explicit site override")
                if args.latitude_deg is not None:
                    scenario["lander"]["latitude_deg"] = args.latitude_deg
                    scenario["lander"]["longitude_deg_east"] = args.longitude_deg_east
                output = geometry_diagnostic(scenario, data_root=args.data_root,
                    kernel_manifest=load_json(kernel_path), near_manifest=load_json(directory / "lola-phase2.manifest.json"),
                    far_manifest=load_json(directory / "lola-far-phase2.manifest.json"),
                    sample_step_s=args.sample_step_s, azimuth_step_deg=args.azimuth_step_deg,
                    required_extent_m=args.required_extent_m, include_synthetic_relay=args.synthetic_relay)
                if args.latitude_deg is not None:
                    output["explicit_site_override"] = {"latitude_deg": args.latitude_deg, "longitude_deg_east": args.longitude_deg_east,
                                                        "scope": "CLI-requested diagnostic test site, not an implicit move or landing recommendation"}
        elif args.command == "environment":
            from soma.environment import environment_diagnostic
            output = environment_diagnostic(load_json(args.path), generation_time_model=args.generation_time_model,
                candidates=load_json(args.contact_candidates) if args.contact_candidates else ())
        elif args.command == "environment-fixture":
            from soma.environment import synthetic_environment_fixture
            scenario = load_scenario(args.path)
            if scenario["analysis_mode"] != "synthetic_fixture":
                raise ValueError("Synthetic environment fixture requires synthetic_fixture analysis mode")
            output = synthetic_environment_fixture(scenario, load_json(args.contacts))
        elif args.command == "replay":
            from soma.schedule.replay import replay_schedule
            from soma.validation import data_volume_bytes, validate_document
            run = load_json(args.path)
            scenario = run["scenario"]
            validate_document(scenario, "scenario")
            result, analysis = run["result"], run["analysis_inputs"]
            validate_document(result, "result")
            expected_hash = scenario_sha256(scenario)
            if result["scenario_sha256"] != expected_hash or analysis["scenario_sha256"] != expected_hash:
                raise ValueError("Run scenario hash does not match result and analysis inputs")
            output = replay_schedule(scenario, analysis["contacts"], result["allocations"], analysis["generation_bins"])
            if result["status"] == "feasible_under_assumptions":
                for field in ("delivered_bytes", "final_byte_arrival_utc"):
                    if result[field] != output[field]:
                        output["errors"].append({"code": "result_mismatch", "reason": f"Native {field} differs from independent replay"})
                if output["delivered_bytes"] != data_volume_bytes(scenario["data_volume"]):
                    output["errors"].append({"code": "result_mismatch", "reason": "Native feasibility does not deliver the complete file"})
            output["passed"] = not output["errors"]
            print(json.dumps(output, indent=2, allow_nan=False))
            return 0 if output["passed"] else 1
        elif args.command == "validate":
            scenario = load_scenario(args.path)
            output = {
                "scenario_id": scenario["scenario_id"],
                "valid": True,
                "scenario_sha256": scenario_sha256(scenario),
            }
        else:
            from soma.engine import plan_run
            options = {key: getattr(args, key) for key in ("chunk_bytes", "bin_s", "time_limit_s") if getattr(args, key) is not None}
            analysis = load_json(args.analysis_inputs) if args.analysis_inputs else None
            if analysis is not None and not isinstance(analysis, dict):
                raise ValueError("Analysis inputs must be a JSON object")
            run = plan_run(load_scenario(args.path), analysis_inputs=analysis, options=options)
            output = run["result"]
            if args.command == "run":
                from soma.exports import create_run_package, json_bytes
                package = create_run_package(run)
                directory = Path(args.output_dir)
                directory.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(package)) as archive:
                    for name in archive.namelist():
                        member = Path(name)
                        if member.is_absolute() or len(member.parts) != 1:
                            raise ValueError("Export contains an unexpected member path")
                        (directory / name).write_bytes(archive.read(name))
                (directory / "run.json").write_bytes(json_bytes(run))
                (directory / "run.zip").write_bytes(package)
                output = {"status": run["result"]["status"], "solver_status": run["result"]["solver_status"],
                          "scenario_sha256": run["result"]["scenario_sha256"],
                          "package_sha256": hashlib.sha256(package).hexdigest(), "output_dir": str(directory.resolve())}
    except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError) as exc:
        print(f"soma: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
