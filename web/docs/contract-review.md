# Interface contract review

Reviewed 2026-11-14 by the GPT-6.1 Sol interface contract/client agent, independently of the engine implementation task. This is an automated Developer B role review for Phase 1, not a human approval or a merge approval.

Read the local Developer A and B instructions, all seven `plan/` documents, all six canonical schemas, `schemas/README.md`, and the engine boundary validation. The review accepts the contract as a Phase 1 review candidate.

The contact schema fixes native timing to source-transmit epochs. Allocation records independently require source transmit intervals, receiver occupancy intervals, and byte availability. No browser derivation is needed. Lander antenna and panel heights remain separate. Frame, reference radius, elevation datum, units, qualified timestamps, net-rate convention, pointing assumptions, and service labels are explicit. Finite storage is required for each node, and battery limits, nonzero lander base demand, terminal rules, and service calendars cannot be omitted.

Result status, solver status, and fidelity are separate. Not-implemented results require unknown/unresolved, empty computed histories, and null delivery metrics. Assumed-rate results retain their fidelity label. Schema validation checks interchange structure only; Python remains responsible for references, chronology, physical relationships, coverage, and future independent schedule replay.

Future phases need reviewed schema additions for horizon profiles, Sun-visible fractions, directions, geometric opportunities and rejection reasons, sampled states, registration, and display payloads. Their absence blocks those displays, not this Phase 1 fixture client. The browser must never synthesize these values. Phase 1 source contact arithmetic expectations are separate documents and are not an engine schedule.

Hash review identified Python's integer/float spelling distinction, which JavaScript cannot preserve after JSON parsing. The engine owner resolved this by adopting RFC 8785 canonical JSON. The client uses UTF-16 key ordering, ECMAScript number spelling, raw Unicode UTF-8 bytes, and rejects unsafe integers, nonfinite numbers, non-JSON values, and lone Unicode surrogates. Cross-runtime tests cover these details.

The client imports canonical schemas directly and registers all URN IDs locally using Ajv2020 plus ajv-formats. Current Ajv documentation was queried through Context7 (`/ajv-validator/ajv`): `$id` identifies local schemas and does not require hosting or network retrieval. No private interface duplicates the schema.

Evidence: Node contract/client tests exercise canonical fixtures, omitted resource limits and timing metadata, unknown status enforcement, exact-hash fixture matching, stale responses, and cancellation. The fixture synchronization command invokes the Python CLI and checks schema and hash before writing display copies. Pure client modules have no rendered interface; visual review belongs to the application/viewer task.

The service client prepares a future protocol: POST `/plans` returns `{job_id}`; GET `/plans/{id}` returns `{status, stage, scenario_sha256}` and a canonical `result` when status is `completed`; DELETE `/plans/{id}` cancels work. This protocol is agreed for future integration and is tested with controlled HTTP doubles. No HTTP planning service exists in Phase 1. Fixture mode is explicit, accepts only an exact scenario hash, and returns the captured engine unknown result. An edited offline scenario fails without computing a replacement.
