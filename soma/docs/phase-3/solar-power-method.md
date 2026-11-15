# Phase 3 solar and electrical methods

The public functions are `soma.illumination.solar_disk_visibility`,
`soma.power.fixed_panel_power` and `soma.power.integrate_battery`.
These are diagnostics under declared inputs, not a scheduler or a delivery
feasibility result. All tests use synthetic angular geometry or hardware.

`solar_disk_visibility(sun_vector_enu_m, earth_vector_enu_m, *, horizon,
sun_radius_m=695700000.0, earth_radius_m=6378137.0,
horizon_margin_deg=0.1, samples=512, max_samples=8192, tolerance=0.005)`
requires observer-relative ENU vectors in meters. The caller must supply vectors
at the solar-panel reference height and a horizon for that same observer, epoch
and frame. An antenna-height horizon remains a separate input. Horizon mappings
are Phase 2 `HorizonProfile.to_dict()` mappings, with explicit `converged` and
`bands` containing azimuth/elevation degrees. Synthetic mappings use this same
shape and must be identified as synthetic by the caller.

Golden-angle points uniformly sample the projected solar disk. Each ray is tested
against periodic linear interpolation of adjacent horizon bands plus the declared
angular margin. Unknown endpoints or unconverged horizon extent make the terrain
classification unknown. Every ray also intersects the spherical Earth and Sun;
Earth blocks only if its positive near intersection precedes the solar surface.
The same ray masks are combined as a union, retaining overlap counts. Thus an
Earth shadow is counted once even when terrain hides that same part of the disk.
The Earth radius is an explicit spherical occulting-radius assumption, not an
Earth station coordinate model or an atmospheric model.

The count doubles until lower/upper sampled fractions change by at most the
specified tolerance, or the bounded maximum is reached. Missing terrain gives
`visible_fraction: null` and lower/upper fractions, unless Earth independently
blocks every unresolved ray. Failed quadrature convergence also gives a null
fraction. Bounds concern unknown terrain on the sampled rays only; they are not
certified quadrature, azimuth interpolation, geolocation or DEM uncertainty
bounds. Successive-count stability cannot prove omitted terrain features are
resolved. The output includes counts, refinement history, horizon convergence,
margin, radii and observer height. Uniform brightness neglects limb darkening.

`fixed_panel_power(panel_profile, sun_vector_enu_m, visible_fraction)` uses the
frozen fixed-panel schema. Its normal must have unit length; it is never silently
normalized. Irradiance is the explicit reference irradiance multiplied by
`(149597870700 m / Sun range)^2`. Power is irradiance times active area,
nonnegative center-direction cosine, efficiency, lumped derating and the direct
solar-visible fraction. Unknown visibility yields unknown power. Multiplying the
visible fraction by center-direction projection approximates incidence across
the disk, especially near edge-on incidence. Trackers, temperature and structural
self-shadowing are unsupported. No LuSEE hardware values are inherited.

`integrate_battery(profile, bins, *, base_load_w)` requires nonzero electrical
base load and explicit contiguous, chronological UTC bins with `generation_w`
and `incremental_load_w`. The optional `power_model` must be
`piecewise_constant`. Every real power change must be a bin boundary. No average
varying interval is accepted as a continuous-time proof. Input left-sampling is
only an approximation if a caller elects to construct such bins from ephemeris
samples; that caller must label it and refine in time independently.

Surplus bus generation serves loads, then charges within the bus-side charge
limit and capacity. Stored energy increases by accepted bus energy times charge
efficiency. The rest is spilled/curtailed bus energy. Deficits remove bus energy
divided by discharge efficiency, and are checked against the bus-side discharge
limit. Both charge and discharge cannot be positive in one constant bin.
`charge_bus_w` is the accepted bin-average after capacity curtailment; the
instantaneous accepted charge never exceeds the profile limit. Reserve extrema
are checked at both ends of every monotone bin, which also checks the interior
under these constant-power assumptions. Violations retain a counterfactual
demand trace, which may go negative and must not be exported as a physical
feasible energy history. Unknown generation propagates unknown stored energy.
Electrical incremental loads are never interpreted as radiated RF power.

## Primary sources inspected

- Barker et al. (2021), section 5, [NASA full text](https://ntrs.nasa.gov/api/citations/20205009660/downloads/Mike%20Barker_%20Paper_%20Improved%20Lola.pdf),
  [record](https://ntrs.nasa.gov/citations/20205009660), DOI
  [10.1016/j.pss.2020.105119](https://doi.org/10.1016/j.pss.2020.105119).
  The horizon method, solar-visible fractions, observer heights, near/far terrain
  and limitations of time-averaged illumination motivate this implementation.
  The PDF was downloaded and extracted for method inspection, not redistributed.
- Saliwanchik et al. (2024), sections 3 and 4,
  [open full text](https://arxiv.org/html/2407.07173v1), DOI
  [10.1117/12.3020538](https://doi.org/10.1117/12.3020538).
  This supplies the power-budget precedent: projected solar array geometry,
  solar fraction, explicit component loads and distinct charge/discharge losses.
  Its temperatures, derating choices, lander, battery and mission results are not
  universal lunar hardware inputs.

Golden-angle sampling, spherical same-ray eclipse masks, the constant-bin bus
convention, refinement threshold and example test profiles are SOMA engineering
choices rather than reproduced paper algorithms or validated mission predictions.
