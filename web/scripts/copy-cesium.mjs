import { cp, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const packageRoot = dirname(require.resolve('cesium/package.json'));
const destination = fileURLToPath(new URL('../public/cesium/', import.meta.url));
await mkdir(destination, { recursive: true });
for (const folder of ['Workers', 'Assets', 'ThirdParty', 'Widgets']) {
  await cp(join(packageRoot, 'Build', 'Cesium', folder), join(destination, folder), { recursive: true });
}
for (const notice of ['LICENSE.md', 'ThirdParty.extra.json', 'ThirdParty.json']) {
  await cp(join(packageRoot, notice), join(destination, notice));
}
