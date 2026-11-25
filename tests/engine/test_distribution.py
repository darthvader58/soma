"""Release smoke tests copied outside the checkout by verify-distribution.py."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INSTALLED_DISTRIBUTION_TEST") != "1",
    reason="Run scripts/verify-distribution.py against a built wheel",
)


def cli(*args):
    executable = Path(sysconfig.get_path("scripts")) / ("soma.exe" if os.name == "nt" else "soma")
    completed = subprocess.run(
        [str(executable), *map(str, args)], capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return json.loads(completed.stdout)


def test_installed_resources_and_console_entrypoint():
    import soma
    from importlib.metadata import metadata
    from soma.validation import load_scenario, resource_directory, schema_registry

    assert Path(soma.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert not (Path.cwd() / "soma").exists()
    assert metadata("soma-lunar")["License-Expression"] == "GPL-3.0-only"
    assert metadata("soma-lunar")["Version"] == soma.__version__
    schemas, _ = schema_registry()
    assert {"scenario", "result", "contact", "allocation", "common"} <= schemas.keys()
    for name in ("schemas", "data", "fixtures"):
        assert resource_directory(name).resolve().is_relative_to(Path(sys.prefix).resolve())
    data = resource_directory("data")
    manifest = json.loads((data / "de421-phase2.manifest.json").read_text())
    retained = next(k for k in manifest["kernels"] if k["role"] == "earth_orientation")
    assert hashlib.sha256((data / "pinned" / retained["path"]).read_bytes()).hexdigest() == retained["sha256"]
    for name in ("synthetic-relay", "synthetic-direct"):
        path = resource_directory("fixtures") / name / "scenario.json"
        scenario = load_scenario(path)
        assert scenario["analysis_mode"] == "synthetic_fixture"
        assert cli("validate", path)["valid"] is True


def test_installed_wheel_plans_exports_and_replays_100_mib(tmp_path):
    from soma.validation import resource_directory

    fixtures = resource_directory("fixtures")
    direct = cli("plan", fixtures / "synthetic-direct" / "scenario.json")
    assert direct["status"] == "infeasible_in_model", json.dumps(direct, indent=2)
    output = tmp_path / "relay-run"
    # One whole-file chunk exercises the hand-checkable two-hop transfer without
    # making this packaging check depend on a seven-chunk MILP's solve time.
    summary = cli(
        "run", fixtures / "synthetic-relay" / "scenario.json", "--output-dir", output,
        "--chunk-bytes", "104857600", "--bin-s", "5", "--time-limit-s", "30",
    )
    run = json.loads((output / "run.json").read_text())
    diagnostics = json.dumps({
        "summary": summary,
        "reason": run["result"]["provenance"]["reason"],
        "warnings": run["result"]["warnings"],
        "solver": {key: value for key, value in run["details"].get("solver", {}).items()
                   if not isinstance(value, (list, dict))},
    }, indent=2)
    assert summary["status"] == "feasible_under_assumptions", diagnostics
    assert run["result"]["delivered_bytes"] == 104_857_600
    assert run["result"]["model_fidelity"] == "assumed_rate_simulation"
    assert run["validation"]["passed"] is True
    assert cli("replay", output / "run.json")["passed"] is True
    verified = subprocess.run(
        [sys.executable, "-m", "soma.verification.exports", str(output / "run.zip")],
        capture_output=True, text=True, check=False,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert json.loads(verified.stdout)["passed"] is True
