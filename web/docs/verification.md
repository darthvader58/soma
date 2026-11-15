# Phase 1 interface verification

Verified 14 November 2026. The implementation is a fixture client and a
**visual draft**, not an integrated scientific planner or final visual design.

The owner read both developer instructions and all seven plan documents.
Three GPT-6.1 Sol agents implemented separate viewer, scenario/schedule, and
contract/client files. The owner reviewed their code, ran the combined checks,
integrated the shell, and fixed the browser and final-review findings.

## Evidence

- 18 Node tests pass: schema validation, Python/JavaScript canonical hashes,
  exact fixture matching, stale responses, cancellation, profile preservation,
  status/fidelity labels, and viewer registration/picking guards.
- 8 Chromium browser tests pass: fixture switching, actual captured unknown
  output, separately labelled arithmetic, precise fractional timestamps,
  keyboard timeline use, every editable form field, hidden-metadata
  preservation, edit invalidation, invalid input, exact result downloads,
  scenario downloads, focus/skip link, text resizing, and responsive overflow.
- Browser console and page-error collections are empty for those runs.
- `npm run build` produces a static Vite build. Cesium is pinned to 1.147.0;
  its runtime assets and notices are copied locally by the build prerequisite.
- The 390, 820, and 1440-pixel viewports have no horizontal page overflow.
  A 390-pixel viewport also passes with text enlarged to 200 percent. This is
  a tested text-resizing case, not an accessibility certification.
- The owner reviewed desktop, tablet, and mobile screenshots. The fallback,
  unresolved solver and model fidelity remain visible in the result flow.
  Saved evidence: [desktop](screenshots/desktop.png),
  [tablet](screenshots/tablet.png), [mobile](screenshots/mobile.png).
- All 16 selected text, component-boundary, focus and timeline color pairs
  were computed using WCAG relative luminance. Normal text ratios range from
  5.93:1 to 12.75:1; the input boundary is 3.20:1 and focus is 5.90:1.
- Source inspection/search found no RF link budget, battery integration,
  horizon ray casting, SPICE call, orbital propagation, or route search in
  browser code. Coordinate conversion for a display pick and time placement
  are presentation operations.

Aside read the local page but failed to perform reliable interactions and
screenshots. The in-app browser execution tool was unavailable. Browser QA
therefore used the locally installed Chromium through Playwright. No external
account actions or submissions were performed.

## Recorded control checks

| Control | Observed behavior |
|---|---|
| Network fixture selector | Switches direct/relay input, resets old result, preserves common task/hardware. |
| Plan delivery | Loads matching captured Python unknown result; edited offline inputs reject. |
| Restore fixture | Restores every original field and clears the previous result/error. |
| Coordinates, separate heights, volume/unit, qualified times | All round-trip in downloaded JSON; unedited profile, battery and provenance fields are preserved. |
| Hardware and route/relay controls | Select declared references without inventing a profile; empty route selection fails schema validation. |
| Declared hardware / engine provenance disclosures | Open supplied finite resource and provenance records. |
| Hand calculation switch | Shows distinctly labelled arithmetic and expected storage, without changing engine status. |
| Timeline | Keyboard End selects the exact horizon endpoint; no new analysis is started. |
| Scenario download | Preserves valid edits; invalid inputs prevent an export rather than silently exporting old values. |
| Result download | Captured file bytes match exactly in fixture mode; service mode serializes the current service result. |
| Skip link and focus | Keyboard reaches the scenario; primary action has visible focus and Tab reaches Restore fixture. |
| Challenge link | Targets the official challenge URL already read in the separate alignment review. |
| Cancellation / stale results | Future service client tested with controlled responses; no live service is claimed. |

## Delivery gate

R-01 PASS: Teal marks the primary action; no gradients, glows, or decorative stripes.
R-02 PASS: Authored interface copy contains no em dash.
R-03 PASS: 390/820/1440-pixel browser checks and enlarged-text layout pass; native controls have 44-pixel targets or associated 44-pixel labels.
R-04 PASS: No decorative icon set or emoji was introduced.
R-05 PASS: Scenario, lunar viewport, time control and result follow the actual planning workflow.
R-06 PASS: System sans-serif supports dense labels; tabular numerals align scientific records; monospace is limited to raw JSON.
R-07 PASS: No decorative background grid.
R-08 PASS: No decorative action arrows.
R-09 PASS: Phase and fidelity labels convey actual implementation state; no decorative capsule badges.
R-10 PASS: No glassmorphism.
R-11 PASS: Controls and panels use restrained 3/4-pixel corners; no uniform pill treatment.
R-12 PASS: No decorative shadows.
R-13 PASS: No glows.
R-14 PASS: No feature-card filler; each panel has a distinct task.
R-15 PASS: Plan delivery, Restore fixture and JSON download labels describe their real actions.
R-16 PASS: Copy names the task and limitations without marketing buzzwords.
R-17 PASS: Displayed numerical inputs come from labelled synthetic fixtures or exact engine records.
R-18 PASS: No testimonials, invented people or customer claims.
R-19 PASS: No automatic decorative motion; time scrubbing is user controlled.
R-20 PASS: The workspace exposes lunar coordinates, separate heights, native contact timing and finite profiles.
R-21 PASS: Light reading panels and a dark lunar viewport have documented functional purposes.
R-22 PASS: No unrelated illustration or generated asset.
R-23 PASS: Product name is text; no unapproved logo, avatar, photo or statistic. Layout follows the supplied functional plan and remains labelled a visual draft.
R-24 PASS: The skip link and official challenge link have valid targets; no speculative navigation.
R-25 PASS: Computed text, focus and component-boundary color ratios meet their applicable thresholds.
R-26 PASS: Recorded control checks cover the real actions; unavailable operations are disabled or explained.
R-27 PASS: Empty result, request progress, offline mismatch, validation and map-fallback states have explicit messages.
R-28 PASS: No generic FAQ.
R-29 PASS: Neutral surfaces, dark text and one teal action accent; status meanings also have text.
R-30 PASS: Layout follows the task, not a copied commercial product.
R-31 PASS: Each panel, color, type choice and position has a documented purpose.
R-32 PASS: Keyboard submit, slider, skip link and focus order pass browser checks; controls are native.
R-33 PASS: UI features were authored directly in source; fixture synchronization only copies declared data and captures engine output.
R-34 PASS: No untested theme toggle is shipped.
R-35 PASS: Build, real browser interactions, screenshots and empty console/page-error checks completed.
R-36 PASS: No fabricated performance, security, compliance, service access or scientific-success claim.
R-37 PASS: The absence of user visual direction is explicit; the implementation is a labelled draft with ENERGY 1 / RHYTHM 1 / MOTION 1.
R-38 PASS: Synthetic records and hand arithmetic remain explicitly separate from actual unknown engine output.
R-39 PASS: Native named controls, labels, pointer/disabled states, visible focus, document landmarks and no automatic motion.
R-40 PASS: The map reserves its layout area; no external font, hero image or blocking third-party script is required for fixture mode.

Liveliness PASS for the declared draft: Plan delivery is the focal action,
spacing groups scenario/viewport/result, teal is restrained, and the recurring
numbered workflow identifies the product task. Final visual direction remains
open rather than being represented as user approved.

Craftsmanship PASS for the Phase 1 client: every section supports inspecting
the scenario/result, states survive map absence and input edits, and no
scientific number is invented to fill an empty output.

## Limits and next gates

This historical Phase 1 report describes the captured delivery-fixture path.
Standalone Python geometry and numerical DEM diagnostics were added in engine
Phase 2; see [engine evidence](../../soma/docs/phase-2/README.md). The delivery
fixture path still has no illumination/power/contact/solver/replay integration
or live HTTP service. No complete engine run package,
Sun/Earth/horizon series, real site/date comparison or integration demo is
claimed here. [Phase 2 interface verification](phase-2-verification.md) adds
controlled tile/render failure and picking checks. Cesium token-backed loading,
real tile failure, depth picking and
landmark residuals remain unverified; no token or authoritative registration
was provided. All aligned overlays stay blocked. Tests of supplied registration
evidence are structural checks, not a numerical registration measurement.

The schema review is by an automated assigned interface reviewer. It is not
human Developer B approval or a merge. Subsequent contract changes still need
review, and later phases must satisfy their scientific gates before release.
