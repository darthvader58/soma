import { execFileSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonicalScenarioHash, validateScenario } from '../src/contracts.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const python = process.env.SOMA_PYTHON || resolve(root, '.venv/bin/python');
for (const name of ['synthetic-direct', 'synthetic-relay']) {
  const folder = resolve(root, 'fixtures', name);
  const scenario = JSON.parse(await readFile(resolve(folder, 'scenario.json'), 'utf8'));
  if (!validateScenario(scenario).valid) throw new Error('Invalid fixture scenario');
  const raw = execFileSync(python, ['-m', 'soma', 'environment-fixture', resolve(folder, 'scenario.json'), '--contacts', resolve(folder, 'contacts.json')], { cwd: root, encoding: 'utf8' });
  const artifact = JSON.parse(raw);
  if (artifact.artifact_type !== 'soma_environment_diagnostic' || artifact.artifact_version !== '0.3.0' || artifact.scenario_sha256 !== await canonicalScenarioHash(scenario)) throw new Error('Science artifact identity mismatch');
  await mkdir(resolve(root, 'web/fixtures', name), { recursive: true });
  await writeFile(resolve(root, 'web/fixtures', name, 'environment.json'), raw);
  await mkdir(resolve(root, 'fixtures/phase-3'), { recursive: true });
  await writeFile(resolve(root, 'fixtures/phase-3', `${name}-environment.json`), raw);
  console.log(`${name}: captured Python environment diagnostic; synthetic inputs`);
}
const real = execFileSync(python, ['-m', 'soma', 'environment', resolve(root, 'soma/docs/phase-2/geometry-diagnostic.json'), '--generation-time-model', 'left_sample_piecewise_constant_assumption'], { cwd: root, encoding: 'utf8' });
await mkdir(resolve(root, 'soma/docs/phase-3'), { recursive: true });
await writeFile(resolve(root, 'soma/docs/phase-3/environment-real.json'), real);
await mkdir(resolve(root, 'web/fixtures/recorded-lola'), { recursive: true });
await writeFile(resolve(root, 'web/fixtures/recorded-lola/environment.json'), real);
console.log('Recorded LOLA: captured measured-terrain diagnostic; missing horizons remain unknown');
