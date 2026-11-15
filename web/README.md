# SOMA fixture workspace

This implements the Phase 1 fixture client, Phase 2 selection, and Phase 3
stored scientific display and comparison.
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

Run these commands from `web/`. The development URL is
`http://127.0.0.1:5173/`. The fixture synchronization command copies the
canonical scenarios/contact inputs/hand expectations and captures new result
JSON by invoking the Python CLI. It never substitutes hand expectations for
the engine output. `SOMA_PYTHON` can name a Python executable with the package
installed; the default is the repository `.venv/bin/python`.

Load either network fixture, edit the scenario, inspect both equipment
heights and finite profiles, then choose **Plan delivery**. In offline mode,
only an exact matching scenario can load a captured result. Edits clear old
results and require a matching engine response; they do not rescale fixture
contacts. Both current results are `unknown` / `unresolved` /
`not_implemented`, with unknown delivery metrics. The hand-calculation switch
shows separately labelled arithmetic and waiting intervals. The shared time
control reads those records without launching another calculation.

The scientific panel reads separate versioned Python diagnostics. One option
uses explicitly invented sky/skyline/contact inputs matching the scenario; the
other shows a separately labelled real LOLA/DE421 case at different coordinates.
Missing measured terrain leaves unknown sunlight, power and battery values.
Changing the scenario hides unmatched graphics. Diagnostic downloads preserve
the generated file bytes. A/B comparison stores immutable scenario/result pairs
and flags task changes; unavailable route and energy summaries remain Unknown.

Date edits keep a fixed absolute deadline: changing the site or data-ready
time does not shift the deadline or analysis horizon. Those fields require
explicit edits. Earth-orbit routing is visibly disabled in this baseline.

The scenario JSON download preserves every unedited profile and provenance
field. Captured-result downloads preserve the original file bytes. Neither is
a complete run package, and no missing CSV or scientific series is rebuilt in
the browser. Live jobs and full engine exports remain future integration work.

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

`VITE_SOMA_API_URL` prepares the future service client. Leave it empty for the
current offline fixture workflow; there is no HTTP planning service yet.
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
[Phase 3 verification](docs/phase-3-verification.md) for evidence and limitations.
