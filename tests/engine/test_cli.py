"""Exercise the repository CLI through its real process boundary."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from soma import plan_delivery
from soma.validation import load_scenario, scenario_sha256, validate_document


ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "soma", *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("fixture", ["synthetic-direct", "synthetic-relay"])
def test_validate_and_plan(fixture):
    path = ROOT / "fixtures" / fixture / "scenario.json"
    scenario = load_scenario(path)
    validation = run_cli("validate", path)
    assert validation.returncode == 0
    assert validation.stderr == ""
    assert json.loads(validation.stdout) == {
        "scenario_id": scenario["scenario_id"],
        "valid": True,
        "scenario_sha256": scenario_sha256(scenario),
    }
    planning = run_cli("plan", path)
    assert planning.returncode == 0
    assert planning.stderr == ""
    result = json.loads(planning.stdout)
    validate_document(result, "result")
    assert result == plan_delivery(scenario)
    assert result["status"] == "unknown"
    assert result["allocations"] == []


@pytest.mark.parametrize("command", ["validate", "plan"])
@pytest.mark.parametrize("invalid", ["malformed", "omitted_storage", "missing"])
def test_input_errors_have_no_result(tmp_path, command, invalid):
    path = tmp_path / "scenario.json"
    if invalid == "malformed":
        path.write_text("{broken", encoding="utf-8")
        expected = "Invalid JSON"
    elif invalid == "omitted_storage":
        scenario = load_scenario(ROOT / "fixtures/synthetic-relay/scenario.json")
        del scenario["profiles"]["relays"][0]["storage_capacity_bytes"]
        path.write_text(json.dumps(scenario), encoding="utf-8")
        expected = "storage_capacity_bytes"
    else:
        expected = "No such file"
    completed = run_cli(command, path)
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert expected in completed.stderr
    assert "Traceback" not in completed.stderr


@pytest.mark.parametrize("args", [("--help",), ("validate", "--help"), ("plan", "--help")])
def test_help(args):
    completed = run_cli(*args)
    assert completed.returncode == 0
    assert "usage:" in completed.stdout
    assert completed.stderr == ""


def test_missing_command_is_usage_error():
    completed = run_cli()
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "usage:" in completed.stderr
    assert "Traceback" not in completed.stderr
