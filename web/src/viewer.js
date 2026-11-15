export const MOON_ASSET_ID = 2684829;

// This checks supplied review evidence; it does not perform frame registration.
export function registrationGate(registration, sourceFrame = 'MOON_ME_DE421') {
  const blocked = (reason) => ({ passed: false, reason });
  if (!registration) return blocked('No engine frame registration supplied. Aligned overlays are blocked.');
  if (!registration.version || registration.authority !== 'soma_engine' ||
      registration.source_frame !== sourceFrame || !registration.renderer_frame ||
      registration.asset_id !== MOON_ASSET_ID || !registration.source_manifest_sha256?.match(/^[a-f0-9]{64}$/)) {
    return blocked('Frame registration provenance is incomplete or does not match this scene.');
  }
  if (!Array.isArray(registration.transform_column_major) || registration.transform_column_major.length !== 16 ||
      !registration.transform_column_major.every(Number.isFinite) ||
      !Number.isFinite(registration.tolerance_m) || registration.tolerance_m <= 0 || !registration.tolerance_justification) {
    return blocked('A versioned transform and justified positive registration tolerance are required.');
  }
  const landmarks = registration.landmarks;
  if (!Array.isArray(landmarks) || landmarks.length < 4 ||
      new Set(landmarks.map((point) => point.id)).size !== landmarks.length ||
      landmarks.some((point) => !point.id || !Number.isFinite(point.residual_m) || point.residual_m < 0 ||
        point.residual_m > registration.tolerance_m || !point.source_ref ||
        !Array.isArray(point.renderer_position_m) || point.renderer_position_m.length !== 3 ||
        !point.renderer_position_m.every(Number.isFinite)) ||
      registration.distribution_review?.accepted !== true || !registration.distribution_review?.evidence_ref) {
    return blocked('At least four distinct, well-distributed landmarks must pass the declared tolerance and distribution review.');
  }
  return { passed: true, reason: 'Supplied registration evidence passes the display gate; scientific review remains with the engine team.' };
}

export function isMoonSurfacePick(picked, moonTileset, depthSupported) {
  return Boolean(depthSupported && moonTileset && picked &&
    (picked.primitive === moonTileset || picked.tileset === moonTileset));
}

export async function createMoonViewer(container, {
  scenario, ionToken, onPick = () => {}, onStatus = () => {}, registration,
  loadCesium = () => import('cesium'),
} = {}) {
  let viewer;
  let handler;
  let shader;
  let destroyed = false;
  let healthy = false;
  let sceneFailed = false;
  let displayPick;
  const removeListeners = [];
  const document = container.ownerDocument;
  const gate = registrationGate(registration, scenario?.lander?.frame);
  const report = (state, message) => onStatus({ state, message, overlaysBlocked: true, registration: gate });
  const clearDisplayPick = () => {
    if (displayPick && viewer && !viewer.isDestroyed()) {
      viewer.entities.remove(displayPick);
      viewer.scene.requestRender();
    }
    displayPick = undefined;
  };
  const releaseScene = () => {
    healthy = false;
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
    setScenario(nextScenario) { scenario = nextScenario; clearDisplayPick(); },
    setTime(epoch) {
      if (!viewer || destroyed) return;
      if (typeof epoch !== 'string' || !/^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$/.test(epoch)) {
        report('invalid_time', 'Map time must be a timezone-qualified timestamp.');
        return;
      }
      try {
        viewer.clock.currentTime = cesium.JulianDate.fromIso8601(epoch);
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
    const moon = await cesium.Cesium3DTileset.fromIonAssetId(MOON_ASSET_ID, { customShader: shader });
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
    notice.textContent = 'Cesium Moon · neutral display lighting, not modeled sunlight. Aligned overlays blocked.';
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
        });
        report('display_pick', 'Display point selected. Its elevation and frame are not service-resolved; numerical terrain coverage must be checked by the engine.');
      } catch {
        report('pick_unavailable', 'Surface picking failed. Use the coordinate fields; no analysis point was created.');
      }
    }, cesium.ScreenSpaceEventType.LEFT_CLICK);
    if (scenario?.data_ready_utc) api.setTime(scenario.data_ready_utc);
    report('ready', viewer.scene.pickPositionSupported
      ? 'Moon topography loaded. Picks are display-only. Aligned overlays remain blocked.'
      : 'Moon topography loaded. This device lacks surface depth picking; use coordinate entry.');
  } catch {
    if (sceneFailed || destroyed) return api;
    fallback('Cesium Moon could not load. Check WebGL support, ion asset access, and the network.');
  }
  return api;
}
