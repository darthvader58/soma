import { loadRegisteredMoon } from './registered-moon.js';
import { isMoonSurfacePick, siteCameraVectors, registrationGate } from './viewer.js';
import { storedSampleAt } from './research-client.js';
import { rendererSamplesAtTime } from './renderer-samples.js';

export function observeMoonContent(tileset, onReady) {
  let revealed = false;
  return tileset.tileVisible.addEventListener(() => {
    if (revealed) return;
    revealed = true;
    onReady();
  });
}

export async function createWorkbenchViewer(container, {
  ionToken, apiBase = '/api', onStatus = () => {}, onSelect = () => {}, onPick = () => {},
  loadCesium = () => import('cesium'), fetchImpl = globalThis.fetch,
} = {}) {
  let C, viewer, moon, handler, shader, result, selectedId, epoch, destroyed = false;
  let resizeObserver, resizeFrame, removeMoonReadiness, cameraMode = 'global';
  let catalog = [], selected = new Set(), siteEntities = [], resultEntities = [], directions = [], spacecraftEntities = new Map();
  let labels = true, paths = true, bodyDirections = true;
  let delivery, deliveryGate, deliverySamples = [];
  const report = message => onStatus(message);
  const validPosition = value => Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
  const cartesian = value => new C.Cartesian3(...value);
  // The marker lift only prevents display z-fighting; it never changes study coordinates or equipment heights.
  const contextMarker = value => cartesian(value.map(component => component * (1 + 10000 / Math.hypot(...value))));
  const clear = entities => { entities.forEach(entity => viewer?.entities.remove(entity)); entities.length = 0; };
  function deliveryLabels() {
    if (!delivery) return;
    const network = cameraMode === 'network';
    for (const [id, node] of spacecraftEntities) {
      if (!node.entity.label) continue;
      node.entity.label.show = labels && (network ? id === 'EARTH' : !delivery.scenario.station_refs.includes(id));
      if (id === 'EARTH') node.entity.label.text = 'Earth network · educational stations';
      else if (delivery.scenario.relay_refs.includes(id)) node.entity.label.text = `${id} · synthetic relay`;
    }
    for (const entity of siteEntities) if (entity.id.startsWith('delivery-surface-') && entity.label) {
      entity.label.show = labels;
      entity.label.text = network ? 'Moon · lander' : `${delivery.scenario.lander.id} · lander`;
    }
  }
  function drawDeliveryTime() {
    clear(deliverySamples);
    if (!viewer || !delivery || !deliveryGate?.passed) return;
    const sample = rendererSamplesAtTime(delivery.display, epoch, [delivery.scenario.lander.id, ...delivery.scenario.relay_refs, ...delivery.scenario.station_refs, 'EARTH']);
    for (const state of sample.states) {
      const node = spacecraftEntities.get(state.target);
      if (node) { node.entity.position = cartesian(state.position); node.entity.show = true; }
    }
    for (const [id, node] of spacecraftEntities) node.entity.show = sample.states.some(state => state.target === id);
    for (const { contact, allocation, positions } of sample.links) deliverySamples.push(viewer.entities.add({
      id: `delivery-link-${contact.contact_id}`, description: `${allocation ? 'Allocated source transmission' : 'Usable contact window, not selected delivery'}: ${contact.sender} to ${contact.receiver}. Exact endpoint positions at source epoch; not a light-time ray path.`,
      polyline: { positions: positions.map(cartesian), arcType: C.ArcType.NONE, width: allocation ? 4 : 2,
        material: allocation ? C.Color.fromCssColorString('#edb965') : new C.PolylineDashMaterialProperty({ color: C.Color.WHITE, dashLength: 16 }) },
    }));
    deliveryLabels();
    viewer.scene.requestRender();
  }
  function fitContextCamera(mode, animate = false) {
    viewer.resize();
    const aspect = viewer.scene.canvas.clientWidth / viewer.scene.canvas.clientHeight;
    const verticalHalfAngle = viewer.camera.frustum.fovy / 2;
    const halfAngle = Math.min(verticalHalfAngle, Math.atan(Math.tan(verticalHalfAngle) * aspect));
    if (!Number.isFinite(halfAngle) || halfAngle <= 0) return;
    // This fits the display body to the viewport; it does not alter any scientific position.
    const distance = 1750000 / Math.sin(halfAngle) * 1.18;
    const axis = mode === 'polar' ? new C.Cartesian3(0, 0, -1) : new C.Cartesian3(4.7, -1.3, 1.3);
    const outward = C.Cartesian3.normalize(axis, new C.Cartesian3());
    const destination = C.Cartesian3.multiplyByScalar(outward, distance, new C.Cartesian3());
    const direction = C.Cartesian3.negate(outward, new C.Cartesian3());
    const view = { destination, orientation: { direction, up: mode === 'polar' ? C.Cartesian3.UNIT_X : C.Cartesian3.UNIT_Z } };
    viewer.camera.cancelFlight();
    if (animate && !globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) viewer.camera.flyTo({ ...view, duration: 0.7 });
    else viewer.camera.setView(view);
    viewer.scene.requestRender();
  }
  function drawSites() {
    if (!viewer || destroyed) return;
    clear(siteEntities);
    for (const site of catalog) {
      if (result?.sites.some(item => item.id === site.id)) continue;
      if (!validPosition(site.position_m)) continue;
      const chosen = selected.has(site.id), inspecting = selectedId === site.id;
      siteEntities.push(viewer.entities.add({
        id: `catalog-${site.id}`, position: contextMarker(site.position_m), properties: { siteId: site.id },
        point: { pixelSize: inspecting ? 12 : chosen ? 9 : 6, color: chosen ? C.Color.fromCssColorString('#edb965') : C.Color.WHITE,
          outlineColor: C.Color.BLACK, outlineWidth: 2 },
        label: { text: site.name, show: labels && (inspecting || chosen), font: '13px sans-serif',
          pixelOffset: new C.Cartesian2(0, -19), fillColor: C.Color.WHITE, showBackground: true,
          backgroundColor: C.Color.fromCssColorString('#172022'), distanceDisplayCondition: new C.DistanceDisplayCondition(0, 1e8) },
      }));
    }
    for (const site of result?.sites ?? []) {
      if (!validPosition(site.position_m)) continue;
      siteEntities.push(viewer.entities.add({
        id: `evaluated-${site.id}`, position: contextMarker(site.position_m), properties: { siteId: site.id },
        point: { pixelSize: selectedId === site.id ? 14 : 11, color: C.Color.TRANSPARENT,
          outlineColor: C.Color.fromCssColorString('#edb965'), outlineWidth: 3 },
        label: { text: `${site.name} · evaluated`, show: labels, font: '13px sans-serif',
          pixelOffset: new C.Cartesian2(0, -19), fillColor: C.Color.WHITE, showBackground: true,
          backgroundColor: C.Color.fromCssColorString('#172022'), distanceDisplayCondition: new C.DistanceDisplayCondition(0, 1e8) },
      }));
    }
    for (const point of delivery?.display.surface_points ?? []) {
      if (!deliveryGate?.passed || !validPosition(point.position_m)) continue;
      siteEntities.push(viewer.entities.add({ id: `delivery-surface-${point.id}`, position: contextMarker(point.position_m), properties: { siteId: point.id },
        description: `${point.provenance_label} Marker uses a display-only lift; the numerical ground position is unchanged.`,
        point: { pixelSize: 13, color: C.Color.TRANSPARENT, outlineColor: C.Color.fromCssColorString('#edb965'), outlineWidth: 3 },
        label: { text: `${point.id} · delivery lander`, show: labels, font: '13px sans-serif', fillColor: C.Color.WHITE,
          pixelOffset: new C.Cartesian2(0, -20), showBackground: true, backgroundColor: C.Color.BLACK },
      }));
    }
    viewer.scene.requestRender();
  }
  function drawDirections() {
    if (!viewer || destroyed) return;
    clear(directions);
    if (!result || !bodyDirections) return;
    const site = selectedId ? result.sites.find(item => item.id === selectedId) : result.sites[0];
    const sample = storedSampleAt(site?.samples, epoch);
    if (!sample || !validPosition(site.position_m)) return;
    for (const [key, title] of [['sun', 'Sun direction'], ['earth', 'Earth center direction']]) {
      const vector = sample[key]?.direction_moon_fixed;
      if (!validPosition(vector)) continue;
      const endpoint = site.position_m.map((value, index) => value + vector[index] * 900000);
      directions.push(viewer.entities.add({ polyline: { positions: [cartesian(site.position_m), cartesian(endpoint)], width: 2,
        material: new C.PolylineDashMaterialProperty({ color: key === 'sun' ? C.Color.fromCssColorString('#edb965') : C.Color.WHITE }) } }));
      directions.push(viewer.entities.add({ position: cartesian(endpoint), label: { text: `${title} · schematic`, font: '12px sans-serif', fillColor: C.Color.WHITE,
        showBackground: true, backgroundColor: C.Color.BLACK, pixelOffset: new C.Cartesian2(0, -8) } }));
    }
    viewer.scene.requestRender();
  }
  const api = {
    setCatalog(sites) { catalog = sites ?? []; drawSites(); },
    setSelection(ids, id) { selected = new Set(ids); selectedId = id; drawSites(); drawDirections(); },
    setLayers(next) { labels = next.labels; paths = next.paths; bodyDirections = next.directions; drawSites(); for (const item of spacecraftEntities.values()) item.path.show = paths; drawDirections(); },
    setResult(next) {
      delivery = undefined; deliveryGate = undefined; clear(deliverySamples);
      result = next;
      if (!viewer || destroyed) return;
      const wasFollowing = Boolean(viewer.trackedEntity);
      viewer.trackedEntity = undefined;
      clear(resultEntities); clear(directions); spacecraftEntities.clear();
      drawSites();
      if (!result) return;
      for (const craft of result.spacecraft ?? []) {
        if (!craft.samples?.length || craft.samples.some(sample => !validPosition(sample.position_m))) continue;
        const position = new C.SampledPositionProperty(C.ReferenceFrame.FIXED);
        position.forwardExtrapolationType = C.ExtrapolationType.NONE;
        position.backwardExtrapolationType = C.ExtrapolationType.NONE;
        for (const sample of craft.samples) position.addSample(C.JulianDate.fromIso8601(sample.epoch_utc), cartesian(sample.position_m));
        position.setInterpolationOptions({ interpolationDegree: 1, interpolationAlgorithm: C.LinearApproximation });
        const entity = viewer.entities.add({ id: `spacecraft-${craft.id}`, position,
          point: { pixelSize: 10, color: C.Color.WHITE, outlineColor: C.Color.fromCssColorString('#edb965'), outlineWidth: 2 },
          label: { text: craft.name, font: '14px sans-serif', fillColor: C.Color.WHITE, pixelOffset: new C.Cartesian2(0, -20), showBackground: true, backgroundColor: C.Color.BLACK },
        });
        const path = viewer.entities.add({ polyline: { show: paths, positions: craft.samples.map(sample => cartesian(sample.position_m)), width: 1.5,
          material: C.Color.fromCssColorString('#edb965').withAlpha(0.7) } });
        spacecraftEntities.set(craft.id, { entity, path: path.polyline }); resultEntities.push(entity, path);
      }
      api.setTime(result.epochs_utc[0]);
      if (wasFollowing) api.camera('global');
    },
    setDelivery(next) {
      api.setResult(undefined);
      delivery = next;
      if (!viewer || destroyed || !delivery) return;
      deliveryGate = registrationGate(delivery.display.registration, delivery.scenario.lander.frame, delivery.scenario.lander);
      drawSites();
      if (!deliveryGate.passed) { report(`Delivery overlays blocked: ${deliveryGate.reason} The exact schedule and resources remain available.`); return; }
      for (const id of [...delivery.scenario.relay_refs, 'EARTH', ...delivery.scenario.station_refs]) {
        const history = (delivery.display.renderer_states ?? []).filter(state => state.target === id && state.frame === delivery.display.registration.renderer_frame && state.position_unit === 'm');
        if (!history.length) continue;
        const profile = delivery.scenario.profiles.relays.find(item => item.id === id);
        const entity = viewer.entities.add({ id: `delivery-node-${id}`, position: cartesian(history[0].position), properties: { siteId: id },
          point: { pixelSize: 10, color: C.Color.WHITE, outlineColor: C.Color.fromCssColorString('#edb965'), outlineWidth: 2 },
          label: { text: id === 'EARTH' ? 'Earth · stored center, network stations nearby' : `${id} · ${profile?.trajectory.kind ?? 'educational ground station'}`, font: '12px sans-serif', fillColor: C.Color.WHITE, showBackground: true, backgroundColor: C.Color.BLACK },
        });
        const path = viewer.entities.add({ polyline: { show: paths, positions: history.map(state => cartesian(state.position)), width: 1.5, material: C.Color.fromCssColorString('#edb965').withAlpha(0.6) } });
        spacecraftEntities.set(id, { entity, path: path.polyline }); resultEntities.push(entity, path);
      }
      api.setTime(delivery.scenario.data_ready_utc);
      report('Delivery scene: solid amber segments are allocated source transmissions; dashed segments are usable contacts only. Endpoints require exact stored states. Earth transfers without supplied endpoints stay in the text schedule.');
    },
    setTime(next) { epoch = next; if (!viewer || destroyed) return; viewer.clock.currentTime = C.JulianDate.fromIso8601(next); if (delivery) drawDeliveryTime(); else drawDirections(); viewer.scene.requestRender(); },
    camera(mode) {
      if (!viewer || destroyed) return;
      cameraMode = mode;
      viewer.trackedEntity = undefined;
      deliveryLabels();
      if (mode === 'follow') { const item = delivery ? spacecraftEntities.get(delivery.scenario.relay_refs[0]) : spacecraftEntities.values().next().value; if (item) viewer.trackedEntity = item.entity; return; }
      if (mode === 'network' || mode === 'moon-network') {
        if (!delivery || !deliveryGate?.passed) { report('Network view requires a registered Python delivery result.'); return; }
        const sample = rendererSamplesAtTime(delivery.display, epoch, [delivery.scenario.lander.id, ...delivery.scenario.relay_refs, ...(mode === 'network' ? [...delivery.scenario.station_refs, 'EARTH'] : [])]);
        const points = [...sample.states.map(state => state.position), ...(delivery.display.surface_points ?? []).map(point => point.position_m)].filter(validPosition);
        if (points.length < 2) { report(`Network view unavailable at ${epoch}: no matching stored endpoint states. Select an exact engine sample or transfer.`); return; }
        const sphere = C.BoundingSphere.fromPoints(points.map(cartesian)); sphere.radius *= 1.15;
        viewer.camera.cancelFlight();
        const aspect = viewer.scene.canvas.clientWidth / viewer.scene.canvas.clientHeight;
        const halfAngle = Math.min(viewer.camera.frustum.fovy / 2, Math.atan(Math.tan(viewer.camera.frustum.fovy / 2) * aspect));
        const distance = sphere.radius / Math.sin(halfAngle);
        // View across the network baseline so the Moon and Earth do not overlap on screen.
        const axis = C.Cartesian3.normalize(Math.hypot(sphere.center.x, sphere.center.y) > 1 ? new C.Cartesian3(-sphere.center.y, sphere.center.x, 0) : C.Cartesian3.UNIT_X, new C.Cartesian3());
        viewer.camera.setView({ destination: new C.Cartesian3(sphere.center.x + axis.x * distance, sphere.center.y + axis.y * distance, sphere.center.z + axis.z * distance), orientation: { direction: C.Cartesian3.negate(axis, new C.Cartesian3()), up: C.Cartesian3.UNIT_Z } });
        report(mode === 'network' ? `Network at ${epoch}. Moon and Earth endpoints retain Python distances; the Moon appears small at this scale. Marker sizes are for legibility. Solid amber: allocated transfer; dashed: usable contact only.` : `Lunar hop at ${epoch}. Lander and synthetic relay retain their Python positions. Solid amber: allocated transfer; dashed: usable contact only. Earth-bound hops use Earth network view.`);
        viewer.scene.requestRender(); return;
      }
      if (mode === 'site') {
        const site = delivery?.display.surface_points.find(item => item.id === delivery.scenario.lander.id) ?? result?.sites.find(item => item.id === selectedId) ?? catalog.find(item => item.id === selectedId);
        const vectors = siteCameraVectors(site?.position_m);
        if (vectors) {
          const view = { destination: cartesian(vectors.destination), orientation: { direction: cartesian(vectors.direction), up: cartesian(vectors.up) } };
          if (globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) viewer.camera.setView(view);
          else viewer.camera.flyTo({ ...view, duration: 0.7 });
        }
        return;
      }
      fitContextCamera(mode, true);
    },
    destroy() { destroyed = true; removeMoonReadiness?.(); resizeObserver?.disconnect(); if (resizeFrame) cancelAnimationFrame(resizeFrame); handler?.destroy(); viewer?.destroy(); shader?.destroy(); },
  };
  try {
    globalThis.CESIUM_BASE_URL = '/cesium/';
    C = await loadCesium(); C.Ellipsoid.default = C.Ellipsoid.MOON;
    if (ionToken?.trim()) C.Ion.defaultAccessToken = ionToken.trim();
    viewer = new C.Viewer(container, { globe: false, baseLayer: false, sceneModePicker: false, baseLayerPicker: false, geocoder: false,
      scene3DOnly: true, sceneMode: C.SceneMode.SCENE3D, animation: false, timeline: false, homeButton: false, navigationHelpButton: false,
      fullscreenButton: false, selectionIndicator: false, infoBox: false, skyBox: false, skyAtmosphere: false, shadows: false,
      shouldAnimate: false, requestRenderMode: true });
    viewer.scene.backgroundColor = C.Color.fromCssColorString('#101719');
    const sphere = viewer.scene.primitives.add(new C.Primitive({
      asynchronous: false,
      geometryInstances: new C.GeometryInstance({ geometry: new C.EllipsoidGeometry({
        radii: new C.Cartesian3(1737400, 1737400, 1737400),
        vertexFormat: C.PerInstanceColorAppearance.VERTEX_FORMAT,
      }), attributes: { color: C.ColorGeometryInstanceAttribute.fromColor(C.Color.fromCssColorString('#586163')) } }),
      appearance: new C.PerInstanceColorAppearance({ flat: true, translucent: false, closed: true }),
    }));
    fitContextCamera('global');
    resizeObserver = new ResizeObserver(() => {
      if (resizeFrame) cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => {
        resizeFrame = undefined;
        if (!destroyed && (cameraMode === 'global' || cameraMode === 'polar')) fitContextCamera(cameraMode);
      });
    });
    resizeObserver.observe(container);
    drawSites();
    report('Reference-sphere context. Loading Moon tiles; global terrain registration is not certified.');
    viewer.scene.renderError.addEventListener(() => report('Moon rendering failed. Scientific samples and charts remain available.'));
    handler = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction(({ position }) => {
      const picked = viewer.scene.pick(position);
      const id = picked?.id?.properties?.siteId?.getValue();
      if (id) { onSelect(id); return; }
      if (!isMoonSurfacePick(picked, moon, viewer.scene.pickPositionSupported)) return;
      const point = viewer.scene.pickPosition(position);
      if (!point) return;
      const coord = C.Cartographic.fromCartesian(point, C.Ellipsoid.MOON);
      if (coord) onPick({ latitude_deg: C.Math.toDegrees(coord.latitude), longitude_deg_east: C.Math.toDegrees(coord.longitude) });
    }, C.ScreenSpaceEventType.LEFT_CLICK);
    if (!ionToken?.trim()) { report('Moon tiles unavailable: no scoped ion token. Reference-sphere context only.'); return api; }
    try {
      const response = await fetchImpl(`${apiBase}/moon/registration`);
      if (!response.ok) throw new Error('Registration unavailable');
      const registration = await response.json();
      if (!registrationGate(registration, 'MOON_ME_DE421').passed) throw new Error('Registration blocked');
      shader = new C.CustomShader({ lightingModel: C.LightingModel.UNLIT });
      const loaded = await loadRegisteredMoon(C, { apiBase, customShader: shader, expectedModelSha256: registration.conversion_manifest_sha256 });
      if (destroyed) { loaded.tileset.destroy(); return api; }
      moon = loaded.tileset;
      let loadFailed = false;
      removeMoonReadiness = observeMoonContent(moon, () => queueMicrotask(() => {
        if (destroyed || loadFailed) return;
        sphere.show = false;
        report('Cesium Moon · neutral lighting. Global sites are reference-sphere context; tested terrain registration covers -90° to -87.5° only.');
        viewer.scene.requestRender();
      }));
      viewer.scene.primitives.add(moon);
      moon.tileFailed.addEventListener(() => { loadFailed = true; report('Some Moon tiles failed. Context markers, stored samples and charts remain available.'); sphere.show = true; });
      report('Reference-sphere context while Moon tiles load. Neutral display lighting; global terrain registration is not certified.');
      viewer.scene.requestRender();
    } catch { report('Moon tiles unavailable. Reference-sphere context only; scientific samples and charts remain available.'); }
  } catch {
    container.innerHTML = '<div class="research-map-fallback"><h2>Moon rendering unavailable</h2><p>Use the object list, numerical inspector and UTC charts. No terrain is inferred from this view.</p></div>';
    report('Moon rendering unavailable. Numerical analysis remains usable.');
  }
  return api;
}
