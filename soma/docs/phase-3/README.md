# Phase 3: illumination, power and contacts

Phase 3 implements diagnostic components in Python and the corresponding stored
data displays in the browser. It does not select or validate a delivery schedule.
The frozen scenario, result, contact, allocation and state schemas are unchanged.
`plan_delivery` still returns `unknown` / `unresolved` / `not_implemented` until
Phase 4 supplies the energy-constrained scheduler and independent replay.

## Reproduction

With the analysis dependencies from the repository README installed:

```sh
.venv/bin/python -m soma environment soma/docs/phase-2/geometry-diagnostic.json --generation-time-model left_sample_piecewise_constant_assumption
.venv/bin/python -m soma environment-fixture fixtures/synthetic-relay/scenario.json --contacts fixtures/synthetic-relay/contacts.json
npm --prefix web run sync:science
.venv/bin/python -m pytest tests/engine -q
npm --prefix web test
npm --prefix web run build
```

`environment` consumes the versioned, recorded Phase 2 states and horizons. It
verifies scenario identity, each state epoch/frame/origin/unit, ordered coverage,
resolved site and separate horizon heights. It computes a new diagnostic without
fetching kernels or terrain. Regenerate the underlying geometry through the
[Phase 2 procedure](../phase-2/README.md) to rerun that earlier calculation.
`environment-fixture` invents explicitly labelled sky/skyline inputs and processes
them through the same Python illumination, power and contact components.
`sync:science` captures both synthetic families and the recorded LOLA case for
the browser. Files are generated, not hand-edited.

The [artifact manifest](../../../data/phase3-evidence.manifest.json) records
checksums. The real output is [environment-real.json](environment-real.json).
Synthetic outputs are under `fixtures/phase-3/`; their source scenarios and
contact inputs remain the original Phase 1 files.

## Behavior and evidence

- Solar disk quadrature combines Earth occultation and terrain masks on the
  same rays, retains unknown coverage and reports refinement. Partial sunrise
  is checked against independent analytic disk-segment arithmetic; overlapping
  eclipse/terrain masks are checked without multiplying blocked fractions.
- Fixed panels use their declared ENU unit normal, active area, efficiency,
  irradiance and lumped derating. Inverse-square Sun distance is explicit.
  Temperature, self-shadowing and tracking hardware remain unsupported.
- Piecewise constant battery bins apply the correct efficiency branch, prevent
  simultaneous charging/discharging, cap storage and charge power, spill excess
  generation and check reserve and instantaneous discharge power. Splitting a
  changing interval preserves a reserve violation even if the battery later
  recovers. A violated demand trace is counterfactual and may go negative; it
  is never exported as a feasible physical energy history.
- Usable contacts require explicit interval-wide geometry evidence, compatible
  terminals/modes, declared ideal pointing, both endpoint calendars, setup and
  teardown, payload rate method and light time. Receiver occupancy and service
  occur after propagation. Sample-only geometry cannot supply interval capacity.
- Assumed net rates remain assumed. An optional fully declared Friis/noise/mode
  budget checks a range bound and margin without overriding geometry or service.
  Coding and protocol fractions affect payload rate once. RF watts remain
  distinct from battery electrical watts.
- Finite-segment terrain/body tests stop at the spacecraft, retain grazing and
  missing-data uncertainty, and support supplied spherical or rotated ellipsoidal
  body masks. Station elevation uses an explicit Earth-ellipsoid surface normal
  in the common frame, never an Earth-center shortcut.

Method definitions and inspected primary sources are in
[solar-power-method.md](solar-power-method.md) and
[contact-method.md](contact-method.md). Tests are synthetic numerical checks,
not mission predictions or validation of operational hardware.

Owner verification: **223 engine tests passed**, including the existing schema,
arithmetic, geometry and independent ephemeris checks. No tests were skipped.
The existing Skyfield/NumPy deprecation warning remains. The interface passed
**39 Node tests, 14 Chromium browser tests, and a production build**; a focused
science-display rerun also passed after label placement was adjusted.

## Versioned environment artifact

`soma_environment_diagnostic`, version `0.3.0`, is separate from the closed
delivery-result schema. Its required records are:

| Field | Meaning |
|---|---|
| `scenario`, `scenario_sha256`, `analysis_point` | Complete task, RFC 8785 scenario identity, explicit resolved or synthetic point. |
| `frame`, `origin`, `position_unit`, `time_scale`, `analysis_horizon` | Moon-fixed DE421, Moon origin, meters, UTC and bounded coverage. |
| `horizons` | Separate panel and antenna profiles with heights, datum, convergence, cache identity and unknown samples. |
| `tracks` | Exact stored endpoint states/directions at each observer height; Earth center is distinct from a configured station. |
| `solar_samples`, `power_samples` | Epoch-tagged disk visibility, unknown bounds, numerical method and electrical generation. |
| `battery` | Explicit base-only load trace, constant-bin convention, null unknowns and violations. |
| `opportunities`, `contact_decisions` | Candidate evidence and structured acceptance/rejection/unknown reasons. |
| `contacts`, `endpoint_occupancy` | Frozen-schema usable contacts and setup-inclusive source/arrival occupancy sidecars; no allocations. |
| `assumptions`, `warnings`, `provenance` | Input class, source manifests/hashes, geometry digest convention and model limits. |

The diagnostic intentionally has no delivered bytes, selected route, allocations
or solver status. No radio activity is selected for its battery trace. Phase 4
must couple energy to route decisions instead of reusing this base-only trace
as proof that transmissions are affordable.

## Recorded outcomes and limits

The synthetic case includes partial sunrise, a changing power series, finite
base-load battery drawdown, accepted assumed-rate contacts, an intentionally
blocked interval and an unknown interval. These are invented inputs, not lunar
conditions. The original hand-calculated relay expectations remain separate.

For the recorded real LOLA site, all panel and antenna horizon azimuths remain
unknown because of measurement/count-mask gaps and failed extent convergence.
Solar fraction and generation therefore remain null, and battery energy becomes
unknown after its declared initial state. No usable contacts are inferred from
the sparse states. This is an honest limit of the acquired terrain case.

The explicit generation time model holds each left sample constant until the
next sample. It is a temporal approximation, not a conservative physical bound
on unsampled solar variation. Constant-bin battery integration checks interiors
only under that declared assumption. No continuous-time event accuracy,
published-site reproduction, full hardware validation, real service allocation,
optimal route, delivery feasibility or success probability is claimed.

The browser reads these records, plots gaps and exact samples, names station
endpoints, displays rejection reasons, and compares two saved delivery results.
Route/wait/energy/reserve summaries absent from the frozen result contract remain
Unknown. See [interface verification](../../../web/docs/phase-3-verification.md).
