const scenarios = import.meta.glob('../fixtures/physical-south-pole/*/scenario.json', { eager: true, import: 'default' });
const results = import.meta.glob('../fixtures/physical-south-pole/*/result.json', { eager: true, import: 'default' });
const resultTexts = import.meta.glob('../fixtures/physical-south-pole/*/result.json', { eager: true, query: '?raw', import: 'default' });
const summaries = import.meta.glob('../fixtures/physical-south-pole/*/summary.json', { eager: true, import: 'default' });
const displays = import.meta.glob('../fixtures/physical-south-pole/*/display-data.json', { eager: true, query: '?url', import: 'default' });
const packages = import.meta.glob('../fixtures/physical-south-pole/*/run.zip', { eager: true, query: '?url', import: 'default' });
const names = { 'direct-ready': 'LOLA · Direct delivery', 'direct-later': 'LOLA · Later direct (infeasible)', 'relay-later': 'LOLA · Later lunar relay' };

export const physicalFixtures = ['direct-ready', 'direct-later', 'relay-later'].map(name => {
  const prefix = `../fixtures/physical-south-pole/${name}/`;
  return { name: names[name], scenario: scenarios[`${prefix}scenario.json`], result: results[`${prefix}result.json`],
    resultText: resultTexts[`${prefix}result.json`], summary: summaries[`${prefix}summary.json`],
    displayUrl: displays[`${prefix}display-data.json`], packageUrl: packages[`${prefix}run.zip`], contacts: [] };
});
