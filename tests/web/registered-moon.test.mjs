import test from 'node:test';
import assert from 'node:assert/strict';
import { loadRegisteredMoon } from '../../web/src/registered-moon.js';

const sha = 'a'.repeat(64);
const origin = 'http://127.0.0.1:5173';
function fixture({ status = 'validated_for_region', fail = false, source, wait } = {}) {
  const calls = [];
  const original = async value => ({ delegated: value });
  const Tileset = {
    loadJson: original,
    async fromIonAssetId(id, options) {
      assert.equal(id, 2684829);
      await wait;
      const delegated = await this.loadJson('https://assets.cesium.com/123/tileset.json');
      assert.deepEqual(delegated, { delegated: 'https://assets.cesium.com/123/tileset.json' });
      const root = await this.loadJson({ url: source ?? 'https://assets.cesium.com/2684829/Moon/v6/tileset.json?v=1' });
      if (fail) throw new Error('secret signed URL');
      return { root, options };
    },
  };
  const conversion = {
    model: { asset_id: 2684829, version: '0.1.0', status, asset_revision_path: 'Moon/v6' },
    sha256: sha, representation: status === 'validated_for_region' ? 'engine_corrected_mesh' : 'corrected_mesh_candidate', tile_base: '/api/moon/tiles/',
  };
  return { C: { Cesium3DTileset: Tileset }, original, calls, conversion,
    options: { origin, expectedModelSha256: sha, fetchImpl: async url => {
      calls.push(url);
      return { ok: true, json: async () => url.endsWith('/conversion') ? conversion : {
        root: { content: { uri: `/api/moon/tiles/root.b3dm?conversion=${sha}` }, children: [
          { content: { url: `/api/moon/tiles/child.json?conversion=${sha}` } },
        ] },
      } };
    } },
  };
}

test('loads approved corrected root through Ion and restores the public hook', async () => {
  const f = fixture();
  const shader = {};
  const { tileset, conversion } = await loadRegisteredMoon(f.C, { ...f.options, customShader: shader });
  assert.equal(conversion, f.conversion);
  assert.equal(tileset.options.customShader, shader);
  assert.equal(tileset.root.root.content.uri, `${origin}/api/moon/tiles/root.b3dm?conversion=${sha}`);
  assert.equal(tileset.root.root.children[0].content.url, `${origin}/api/moon/tiles/child.json?conversion=${sha}`);
  assert.deepEqual(f.calls, [`${origin}/api/moon/conversion`, `${origin}/api/moon/tiles/tileset.json?conversion=${sha}`]);
  assert.equal(f.C.Cesium3DTileset.loadJson, f.original);
});

test('candidate requires explicit diagnostic opt-in', async () => {
  const f = fixture({ status: 'candidate_pending_corrected_scene_landmarks' });
  await assert.rejects(loadRegisteredMoon(f.C, f.options));
  assert.equal(f.calls.length, 1);
  await loadRegisteredMoon(f.C, { ...f.options, allowCandidate: true, expectedModelSha256: undefined });
});

test('production requires matching checksum and supported model', async () => {
  for (const mutation of [
    f => { f.options.expectedModelSha256 = undefined; },
    f => { f.options.expectedModelSha256 = 'b'.repeat(64); },
    f => { f.conversion.model.version = '2'; },
    f => { f.conversion.model.asset_id = 123; },
  ]) {
    const f = fixture(); mutation(f);
    await assert.rejects(loadRegisteredMoon(f.C, f.options));
    assert.equal(f.calls.length, 1);
    assert.equal(f.C.Cesium3DTileset.loadJson, f.original);
  }
});

test('restores hook and sanitizes errors on Ion failure', async () => {
  const f = fixture({ fail: true });
  await assert.rejects(loadRegisteredMoon(f.C, f.options), error => !error.message.includes('secret'));
  assert.equal(f.C.Cesium3DTileset.loadJson, f.original);
});

test('rejects an unrecognized Ion source and foreign API origin', async () => {
  const f = fixture({ source: 'https://assets.cesium.com.evil.test/2684829/Moon/v6/tileset.json' });
  await assert.rejects(loadRegisteredMoon(f.C, f.options));
  assert.equal(f.calls.length, 1);
  await assert.rejects(loadRegisteredMoon(f.C, { ...f.options, apiBase: 'https://example.com/api' }));
  assert.equal(f.C.Cesium3DTileset.loadJson, f.original);
});

test('rejects concurrent loads without disturbing the active hook', async () => {
  let release;
  const wait = new Promise(resolve => { release = resolve; });
  const f = fixture({ wait });
  const loading = loadRegisteredMoon(f.C, f.options);
  await assert.rejects(loadRegisteredMoon(f.C, f.options), /already in progress/);
  release();
  await loading;
  assert.equal(f.C.Cesium3DTileset.loadJson, f.original);
});
