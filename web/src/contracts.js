import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import common from '../../schemas/common.schema.json' with { type: 'json' };
import scenario from '../../schemas/scenario.schema.json' with { type: 'json' };
import contact from '../../schemas/contact.schema.json' with { type: 'json' };
import allocation from '../../schemas/allocation.schema.json' with { type: 'json' };
import result from '../../schemas/result.schema.json' with { type: 'json' };
import state from '../../schemas/state.schema.json' with { type: 'json' };

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
for (const schema of [common, scenario, contact, allocation, result, state]) ajv.addSchema(schema);

function validate(schema, value) {
  const check = ajv.getSchema(schema.$id);
  const valid = check(value);
  return { valid, errors: valid ? [] : check.errors.map(error => `${error.instancePath || '/'} ${error.message}${error.params.missingProperty ? `: ${error.params.missingProperty}` : ''}`) };
}

export const validateScenario = value => validate(scenario, value);
export const validateResult = value => validate(result, value);

function jsonString(value) {
  if (!value.isWellFormed()) throw new Error('Scenario strings must not contain lone Unicode surrogates.');
  return JSON.stringify(value);
}

// RFC 8785: UTF-16 key ordering, ECMAScript number spelling, and UTF-8 bytes.
export function canonicalScenarioJSON(value) {
  if (value === null || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'string') return jsonString(value);
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || Math.abs(value) > Number.MAX_SAFE_INTEGER) throw new Error('Scenario numbers must be finite and within the interoperable safe-number domain.');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalScenarioJSON).join(',')}]`;
  if (typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
    const keys = Object.keys(value).sort();
    return `{${keys.map(key => `${jsonString(key)}:${canonicalScenarioJSON(value[key])}`).join(',')}}`;
  }
  throw new Error('Scenario contains a non-JSON value.');
}

export async function canonicalScenarioHash(value) {
  const bytes = new TextEncoder().encode(canonicalScenarioJSON(value));
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}
