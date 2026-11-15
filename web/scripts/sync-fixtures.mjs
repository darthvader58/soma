import { execFileSync } from 'node:child_process';
import { readFile, writeFile, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
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
  const temporary = await mkdtemp(resolve(tmpdir(), 'soma-capture-'));
  let run, resultText, archive, summaryText;
  try {
    execFileSync(python, ['-m', 'soma', 'run', resolve(source, 'scenario.json'), '--output-dir', temporary], { cwd: root, encoding: 'utf8' });
    run = JSON.parse(await readFile(resolve(temporary, 'run.json'), 'utf8'));
    resultText = await readFile(resolve(temporary, 'result.json'), 'utf8');
    summaryText = await readFile(resolve(temporary, 'summary.json'), 'utf8');
    archive = await readFile(resolve(temporary, 'run.zip'));
  } finally { await rm(temporary, { recursive: true, force: true }); }
  const result = JSON.parse(resultText);
  const resultValidation = validateResult(result);
  if (!resultValidation.valid) throw new Error(resultValidation.errors.join('; '));
  if (result.status === 'feasible_under_assumptions' && run.validation?.passed !== true) throw new Error('A feasible capture requires independent replay.');
  if (result.scenario_sha256 !== await canonicalScenarioHash(scenario)) throw new Error('Python and browser scenario hashes differ.');
  await mkdir(destination, { recursive: true });
  for (const file of ['scenario.json', 'contacts.json', 'expected.json']) await writeFile(resolve(destination, file), await readFile(resolve(source, file)));
  await writeFile(resolve(destination, 'result.json'), resultText);
  await writeFile(resolve(destination, 'summary.json'), summaryText);
  await writeFile(resolve(destination, 'run.zip'), archive);
  const evidence = resolve(root, 'fixtures/phase-4', name);
  await mkdir(evidence, { recursive: true });
  await writeFile(resolve(evidence, 'run.json'), `${JSON.stringify(run, null, 2)}\n`);
  await writeFile(resolve(evidence, 'result.json'), resultText);
  await writeFile(resolve(evidence, 'summary.json'), summaryText);
  await writeFile(resolve(evidence, 'run.zip'), archive);
  console.log(`${name}: captured engine ${result.status}, ${result.solver_status}, replay ${run.validation?.passed ?? 'not_applicable'}`);
}
