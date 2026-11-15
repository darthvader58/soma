import test from 'node:test';
import assert from 'node:assert/strict';
import { comparisonViewModel } from '../../web/src/comparison.js';
import { readFileSync } from 'node:fs';
const scenario={data_ready_utc:'2026-11-14T00:00:00Z',deadline_utc:'2026-11-15T00:00:00Z',data_volume:{value:100,unit:'MiB'},hardware_profile_ref:'h',profiles:{hardware:[{id:'h',battery:{initial_energy_wh:80}}],relays:[],stations:[]},relay_refs:[],station_refs:[],route_families:['direct_to_earth']};
test('date comparison states unchanged absolute deadline; battery and deadline changes are flagged',()=>{
 const b=structuredClone(scenario); b.data_ready_utc='2026-11-14T01:00:00Z';
 let model=comparisonViewModel([{scenario},{scenario:b}]);assert.equal(model.dateChanged,true);assert.equal(model.deadlineChanged,false);
 b.deadline_utc='2026-11-16T00:00:00Z';b.profiles.hardware[0].battery.initial_energy_wh=60;
 model=comparisonViewModel([{scenario},{scenario:b}]);assert.equal(model.deadlineChanged,true);assert.equal(model.differences.find(d=>d.label.startsWith('Initial battery')).changed,true);
});
test('comparison never derives absent wait, energy, route or reserve from schedule histories',()=>{
 const model=comparisonViewModel([{scenario,result:{status:'unknown',allocations:[{}],energy_history:[{stored_energy_wh:80}],storage_intervals:[{}]}}]);
 for(const key of ['route','wait','energy','minimumReserve','completion'])assert.equal(model.rows[0][key],undefined);
});
test('fields outside the frozen result contract are ignored',()=>{
 const model=comparisonViewModel([{scenario,result:{route:'fiction',route_family:'fiction',wait_time_s:0,communications_energy_wh:0,minimum_reserve_wh:0,limiting_reason:'fiction',provenance:{reason:'unresolved'}}}]);
 for(const key of ['route','wait','energy','minimumReserve'])assert.equal(model.rows[0][key],undefined);
 assert.equal(model.rows[0].limitingReason,'unresolved');
});

test('comparison reads only a matching replayed Python summary and preserves computed zero', () => {
 const read = name => JSON.parse(readFileSync(new URL(`../../web/fixtures/synthetic-relay/${name}.json`, import.meta.url), 'utf8'));
 const entry = { scenario: read('scenario'), result: read('result'), summary: read('summary') };
 let row = comparisonViewModel([entry]).rows[0];
 assert.match(row.route, /synthetic-lunar-relay/);
 assert.equal(row.wait, entry.summary.mean_relay_wait_s);
 assert.equal(row.energy, entry.summary.lander_communications_energy_wh);
 entry.summary.mean_relay_wait_s = 0;
 assert.equal(comparisonViewModel([entry]).rows[0].wait, 0);
 entry.summary.scenario_sha256 = '0'.repeat(64);
 assert.equal(comparisonViewModel([entry]).rows[0].energy, undefined);
 entry.summary.scenario_sha256 = entry.result.scenario_sha256;
 entry.summary.replay.passed = false;
 assert.equal(comparisonViewModel([entry]).rows[0].route, undefined);
});
