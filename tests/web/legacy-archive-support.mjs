const localHosts = new Set(['127.0.0.1', 'localhost', '[::1]']);

export function isLocalArchiveTestURL(value) {
  const url = new URL(value);
  return url.protocol === 'http:' && localHosts.has(url.hostname);
}

const archiveDocument = `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>SOMA legacy delivery regression harness</title>
</head>
<body>
  <a class="skip-link" href="#scenario">Skip to scenario</a>
  <div id="app"></div>
  <script type="module" src="/src/archive.js"></script>
</body>
</html>`;

export async function installLegacyArchiveHarness(page, { baseURL }) {
  if (!isLocalArchiveTestURL(baseURL)) {
    throw new Error('Legacy delivery UI regression tests require a local Vite server; the public demo only serves the research dashboard.');
  }
  const origin = new URL(baseURL).origin;
  // Fulfilled documents need explicit loopback access for Vite's development WebSocket.
  await page.context().grantPermissions(['local-network-access'], { origin });
  await page.route(url => url.origin === origin && url.pathname === '/' && url.searchParams.get('mode') === 'archive', async route => {
    const request = route.request();
    if (!request.isNavigationRequest() || request.resourceType() !== 'document') {
      await route.continue();
      return;
    }
    await route.fulfill({ contentType: 'text/html', body: archiveDocument });
  });
}
