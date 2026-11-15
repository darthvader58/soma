# Independent Phase 6 reproduction

On 15 November 2026, an automated independent non-author GPT-6.1 reviewer
inspected the Phase 6 evidence from source base `29c67b7`. This was an agent
review, not a separate person or human usability study. No browser or credentials
were used. The reproduction ran in the existing workspace; it does not claim a
new clean source copy.

The canonical archive was `fixtures/phase-6/manual-live/run.zip`, SHA-256
`90a892d9a631754c6bcf6eddfda7681df765292e6573c662e16b66ad1ca51c30`.
Its scenario hash was
`ac353a904a2a21cd9d004885b687ec2b3bae750953c80073dcc893d18509300a`.

The reviewer executed:

```sh
.venv/bin/python -m soma.verification.exports fixtures/phase-6/manual-live/run.zip
.venv/bin/pytest tests/engine/test_phase6_handoff.py tests/engine/test_phase6_sensitivity.py -q
```

Archive verification passed with no errors. The two test files passed all nine
tests in 44.63 seconds, with 19,849 existing PuLP deprecation warnings.

For an independent optimization, the reviewer read `scenario.json`,
`analysis-inputs.json`, `result.json` and `run-manifest.json` directly from the
ZIP using Python's `zipfile` and `json` modules. The reviewer called
`soma.engine.plan_run(scenario, analysis_inputs=analysis_inputs,
options=manifest['details']['scheduler_options'])`. The archived options were
`bin_s=5`, `chunk_bytes=16777216` and `time_limit_s=15`. The newly computed
allocations equaled the archived allocations exactly. The result was
`feasible_under_assumptions`, solver status `proven_optimum`, with 16,777,216
bytes delivered at `2026-11-14T10:00:15Z`. These are synthetic planning results.

The reviewer also inspected the stored-state acceptance evidence. The live
contact-only relay has no trajectory and exports empty spacecraft states, so
the correct selected-time readout is Unknown. `tests/web/display.test.mjs`
separately checks a declared synthetic spacecraft sample: equality at its exact
epoch, retained origin/frame/units metadata, no sample at the next second and
rejection of missing frame metadata. The browser suite was inspected, not rerun
by this reviewer. The absence rule does not authorize inventing a trajectory.

The computed demonstration changes data readiness within one operating day.
Unsupported site/date behavior remains explicit; this review does not establish
a physical site/date relay rescue. Public corrected-ion permission remains
unresolved for a future public deployment and is outside this local verification scope. This receipt establishes
independent non-author agent reproduction; it does not assert that a separate
human followed the demonstration.

The machine-readable receipt is
[independent-review.json](../../../fixtures/phase-6/independent-review.json).
