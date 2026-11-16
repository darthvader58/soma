import { readFile, mkdir, copyFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// Copy the engine-authored artifacts byte for byte; never regenerate a schedule here.
for (const name of ['direct-ready', 'direct-later', 'relay-later']) {
  const source = fileURLToPath(new URL(`../../fixtures/physical-south-pole/${name}/run.zip`, import.meta.url));
  const target = fileURLToPath(new URL(`../fixtures/physical-south-pole/${name}/`, import.meta.url));
  await mkdir(target, { recursive: true });
  execFileSync('unzip', ['-o', source, 'scenario.json', 'result.json', 'summary.json', 'display-data.json', 'renderer-registration.json', '-d', target]);
  await copyFile(source, `${target}/run.zip`);
  const result = JSON.parse(await readFile(`${target}/result.json`, 'utf8'));
  console.log(`${name}: ${result.status}; ${result.allocations.length} engine allocations`);
}
