import { execFileSync } from 'node:child_process';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { validateResult, validateScenario, canonicalScenarioHash } from '../src/contracts.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const python = process.env.SOMA_PYTHON || resolve(root, '.venv/bin/python');
for (const name of ['synthetic-direct', 'synthetic-relay']) {
  const source = resolve(root, 'fixtures', name);
  const destination = resolve(root, 'web/fixtures', name);
  const scenario = JSON.parse(await readFile(resolve(source, 'scenario.json'), 'utf8'));
  const validation = validateScenario(scenario);
  if (!validation.valid) throw new Error(validation.errors.join('; '));
  const result = JSON.parse(execFileSync(python, ['-m', 'soma', 'plan', resolve(source, 'scenario.json')], { cwd: root, encoding: 'utf8' }));
  const resultValidation = validateResult(result);
  if (!resultValidation.valid) throw new Error(resultValidation.errors.join('; '));
  if (result.status !== 'unknown' || result.model_fidelity !== 'not_implemented') throw new Error('Phase 1 capture expected the engine not-implemented result.');
  if (result.scenario_sha256 !== await canonicalScenarioHash(scenario)) throw new Error('Python and browser scenario hashes differ.');
  await mkdir(destination, { recursive: true });
  for (const file of ['scenario.json', 'contacts.json', 'expected.json']) await writeFile(resolve(destination, file), await readFile(resolve(source, file)));
  await writeFile(resolve(destination, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(`${name}: captured engine ${result.status}, ${result.scenario_sha256}`);
}
