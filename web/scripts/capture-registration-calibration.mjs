import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';

const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const factory = 'C.Cesium3DTileset.fromIonAssetId(ASSET_ID, { customShader: shader })';
const tokenDeclaration = 'const token = import.meta.env?.VITE_CESIUM_ION_TOKEN;';
const sourcePath = new URL('../src/registration-diagnostic.js', import.meta.url);
let browser;
let outputPath = process.argv[4];
let pageErrors = 0, consoleErrors = 0, interceptions = 0, factoryMatches = 0, tokenMatches = 0, blockedRequests = 0;
let blockedAssetRequests = 0;
const blockedRequestDetails = [];
let transformedSourceSha256 = null, marker = false, result = null, failure = null;
let requestSha256 = null, planesSha256 = null, sourceSha256 = null, planes = null;

try {
  if (process.argv.length !== 5) throw new Error('invalid_arguments');
  const [requestBytes, planesBytes, sourceBytes] = await Promise.all([
    readFile(process.argv[2]), readFile(process.argv[3]), readFile(sourcePath),
  ]);
  requestSha256 = sha256(requestBytes);
  planesSha256 = sha256(planesBytes);
  sourceSha256 = sha256(sourceBytes);
  const request = JSON.parse(requestBytes.toString());
  planes = JSON.parse(planesBytes.toString());
  if (!Array.isArray(planes.positions) || planes.positions.length < 9 || planes.positions.length % 3 ||
      !planes.positions.every(Number.isFinite) || !Array.isArray(planes.indices) ||
      !planes.indices.length || planes.indices.length % 3 || planes.positions.length / 3 > 65536 ||
      !planes.indices.every(index => Number.isInteger(index) && index >= 0 && index < planes.positions.length / 3) ||
      !Number.isFinite(planes.expected_height_m)) throw new Error('invalid_planes');

  const replacement = `Promise.resolve((()=>{
    globalThis.somaCalibrationSurfaceOnly=true;
    const points=new Float64Array(${JSON.stringify(planes.positions)});
    const geometry=new C.Geometry({attributes:{position:new C.GeometryAttribute({componentDatatype:C.ComponentDatatype.DOUBLE,componentsPerAttribute:3,values:points})},indices:new Uint16Array(${JSON.stringify(planes.indices)}),primitiveType:C.PrimitiveType.TRIANGLES,boundingSphere:C.BoundingSphere.fromVertices(points)});
    const primitive=new C.Primitive({geometryInstances:new C.GeometryInstance({geometry,attributes:{color:C.ColorGeometryInstanceAttribute.fromColor(C.Color.WHITE)}}),appearance:new C.PerInstanceColorAppearance({flat:true,closed:false}),asynchronous:false});
    primitive.root={transform:C.Matrix4.IDENTITY,computedTransform:C.Matrix4.IDENTITY};primitive.tileFailed=new C.Event();
    return primitive;
  })())`;
  const target = new URL(process.env.SOMA_REGISTRATION_URL || 'http://127.0.0.1:5173/registration.html');
  if (!['http:', 'https:'].includes(target.protocol)) throw new Error('invalid_registration_url');
  browser = await chromium.launch({
    ...(process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {}),
    args: ['--enable-unsafe-swiftshader'],
  });
  const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
  page.on('pageerror', () => pageErrors++);
  page.on('console', message => { if (message.type() === 'error') consoleErrors++; });
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    const assetRequest = /\/v1\/assets(?:\/|$)|(?:^|\/)2684829(?:\/|$)|\.(?:b3dm|glb)$/i.test(url.pathname);
    if (url.origin !== target.origin || assetRequest) {
      blockedRequests++;
      if (assetRequest) blockedAssetRequests++;
      blockedRequestDetails.push({ origin: url.origin, pathname: url.pathname,
        category: assetRequest ? 'asset_endpoint_or_tile' : 'unexpected_cross_origin' });
      await route.abort();
      return;
    }
    await route.continue();
  });
  await page.route('**/src/registration-diagnostic.js*', async route => {
    interceptions++;
    if (new URL(route.request().url()).origin !== target.origin || interceptions !== 1) {
      blockedRequests++;
      await route.abort();
      return;
    }
    try {
      const response = await route.fetch();
      const source = await response.text();
      transformedSourceSha256 = sha256(Buffer.from(source));
      factoryMatches = source.split(factory).length - 1;
      tokenMatches = source.split(tokenDeclaration).length - 1;
      if (!response.ok() || factoryMatches !== 1 || tokenMatches !== 1) {
        await route.abort();
        return;
      }
      const injected = source.replace(factory, replacement).replace(tokenDeclaration, "const token = 'synthetic-calibration-only';");
      await route.fulfill({ response, body: injected });
    } catch {
      await route.abort().catch(() => {});
    }
  });
  await page.goto(target.href);
  if (interceptions !== 1 || factoryMatches !== 1 || tokenMatches !== 1 || blockedRequests) {
    throw new Error('calibration_assertion_failed');
  }
  await page.locator('#probe-request').fill(JSON.stringify(request));
  await page.locator('#measure-probes').click();
  await page.waitForFunction(() => window.somaRegistrationMeasurement && window.somaRegistrationMeasurement.status !== 'running', undefined, { timeout: 140000 });
  marker = await page.evaluate(() => window.somaCalibrationSurfaceOnly === true);
  result = await page.evaluate(() => window.somaRegistrationMeasurement);
  if (interceptions !== 1 || factoryMatches !== 1 || tokenMatches !== 1 || !marker || blockedRequests || blockedAssetRequests ||
      result.status !== 'completed' || pageErrors || consoleErrors) throw new Error('calibration_assertion_failed');
  result.asset_id = null;
  result.artifact_type = 'soma_synthetic_calibration_measurement';
  result.warnings = ['Synthetic planar geometry tests the renderer instrument only; no Moon asset or frame registration was evaluated.'];
} catch (error) {
  failure = ['invalid_arguments', 'invalid_planes', 'invalid_registration_url', 'calibration_assertion_failed'].includes(error.message)
    ? error.message : error.name;
  process.exitCode = 1;
} finally {
  if (browser) await browser.close().catch(() => { failure ||= 'browser_close_failed'; process.exitCode = 1; });
  if (outputPath) {
    const artifact = {
      artifact_type: 'soma_renderer_instrument_calibration', format_version: '0.1.0',
      status: failure ? 'failed' : 'completed', failure_category: failure,
      registration_status: 'not_evaluated', asset_id: null,
      provenance: { request_sha256: requestSha256, planes_sha256: planesSha256,
        diagnostic_source_sha256: sourceSha256, transformed_diagnostic_source_sha256: transformedSourceSha256 },
      interception: { module_requests: interceptions, factory_matches: factoryMatches, token_matches: tokenMatches,
        runtime_marker: marker, blocked_requests: blockedRequests, blocked_asset_requests: blockedAssetRequests,
        blocked_request_details: blockedRequestDetails },
      page_errors: pageErrors, console_errors: consoleErrors,
      synthetic_geometry: planes, measurement: result,
      warning: 'Synthetic instrument diagnostic only; no Moon asset or registration approval.',
    };
    try { await writeFile(outputPath, JSON.stringify(artifact, null, 2) + '\n'); }
    catch { console.error(JSON.stringify({ error_category: 'output_write_failed' })); process.exitCode = 1; }
  }
  console.log(JSON.stringify({ status: failure ? 'failed' : 'completed', failure_category: failure,
    module_requests: interceptions, blocked_requests: blockedRequests, page_errors: pageErrors, console_errors: consoleErrors }));
}
