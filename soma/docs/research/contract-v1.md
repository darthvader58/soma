# Live research slice contract

This is a new geometry-study contract. The frozen delivery scenario/result schemas remain unchanged. Python owns every scientific quantity. Version is `1.0.0`.

## Request

```json
{
  "study_version": "1.0.0",
  "analysis_type": "geometry",
  "frame": "MOON_ME_DE421",
  "reference_radius_m": 1737400,
  "surface_model": "reference_sphere",
  "sites": [
    {"id":"site-a","name":"Selected site","latitude_deg":-89,"longitude_deg_east":1,"elevation_m":0,"antenna_height_m":2,"panel_height_m":1}
  ],
  "time": {"start_utc":"2026-11-16T00:00:00Z","end_utc":"2026-11-16T06:00:00Z","step_s":60},
  "spacecraft_refs": []
}
```

Use timezone-qualified epochs, unique site IDs, finite numeric inputs, 1 to 8 sites, at most 2000 epochs and at most 5000 site/epoch pairs. Maximum study duration is 31 days and minimum sampling step is 10 seconds for this bounded public geometry slice. A request must fit actual kernel coverage. No silent clamping or substitution. Antenna/panel heights remain separate. Elevation is a declared input above the reference sphere, not a measurement from a rendered pick. All normalizations participate in RFC8785 study hashing.

## Python interfaces

`soma.research.validate_study(document)` returns the normalized detached request or raises a `StudyValidationError` derived from `ValueError`.

`soma.research.study_sha256(request)` returns the canonical request hash.

`soma.research.analyze_study(request, *, data_root=None, progress=None, cancel_event=None)` returns the structured result below. No kernel files are fetched from inside a scientific calculation. Providers use the source manifests and actual coverage checks. Data preparation is a separate operation.

## Result fields

The result has `study_version`, `analysis_type`, `study_sha256`, `status` (`completed` for a calculated geometry study), `request` (normalized original request), `frame`, `origin` (`MOON`), `reference_radius_m`, `epochs_utc`, `sites`, `bodies`, `spacecraft`, `provenance`, and `limitations`.

Each site has its request fields, `position_m`, `antenna_position_m`, `panel_position_m`, `samples`, `summary`, and `quality`. A sample has `epoch_utc`, `sun`, and `earth`. Each direction has `azimuth_deg`, `elevation_deg`, `range_m`, and `direction_moon_fixed` (unit three-vector). Use the panel observer for Sun and antenna observer for Earth. Summary contains `sun_elevation_min_deg`, `sun_elevation_max_deg`, `earth_elevation_min_deg`, `earth_elevation_max_deg`. Quality must explicitly state reference-sphere modeling and that terrain visibility, solar disk fraction, power and usable contacts were not evaluated. Above the spherical horizon does not establish terrain-clear access.

`bodies` is an array with `{id, samples}`, where ID is `SUN` or `EARTH`; each sample has `epoch_utc`, `position_m`, `velocity_m_s` in the declared Moon-fixed frame. `spacecraft` follows `{id, name, input_class, source_ref, samples}` with the same sample fields. Spacecraft sources must be verified public mission ephemerides or explicitly configured designed models; none are inserted implicitly. Root provides a pinned LRO source manifest, and no LRO relay service is implied.

Provenance contains the kernel/source manifest hashes, software/provider identity, same-epoch geometric `NONE` aberration convention, actual verified coverage and input assumptions. It must not claim independent accuracy validation solely because two calls to the same function agree.

## Catalog and service

Root owns `data/research-sites.json` and `soma/research/catalog.py`. `site_catalog()` returns `{catalog_version, frame, reference_radius_m, sites}`. Catalog site fields include `id`, `name`, `kind`, latitude/longitude, `position_m` (Python-derived reference-sphere display coordinate), source URLs, coordinate precision/realization notes and `input_class`. Unregistered catalog points are context markers, not terrain-aligned scientific results.

Routes use `/research` locally and `/api/research` through Vercel:

- `GET /research/catalog`: catalog above.
- `GET /research/capabilities`: readiness, actual source coverage, spacecraft profiles/coverage, request budgets, `service_mode`, async/persistence capabilities.
- `POST /research/analyze`: bounded synchronous calculation; returns the scientific result directly. Suitable for the measured small geometry slice, with no false durable job claim.
- `POST /research/jobs`, `GET /research/jobs/{id}`, `DELETE /research/jobs/{id}`: optional local durable isolated jobs. Submission includes job ID and study hash; snapshots include status, stage, hash, result/error. These routes return HTTP 503 on Vercel.
- `GET /research/jobs/{id}/export`: immutable completed research package.

The UI should query capabilities and use the supported compute mode. Cancellation of a synchronous HTTP request only stops waiting unless server cancellation is actually available. Missing backend/data must display an explicit unavailable state, with no fabricated replacement result. Captured delivery examples remain a separate archive view.

The public application and bounded synchronous geometry API run on Vercel. The containerized persistent service is an optional local reproduction tool, not a second hosting deployment. Heavy terrain/scheduling jobs require separate resource validation before they can be exposed publicly. The hosted route must not be advertised as durable asynchronous compute.
