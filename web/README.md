# SOMA fixture workspace

This implements the scenario editor, stored scientific display/comparison and
live planning-service client. Phase 5 numerical integration is verified; the
scientific map-registration acceptance gate remains unfinished.
It remains a **visual draft**, not a completed
scientific product. The user delegated both developer roles to the same team;
the engine and browser remain separate authorities. Python owns all physics
and scheduling. The browser validates, hashes and displays supplied records.

Use Node 22.12+ (or Node 24) and the Python setup in the repository README:

```sh
npm ci
npm run sync:fixtures
npm run sync:science
npm test
npm run build
npm run dev
```

Start `.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000` from the
repository root in another terminal. The default browser calls `/api` through
Vite's loopback proxy. Use `VITE_SOMA_MODE=fixture npm run dev` for explicit
offline mode. A failed live request never loads a captured result instead.

Run these commands from `web/`. The development URL is
`http://127.0.0.1:5173/`. The fixture synchronization command copies the
canonical scenarios/contact inputs/hand expectations and captures new result
JSON, a versioned summary and the complete ZIP by invoking the Python CLI once
per scenario. It also records each full run under `fixtures/phase-4/`. It never
substitutes hand expectations for the engine output. `SOMA_PYTHON` can name a Python executable with the package
installed; the default is the repository `.venv/bin/python`.

Load either network fixture, edit the scenario, inspect both equipment
heights and finite profiles, then choose **Plan delivery**. Live mode calculates
that scenario in Python and matches the completed job, summary and display by
hash. In offline mode,
only an exact matching scenario can load a captured result. Edits clear old
results and require a matching engine response; they do not rescale fixture
contacts. The 100 MiB direct case is infeasible in the bounded model. The relay
case passes independent replay with `feasible_incumbent` and assumed-rate
fidelity; optimality is unproven. The hand-calculation switch
shows separately labelled arithmetic and waiting intervals. The shared time
control reads those records without launching another calculation.

The scientific panel reads separate versioned Python diagnostics. One option
uses explicitly invented sky/skyline/contact inputs matching the scenario; the
other shows a separately labelled real LOLA/DE421 case at different coordinates.
Missing measured terrain leaves unknown sunlight, power and battery values.
Changing the scenario hides unmatched graphics. Diagnostic downloads preserve
the generated file bytes. A/B comparison stores immutable scenario/result pairs
and flags task changes. Route, byte-weighted relay wait, communications energy
and reserve margin come only from a matching versioned Python summary of a
replayed feasible run. Missing or mismatched summary values remain Unknown.
The separate diagnostic battery trace covers base load only; the delivery
result contains the selected schedule's battery history.

Date edits keep a fixed absolute deadline: changing the site or data-ready
time does not shift the deadline or analysis horizon. Those fields require
explicit edits. Earth-orbit routing is visibly disabled in this baseline.

The scenario JSON download preserves every unedited profile and provenance
field. Captured-result downloads preserve the original file bytes. Neither is
a complete run package. **Download fixture run package (ZIP)** fetches the
complete Python-authored archive unchanged, including CSVs and checksums.
No missing CSV or scientific series is rebuilt in the browser. Retry retains
the failed scenario snapshot; edits, cancel and restore invalidate stale work.

## Optional Moon display

Copy `.env.example` to `.env.local` and supply a scoped Cesium ion application
token with Moon asset access. Restart Vite after changing environment values.
The pinned client uses Moon 3D Tiles asset 2684829 and preserves Cesium notices.
The token is a browser-visible application token, so scope it for this app.
No evaluation token, paid service access, or unrestricted redistribution is
assumed. Without a token or usable tiles, numerical content remains readable.

See [viewer-registration.md](docs/viewer-registration.md) for the blocked
overlay gate. There is no engine registration yet. A display pick is only a
display observation: its marker uses the raw renderer position and is labelled
as unresolved. It does not change the physical scenario or either equipment
height. The immutable synthetic fixture point and edited draft inputs have
separate readouts. Typed coordinates remain declared-frame draft inputs until
the engine resolves them. Tile/render failures clear display selections and
preserve the numerical view. Lighting is neutral display lighting,
not a prediction of sunlight. Token-backed rendering/picking are unverified.

`VITE_SOMA_API_URL` defaults to `/api`; the Vite server forwards it to Python on
port 8000. `SOMA_API_PROXY_TARGET` configures another service target. A deployed
static build requires an equivalent reverse proxy. `VITE_SOMA_MODE=fixture`
selects the offline client. Live integration is verified; the coordinate bridge
remains blocked. No spacecraft position is invented for the contact-only relay
fixture. Exact stored samples and the registration reasons appear beside the map.
The protocol and automated schema review are in
[contract-review.md](docs/contract-review.md).

## Browser verification

The Playwright suite checks real controls, exact JSON downloads, preserved
hidden fields, invalidated edits, keyboard submission and timeline scrubbing,
and page overflow at 390, 820 and 1440 pixels:

```sh
npx playwright install chromium
npm run test:browser
```

Alternatively set `SOMA_BROWSER_EXECUTABLE` to an installed compatible Chromium
binary. Test results and local Cesium build assets are ignored. See
[Phase 1 verification](docs/verification.md) and
[Phase 2 verification](docs/phase-2-verification.md), and
[Phase 3 verification](docs/phase-3-verification.md), and
[Phase 4 verification](docs/phase-4-verification.md) for evidence and limitations.

The [Phase 5 report](docs/phase-5-verification.md) adds four actual-service browser
checks and the current acceptance boundary. Run `npm run test:live` after Python
setup to reproduce them. The local Cesium token file is ignored by Git and is
never included in exported run packages.
