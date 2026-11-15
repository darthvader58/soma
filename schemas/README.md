# SOMA contract v0.1.0

Phase 1 review candidate. The assigned interface reviewer has completed the
automated structural review described below; this is not a merge approval.
The schemas use JSON Schema Draft 2020-12. Register all six `$id` values from
this directory locally and enable format validation; no schema needs a network
fetch. Python additionally checks references, chronology, physical resource
relationships, and the declared fixture coverage. Units are part of every field
name or a required unit enum. Unknown quantities use JSON `null`, never zero.

`scenario.schema.json` embeds versioned resource profiles so a scenario can load
without browser state or an external profile server. References must resolve to
exactly one embedded profile. All nodes have explicit finite storage. Empty
service windows mean no service. Missing fields never create resources. Schema
validation accepts a bounded vocabulary for future analysis, but Phase 1 only
supports `synthetic_fixture` with `synthetic-contract-v1`. That mode validates
invented inputs; it provides no physical terrain or ephemeris coverage.

Native contacts use source-transmit epochs and net payload bits per second with
overhead already applied. Allocations identify a byte range of a named chunk,
its contact, both endpoint occupancy intervals, and receiver byte availability.
Final-byte arrival includes propagation and processing. A modeled-link label
must never be used for assumed rates. Schema validity alone does not certify a
schedule; independent replay is a later implementation gate.

The initial `plan_delivery` result has status `unknown`, solver status
`unresolved`, fidelity `not_implemented`, empty computed histories, and `null`
delivery metrics. Hand-calculated fixture expectations live outside that result
and must never be presented as an engine-generated schedule.

Boundary timestamps require RFC 3339 dates with seconds and a timezone.
Qualified offsets are accepted and normalized to UTC by `soma.time`.
Longitude is east positive in [-180, 180); latitude is planetocentric.
Lunar locations explicitly identify `MOON_ME_DE421` and a reference sphere;
Earth station coordinates explicitly use WGS84 / ITRF93.

State epochs identify their representation explicitly: UTC uses `rfc3339`
and a qualified timestamp, while TDB uses `seconds_past_j2000_tdb` and a
finite numeric epoch. A state with malformed time metadata is invalid.
This defines interchange semantics; the Phase 1 package does not convert
between UTC and TDB without SPICE kernels.

After Phase 1, contract changes require a pull request reviewed by Developer B.
The scientific source is the seven documents in `plan/`, especially Parts 1,
3, 4, and 5. No external library algorithm is copied into this contract.

The assigned interface reviewer has completed the Phase 1 structural review;
see `web/docs/contract-review.md`. This is an automated agent review under the
user's combined-role authorization, not approval from the absent Developer B.
Environmental records and renderer registration remain future contract work.

`scenario_sha256` is SHA-256 of RFC 8785 canonical JSON bytes. Equivalent JSON
numbers such as 1 and 1.0 identify the same input; timezone spelling remains
part of the input. Numeric values must be finite and within JavaScript's safe
integer range in magnitude. This prevents browser rounding from silently
changing profile resources. `fixtures/hash-vectors.json` supplies shared
Unicode, exponent, signed-zero, and nested-object interoperability cases.
