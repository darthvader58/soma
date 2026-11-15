const ASSET_ID = 2684829;
const BATCH_SIZE = 32;
const BUDGET_MS = 120000;
const QUERY_WIDTH_M = 0.1;

export function validateProbeRequest(value) {
  if (!value || value.format_version !== '0.1.0' || typeof value.request_id !== 'string' ||
      !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$/.test(value.request_id) ||
      value.source_frame !== 'MOON_ME_DE421' || value.candidate_bridge !== 'identity_for_measurement_only') {
    throw new Error('Request requires version 0.1.0, a simple request_id, MOON_ME_DE421 and identity_for_measurement_only.');
  }
  if (!Array.isArray(value.probes) || !value.probes.length || value.probes.length > 4096) {
    throw new Error('Declare between 1 and 4096 probes.');
  }
  const ids = new Set();
  for (const probe of value.probes) {
    if (!probe || typeof probe.id !== 'string' || !probe.id || probe.id.length > 160 || ids.has(probe.id) ||
        !Array.isArray(probe.position_m) || probe.position_m.length !== 3 || !probe.position_m.every(Number.isFinite)) {
      throw new Error('Each probe requires a unique id and three finite position_m coordinates.');
    }
    const radius = Math.hypot(...probe.position_m);
    if (radius < 1600000 || radius > 1900000) throw new Error('Probe positions must be near the lunar surface: radius 1600000 to 1900000 meters.');
    ids.add(probe.id);
  }
  return structuredClone(value);
}

function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

function attachDiagnostic() {
  const byId = id => document.getElementById(id);
  let output;
  let active;
  Object.defineProperty(window, 'somaRegistrationMeasurement', { get: () => output, configurable: false });
  const publish = value => {
    output = freeze(structuredClone(value));
    byId('probe-result').value = JSON.stringify(output, null, 2);
    byId('download-probes').disabled = false;
  };
  byId('cancel-probes').addEventListener('click', () => active?.abort());
  byId('download-probes').addEventListener('click', () => {
    if (!output) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(output, null, 2) + '\n'], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${output.request_id}-raw-mesh.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  byId('measure-probes').addEventListener('click', async () => {
    if (active) return;
    let request;
    try {
      if (byId('probe-request').value.length > 4000000) throw new Error('Probe request exceeds the diagnostic input limit.');
      request = validateProbeRequest(JSON.parse(byId('probe-request').value));
    } catch (error) { byId('measurement-status').textContent = `Invalid request: ${error.message}`; return; }
    const controller = new AbortController();
    active = controller;
    byId('measure-probes').disabled = true;
    byId('cancel-probes').disabled = false;
    const started = performance.now();
    const measurement = {
      artifact_type: 'soma_raw_renderer_measurement', format_version: '0.1.0',
      request_id: request.request_id, source_frame: request.source_frame,
      candidate_bridge: request.candidate_bridge, request,
      started_utc: new Date().toISOString(), status: 'running', asset_id: ASSET_ID,
      cesium_version: null, ellipsoid_radii_m: null, tileset_model_matrix_column_major: null,
      root_transform_column_major: null, root_computed_transform_column_major: null,
      query_width_m: QUERY_WIDTH_M, batch_size: BATCH_SIZE, budget_ms: BUDGET_MS,
      vertical_exaggeration: 1, clamp_to_height_supported: null, tile_failure_count: 0,
      registration_status: 'not_evaluated',
      warnings: ['Raw renderer geometry only; no frame registration, fiducial correspondence or residual is established.',
        'Maximum available mesh detail is not a claim of source accuracy.',
        'Returned world positions already include Cesium tile and model transforms.'],
      probes: request.probes.map(probe => ({ id: probe.id, input_position_m: [...probe.position_m], renderer_position_m: null, status: 'not_measured' })),
    };
    let viewer;
    let shader;
    let removeTileFailure;
    let removeRenderFailure;
    let timer;
    let expired = false;
    const stop = new Promise((_, reject) => {
      controller.signal.addEventListener('abort', () => reject(new Error('canceled')), { once: true });
      timer = setTimeout(() => { expired = true; reject(new Error('timeout')); }, BUDGET_MS);
    });
    // All awaited work races the same total budget; late queries cannot publish.
    const bounded = promise => Promise.race([promise, stop]);
    publish(measurement);
    try {
      byId('measurement-status').textContent = 'Loading the dedicated Moon-only scene.';
      const token = import.meta.env?.VITE_CESIUM_ION_TOKEN;
      if (typeof token !== 'string' || !token.trim()) throw new Error('missing_scoped_ion_token');
      const C = await bounded(import('cesium'));
      if (controller.signal.aborted || expired) throw new Error('canceled');
      measurement.cesium_version = C.VERSION;
      C.Ellipsoid.default = C.Ellipsoid.MOON;
      C.Ion.defaultAccessToken = token.trim();
      viewer = new C.Viewer(byId('measurement-view'), {
        ellipsoid: C.Ellipsoid.MOON, globe: false, baseLayer: false, sceneModePicker: false,
        baseLayerPicker: false, geocoder: false, scene3DOnly: true, animation: false,
        timeline: false, homeButton: false, navigationHelpButton: false, fullscreenButton: false,
        selectionIndicator: false, infoBox: false, skyBox: false, skyAtmosphere: false,
        shadows: false, shouldAnimate: false, requestRenderMode: false,
      });
      viewer.scene.verticalExaggeration = 1;
      measurement.logarithmic_depth_buffer = viewer.scene.logarithmicDepthBuffer;
      measurement.clamp_to_height_supported = viewer.scene.clampToHeightSupported;
      measurement.ellipsoid_radii_m = [viewer.scene.ellipsoid.radii.x, viewer.scene.ellipsoid.radii.y, viewer.scene.ellipsoid.radii.z];
      if (!measurement.clamp_to_height_supported) throw new Error('unsupported_depth_textures');
      removeRenderFailure = viewer.scene.renderError.addEventListener(() => controller.abort());
      shader = new C.CustomShader({ lightingModel: C.LightingModel.UNLIT });
      const moonPromise = C.Cesium3DTileset.fromIonAssetId(ASSET_ID, { customShader: shader }).then(moon => {
        if (controller.signal.aborted || expired || !viewer || viewer.isDestroyed()) {
          if (!moon.isDestroyed()) moon.destroy();
          throw new Error('canceled');
        }
        return moon;
      });
      const moon = await bounded(moonPromise);
      viewer.scene.primitives.add(moon);
      measurement.tileset_model_matrix_column_major = C.Matrix4.toArray(moon.modelMatrix);
      measurement.root_transform_column_major = C.Matrix4.toArray(moon.root.transform);
      removeTileFailure = moon.tileFailed.addEventListener(() => { measurement.tile_failure_count++; });
      viewer.camera.setView({ destination: new C.Cartesian3(0, 0, -5000000),
        orientation: { direction: new C.Cartesian3(0, 0, 1), up: new C.Cartesian3(1, 0, 0) } });
      for (let offset = 0; offset < request.probes.length; offset += BATCH_SIZE) {
        if (controller.signal.aborted || expired) throw new Error('canceled');
        const batch = request.probes.slice(offset, offset + BATCH_SIZE);
        byId('measurement-status').textContent = `Measuring probes ${offset + 1} to ${offset + batch.length} of ${request.probes.length}.`;
        const samples = batch.map(probe => new C.Cartesian3(...probe.position_m));
        const returned = await bounded(viewer.scene.clampToHeightMostDetailed(samples, [], QUERY_WIDTH_M));
        if (controller.signal.aborted || expired) throw new Error('canceled');
        returned.forEach((point, index) => {
          const row = measurement.probes[offset + index];
          if (point && [point.x, point.y, point.z].every(Number.isFinite)) {
            row.renderer_position_m = [point.x, point.y, point.z];
            row.status = 'measured';
          } else row.status = 'no_hit';
        });
        measurement.root_computed_transform_column_major = C.Matrix4.toArray(moon.root.computedTransform);
        publish(measurement);
      }
      measurement.status = measurement.probes.every(probe => probe.status === 'measured') ? 'completed' : 'partial_unknown';
    } catch (error) {
      measurement.status = expired ? 'timeout' : controller.signal.aborted ? 'canceled' : 'unavailable';
      measurement.failure_reason = ['missing_scoped_ion_token', 'unsupported_depth_textures'].includes(error.message)
        ? error.message : expired ? 'measurement_budget_exceeded' : controller.signal.aborted ? 'canceled_or_render_failure' : 'asset_or_query_failure';
      // Network errors can contain signed URLs; never copy their messages.
    } finally {
      clearTimeout(timer);
      measurement.elapsed_ms = performance.now() - started;
      measurement.finished_utc = new Date().toISOString();
      publish(measurement);
      removeTileFailure?.();
      removeRenderFailure?.();
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
      viewer = undefined;
      if (shader && !shader.isDestroyed()) shader.destroy();
      active = undefined;
      byId('measure-probes').disabled = false;
      byId('cancel-probes').disabled = true;
      byId('measurement-status').textContent = `Measurement ${measurement.status}. ${measurement.probes.filter(probe => probe.status === 'measured').length} of ${measurement.probes.length} raw mesh positions recorded. Registration was not evaluated.`;
    }
  });
}

if (typeof document !== 'undefined' && document.getElementById('probe-request')) attachDiagnostic();
