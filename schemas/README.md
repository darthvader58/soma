# SOMA contract v0.1.0

Versioned contracts for the implemented planner and geometry study service.
The schemas use JSON Schema Draft 2020-12. Register all schema `$id` values from
this directory locally and enable format validation; no schema needs a network
fetch. Python additionally checks references, chronology, physical resource
relationships, and the declared fixture coverage. Units are part of every field
name or a required unit enum. Unknown quantities use JSON `null`, never zero.

`scenario.schema.json` embeds versioned resource profiles so a scenario can load
without browser state or an external profile server. References must resolve to
exactly one embedded profile. All nodes have explicit finite storage. Empty
service windows mean no service. Missing fields never create resources. Schema
validation accepts a bounded vocabulary. The planner supports synthetic fixture
inputs and a separately prepared, bounded `terrain_ephemeris` provider. The
synthetic mode supplies no physical terrain or ephemeris coverage; schema
validity alone does not establish provider coverage.

Native contacts use source-transmit epochs and net payload bits per second with
overhead already applied. Allocations identify a byte range of a named chunk,
its contact, both endpoint occupancy intervals, and receiver byte availability.
Final-byte arrival includes propagation and processing. A modeled-link label
must never be used for assumed rates. Schema validity alone does not certify a
schedule; the implemented independent replay validator must check it.

`plan_delivery` returns `feasible_under_assumptions`, `infeasible_in_model` or
`unknown`, with separate solver status, model fidelity and provenance. Feasible
results are released only after schedule replay passes. Hand-calculated fixture
expectations live outside that result and must never be presented as an
engine-generated schedule.

Boundary timestamps require RFC 3339 dates with seconds and a timezone.
Qualified offsets are accepted and normalized to UTC by `soma.time`.
Longitude is east positive in [-180, 180); latitude is planetocentric.
Lunar locations explicitly identify `MOON_ME_DE421` and a reference sphere;
Earth station coordinates explicitly use WGS84 / ITRF93.

State epochs identify their representation explicitly: UTC uses `rfc3339`
and a qualified timestamp, while TDB uses `seconds_past_j2000_tdb` and a
finite numeric epoch. A state with malformed time metadata is invalid.
This defines interchange semantics; actual UTC/TDB conversion requires the
matched SPICE kernel context.

After Phase 1, contract changes require a pull request reviewed by Developer B.
The scientific source is the seven documents in `plan/`, especially Parts 1,
3, 4, and 5. No external library algorithm is copied into this contract.

The assigned interface reviewer has completed the Phase 1 structural review;
see `web/docs/contract-review.md`. This is an automated agent review under the
user's combined-role authorization, not approval from the absent Developer B.
That review is historical evidence. The current exporter supplies environmental
records and renderer registration without changing the source-transmit timing
convention. `study.schema.json` and `study-result.schema.json` separately define
reference-sphere geometry studies and stored samples.

`scenario_sha256` is SHA-256 of RFC 8785 canonical JSON bytes. Equivalent JSON
numbers such as 1 and 1.0 identify the same input; timezone spelling remains
part of the input. Numeric values must be finite and within JavaScript's safe
integer range in magnitude. This prevents browser rounding from silently
changing profile resources. `fixtures/hash-vectors.json` supplies shared
Unicode, exponent, signed-zero, and nested-object interoperability cases.
