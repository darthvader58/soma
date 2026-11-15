# Phase 6 verification records

These are generated synthetic planning calculations, not lunar mission predictions.
No expected outcome, schedule or timestamp was edited after calculation.

- `demo/`: three controlled 16 MiB cases generated with 30 s bins by
  `soma/docs/phase-6/reproduce-demo.py`. Each includes scenario, full run, ZIP and
  independent export verification. Task, hardware, battery, site, network and
  absolute deadline are held constant; only readiness and route-family enablement
  change.
- `manual-live/`: exact ZIP downloaded from the real service through Aside,
  using default 5 s bins. Its export verification and fresh-process reproduction
  preserve the actual scenario hash, settings, arrival and allocations.
- `sensitivity.json`: six 100 MiB schedule experiments and four separate static
  terrain experiments with full inputs, hashes, actual outcomes and limitations.

Use `python -m soma.verification.exports PATH/run.zip` to check an archive without
an optimizer. Use the Phase 6 reproduction guide to recalculate from its exported
scenario, analysis inputs and recorded scheduler settings. Old phase records
remain immutable snapshots of their own software and registration versions.

The technical evidence passes for this reduced scope. Public corrected-map
release remains conditional on the unresolved ion usage permission described in
`soma/docs/phase-6/source-and-license-audit.md`. No tile binaries, credentials,
DEM/geoid rasters or kernels are included here.
