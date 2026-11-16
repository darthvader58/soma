# Live delivery interface verification

The interface consumes the version 1.0.0 hosted transport and native 0.1.0 scientific contracts. It posts editable declared scenarios to Python, validates matching scenario/result/display hashes, requires independent replay for feasible candidates and preserves the original native ZIP after inner gzip decompression and SHA-256/size verification. The HTTP stack decodes outer gzip separately. Response budgets are 16 MB decoded and 4 MB wire.

The scene uses registered Python endpoint states and exact source-transmit intervals. It does not propagate trajectories, recompute visibility or integrate energy. Static legacy surface records can supply their declared antenna position; an exact registered lander state takes priority. Unsupported sample times remain unknown. Earth network view fits actual stored positions and labels the resulting scale. LRO remains archival geometry context and is never offered as relay service.

Validation on 18 November 2026:

- `cd web && npm test`: 105 passed.
- `cd web && npm run build`: passed.
- `cd web && SOMA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npx playwright test --config playwright.delivery.config.js`: fresh backend integration passed in 18.9 seconds. The test starts an isolated API on 8071 and Vite on 5191, with prepared sources in `api/_data`.
- The integration test checks blank numeric/UTC inputs, an actual fresh Python request, solver/fidelity/replay/arrival display, exact transfer focus, the actual Cesium network camera, original ZIP download checksum/size, profile refresh after edits, stale download disabling and return to Geometry. It uses a reference-sphere fallback without an ion token, so it does not certify streamed tiles.

An earlier browser run was invalidated by development hot reload during editing; the stable rerun passed. The ordinary Playwright cache is absent on this workstation, so the installed Chrome executable is selected explicitly. Root-agent Aside review owns visual desktop/mobile screenshots and the personal delivery gate.
