# Phase 2 numerical evidence

This is geometric and terrain-method evidence, not a delivery plan or a mission
prediction. The canonical delivery result remains `unknown`. The browser does
not calculate or display a replacement scientific result.

The recorded [geometry diagnostic](geometry-diagnostic.json) uses the explicit
verification point −89.03093035536243° planetocentric latitude,
1.389336784014743° east, selected from a positive-count PGDA pixel. Its source
polar coordinates are x=712.5 m, y=29,377.5 m. Its measured-grid height is
−301.98974609375 m above the 1,737,400 m reference sphere, in
`MOON_ME_DE421`. This is a numerical control point, not a named landing site
or an assessment of landing safety. Renderer landmark registration is pending.

At 2026-11-14T08:50:00Z, the recorded Sun-center direction at panel height is
approximately azimuth 120.76699°, elevation 1.06105°, range 147,794,144,140 m.
Earth center at antenna height is approximately azimuth 356.87520°, elevation
−3.29728°, range 405,505,228 m. These are same-epoch geometric directions, not
apparent directions, solar-disk visibility, or a particular station's access.

The diagnostic contains 16 epochs at 300-second spacing through 10:05 UTC.
Panel and antenna horizons are separate. Every horizon band remains unknown
because measured-data gaps prevent the declared convergence check, including
the coarse far terrain. Sampled lower bounds are retained as diagnostics and
are never substituted for a complete skyline. The optional, explicitly
synthetic two-body relay intersects the declared body model in this run.
No outcome has been edited to make a favorable example.

Geometric intervals are grouped adjacent samples with recorded boundary
uncertainty. Their interiors are not continuously proved, and opportunities
shorter than the time step can be missed. They carry no rate or capacity.
Station positions use Earth translation plus WGS84/ITRF93 rotation; station
opportunities remain unknown because the complete endpoint/segment check has
not yet been built. Source/receiver contact timing remains a later-layer task.

## Independent comparison

[independent-verification.json](independent-verification.json) compares
SpiceyPy/CSPICE against the independent Skyfield/jplephem SPK/PCK readers at
three epochs, plus elementary ENU arithmetic. The readers share JPL DE421 and
lunar-orientation data, so the comparison checks implementation, origins,
units and frames. It does not independently validate the ephemeris itself.

The maximum inertial position difference is 0.003529 m, the maximum
matched-epoch rotation-element difference is 1.034e-12, and the maximum local
elevation difference is 4.241e-11 degrees. Checks use conservative numerical
tolerances of 0.01 m, 1e-10 matrix elements, and 1e-7 degrees respectively.
These are numerical comparison limits, not physical uncertainty estimates.

Skyfield 1.55 evaluates lunar rotation with a single floating-point TDB Julian
date. Its 4–19 microsecond epoch rounding explains raw fixed-vector differences
up to about 7.54 m at Sun distance. The report keeps those raw residuals and
compares rotation matrices at the same quantized epoch. It preserves split-JD
precision for inertial SPK comparisons. This precision issue is reported,
rather than conflated with terrain or ephemeris error.

An additional regression uses the independent numerical Earth vector published
in NAIF `moon_080317.tf` for 17 March 2008. Analytic tests cover coordinate
round trips, pole bases, units, synthetic ridges, missing samples, separate
equipment heights, bounded trajectory histories and finite
segments where terrain beyond the spacecraft cannot block it.

## Reproduction and boundaries

Use the commands in the root README with Python 3.12+ and the `analysis` and
`verification` extras. Binary data live outside the repository, under an
explicit data root. All files and extraction parameters are pinned in `data/`.
The acquisition command successfully verified/recreated the local bundle.
Set `SOMA_PHASE2_DATA_ROOT` when running the integration tests elsewhere.
Those tests explicitly skip when external data have not been acquired; the
recorded development run used the real files with no skips.

No solar fraction, eclipse mask, panel power, battery integration, usable
contact, finite-volume schedule, replay validator, live service or renderer
registration is implemented by this artifact. Phase 3 must preserve unknown
terrain and enforce its own physical gates. A sampling-stable synthetic
skyline does not supply missing real measurements. A Skyfield/NumPy upstream
array-shape deprecation warning is visible during verification; it does not
change the numerical checks.
