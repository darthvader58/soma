"""Standalone contract validation, scientific diagnostics and delivery boundary."""

import argparse
import json
import sys

from soma import plan_delivery
from soma.validation import ScenarioValidationError, load_json, load_scenario, resource_directory, scenario_sha256


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soma",
        description="Validate scenarios, compute standalone diagnostics, or inspect the unresolved delivery planner.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate", "Validate a standalone scenario JSON file"),
        ("plan", "Return an unknown result; scientific planning is not implemented"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("path", help="Path to scenario JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            scenario = load_scenario(args.path)
            output = {
                "scenario_id": scenario["scenario_id"],
                "valid": True,
                "scenario_sha256": scenario_sha256(scenario),
            }
        else:
            output = plan_delivery(load_scenario(args.path))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"soma: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
