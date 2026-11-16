const artifacts = import.meta.glob('../fixtures/demo-constraints/*/{scenario,result,summary}.json', { eager: true, import: 'default' });
const resultTexts = import.meta.glob('../fixtures/demo-constraints/*/result.json', { eager: true, query: '?raw', import: 'default' });
const displays = import.meta.glob('../fixtures/demo-constraints/*/display-data.json', { eager: true, query: '?url', import: 'default' });
const packages = import.meta.glob('../fixtures/demo-constraints/*/run.zip', { eager: true, query: '?url', import: 'default' });
const evidence = import.meta.glob('../fixtures/demo-constraints/demonstration.json', { eager: true, import: 'default' });
export const constraintFixtures = ['battery-low', 'service-off'].flatMap(caseId => {
  const prefix = `../fixtures/demo-constraints/${caseId}/`;
  if (!artifacts[`${prefix}scenario.json`]) return [];
  return [{ caseId, controlledEvidence: Object.values(evidence)[0]?.cases?.find(item => item.case_id === caseId), name: caseId === 'battery-low' ? 'Synthetic · Battery constraint' : 'Synthetic · Service constraint',
    scenario: artifacts[`${prefix}scenario.json`], result: artifacts[`${prefix}result.json`],
    resultText: resultTexts[`${prefix}result.json`], summary: artifacts[`${prefix}summary.json`],
    displayUrl: displays[`${prefix}display-data.json`], packageUrl: packages[`${prefix}run.zip`], contacts: [] }];
});
