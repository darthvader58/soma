import test from 'node:test';
import assert from 'node:assert/strict';
import { plotSegments, scienceViewModel } from '../../web/src/science.js';

test('unknown horizon bands break the displayed profile rather than becoming clear terrain',()=>{
 const segments=plotSegments([{az:0,el:5},{az:10,el:null},{az:20,el:0}],s=>s.az,s=>s.el);
 assert.deepEqual(segments,[[[0,5]],[[20,0]]]);
});
test('directions use the selected height and exact stored timestamp; Earth center stays distinct',()=>{
 const env={tracks:[{target:'EARTH',observer_role:'antenna',samples:[{epoch_utc:'a',classification:'blocked',classification_reason:'terrain'}]},{target:'SUN',observer_role:'panel',samples:[{epoch_utc:'a',direction:{elevation_deg:2}}]}]};
 assert.equal(scienceViewModel(env,'a','antenna').directions[0].target,'Earth center (not a station)');
 assert.equal(scienceViewModel(env,'b','antenna').directions[0].sample,undefined);
 assert.equal(scienceViewModel(env,'a','panel').directions[0].target,'SUN');
});
test('a blocked candidate never becomes a contact or allocation; missing reasons are unknown',()=>{
 const env={contact_decisions:[{candidate_id:'blocked',status:'blocked',reasons:['terrain']},{candidate_id:'missing',status:'unknown'}]};
 const model=scienceViewModel(env,'a'); assert.deepEqual(model.contacts,[]); assert.equal(model.decisions[0].status,'blocked');assert.match(model.decisions[1].reasons[0],/Unknown/);assert.equal(model.allocations,undefined);
});
test('missing solar values remain missing and computed zero stays zero',()=>{
 assert.equal(scienceViewModel({solar_samples:[{epoch_utc:'a',visible_fraction:0}]},'a').solar.visible_fraction,0);
 assert.equal(scienceViewModel({},'a').solar,undefined);
});

test('rendered diagnostic labels provenance, blocked reasons and contact semantics',async()=>{
 class Node {
  constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.classList={add(){}};this._text='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(n=>n.textContent).join(' ');}
  append(...children){this.children.push(...children);}
  replaceChildren(){this.children=[];this._text='';}
  setAttribute(name,value){this.attributes[name]=String(value);}
  addEventListener(){}
 }
 const prior=globalThis.document;globalThis.document={createElement:tag=>new Node(tag),createElementNS:(_,tag)=>new Node(tag)};
 try{
  const {renderScience}=await import('../../web/src/science.js');const root=new Node('div');
  const env={frame:'MOON_ME_DE421',horizons:{panel:{site:{height_m:1,frame:'MOON_ME_DE421',elevation_datum:'height_above_reference_sphere'},bands:[{azimuth_deg:0,elevation_deg:null}]}},provenance:{terrain:[{elevation_sha256:'source-digest'}]},contact_decisions:[{candidate_id:'blocked-test',status:'blocked',reasons:['solid_body_intersection']}],solar_samples:[]};
  const control=renderScience(root,{environment:env,selectedTime:'a'});
  assert.match(root.textContent,/Fixture-backed/);assert.match(root.textContent,/Height: 1 m/);assert.match(root.textContent,/source-digest/);assert.match(root.textContent,/solid_body_intersection/);assert.match(root.textContent,/No usable contacts supplied/);assert.match(root.textContent,/Selected transmissions appear only/);
  control.setTime('b');assert.match(root.textContent,/Selected UTC: b/);control.destroy();assert.equal(root.textContent,'');
 }finally{globalThis.document=prior;}
});
