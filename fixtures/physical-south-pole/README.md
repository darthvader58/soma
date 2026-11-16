# Bounded physical delivery demonstration

`scenario.json` and `scenario-later.json` are complete requests for the same
LOLA site on November 24 and 30, 2026. Physical preparation computes terrain,
ephemeris, illumination, power and contacts. Hardware, radio rates, service and
the short-arc two-body relay remain explicitly assumed/synthetic.

`direct-ready/`, `direct-later/` and `relay-later/` contain computed, verified run
ZIPs, standalone scenarios, summaries and export receipts. The ZIP contains the
native result, analysis inputs, provenance, exact CSV records, display states,
registration, explanation and per-member checksums. It contains no source DEM,
kernel or tile binaries. Infeasibility is a discretized-model conclusion; replay
checks claimed feasible schedules and does not independently prove infeasibility.

`terrain-verification.json` records quality masks, extent/spatial refinement,
the assumed outer-terrain envelope and a separate scalar implementation check.
`sampling-verification.json` records the controlled 60/30-second comparison and
replayable inputs/results. `independent-audit.json` identifies the exact archives
verified and reoptimized by a non-author agent.

See the [physical first-release guide](../../soma/docs/physical-first-release/README.md)
for commands, method, outcomes, plan coverage and limitations.
