# Recorded live browser/service run

`live-relay/run.zip` is the exact package downloaded by Chromium from the real
local service through the Vite `/api` proxy. The browser test compares these
bytes with the completed job's export and checks all ZIP member hashes and
schedule CSV epochs. No captured planning response is substituted into that test.

`live-relay/run.json` collects the package's scenario, native result, analysis
inputs, independent replay and run-manifest details into the CLI replay shape.
No allocation, outcome or metric is edited. `data/phase5-evidence.manifest.json`
records the package hash and outcome. The solver may choose a different valid
incumbent when optimization is repeated; the recorded schedule is independently
replayable:

```sh
.venv/bin/python -m soma replay fixtures/phase-5/live-relay/run.json
```

The 100 MiB synthetic relay case passes replay under assumed rates and service,
with optimality unproven. Its scenario explicitly supplies contact windows
without a trajectory. `display-data.json` therefore has no spacecraft states.
The exported renderer-registration artifact remains blocked: authenticated
Moon metadata access has not established its frame realization or independent
terrain landmark residuals. No token or credentialed URL is included.

This records the working numerical integration, not complete Phase 5 map
acceptance, a physical lunar prediction or the Phase 6 demonstration.
