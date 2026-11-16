# Research dashboard compatibility verification

Recorded at 2026-11-17T06:49:05.658975Z. This is a targeted verification of the public archive retirement and its evidence dependencies. The user requested that the public application show the research dashboard. Historical delivery fixtures and components remain available for offline regression.

The scientific engine, frozen schemas and archived scenario/result/ZIP outputs have no edits in this change. Original scientific scope, review dates and recorded verification counts remain unchanged in the historical manifests. Their completion flags describe the original bounded release; they do not certify the new dashboard or claim a current public delivery interface.

## Source bindings

All 438 manifest bindings match their current files. The refresh follows dependency order: Phase6 evidence, physical-first-release evidence, then the fixture inventory. The localhost-only helper `tests/web/legacy-archive-support.mjs` is bound as offline regression infrastructure in the two evidence manifests. It injects a local test document and grants origin-scoped loopback access; the public `main.js` imports only the workbench.

| Manifest | Bindings | SHA256 |
| --- | ---: | --- |
| `data/phase6-evidence.manifest.json` | 43 | `4ec2d2ace2f8e9d9426fd2c61828501bc2f8fbb6e5864874b7a111795d8aa770` |
| `data/physical-first-release-evidence.manifest.json` | 97 | `2700c0b0f24b1a682ea5d0d0ea2c7317107535591c2820905f8232e31613b3e0` |
| `fixtures/manifest.json` | 298 | `a8570993168e2b20cb02885810d3ed9615fd9914074380cf9322bd5d21dac020` |

## Checks executed

| Check | Result |
| --- | --- |
| Contract, schema/manifest bindings, fixture arithmetic and Phase6 completion tests | 74 passed, 0 failed, 0 skipped in 14.00 s |
| Stored physical-first-release completion/replay evidence | 33 checks passed; no errors |
| Fresh synthetic 100 MiB relay calculation | `feasible_under_assumptions`; `feasible_incumbent` |
| Independent CLI replay of that fresh synthetic run | Passed; no errors; 104,857,600 bytes delivered |

```sh
.venv/bin/pytest -q tests/engine/test_fixture_manifest.py tests/engine/test_contract.py tests/engine/test_manifests.py tests/engine/test_fixture_arithmetic.py tests/engine/test_phase6_completion.py
.venv/bin/python -m soma.verification.physical_completion
.venv/bin/python -m soma run fixtures/synthetic-relay/scenario.json --output-dir /private/tmp/soma-dashboard-synthetic-relay-check --time-limit-s 15
.venv/bin/python -m soma replay /private/tmp/soma-dashboard-synthetic-relay-check/run.json
```

The fresh synthetic schedule's final byte arrives at `2026-11-14T10:01:35Z`. Its scenario hash is `b1d39f45c88b822029edacd515a698b928af4188751bcee364367772427f9106`. The generated run ZIP hash is `12de8eb12c1cb8d90ee3b9f1157bb6593311409da19c3dddeb903d2db345673c`. This is a bounded synthetic test using declared assumed contacts/rates/service, not a lunar mission prediction. The incumbent is feasible under those assumptions; optimality is unproven. The independent replay checks the complete modeled schedule.

A full engine suite was not rerun for this presentation/routing change. The counts above are the fresh targeted checks. Browser, visual and deployment verification belong to the separate UI/routing workstreams and are not claimed by this report. No archived fixture output was regenerated or replaced.
