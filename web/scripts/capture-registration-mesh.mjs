import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';

const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const MAX_BODIES = 512, MAX_BYTES = 128 * 1024 * 1024;
const sourcePath = new URL('../src/registration-diagnostic.js', import.meta.url);
const repoPath = fileURLToPath(new URL('../../', import.meta.url));
const needle = 'viewer.scene.primitives.add(moon);';
const injection = `globalThis.somaTileRecords=[];
 globalThis.somaMeshCaptureInstalled=true;
 moon.tileLoad.addEventListener(tile=>{
   const content=tile.content;
   globalThis.somaTileRecords.push({path:new URL(content.url,location.href).pathname,
     transform:C.Matrix4.toArray(tile.computedTransform),geometric_error_m:tile.geometricError,
     triangles:content.trianglesLength,geometry_bytes:content.geometryByteLength});
 });
 ${needle}`;
let browser, page, onResponse, directory, measurement = null, tiles = [], requestSha256 = null;
let sourceSha256 = null, transformedSourceSha256 = null;
let pageErrors = 0, interceptions = 0, matches = 0, marker = false, bodyCount = 0, totalBytes = 0;
let failure = null;
const records = [], pending = [], bodies = new Map();

try {
  if (process.argv.length !== 4) throw new Error('invalid_arguments');
  directory = resolve(process.argv[3]);
  const repoRelative = relative(repoPath, directory);
  if (!repoRelative || (!repoRelative.startsWith('..' + '/') && repoRelative !== '..' && !isAbsolute(repoRelative))) {
    directory = undefined;
    throw new Error('output_directory_inside_repository');
  }
  const [requestBytes, sourceBytes] = await Promise.all([readFile(process.argv[2]), readFile(sourcePath)]);
  requestSha256 = sha256(requestBytes);
  sourceSha256 = sha256(sourceBytes);
  const request = JSON.parse(requestBytes.toString());
  const target = new URL(process.env.SOMA_REGISTRATION_URL || 'http://127.0.0.1:5173/registration.html');
  if (!['http:', 'https:'].includes(target.protocol)) throw new Error('invalid_registration_url');
  browser = await chromium.launch({
    ...(process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {}),
    args: ['--enable-unsafe-swiftshader'],
  });
  page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
  page.on('pageerror', () => pageErrors++);
  onResponse = response => {
    let path;
    try { path = new URL(response.url()).pathname; } catch { return; }
    if (!/\.(glb|b3dm)$/i.test(path)) return;
    bodyCount++;
    if (bodyCount > MAX_BODIES) {
      records.push({ path, failure: 'body_count_limit' });
      return;
    }
    pending.push((async () => {
      try {
        if (!response.ok()) { records.push({ path, failure: 'http_failure' }); return; }
        const declaredLength = Number(response.headers()['content-length']);
        if (Number.isFinite(declaredLength) && declaredLength > MAX_BYTES) {
          records.push({ path, failure: 'body_size_limit' }); return;
        }
        const body = await response.body();
        if (body.length > MAX_BYTES - totalBytes) {
          records.push({ path, failure: 'total_size_limit' }); return;
        }
        totalBytes += body.length;
        const sha = sha256(body);
        bodies.set(sha, body);
        records.push({ path, sha256: sha, bytes: body.length, magic: body.toString('ascii', 0, 4) });
      } catch { records.push({ path, failure: 'response_body_unavailable' }); }
    })());
  };
  page.on('response', onResponse);
  await page.route('**/src/registration-diagnostic.js*', async route => {
    interceptions++;
    if (new URL(route.request().url()).origin !== target.origin || interceptions !== 1) {
      await route.abort(); return;
    }
    try {
      const response = await route.fetch();
      const source = await response.text();
      transformedSourceSha256 = sha256(Buffer.from(source));
      matches = source.split(needle).length - 1;
      if (!response.ok() || matches !== 1) { await route.abort(); return; }
      await route.fulfill({ response, body: source.replace(needle, injection) });
    } catch { await route.abort().catch(() => {}); }
  });
  await page.goto(target.href);
  if (interceptions !== 1 || matches !== 1) throw new Error('interception_failed');
  await page.locator('#probe-request').fill(JSON.stringify(request));
  await page.locator('#measure-probes').click();
  await page.waitForFunction(() => window.somaRegistrationMeasurement && window.somaRegistrationMeasurement.status !== 'running', undefined, { timeout: 140000 });
  const captured = await page.evaluate(() => ({ measurement: window.somaRegistrationMeasurement,
    tiles: window.somaTileRecords, marker: window.somaMeshCaptureInstalled === true }));
  measurement = captured.measurement;
  tiles = captured.tiles;
  marker = captured.marker;
  page.off('response', onResponse);
  await Promise.all(pending);
  if (measurement.status !== 'completed' || pageErrors || !marker || interceptions !== 1 || matches !== 1 ||
      !Array.isArray(tiles) || !tiles.length || !records.length || records.some(record => record.failure)) {
    throw new Error('capture_assertion_failed');
  }
  await mkdir(directory, { recursive: true });
  for (const [sha, body] of bodies) await writeFile(resolve(directory, `${sha}.bin`), body);
} catch (error) {
  failure = ['invalid_arguments', 'output_directory_inside_repository', 'invalid_registration_url',
    'interception_failed', 'capture_assertion_failed'].includes(error.message) ? error.message : error.name;
  process.exitCode = 1;
} finally {
  if (page && onResponse) page.off('response', onResponse);
  await Promise.allSettled(pending);
  if (browser) await browser.close().catch(() => { failure ||= 'browser_close_failed'; process.exitCode = 1; });
  if (directory) {
    const metadata = { artifact_type: 'soma_renderer_mesh_capture', format_version: '0.1.0',
      status: failure ? 'failed' : 'completed', failure_category: failure, registration_status: 'not_evaluated',
      provenance: { request_sha256: requestSha256, diagnostic_source_sha256: sourceSha256,
        transformed_diagnostic_source_sha256: transformedSourceSha256 },
      interception: { module_requests: interceptions, source_matches: matches, runtime_marker: marker },
      page_errors: pageErrors, limits: { max_bodies: MAX_BODIES, max_bytes: MAX_BYTES },
      total_response_bytes: totalBytes, measurement, tiles, responses: records,
      warning: 'Local diagnostic only; binary tile content must not be committed or redistributed.' };
    try {
      await mkdir(directory, { recursive: true });
      await writeFile(resolve(directory, 'metadata.json'), JSON.stringify(metadata, null, 2) + '\n');
    } catch { console.error(JSON.stringify({ error_category: 'output_write_failed' })); process.exitCode = 1; }
  }
  console.log(JSON.stringify({ status: failure ? 'failed' : 'completed', failure_category: failure,
    page_errors: pageErrors, module_requests: interceptions, response_count: bodyCount, total_response_bytes: totalBytes }));
}
