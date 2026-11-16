import test from 'node:test';
import assert from 'node:assert/strict';
import { researchResult } from './research-support.mjs';
import { createResearchClient, studyHash, validateStudyInputs, storedSampleAt } from '../../web/src/research-client.js';
const study = () => ({ study_version:'1.0.0', analysis_type:'geometry', frame:'MOON_ME_DE421', reference_radius_m:1737400, surface_model:'reference_sphere', sites:[{id:'custom',name:'Custom',latitude_deg:15.4,longitude_deg_east:12.3,elevation_m:0,antenna_height_m:2,panel_height_m:1}], time:{start_utc:'2026-11-16T00:00:00Z',end_utc:'2026-11-16T06:00:00Z',step_s:120},spacecraft_refs:[] });
const calculated = async request => researchResult(request);
const response = body => ({ok:true,status:200,json:async()=>body});
test('geometry budgets include the final shortened interval, support custom global sites and reject excess work', () => {
 const request=study(); request.time.step_s=130;
 assert.equal(validateStudyInputs(request).epochs,168); assert.deepEqual(validateStudyInputs(request).errors,[]);
 request.sites=Array.from({length:8},(_,i)=>({...request.sites[0],id:`s${i}`})); request.time.step_s=10;
 assert.match(validateStudyInputs(request).errors.join(' '),/5,000/);
 request.sites[0].panel_height_m=NaN; assert.match(validateStudyInputs(request).errors.join(' '),/finite/);
});
test('new arbitrary geometry inputs are posted to Python without fixture matching', async()=>{
 let submitted;
 const client=createResearchClient({fetchImpl:async(url,options)=>{assert.equal(url,'/api/research/analyze');submitted=JSON.parse(options.body);return response(await calculated(submitted));}});
 const request=study(); request.sites[0].longitude_deg_east=74.126;
 const result=await client.analyze(request,{async_available:false});
 assert.deepEqual(submitted,request);assert.equal(result.hash,await studyHash(request));assert.equal(result.jobId,undefined);
});
test('mismatched result request or hash is discarded',async()=>{
 const client=createResearchClient({fetchImpl:async()=>response({...await calculated(study()),study_sha256:'0'.repeat(64)})});
 await assert.rejects(client.analyze(study(),{}),/hash/);
});
test('sync cancellation stops waiting and cannot publish a late scientific result',async()=>{
 let release,started;const pending=new Promise(resolve=>{release=resolve});const entered=new Promise(resolve=>{started=resolve});
 const client=createResearchClient({fetchImpl:async()=>{started();await pending;return response(await calculated(study()));}});
 const run=client.analyze(study(),{});await entered;
 assert.match(await client.cancel(),/synchronous calculation may continue/);release();await assert.rejects(run,{name:'AbortError'});
});
test('capability-negotiated persistent jobs preserve hash, progress and export URL',async()=>{
 const hash=await studyHash(study()),paths=[];let progress;
 const client=createResearchClient({fetchImpl:async(url,options)=>{paths.push([url,options?.method]);if(options?.method==='POST')return response({job_id:'study-1',study_sha256:hash});return response({status:'completed',stage:'done',study_sha256:hash,result:await calculated(study())});}});
 const result=await client.analyze(study(),{service_mode:'persistent',async_available:true},stage=>progress=stage.stage);
 assert.equal(result.jobId,'study-1');assert.equal(progress,'done');assert.equal(client.exportUrl(result.jobId),'/api/research/jobs/study-1/export');assert.equal(paths.length,2);
});
test('canceling a late persistent submission requests deletion and never publishes it',async()=>{
 let release,started;const pending=new Promise(resolve=>{release=resolve});const entered=new Promise(resolve=>{started=resolve});let removed=false;
 const client=createResearchClient({fetchImpl:async(url,options)=>{if(options.method==='DELETE'){removed=true;return response(null);}started();await pending;return response({job_id:'orphan',study_sha256:await studyHash(study())});}});
 const run=client.analyze(study(),{async_available:true});await entered;await client.cancel();release();await assert.rejects(run,{name:'AbortError'});assert.equal(removed,true);
});
test('scientific readout uses stored epochs and does not extrapolate or interpolate classification',()=>{
 const samples=[{epoch_utc:'2026-11-16T00:00:00Z',sun:{elevation_deg:0}},{epoch_utc:'2026-11-16T00:02:00Z',sun:{elevation_deg:2}}];
 assert.equal(storedSampleAt(samples,'2026-11-16T00:01:00Z'),samples[0]);assert.equal(storedSampleAt(samples,'2026-11-15T23:59:59Z'),undefined);assert.equal(storedSampleAt(samples,'2026-11-16T00:02:01Z'),undefined);assert.equal(storedSampleAt(samples,'bad'),undefined);
});
