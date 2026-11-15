# Developer B Phase 4 verification

The browser now displays actual captured Python schedules, structured transfer
and storage explanations, staged jobs, cancellation, immutable retry and exact
run-package downloads. The six frozen schemas are unchanged. A versioned
Python summary supplies comparison metrics; no physics moved into JavaScript.

The existing **draft without direction** remains labelled, with ENERGY 1 /
RHYTHM 1 / MOTION 1. The owner reviewed the implementation and screenshots and
ran the combined checks. This is automated engineering verification, not a
human Developer B approval, accessibility certification or Phase 5 integration.

## Recorded checks

**51 Node tests, 17 Chromium browser tests and the production build pass.**
Browser console/page-error collections are empty. Installed Chromium was used
through Playwright after the earlier Aside local-interaction failures.

| Interaction | Evidence |
|---|---|
| Actual outcomes | Direct 100 MiB failure and replayed relay success are captured from Python. Assumed-rate fidelity and `feasible_incumbent` remain visible beside status. |
| Timing and explanation | Source TX, receiver payload occupancy, byte availability, endpoint names, storage and final-byte arrival are supplied fields. Folded timeline lanes preserve exact intervals. Missing unused-contact reasons stay Unknown. |
| Delayed cancellation | An explicitly labelled delayed fixture can be canceled; no result or download appears after its former completion time. |
| Live-client races | Controlled transport tests cover stale polling, superseded accepted jobs, late accepted POST cleanup, scenario-hash rejection and export invalidation. |
| Retry | Failed offline edits retain the same detached scenario. Restore clears retry; later edits cannot reuse an earlier result. |
| Downloads | Downloaded ZIP bytes equal `web/fixtures/synthetic-relay/run.zip`. Result and scientific diagnostic downloads also retain captured bytes. The browser creates no CSV or archive. |
| Summary comparison | Matching versioned Python summary with replay passed supplies route/wait/energy/margin. Missing, unapproved, stale or unreplayed values remain Unknown. Computed zero remains zero. |
| Task control | Saved snapshots name changed network/deadline/battery assumptions and retain the fixed absolute deadline rule. No best-site ranking is inferred. |
| Optional map | Missing-token fallback preserves schedule, explanation, histories and downloads. Renderer registration still blocks aligned overlays. |
| Keyboard and layout | Native form, retry, disclosures, downloads and timeline work; 390/820/1440-pixel layouts and 200 percent text resizing remain contained. Wide tables scroll within their named regions. |

The owner inspected the [desktop relay result](screenshots/phase-4/relay-result.png)
and [mobile relay result](screenshots/phase-4/mobile-result.png). Outcome, solver,
model fidelity and delivered bytes precede long records. Schedule lanes and
large histories use native disclosures, retaining keyboard access without
placing thousands of rows before the outcome. The scientific diagnostic
explicitly identifies its base-load-only battery trace.

Reproduce from `web/` after the root Python setup:

```sh
npm run sync:fixtures
npm test
npm run build
npm run test:browser
```

`SOMA_BROWSER_EXECUTABLE` may select an installed compatible Chromium.
`sync:fixtures` solves again and may select a different valid incumbent under
the time limit. Tests verify the newly captured fields and bytes, rather than
requiring an invented successful schedule or fixed optimal completion time.

## Delivery gate

The owner reapplied the full gate to this scoped visual draft. Each line is
backed by source inspection, the interaction checks above or the prior measured
palette evidence in [verification.md](verification.md). No new colors were added.

R-01 PASS: Existing teal primary action; no gradients or decorative glow.
R-02 PASS: Authored UI copy contains no em dash.
R-03 PASS: Browser overflow checks pass at 390/820/1440 pixels and enlarged text.
R-04 PASS: No decorative icons or icon set added.
R-05 PASS: Scenario, time, outcome and diagnostic sections follow the planning task.
R-06 PASS: Existing system sans-serif and tabular numbers serve dense records.
R-07 PASS: No decorative background grid.
R-08 PASS: No decorative action arrows.
R-09 PASS: Labels describe actual fixture, solver and fidelity state.
R-10 PASS: No glassmorphism.
R-11 PASS: Existing restrained corners; no pill treatment.
R-12 PASS: No decorative shadows.
R-13 PASS: No glow.
R-14 PASS: No repeated promotional cards or filler sections.
R-15 PASS: Plan delivery, Retry same scenario and Download fixture run package name their actions.
R-16 PASS: No marketing superlatives or AI buzzwords.
R-17 PASS: Displayed values come from labelled scenario/engine artifacts.
R-18 PASS: No testimonials.
R-19 PASS: No template animation; timeline motion is user-controlled.
R-20 PASS: Paired timing/height labels and numerical planning flow express SOMA's task.
R-21 PASS: Existing light workspace supports long scientific records; no theme toggle added.
R-22 PASS: No generic illustration.
R-23 PASS: No unapproved visual assets; missing Moon tiles have a visible fallback.
R-24 PASS: Challenge and document links have real targets.
R-25 PASS: Existing measured text/focus palette retained; no new color pair introduced.
R-26 PASS: Retry, cancel, disclosures, plan, selectors, time and downloads have tested behavior.
R-27 PASS: Empty, running, canceled, error and complete states have explicit text.
R-28 PASS: No FAQ filler.
R-29 PASS: Existing neutral palette and restrained teal accent retained.
R-30 PASS: Existing planning workspace is not a product clone.
R-31 PASS: Outcomes lead; long records fold for scanning; exact intervals remain in text for audit.
R-32 PASS: Native controls/disclosures, skip link and visible focus pass keyboard tests.
R-33 PASS: Production changes are maintained in source; test-only delay interception is explicitly labelled.
R-34 PASS: No theme switch or alternate broken theme.
R-35 PASS: Production build and seventeen real-browser interaction checks pass with no console/page errors.
R-36 PASS: No flight, booked-service, thermal or standards-compliance claim.
R-37 PASS: Visual draft and honest low-energy dials remain explicit.
R-38 PASS: Captures were computed by Python; synthetic assumptions remain visible.
R-39 PASS: Native named controls, labels, scroll regions and reduced-motion rules retained.
R-40 PASS: No new media or blocking third-party scripts; optional Cesium remains lazy loaded.

Liveliness PASS: The declared dials match the calm interface. Plan delivery is
the focal action; structural spacing separates input, outcome and evidence.
Teal marks actions sparingly. Exact UTC/frame/height labels repeat the scientific
identity. The prior Design Read and reasons remain in `design.md`.

C-1 PASS: Every added element exposes supplied evidence or a real job action.
C-2 PASS: Recorded controls have working behavior.
C-3 PASS: No section was added to fill a template.
C-4 PASS: Missing map, error, cancellation, keyboard and responsive cases pass.
C-5 PASS: No fabricated testimonial, statistic or mission outcome.

## Remaining gates

The default browser workflow uses captured fixtures. The headless service is
verified independently; connecting it to the browser and validating frame
registration remain Phase 5. Token-backed Moon rendering/picking, registered
spacecraft/contact overlays and the Phase 6 end-to-end demonstration remain
unverified. The fixed synthetic scenario does not establish real lunar
site/date feasibility; measured terrain gaps still mean unknown power.
