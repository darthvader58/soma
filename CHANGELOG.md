# Changelog

## 0.1.0 - 2026-11-25

First packaged release of `soma-lunar` (Python import `soma`).

- Standalone scenario validation with explicit units, times, frames, finite
  resources, versioned JSON schemas, and canonical scenario hashes.
- Matched DE421/SPICE geometry, numerical LOLA terrain access, terrain horizons,
  finite-range visibility, sampled solar-disk visibility, and electrical power
  calculations under declared assumptions.
- Bounded direct-to-Earth and single-lunar-relay delivery planning with
  contact capacity, causal forwarding, storage, terminal conflicts, propagation
  delay, and lander battery constraints.
- Independent schedule replay and auditable JSON, CSV, CZML, Markdown, and ZIP
  exports with scientific status separate from solver status.
- Command-line workflows and a local process-isolated planning service.
- A web workbench for reference-sphere geometry and bounded terrain-backed
  delivery, with Python-calculated states and downloadable run packages.
- Synthetic direct/relay examples and a recorded 16 MiB south-polar date
  comparison, with assumptions, provenance, and reproduction instructions.

Terrain-backed planning is limited to its declared region, dates, and sampling.
Rates, service, hardware, and synthetic relay trajectories are assumptions.
Earth-orbit routing and general constellation optimization are not implemented.
This release is a planning model, not an operational mission prediction.
