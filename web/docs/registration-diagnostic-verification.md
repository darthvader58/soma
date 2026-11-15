# Registration diagnostic verification

This is a draft developer instrument with ENERGY 1 / RHYTHM 1 / MOTION 1.
Its single task is to accept predeclared probes and capture raw observations.
It neither computes registration approval nor changes the planning scenario.
System text, native controls and a linear request/status/result flow serve
technical inspection. No branding direction is asserted.

The owner inspected the enlarged [mobile control view](screenshots/phase-5/registration-diagnostic-mobile.png).
Chromium checks pass for invalid input, cancellation, unchanged JSON download,
390-pixel overflow, actual 200-percent body text sizing, keyboard focus and zero
page errors. Four- and 100-probe actual captures exercise successful completion.
Unit tests reject false registration assertions and invalid/excessive requests.
The production app build passes; this separate developer HTML entry is served
by Vite in development and is not included in that production entry point.

Normal text/background contrast is 13.13:1; the focus/background pair is 5.59:1,
computed with the skill's contrast checker. Source review and executed controls
support this scoped delivery gate:

R-01 PASS: No gradients or decorative glow.
R-02 PASS: No authored em dash in the diagnostic UI.
R-03 PASS: 390-pixel and actual doubled text checks contain the page.
R-04 PASS: No decorative icon set.
R-05 PASS: Request, measurement status and raw result follow the task.
R-06 PASS: System text and smaller raw-JSON monospace have a written inspection purpose.
R-07 PASS: No decorative background grid.
R-08 PASS: No decorative action arrows.
R-09 PASS: Status reports measured, unknown or canceled work.
R-10 PASS: No glass effects.
R-11 PASS: Native controls avoid pill treatment.
R-12 PASS: No decorative shadows.
R-13 PASS: No glow.
R-14 PASS: No filler cards.
R-15 PASS: Measure, Cancel and Download name their tested actions.
R-16 PASS: Copy describes raw observations and limitations.
R-17 PASS: Limits are implemented; counts come from captures.
R-18 PASS: No testimonials.
R-19 PASS: No template animation; the scene exists only during a requested measurement.
R-20 PASS: Explicit lunar frame, unit and unregistered-candidate labels identify the instrument.
R-21 PASS: Light text workspace supports long JSON inspection; dark canvas holds the optional scene.
R-22 PASS: No generic illustrations.
R-23 PASS: Existing authorized Moon asset is used with Cesium credits; no fabricated media.
R-24 PASS: No nonexistent navigation links.
R-25 PASS: Text and focus contrast were calculated.
R-26 PASS: Measure, invalid input, cancel and exact download were exercised.
R-27 PASS: Ready, loading, complete, unavailable and canceled states have text.
R-28 PASS: No FAQ filler.
R-29 PASS: Neutral palette plus restrained green focus.
R-30 PASS: No product clone.
R-31 PASS: Layout exposes the request and evidence without implying approval.
R-32 PASS: Native tab order and visible keyboard focus verified.
R-33 PASS: Maintained source implements the page; synthetic calibration interception is a labelled experiment.
R-34 PASS: No theme switch or alternate broken theme.
R-35 PASS: Real captures, browser control checks and app build ran.
R-36 PASS: No certified alignment, accuracy or mission claim.
R-37 PASS: Draft diagnostic status and calm dials are explicit.
R-38 PASS: Actual observations and failed calibration attempts are distinguished.
R-39 PASS: Main landmark, language/title, labels, native controls and pointer/disabled states are present.
R-40 PASS: Canvas space is reserved; no new media or blocking third-party script.

Liveliness PASS: One focal measurement action, structural whitespace, restrained
focus accent and repeated precise frame/unit labels match the declared dials.
C-1 PASS: Every element serves request or evidence inspection.
C-2 PASS: Recorded controls have real actions.
C-3 PASS: No template-only section.
C-4 PASS: Invalid input, cancellation, unknown hits, mobile and keyboard remain explicit.
C-5 PASS: No fabricated statistic, endorsement or passing registration.

This UI gate is separate from scientific map acceptance. The engine's v0.2
certificate covers the tested application region from -90 to -87.5 degrees
latitude in the corrected representation. Four resolved grid features and 48
height controls were checked at the detailed 5.21 m mesh level. The 3.54 m
grid-resolution allowance is not a continuous-peak localization bound or an
absolute geolocation guarantee, and the test does not certify all locations or
mesh detail levels. Root and four control-tile fingerprints are sampled
snapshot checks, rather than a checksum pin for every regional tile.

The diagnostic defaults to the unmodified asset. In development,
`registration.html?representation=registered` uses the same engine-corrected
loader as the application and records its conversion checksum and certificate
version. `SOMA_REGISTRATION_URL` selects this URL for the capture script.
Measurements remain raw observations with `registration_status: not_evaluated`.
