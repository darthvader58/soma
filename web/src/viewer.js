import { loadRegisteredMoon } from './registered-moon.js';
import { rendererSamplesAtTime } from './renderer-samples.js';

export const MOON_ASSET_ID = 2684829;

export function siteCameraVectors(position) {
  if (!Array.isArray(position) || position.length !== 3 || !position.every(Number.isFinite)) return undefined;
  const length = Math.hypot(...position);
  if (!Number.isFinite(length) || length === 0) return undefined;
  const radial = position.map(v => v / length);
  const axis = Math.abs(radial[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0];
  const dot = axis[0] * radial[0] + axis[1] * radial[1] + axis[2] * radial[2];
  const tangent = axis.map((v, i) => v - dot * radial[i]);
  const tangentLength = Math.hypot(...tangent);
  return { destination: position.map((v, i) => v + 80000 * radial[i]),
    direction: radial.map(v => -v), up: tangent.map(v => v / tangentLength) };
}

// This checks supplied review evidence; it does not perform frame registration.
export function registrationGate(registration, sourceFrame = 'MOON_ME_DE421', position) {
  const blocked = (reason) => ({ passed: false, reason });
  if (!registration) return blocked('No engine frame registration supplied. Aligned overlays are blocked.');
  if ((typeof registration.status === 'string' && registration.status.startsWith('blocked')) ||
      (typeof registration.registration_status === 'string' && registration.registration_status.startsWith('blocked'))) {
    return blocked(registration.reason ?? `Engine renderer registration ${registration.version ?? 'unknown'} is blocked. ${(registration.release_gate?.blockers ?? []).join('; ')}`);
  }
  if (registration.release_gate && registration.release_gate.overlays_allowed !== true) return blocked('Engine release gate prohibits scientific overlays.');
  const region = registration.certified_region;
  if (registration.representation !== 'engine_corrected_mesh' ||
      registration.renderer_frame !== 'SOMA_MOON_ME_DE421_CORRECTED_V1' ||
      !/^[a-f0-9]{64}$/.test(registration.conversion_manifest_sha256 ?? '') ||
      registration.release_gate?.map_registration_passed !== true ||
      !Array.isArray(region?.latitude_deg) || !Array.isArray(region?.longitude_deg_east) ||
      region.latitude_deg.length !== 2 || region.longitude_deg_east.length !== 2 ||
      ![...region.latitude_deg, ...region.longitude_deg_east].every(Number.isFinite) ||
      region.latitude_deg[0] !== -90 || region.latitude_deg[1] !== -87.5 ||
      region.longitude_deg_east[0] !== -180 || region.longitude_deg_east[1] !== 180) {
    return blocked('The corrected Moon scene requires its validated conversion and certified south-polar region.');
  }
  if (registration.scope_application?.site_inside_certified_region === false ||
      (position && (!Number.isFinite(position.latitude_deg) || !Number.isFinite(position.longitude_deg_east) ||
        position.latitude_deg < region.latitude_deg[0] || position.latitude_deg > region.latitude_deg[1] ||
        position.longitude_deg_east < region.longitude_deg_east[0] || position.longitude_deg_east > region.longitude_deg_east[1]))) {
    return blocked('This site is outside the certified south-polar registration region.');
  }
  if (!registration.version || registration.authority !== 'soma_engine' ||
      registration.source_frame !== sourceFrame || !registration.renderer_frame ||
      registration.asset_id !== MOON_ASSET_ID || !registration.source_manifest_sha256?.match(/^[a-f0-9]{64}$/)) {
    return blocked('Frame registration provenance is incomplete or does not match this scene.');
  }
  if (!Array.isArray(registration.transform_column_major) || registration.transform_column_major.length !== 16 ||
      !registration.transform_column_major.every(Number.isFinite) ||
      !registration.transform_column_major.every((value, index) => value === (index % 5 === 0 ? 1 : 0)) ||
      !Number.isFinite(registration.tolerance_m) || registration.tolerance_m <= 0 || registration.tolerance_m > 10 || !registration.tolerance_justification) {
    return blocked('A versioned transform and justified positive registration tolerance are required.');
  }
  const landmarks = registration.landmarks;
  if (!Array.isArray(landmarks) || landmarks.length < 4 ||
      new Set(landmarks.map((point) => point.id)).size !== landmarks.length ||
      landmarks.some((point) => !point.id || !Number.isFinite(point.residual_m) || point.residual_m < 0 ||
        point.residual_m > registration.tolerance_m || !point.source_ref ||
        !Number.isFinite(point.horizontal_grid_resolution_allowance_m) || point.horizontal_grid_resolution_allowance_m < 0 ||
        !Number.isFinite(point.resolution_adjusted_residual_m) || point.resolution_adjusted_residual_m < point.residual_m ||
        point.resolution_adjusted_residual_m > registration.tolerance_m ||
        !Array.isArray(point.renderer_position_m) || point.renderer_position_m.length !== 3 ||
        !point.renderer_position_m.every(Number.isFinite) ||
        !Array.isArray(point.analysis_position_m) || point.analysis_position_m.length !== 3 ||
        !point.analysis_position_m.every(Number.isFinite)) ||
      registration.distribution_review?.accepted !== true || !registration.distribution_review?.evidence_ref) {
    return blocked('At least four distinct, well-distributed landmarks must pass the declared tolerance and distribution review.');
  }
  return { passed: true, reason: 'Frame alignment verified for the tested region from -90° to -87.5° latitude.' };
}

export function isMoonSurfacePick(picked, moonTileset, depthSupported) {
  return Boolean(depthSupported && moonTileset && picked &&
    (picked.primitive === moonTileset || picked.tileset === moonTileset));
}

export async function createMoonViewer(container, {
  scenario, ionToken, onPick = () => {}, onStatus = () => {}, registration,
  loadCesium = () => import('cesium'),
  apiBase = '/api', fetchImpl = globalThis.fetch, loadMoon = loadRegisteredMoon,
  loadRegistration = async () => {
    const response = await fetchImpl(`${apiBase.replace(/\/$/, '')}/moon/registration`);
    if (!response.ok) throw new Error('Moon registration is unavailable');
    return response.json();
  },
} = {}) {
  let viewer;
  let handler;
  let shader;
  let destroyed = false;
  let healthy = false;
  let sceneFailed = false;
  let displayPick;
  let sceneRegistration;
  let conversionSha;
  let resultEntities = [];
  let sampleEntities = [];
  let completedDisplay;
  let selectedEpoch = scenario?.data_ready_utc;
  let hasCompletedDisplay = false;
  let cameraTarget;
  const removeListeners = [];
  const document = container.ownerDocument;
  let gate = registrationGate(registration, scenario?.lander?.frame);
  const report = (state, message) => onStatus({ state, message, overlaysBlocked: !healthy || !gate.passed || !hasCompletedDisplay, cameraAvailable: Boolean(healthy && gate.passed && hasCompletedDisplay && siteCameraVectors(cameraTarget)), registration: gate });
  const clearResult = () => {
    if (viewer && !viewer.isDestroyed()) resultEntities.forEach(entity => viewer.entities.remove(entity));
    resultEntities = [];
    clearSamples();
    completedDisplay = undefined;
    cameraTarget = undefined;
  };
  const clearSamples = () => {
    if (viewer && !viewer.isDestroyed()) sampleEntities.forEach(entity => viewer.entities.remove(entity));
    sampleEntities = [];
  };
  const drawSamples = () => {
    clearSamples();
    if (!healthy || !gate.passed || !completedDisplay) return;
    const sample = rendererSamplesAtTime(completedDisplay, selectedEpoch, scenario?.relay_refs ?? []);
    for (const state of sample.states) sampleEntities.push(viewer.entities.add({
      id: `stored-${state.target}`, position: new cesium.Cartesian3(...state.position),
      description: `${state.provenance_label}. Exact stored UTC ${state.epoch}; ${state.transform_ref}.`,
      point: { pixelSize: 9, color: cesium.Color.WHITE, outlineColor: cesium.Color.BLACK, outlineWidth: 2 },
      label: { text: `${state.target} (stored sample)`, font: '14px sans-serif', fillColor: cesium.Color.WHITE,
        pixelOffset: new cesium.Cartesian2(0, -24), showBackground: true, backgroundColor: cesium.Color.BLACK,
        disableDepthTestDistance: Number.POSITIVE_INFINITY },
    }));
    for (const { contact, allocation, positions } of sample.links) sampleEntities.push(viewer.entities.add({
      id: `contact-${contact.contact_id}`,
      description: `${allocation ? 'Scheduled transmission' : 'Offered contact window only'}: ${contact.sender} to ${contact.receiver}. Endpoint positions at selected source epoch; not a light-time ray path. ${contact.service_provenance}`,
      polyline: { positions: positions.map(position => new cesium.Cartesian3(...position)),
        arcType: cesium.ArcType.NONE, width: allocation ? 4 : 2,
        material: allocation ? cesium.Color.WHITE : new cesium.PolylineDashMaterialProperty({ color: cesium.Color.WHITE, dashLength: 16 }) },
    }));
  };
  const clearDisplayPick = () => {
    if (displayPick && viewer && !viewer.isDestroyed()) {
      viewer.entities.remove(displayPick);
      viewer.scene.requestRender();
    }
    displayPick = undefined;
  };
  const releaseScene = () => {
    healthy = false;
    hasCompletedDisplay = false;
    clearResult();
    clearDisplayPick();
    removeListeners.splice(0).forEach((remove) => remove());
    handler?.destroy();
    handler = undefined;
    if (viewer && !viewer.isDestroyed()) viewer.destroy();
    viewer = undefined;
    if (shader && !shader.isDestroyed()) shader.destroy();
    shader = undefined;
  };
  const fallback = (message) => {
    releaseScene();
    container.replaceChildren();
    const panel = document.createElement('div');
    panel.className = 'moon-fallback';
    const title = document.createElement('h3');
    title.className = 'moon-fallback-title';
    title.textContent = 'Lunar terrain unavailable';
    const copy = document.createElement('p');
    copy.className = 'moon-fallback-copy';
    copy.textContent = `${message} Use the coordinate fields to select a site. The numerical scenario and schedule remain available.`;
    const alignment = document.createElement('p');
    alignment.className = 'moon-fallback-copy';
    alignment.textContent = gate.reason;
    panel.append(title, copy, alignment);
    container.append(panel);
    report('fallback', copy.textContent);
  };
  const api = {
    clearDisplayPick,
    inspectSiteTerrain() {
      if (!healthy || !gate.passed || !hasCompletedDisplay || !cameraTarget) return false;
      const vectors = siteCameraVectors(cameraTarget);
      if (!vectors) return false;
      viewer.camera.setView({
        destination: new cesium.Cartesian3(...vectors.destination),
        orientation: { direction: new cesium.Cartesian3(...vectors.direction), up: new cesium.Cartesian3(...vectors.up) },
      });
      viewer.scene.requestRender();
      return true;
    },
    relayOverview() {
      if (!healthy || !gate.passed || !hasCompletedDisplay || !siteCameraVectors(cameraTarget)) return false;
      viewer.camera.setView({
        destination: new cesium.Cartesian3(0, 0, -5000000),
        orientation: { direction: new cesium.Cartesian3(0, 0, 1), up: new cesium.Cartesian3(1, 0, 0) },
      });
      viewer.scene.requestRender();
      return true;
    },
    setScenario(nextScenario) {
      scenario = nextScenario;
      api.setDisplay(undefined);
      clearDisplayPick();
    },
    setDisplay(display) {
      clearResult();
      hasCompletedDisplay = false;
      if (!healthy) {
        report('scene_unavailable', 'The lunar scene is unavailable. The numerical schedule remains available; scientific overlays are blocked.');
        return;
      }
      if (!display) {
        gate = registrationGate(sceneRegistration, scenario?.lander?.frame, scenario?.lander);
        report(gate.passed ? 'awaiting_result' : 'registration_blocked', gate.passed
          ? `${gate.reason} Waiting for a matching completed job.` : gate.reason);
        return;
      }
      gate = registrationGate(display?.registration, scenario?.lander?.frame, scenario?.lander);
      if (gate.passed && (display.registration.conversion_manifest_sha256 !== conversionSha ||
          display.registration.version !== sceneRegistration?.version)) {
        gate = { passed: false, reason: 'Completed-job registration does not match the loaded Moon conversion.' };
      }
      if (gate.passed && healthy) {
        const points = display.surface_points ?? [];
        if (points.some(point => point.frame !== display.registration.renderer_frame || point.origin !== 'MOON' ||
            point.position_unit !== 'm' || point.epoch !== null || point.time_scale !== 'static' ||
            !point.provenance_label || !Array.isArray(point.position_m) || point.position_m.length !== 3 ||
            !point.position_m.every(Number.isFinite))) {
          gate = { passed: false, reason: 'Declared analysis point has incomplete display provenance.' };
        } else for (const point of points) resultEntities.push(viewer.entities.add({
          id: `analysis-${point.id}`, position: new cesium.Cartesian3(...point.position_m),
          description: point.provenance_label,
          point: { pixelSize: 10, color: cesium.Color.WHITE, outlineColor: cesium.Color.BLACK, outlineWidth: 2 },
          label: { text: 'Engine analysis site', font: '14px sans-serif', fillColor: cesium.Color.WHITE,
            pixelOffset: new cesium.Cartesian2(0, -24), showBackground: true, backgroundColor: cesium.Color.BLACK,
            disableDepthTestDistance: Number.POSITIVE_INFINITY },
        }));
      }
      viewer?.scene.requestRender();
      hasCompletedDisplay = gate.passed;
      completedDisplay = gate.passed ? display : undefined;
      cameraTarget = gate.passed ? display.surface_points?.[0]?.position_m : undefined;
      drawSamples();
      api.relayOverview();
      report(gate.passed ? 'registered' : 'registration_blocked', `${gate.reason}${gate.passed && !display.states?.length ? ' No stored relay trajectory.' : ''}`);
    },
    setTime(epoch) {
      if (!viewer || destroyed) return;
      if (typeof epoch !== 'string' || !/^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$/.test(epoch)) {
        report('invalid_time', 'Map time must be a timezone-qualified timestamp.');
        return;
      }
      try {
        viewer.clock.currentTime = cesium.JulianDate.fromIso8601(epoch);
        selectedEpoch = epoch;
        drawSamples();
        viewer.scene.requestRender();
      } catch { report('invalid_time', 'Map time must be a timezone-qualified timestamp.'); }
    },
    destroy() {
      destroyed = true;
      releaseScene();
      container.replaceChildren();
    },
  };
  let cesium;
  if (typeof ionToken !== 'string' || !ionToken.trim()) {
    fallback('A scoped Cesium ion token with Moon asset access has not been configured.');
    return api;
  }
  report('loading', 'Loading Cesium Moon topography. Aligned overlays are blocked pending engine registration.');
  try {
    globalThis.CESIUM_BASE_URL = '/cesium/';
    cesium = await loadCesium();
    cesium.Ellipsoid.default = cesium.Ellipsoid.MOON;
    cesium.Ion.defaultAccessToken = ionToken.trim();
    viewer = new cesium.Viewer(container, {
      globe: false, baseLayer: false, sceneModePicker: false, baseLayerPicker: false,
      geocoder: false, scene3DOnly: true, sceneMode: cesium.SceneMode.SCENE3D,
      animation: false, timeline: false, homeButton: false, navigationHelpButton: false,
      fullscreenButton: false, selectionIndicator: false, infoBox: false,
      skyBox: false, skyAtmosphere: false, shadows: false, shouldAnimate: false,
      requestRenderMode: true,
    });
    healthy = true;
    removeListeners.push(viewer.scene.renderError.addEventListener(() => {
      sceneFailed = true;
      report('render_failure', 'The lunar scene could not render. Surface selection has been cleared.');
      fallback('The lunar scene could not render; surface picking is unavailable.');
    }));
    viewer.scene.backgroundColor = cesium.Color.fromCssColorString('#101719');
    shader = new cesium.CustomShader({ lightingModel: cesium.LightingModel.UNLIT });
    sceneRegistration = registration ?? await loadRegistration();
    gate = registrationGate(sceneRegistration, scenario?.lander?.frame);
    if (!gate.passed) throw new Error('Registered Moon certificate is blocked');
    const loaded = await loadMoon(cesium, { apiBase, customShader: shader,
      expectedModelSha256: sceneRegistration.conversion_manifest_sha256 });
    const moon = loaded.tileset;
    conversionSha = loaded.conversion.sha256;
    if (conversionSha !== sceneRegistration.conversion_manifest_sha256) {
      if (!moon.isDestroyed()) moon.destroy();
      throw new Error('Moon conversion changed');
    }
    if (!healthy || destroyed || sceneFailed) {
      if (!moon.isDestroyed()) moon.destroy();
      return api;
    }
    viewer.scene.primitives.add(moon);
    viewer.camera.setView({
      destination: new cesium.Cartesian3(0, 0, -5000000),
      orientation: { direction: new cesium.Cartesian3(0, 0, 1), up: new cesium.Cartesian3(1, 0, 0) },
    });
    const notice = document.createElement('p');
    notice.className = 'viewer-notice';
    notice.textContent = 'Cesium Moon · neutral display lighting, not modeled sunlight. Tested registration region: -90° to -87.5° latitude.';
    container.append(notice);
    removeListeners.push(moon.tileFailed.addEventListener(() => {
      report('tile_failure', 'Moon tile request failed. Surface selection has been cleared.');
      fallback('Moon tiles failed to load; surface picking is unavailable.');
    }));
    handler = new cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction(({ position }) => {
      if (!healthy || destroyed || !viewer) return;
      try {
        const scene = viewer.scene;
        if (!isMoonSurfacePick(scene.pick(position), moon, scene.pickPositionSupported)) {
          report('pick_unavailable', 'Select loaded lunar surface, or use coordinate entry. Sky and asset picks do not select a site.');
          return;
        }
        const point = scene.pickPosition(position);
        if (!point) {
          report('pick_unavailable', 'No lunar surface depth is available. Use coordinate entry.');
          return;
        }
        const coordinates = cesium.Cartographic.fromCartesian(point, cesium.Ellipsoid.MOON);
        if (!coordinates || ![coordinates.latitude, coordinates.longitude, coordinates.height].every(Number.isFinite)) {
          report('pick_unavailable', 'No valid lunar surface coordinates are available. Use coordinate entry.');
          return;
        }
        clearDisplayPick();
        // The marker preserves the raw scene pick; no engine-frame position is inferred.
        displayPick = viewer.entities.add({
          id: 'display-only-selected-point',
          position: cesium.Cartesian3.clone(point),
          point: { pixelSize: 10, color: cesium.Color.WHITE, outlineColor: cesium.Color.BLACK, outlineWidth: 2, disableDepthTestDistance: Number.POSITIVE_INFINITY },
          label: { text: 'Display point · not service-resolved', font: '14px sans-serif',
            pixelOffset: new cesium.Cartesian2(0, -24), fillColor: cesium.Color.WHITE,
            showBackground: true, backgroundColor: cesium.Color.BLACK,
            disableDepthTestDistance: Number.POSITIVE_INFINITY },
        });
        scene.requestRender();
        onPick({
          latitude_deg: cesium.Math.toDegrees(coordinates.latitude),
          longitude_deg_east: ((cesium.Math.toDegrees(coordinates.longitude) + 180) % 360 + 360) % 360 - 180,
          display_elevation_m: coordinates.height,
          source: 'cesium_moon_display_pick', service_resolved: false,
          frame_registered: registrationGate(sceneRegistration, scenario?.lander?.frame, {
            latitude_deg: cesium.Math.toDegrees(coordinates.latitude),
            longitude_deg_east: cesium.Math.toDegrees(coordinates.longitude),
          }).passed,
        });
        report('display_pick', 'Display point selected. Rendered elevation is display-only; numerical terrain coverage must be checked by the engine.');
      } catch {
        report('pick_unavailable', 'Surface picking failed. Use the coordinate fields; no analysis point was created.');
      }
    }, cesium.ScreenSpaceEventType.LEFT_CLICK);
    if (scenario?.data_ready_utc) api.setTime(scenario.data_ready_utc);
    report('ready', viewer.scene.pickPositionSupported
      ? `${gate.reason} Picks retain display-only elevation.`
      : 'Moon topography loaded. This device lacks surface depth picking; use coordinate entry.');
  } catch {
    if (sceneFailed || destroyed) return api;
    fallback('Cesium Moon could not load. Check WebGL support, ion asset access, and the network.');
  }
  return api;
}
