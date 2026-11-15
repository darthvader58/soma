const activeLoads = new WeakSet();
const ASSET_ID = 2684829;

function trustedRoot(resource) {
  try {
    const url = new URL(typeof resource === 'string' ? resource : resource.url);
    return url.protocol === 'https:' && url.hostname.endsWith('.cesium.com')
      && url.pathname.endsWith('/2684829/Moon/v6/tileset.json')
      && [...url.searchParams.keys()].every(key => key === 'v');
  } catch { return false; }
}

function absoluteContent(document, origin) {
  function visit(tile) {
    for (const content of [tile.content, ...(tile.contents ?? [])]) {
      if (!content) continue;
      for (const key of ['uri', 'url']) {
        if (typeof content[key] === 'string' && content[key].startsWith('/api/moon/tiles/')) {
          content[key] = new URL(content[key], origin).href;
        }
      }
    }
    for (const child of tile.children ?? []) visit(child);
  }
  if (!document?.root) throw new Error('Registered Moon root is missing');
  visit(document.root);
  return document;
}

export async function loadRegisteredMoon(C, {
  apiBase = '/api', assetId = ASSET_ID, customShader, allowCandidate = false,
  expectedModelSha256, fetchImpl = globalThis.fetch, origin = globalThis.location?.origin,
} = {}) {
  const Tileset = C.Cesium3DTileset;
  if (activeLoads.has(Tileset)) throw new Error('Registered Moon loading is already in progress');
  if (assetId !== ASSET_ID) throw new Error('Unsupported registered Moon asset');
  const base = new URL(`${apiBase.replace(/\/$/, '')}/moon/`, origin);
  if (base.origin !== new URL(origin).origin) throw new Error('Registered Moon requires the application origin');
  activeLoads.add(Tileset);
  const original = Tileset.loadJson;
  let installed = false;
  try {
    const response = await fetchImpl(new URL('conversion', base).href);
    if (!response.ok) throw new Error('Registered Moon conversion is unavailable');
    const conversion = await response.json();
    const model = conversion.model;
    if (model?.asset_id !== ASSET_ID || model.version !== '0.1.0'
        || model.asset_revision_path !== 'Moon/v6'
        || !(conversion.representation === 'engine_corrected_mesh'
          || (allowCandidate && conversion.representation === 'corrected_mesh_candidate'))
        || conversion.tile_base !== '/api/moon/tiles/'
        || !/^[a-f0-9]{64}$/.test(conversion.sha256 ?? '')) {
      throw new Error('Unsupported registered Moon conversion');
    }
    if ((!expectedModelSha256 && !allowCandidate)
        || (expectedModelSha256 && conversion.sha256 !== expectedModelSha256)) {
      throw new Error('Registered Moon conversion checksum is not approved');
    }
    if (model.status !== 'validated_for_region'
        && !(allowCandidate && model.status === 'candidate_pending_corrected_scene_landmarks')) {
      throw new Error('Registered Moon landmarks have not passed validation');
    }
    let rootLoaded = false;
    Tileset.loadJson = async function (resource, ...args) {
      if (!trustedRoot(resource)) return original.call(this, resource, ...args);
      rootLoaded = true;
      const rootUrl = new URL('tiles/tileset.json', base);
      rootUrl.searchParams.set('conversion', conversion.sha256);
      const rootResponse = await fetchImpl(rootUrl.href);
      if (!rootResponse.ok) throw new Error('Registered Moon mesh is unavailable');
      return absoluteContent(await rootResponse.json(), origin);
    };
    installed = true;
    const tileset = await Tileset.fromIonAssetId(assetId, { customShader });
    if (!rootLoaded) {
      tileset.destroy?.();
      throw new Error('Registered Moon source revision was not recognized');
    }
    return { tileset, conversion };
  } catch {
    // Ion failures can contain credentials in signed resource URLs.
    throw new Error('Registered Moon could not load its approved display conversion');
  } finally {
    if (installed) Tileset.loadJson = original;
    activeLoads.delete(Tileset);
  }
}
