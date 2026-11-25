# Contributing to SOMA

SOMA develops auditable lunar data-delivery calculations under explicit
assumptions. Contributions should make a scientific result, a reproducible
workflow, or its explanation more reliable.

## Before changing the model

Read the [scientific plan](https://github.com/darthvader58/soma/blob/main/plan/README.md)
and the chapter relevant to your change. The Python engine is the authority for
geometry, illumination, power, contacts, and scheduling. The web application
displays its results. Discuss changes to supported physics, route families,
schemas, or data sources in an issue before implementing them.

Keep one scientific purpose per pull request. Preserve explicit units, origin,
frame realization, epoch, time scale, and source provenance. Missing data must
remain unknown. A scenario must declare finite resources and service assumptions.
Changes to the JSON contract need review by both engine and interface maintainers.

## Development setup

Use Python 3.12 or newer:

```sh
git clone https://github.com/darthvader58/soma.git
cd soma
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[planning,service,verification,test]"
```

Planning requires an executable CBC solver. Numerical analysis also uses native
SPICE and geospatial dependencies. See the
[installation guide](https://soma-ce3178ca.mintlify.site/getting-started/installation)
for requirements. The synthetic checks below need no terrain/kernel download.

## Verify an engine change

From the repository root:

```sh
python -m pytest tests/engine -q
python -m soma validate fixtures/synthetic-relay/scenario.json
python -m soma run fixtures/synthetic-relay/scenario.json --output-dir /tmp/soma-contribution-relay
python -m soma replay /tmp/soma-contribution-relay/run.json
python -m soma.verification.exports /tmp/soma-contribution-relay/run.zip
```

Add a focused test for a changed physical rule or constraint. Prefer a
hand-computable case, a regression reproducing a failure, or an independent
reference calculation. Agreement between two calls to the same function is a
regression check, not independent scientific evidence. Report skipped checks and
their reasons. Tests that need separately acquired scientific data must say so.

For interface changes, use the supported Node.js version in
[web/README.md](https://github.com/darthvader58/soma/blob/main/web/README.md), then run:

```sh
npm --prefix web ci
npm --prefix web test
npm --prefix web run build
```

Documentation changes should keep examples consistent with the installed
package. Read the [documentation setup](https://github.com/darthvader58/soma/blob/main/docs/README.md)
for Mintlify validation. Do not commit generated scientific binaries, credentials,
large downloads, or restricted source material.

## Report a reproducible problem

Use a minimal scenario and the exact command or API request. Include the SOMA,
Python, operating-system, and solver versions; expected and actual behavior;
scientific status and solver status; and warnings or replay errors. For numerical
differences, include units, frame realization, UTC interval, equipment heights,
sampling settings, dataset/kernel manifest IDs, and hashes. Attach an exact run
package when its inputs can be shared.

Distinguish a software defect from a changed assumption or unsupported coverage.
Remove credentials and private mission data before posting a public issue.

## Submit a pull request

Describe the concrete behavior before and after the change, the relevant plan
sections, and the fixture or calculation that supports it. List remaining
synthetic inputs and approximation limits. Scientific schedules must come from
the engine and pass replay; do not edit outcomes to fit a demonstration.

Preserve upstream notices when adapting code. Add original source references and
record data redistribution terms. Contributions are distributed under the
project's [GNU GPLv3 license](https://github.com/darthvader58/soma/blob/main/LICENSE);
dependencies and datasets keep their own licenses.
