import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import study from '../../schemas/study.schema.json' with { type: 'json' };
import result from '../../schemas/study-result.schema.json' with { type: 'json' };
const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv); ajv.addSchema(study); ajv.addSchema(result);
export function validateResearchResult(value) {
  const check = ajv.getSchema(result.$id);
  if (!check(value)) throw new Error(`Scientific response does not match the research contract: ${check.errors[0].instancePath || '/'} ${check.errors[0].message}.`);
  return value;
}
