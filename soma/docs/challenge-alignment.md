# Official challenge alignment review

Reviewed 14 November 2026. This is a scope review, not scientific validation or a claim of challenge completion.

## Live source and evidence

The official [Lunar Landing Site Navigator](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/) page was read live through Aside Browser. The visible heading and event metadata identified the **2026 NASA Space Apps Challenge**. The document title was NASA Space Apps Challenge. Both the complete Details content and [Resources tab](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=resources) were inspected, including text abbreviated by the browser's accessibility snapshot. The Resources tab was opened through its visible control; the resulting URL and selected tab were verified.

Aside CLI initially encountered a sandbox denial connecting to its local daemon. Read-only local browser access was approved and succeeded; the challenge itself was available. No challenge participation, submission, account, or team action was taken. The Teams tab was outside this requirements review. No linked third-party resource was treated as an additional challenge requirement.

## What the official brief asks for

The central task is an intuitive means to evaluate lunar sites and dates rapidly, showing the local Sun/Earth geometry so users can assess solar generation potential and direct Earth communications. Mission planners, educators, and the public are the stated audiences. The background emphasizes south-pole terrain and the need to reconsider locations or dates after mission schedule changes. [Official Details](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=details).

The objectives introduce a menu of possible features. The most direct visualization instruction concerns Sun and Earth relative to the site's horizon at the chosen date. Curated sites, custom coordinates, comparison layout, date controls, solar-elevation metrics, daylight duration, Earth windows, sunset/Earthset countdowns, animation, and audience-specific explanations are suggestions. The brief permits several application formats; it does not require Cesium, Python, a web service, or a particular solver. Its technical considerations are expressly optional, including topography, ephemeris tools or precomputed data, refraction treatment, and libration. These suggestions still motivate scientifically sound implementation choices. [Official Details](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=details).

No challenge-specific submission checklist, file format, video length, judging rubric, or submission deadline appeared in the inspected Details or Resources content. This review does not establish general event submission rules; those remain unverified rather than inferred from other years.

## Coverage and outstanding work

The seven documents in `plan/` and all six contract schemas plus `schemas/README.md` were read for this comparison. Implementation status below refers to the Phase 1 engine boundary, not to Developer B's interface.

| Official objective or suggestion | Existing plan coverage | Phase 1 evidence and remaining work |
|---|---|---|
| Rapid evaluation and comparison of sites/dates | Plan overview; Parts 2, 4, and 5 specify controlled comparisons and common assumptions. | Scenario records position, date interval, hardware and task inputs. Current validation is restricted to synthetic coverage. No physical comparison exists yet; no measured speed or usability claim is supported. |
| Local Sun and Earth positions with a horizon | Parts 1 and 4 require frame-consistent geometry and numerical terrain horizons; Part 2 describes the horizon inset. | State schema preserves origin/frame/time/units but does not itself export local azimuth/elevation or a horizon. `plan_delivery` computes none. These outputs must be implemented and carried into the display contract. |
| Assess solar power potential | Part 4 requires solar-disk fraction, panel projection, generation and battery constraints. | Scenario contains separate panel height, fixed-array geometry and battery resources. Result has an energy-history placeholder, but no illumination or generation record. Phase 3 remains necessary. |
| Assess direct Earth communication windows | Parts 1 and 3 distinguish Earth direction, actual station geometry and usable contacts. | Direct route family and explicit stations are present. Contacts remain empty; no Earth windows or physical links have been computed. Preserve a no-relay baseline in final demonstrations. |
| Understand time evolution and operational windows | Parts 2 and 5 specify one timeline driven by immutable engine output. | Qualified timestamps and endpoint occupancy are defined. Sun/Earth event histories, solar duration and window displays remain future work. A smooth orbit animation cannot substitute for these quantities. |
| Explain changes to a broad audience | Parts 2, 4 and 5 require structured explanations, warnings and a readable fallback. | Unknown status, provenance and synthetic labels prevent fabricated success. Intuitive comparison and public-facing comprehension have not been demonstrated. |
| Use credible geometry/topography and declare limitations | Parts 1, 4 and 6 source register identify matched lunar kernels, DEM metadata and independent checks. | Inputs record frame, reference sphere and equipment heights. No physical terrain or ephemeris coverage is supplied by synthetic fixtures. Phase 2 numerical acceptance gates remain open. |

The strict result schema currently forbids undeclared fields and lacks Sun/Earth directions, horizon profiles, visible solar fraction, generation history, and explicit geometric Earth-visibility history. The plan already calls for intermediate scientific records and a reduced display payload, so this is an unfinished delivery contract, not a reason to move physics into the browser. Before Phase 2/3 integration, define versioned records or referenced export artifacts and obtain Developer B's required review. Do not silently extend the frozen schema.

`soma/engine.py` correctly returns `unknown`, `unresolved`, and `not_implemented`, with empty computed histories and null delivery metrics. The relay arithmetic fixtures establish hand-checkable synthetic expectations only. Neither establishes challenge fulfillment.

## Scope distinctions and discrepancy

Finite-volume scheduling, storage, relay selection, energy-constrained optimization, replay validation, and detailed link budgets are SOMA product choices. The official brief does not require relay routing. They can explain why environmental conditions matter, but must not displace the core site/date comparison, local Sun/Earth/horizon view, solar assessment, and direct Earth baseline.

One wording discrepancy should be corrected when the shared plan is next reviewed: Part 1 describes no atmospheric refraction as a challenge requirement. In the live page it appears among optional considerations. Keeping refraction out of the lunar model remains a scientific requirement of SOMA; the distinction concerns attribution to the challenge, not the physics. No other substantive conflict with the plan's stated challenge scope was found.

## Official resource scope

The live Resources tab links [Quickmap](https://quickmap.lroc.asu.edu/) for lunar imagery/topography, [Moon Trek](https://trek.nasa.gov/moon/) for terrain exploration, [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/) for celestial geometry, and [CSA Moon Exploration](https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/) for mission context. These are resource suggestions, not mandated dependencies. The tab instructs participants to honor external data-use terms and disclaims NASA endorsement of external entities. SOMA's source register and license review should retain these boundaries. [Official Resources](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=resources).

## Proposed final acceptance evidence

These are SOMA review gates derived from the brief, not an official judging rubric:

1. Demonstrate two supported sites or two dates with controlled hardware and task assumptions, explain the change, and state coverage limits.
2. Show computed Sun and Earth directions against the actual declared terrain horizon at the selected time, with panel and antenna heights distinguished.
3. Show illumination and solar generation over the interval, and direct Earth geometric windows separately from station-specific usable contacts.
4. Keep the direct Earth result inspectable when a relay is enabled; label any synthetic trajectory, calendar, or assumed rate.
5. Verify that the displayed times, geometry and power values come from the engine exports, and remain readable when map tiles fail.
6. Recheck the live challenge and applicable event submission rules before submission. Record any later changes rather than treating this access-date review as permanent.

## Implementation update through Phase 3

The table above is the historical Phase 1 snapshot. Phase 2 now supplies pinned
Sun/Earth/station directions and quality-aware numerical horizons, and the
interface implements the Moon selection/fallback flow. Phase 3 adds disk
visibility, electrical generation, battery diagnostics, contact gates, stored
scientific graphics and comparison of saved delivery results. Sun/Earth/station
directions appear against the selected height's horizon without browser physics.
Synthetic algorithm inputs and the separate real LOLA record are visibly distinct.

The real case still has unknown terrain horizons and therefore unknown sunlight
and power; it cannot support a favorable site claim. Saved delivery results remain
unknown, and task differences are flagged rather than ranked. Scheduling/replay,
live service integration, registered overlays and the controlled end-to-end demo
remain later-phase work. These additions address the core site/date/environment
brief without claiming complete challenge fulfillment, evaluated usability,
operational service access or landing safety. Current evidence is in
[Phase 3 methods](phase-3/README.md) and
[interface verification](../../web/docs/phase-3-verification.md).
