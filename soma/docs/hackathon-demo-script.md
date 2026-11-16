# SOMA hackathon demonstration and recording script

Use the [public demonstration](https://soma-atlas-two.vercel.app/?case=direct-ready). All five cases follow one **hypothetical south-pole lander study**: return a 16 MiB science-data bundle within six hours. Published numerical LOLA terrain and DE421 ephemerides anchor the environmental calculations at a real lunar location. This is a proposed mission study, not a reconstruction of a flown mission.

## Mission brief and evidence

| Input | Value and evidence |
| --- | --- |
| Surface location | 89.030930°S, 1.389337°E, planetocentric / east-positive, in the declared DE421 lunar frame |
| Numerical terrain | NASA's published [south-pole LOLA mosaic](https://pgda.gsfc.nasa.gov/products/81), with pinned extracts and explicit interpolation/count-mask handling |
| Operating dates | 24 and 30 November 2026; Sun/Earth geometry calculated from the pinned ephemerides |
| Delivery task | 16 MiB within six hours; an illustrative science-data bundle, not an instrument's published data product |
| Small-lander profile | 80 Wh initial battery, 10 Wh reserve, 5 W base load; engineering assumptions, not a flight-qualified hardware specification |
| Lunar relay | Finite-storage synthetic two-body preset; assumed rates, ideal pointing and declared service, not an operational provider's ephemeris or booking |
| Operational questions | Date selection, delayed forwarding, low initial battery, and loss of relay service |

NASA describes delay/disruption-tolerant networking as a response to intermittent space links. That is the [operational motivation](https://www.nasa.gov/communicating-with-missions/delay-disruption-tolerant-networking/) for showing storage and forwarding; SOMA is not a flight DTN implementation.

## Recording setup

Record a 1920 × 1080 browser window at 100% zoom with microphone narration. Keep the public application and this documentation open in separate tabs. Load each case once before recording so its display data and terrain are ready. Keep the Cesium attribution visible whenever the map appears. Record the app, documentation and exported run files.

Aim for **7 minutes 10 seconds**, speaking at approximately 125–140 words per minute. The timestamps below include short holds while viewers read a result. Leave the key states visible for at least five seconds rather than rushing between cases. A rehearsal should remain longer than five minutes.

| Time | What to record |
| --- | --- |
| 0:00–0:40 | Opening problem, application title and Mission cases. |
| 0:40–1:25 | Direct delivery: inputs, computed outcome and arrival time. |
| 1:25–2:10 | Later direct: controlled date change and zero-capacity explanation. |
| 2:10–3:20 | Lunar relay: stored transmission sample, timeline and forwarding wait. |
| 3:20–4:10 | Sun/Earth horizon diagnostic and modeled power. |
| 4:10–4:55 | Low battery: the same later mission with 11 Wh initial energy. |
| 4:55–5:40 | Relay unavailable: the same mission without relay service windows. |
| 5:40–6:30 | Download the exact relay run and show the library documentation. |
| 6:30–7:10 | Return to the relay scene and state the contribution and scope. |

## 0:00–0:40: The decision

**Record:** Open [Direct delivery](https://soma-atlas-two.vercel.app/?case=direct-ready). Show the title, the five Mission cases and the Moon. Use a slow scroll to the scene if needed.

**Say:**

“A lunar landing site is also an operating environment. Terrain can hide Earth, sunlight changes with the date, and a transmission consumes energy while a deadline keeps approaching. A useful planning question is: can this lander deliver this dataset to Earth in time?

This is SOMA, a lunar data-delivery planner. We are studying a proposed small lander at a real south-pole location, using published lunar terrain and ephemerides. I’ll show a successful delivery, a date that changes the answer, a relay solution, and operational changes to battery energy and service availability.”

## 0:40–1:25: A direct delivery that works

**Record:** Click **Direct delivery**. Hold on **Engine outcome**. Show the case inputs, then use **Delivery result** to reveal the final-byte arrival. The full scenario is in the left panel; its fields stay read-only during this walkthrough.

**Say:**

“Our example is at approximately eighty-nine degrees south and one point four degrees east. A sixteen-mebibyte science-data bundle is ready at eight UTC on November twenty-fourth, with a deadline six hours later. The assumed small-lander profile starts with eighty watt-hours and retains a ten watt-hour reserve.

The Python engine finds a direct-to-Earth schedule. The complete file arrives at approximately eight ten and one second UTC. That is the last byte arriving at the receiver. The result retains its assumed-rate label and its solver status, alongside the schedule and resource histories that explain the conclusion.”

## 1:25–2:10: A later date changes the answer

**Record:** Return to Mission cases and click **Later direct**, or open its [direct link](https://soma-atlas-two.vercel.app/?case=direct-later). Show **What changed**, then **Engine outcome** and **Contact timeline**.

**Say:**

“Now we move the same site to November thirtieth. The dataset, hardware and initial battery stay fixed. The deadline remains six hours after data readiness, and the declared service windows move with the mission window.

This time direct delivery fails in the declared model. The explanation is specific: the usable direct contacts provide zero payload bits before the deadline, while our file requires more than one hundred and thirty-four million bits.

An empty transmission schedule is therefore a computed failure with a reason. This comparison shows why evaluating the location together with the operating date matters.”

## 2:10–3:20: Store, wait and forward

**Record:** Click **Lunar relay** or open its [direct link](https://soma-atlas-two.vercel.app/?case=relay-later). Click **Show relay transmission · 09:33:30 UTC**. Hold on the map and solid allocated link. Then click **Contact timeline** and show the source transmission, receiver occupancy and storage rows.

**Say:**

“For the same later task, we now enable one declared lunar relay. Its trajectory is a synthetic two-body preset, with finite storage and explicitly assumed radio rates and service. These are the assumptions of this demonstration.

At this stored timestamp, the solid line represents an allocated transmission from the lander to the relay. Selecting a time reads an engine-authored state; it does not run a new optimization.

The lander transmits from nine thirty-three thirty until nine thirty-five. After the whole chunk becomes available, it waits for the later ground contact. Forwarding begins at nine thirty-six, and the final byte reaches the Earth receiver at approximately nine thirty-seven and one second.

The schedule accounts for that wait, finite storage, radio occupancy, propagation delay and lander energy. This result is a feasible incumbent: the schedule passed independent replay, while full optimality remains unproved.”

## 3:20–4:10: Explain the environmental inputs

**Record:** In **Contact timeline**, select **2026-11-30T09:34:00Z** from **Stored engine sample (UTC / stated offset)**. This exact minute has matching scientific diagnostic records. Click **Power and horizon**. Under **Observer height**, choose **Antenna** to show the Earth/station/relay directions and horizon, then **Panel** to show the Sun direction and zero generated power. The Earth-center direction is not a station-service determination.

**Say:**

“The environmental explanation sits underneath the route. Here we can inspect the computed terrain horizon and the Sun and Earth directions at an exact stored time. Antenna height and panel height remain separate inputs, because they can see different horizons.

The numerical analysis uses published LOLA elevation grids and matched DE421 geometry. The Moon rendering uses neutral display lighting; its visual shading is separate from the calculated solar diagnostic.

For this later six-hour case, modeled panel generation is zero at the supplied samples. The selected schedule must therefore respect the declared battery model. Missing samples remain unknown, and published grid interpolation remains labeled.”

## 4:10–4:55: A low battery changes the operating plan

**Record:** Click **Low battery** or open its [direct link](https://soma-atlas-two.vercel.app/?case=battery-low). Show **What changed**, the controlled-test explanation and the native **Unknown** engine outcome. Keep the explanation of incomplete contact coverage visible.

**Say:**

“Now consider the same later mission starting with a depleted battery. Only its initial energy changes, from eighty to eleven watt-hours. The reserve stays at ten; the site, date, sixteen-mebibyte task and hardware stay fixed.

The original relay schedule no longer passes independent replay: it violates the reserve. The six-hour base load alone requires more energy than the one watt-hour available above reserve, with no modeled generation at the supplied samples.

The native result remains unknown because the preserved contact coverage is incomplete. We show both facts: the known plan fails the battery check, and the engine does not claim an exhaustive routing proof.”

## 4:55–5:40: Visibility does not allocate service

**Record:** Click **Relay unavailable** or open its [direct link](https://soma-atlas-two.vercel.app/?case=service-off). Show the changed service calendar, the controlled-test explanation, the native **Unknown** result and its empty selected-transmission schedule.

**Say:**

“Return the battery to eighty watt-hours, but suppose the planned relay service is unavailable. Only the relay calendar changes. A spacecraft can be visible without having a reservation to receive and forward our data.

Independent replay rejects the original relay schedule for unavailable service. The captured direct-contact set cannot provide a replacement for this later-date task. With incomplete contact coverage, the engine again reports unknown rather than claiming that every possible network would fail.

These are practical planning decisions: can we operate with this battery state, and can we rely on this service allocation? Each answer retains the evidence and its limits.”

## 5:40–6:30: Make the result reproducible

**Record:** Return to **Lunar relay**. Click **Run package**, then **Download run package (ZIP)**. Show the downloaded archive's filenames: `scenario.json`, `run-manifest.json`, `schedule.csv`, `energy.csv`, `buffer-history.csv`, `summary.json`, `replay.json`. Then click **Documentation** and open **Python API** or **Calculate a synthetic delivery**. Pre-open the downloaded archive during rehearsal if your operating system needs time to display it.

**Say:**

“A researcher needs the calculation behind the picture. This download preserves the exact scenario, source manifest, contacts, selected schedule, energy, storage and independent replay evidence. Another person can inspect the assumptions and reproduce the calculation with the Python library.

The documentation shows installation, the planning API, the local HTTP service and export verification. The browser and library share the same engine-authored results.

The hosted demonstration loads verified captured runs. New supported coordinates, dates or hardware can be calculated through the full Python engine with the required numerical datasets. Published terrain and ephemerides remain separate from assumed hardware, rates and service.”

## 6:30–7:10: Close on the contribution

**Record:** Return to **Lunar relay**, use **Show relay transmission · 09:33:30 UTC** again and hold the Moon, relay and allocated contact. End with the site and the Documentation button visible through a slow scroll.

**Say:**

“The Lunar Landing Site Navigator challenge asks teams to make site, date, sunlight and Earth-visibility trade-offs understandable. SOMA connects those conditions to a concrete delivery question: what transmits, when, through whom, and under which assumptions?

We have shown a successful direct plan, a later-date failure, a store-and-forward relay solution, and two operational changes that invalidate that known plan. Each outcome has an inspectable record, including the unresolved cases.

SOMA is a planning model under declared assumptions. Its contribution is an auditable conversation between terrain, timing, communications and energy, so a team can understand why an operating plan works or fails.”

## Rehearsal checklist

- Start at `?case=direct-ready`; wait for the computed outcome and terrain to load.
- Follow **Direct delivery**, **Later direct**, **Lunar relay**, **Low battery**, then **Relay unavailable**. All five retain the same 16 MiB workload and six-hour deadline rule.
- Use the relay focus button for the visible allocated link and the exact `09:34:00Z` sample for the scientific diagnostic.
- Keep the supplied native solver status, assumptions and units visible when discussing an outcome.
- Download the successful relay package for the reproducibility segment.
- Read the narration aloud once with a timer. Keep the final recording longer than five minutes; the planned screen holds target roughly seven minutes.

The challenge framing is based on the [official Lunar Landing Site Navigator brief](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/). Outcomes and times come from the repository's engine-generated terrain-backed mission and controlled-variant archives. The scientific sources support the terrain, geometry and methods; they do not establish that this proposed lander or relay is an operating mission.
