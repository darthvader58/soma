# Hosted planner

The hosted application uses `VITE_SOMA_MODE=fixture` to load verified, captured
Python runs. The published numerical LOLA terrain and DE421 ephemerides support
three cases: direct delivery, a later direct case with zero usable capacity, and
a later lunar-relay case. The direct result loads automatically. Selecting a
physical case loads its computed contacts, allocations, storage, diagnostic
samples and registration certificate. Rates, service and the synthetic relay
trajectory retain their declared assumptions.

The static assets preserve the engine's scenario, result, summary, display data
and complete run ZIP. Downloads do not reconstruct the archive. Run
`npm --prefix web run sync:physical` to copy the approved artifacts again from
`fixtures/physical-south-pole/`.

Moon rendering also requires the hosted Python display adapter at
`/api/moon/*`. Vercel routes these requests to `api/index.py`, which serves the
engine-corrected registered Moon mesh. The browser uses the engine-authored
certificate and checks the conversion checksum before displaying aligned
overlays. Raw ion tiles are not a substitute for this corrected endpoint.
Cesium attribution remains visible. A map failure preserves the text schedule
and downloads.

Configure these environment variables in the hosting project; do not commit
their values:

| Variable | Purpose |
| --- | --- |
| `VITE_SOMA_MODE` | Set to `fixture` for the captured hosted planner. |
| `VITE_CESIUM_ION_TOKEN` | Browser-visible, read-only token scoped to Moon asset 2684829 and the approved application URL. |
| `SOMA_CESIUM_ION_TOKEN` | Server-side Moon access used by the corrected display endpoint. |
| `SOMA_PUBLIC_ORIGIN` | Approved HTTPS application origin used for upstream display requests. |
| `VITE_SOMA_API_URL` | Full planning-service base URL in live mode; defaults to `/api`. The hosted display adapter does not provide planning jobs. |

The currently provisioned scoped token expires **15 December 2026**. Rotate it
before expiry, update the applicable server and browser variables, and rebuild
the application because Vite embeds browser variables at build time. Confirm
the token permits the deployed origin and Moon asset before promoting a build.

New arbitrary sites, dates or hardware require the full local Python engine
and its numerical datasets and kernels. Captured mode accepts only exact
matching scenarios and never computes a replacement plan in JavaScript. Use
live mode with the full engine for new jobs; the small hosted Moon adapter
handles display requests only.
