"""Exercise the repository CLI through its real process boundary."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from soma.validation import load_scenario, scenario_sha256, validate_document


ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "soma", *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("fixture", ["synthetic-direct", "synthetic-relay"])
def test_validate_and_plan(fixture, tmp_path):
    scenario = load_scenario(ROOT / "fixtures" / fixture / "scenario.json")
    scenario["data_volume"] = {"value": 16, "unit": "byte"}
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario))
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
    assert result["scenario_sha256"] == scenario_sha256(scenario)
    assert result["status"] == "feasible_under_assumptions"
    assert result["delivered_bytes"] == 16
    assert result["allocations"]


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


@pytest.mark.parametrize("args", [("--help",), ("validate", "--help"), ("plan", "--help"), ("run", "--help"), ("replay", "--help")])
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


def test_run_exports_one_exact_run_and_replay_rejects_corruption(tmp_path):
    import hashlib
    import zipfile

    scenario = load_scenario(ROOT / 'fixtures/synthetic-relay/scenario.json')
    scenario['data_volume'] = {'value': 16, 'unit': 'byte'}
    path = tmp_path / 'scenario.json'
    path.write_text(json.dumps(scenario))
    directory = tmp_path / 'capture'
    completed = run_cli('run', path, '--output-dir', directory, '--chunk-bytes', 16, '--bin-s', 30, '--time-limit-s', 5)
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary['status'] == 'feasible_under_assumptions'
    assert summary['package_sha256'] == hashlib.sha256((directory / 'run.zip').read_bytes()).hexdigest()
    with zipfile.ZipFile(directory / 'run.zip') as archive:
        for name in archive.namelist():
            assert archive.read(name) == (directory / name).read_bytes()
    run = json.loads((directory / 'run.json').read_text())
    assert run['result'] == json.loads((directory / 'result.json').read_text())
    replay = run_cli('replay', directory / 'run.json')
    assert replay.returncode == 0, replay.stderr + replay.stdout
    assert json.loads(replay.stdout)['passed']
    run['result']['allocations'][0]['byte_length'] += 1
    corrupt = tmp_path / 'corrupt.json'
    corrupt.write_text(json.dumps(run))
    replay = run_cli('replay', corrupt)
    assert replay.returncode != 0
    assert not json.loads(replay.stdout)['passed']
    assert 'Traceback' not in replay.stderr
    run['result']['allocations'][0]['byte_length'] -= 1
    run['result']['delivered_bytes'] += 1
    corrupt.write_text(json.dumps(run))
    report = run_cli('replay', corrupt)
    assert report.returncode != 0
    assert any(error['code'] == 'result_mismatch' for error in json.loads(report.stdout)['errors'])
    # Explicit, hash-bound analysis inputs use the same CLI planning boundary.
    inputs = directory / 'analysis-inputs.json'
    external = run_cli('plan', path, '--analysis-inputs', inputs, '--bin-s', 30, '--time-limit-s', 5)
    assert external.returncode == 0, external.stderr
    assert json.loads(external.stdout)['status'] == 'feasible_under_assumptions'


def test_run_invalid_options_and_replay_hash_mismatch_have_no_traceback(tmp_path):
    scenario_path = ROOT / 'fixtures/synthetic-direct/scenario.json'
    completed = run_cli('run', scenario_path, '--output-dir', tmp_path / 'out', '--chunk-bytes', 0)
    assert completed.returncode != 0
    assert 'Traceback' not in completed.stderr
    assert not (tmp_path / 'out').exists()
    malformed = tmp_path / 'run.json'
    malformed.write_text('{}')
    replay = run_cli('replay', malformed)
    assert replay.returncode != 0
    assert 'Traceback' not in replay.stderr
