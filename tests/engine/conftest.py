import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def relay_scenario():
    return json.loads((ROOT / "fixtures/synthetic-relay/scenario.json").read_text())


@pytest.fixture
def direct_scenario():
    return json.loads((ROOT / "fixtures/synthetic-direct/scenario.json").read_text())
