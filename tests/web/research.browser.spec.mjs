import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import { researchCatalog, researchCapabilities, researchResult } from './research-support.mjs';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');

async function setup(page, { mockViewer = true, ready = true } = {}) {
 const requests=[];
 await page.route('**/api/research/catalog', route=>route.fulfill({json:researchCatalog}));
 await page.route('**/api/research/capabilities', route=>route.fulfill({json:{...researchCapabilities,ready}}));
 await page.route('**/api/research/analyze',async route=>{const body=route.request().postDataJSON();requests.push(body);await route.fulfill({json:researchResult(body)});});
 if(mockViewer) await page.route('**/src/workbench-viewer.js',route=>route.fulfill({contentType:'text/javascript',body:`
 export async function createWorkbenchViewer(container,{onStatus}){
  onStatus('Test-only display adapter. No terrain or scientific accuracy claimed.');
  container.innerHTML='<div class="research-map-fallback"><h2>Test-only lunar scene</h2><p>Contract test display adapter.</p></div>';
  return {setCatalog(sites){container.dataset.siteCount=sites.length},setSelection(ids,id){container.dataset.selected=id},setResult(result){container.dataset.spacecraft=result?.spacecraft?.length??0},setTime(epoch){container.dataset.epoch=epoch},camera(mode){container.dataset.camera=mode},setLayers(layers){container.dataset.layers=JSON.stringify(layers)}};
 }` }));
 return requests;
}

test('default workbench submits multi-site Python study, shares time and preserves exact JSON result', async({page})=>{
 const requests=await setup(page);await page.goto('/');
 await expect(page.getByRole('heading',{name:'Lunar research workbench',exact:true})).toBeVisible();
 await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 expect(requests[0].sites).toHaveLength(3);expect(requests[0].spacecraft_refs).toEqual(['lro-test-only']);
 await expect(page.locator('#site-comparison tbody tr')).toHaveCount(3);
 await expect(page.getByRole('link',{name:'Coordinate source 1'})).toHaveAttribute('href','https://example.org/test-only');
 const first=await page.locator('#selected-utc').textContent();
 await page.getByRole('button',{name:'Next stored sample'}).click();
 await expect(page.locator('#selected-utc')).not.toHaveText(first);
 await expect(page.locator('#research-moon')).toHaveAttribute('data-epoch',requests[0].time.start_utc.replace('00:00:00','03:00:00'));
 await expect(page.locator('#site-readout')).toContainText('03:00:00');
 await page.getByRole('button',{name:'Follow spacecraft',exact:true}).click();
 await expect(page.locator('#research-moon')).toHaveAttribute('data-camera','follow');
 await page.getByRole('button',{name:'Inspect stored state',exact:true}).click();
 await expect(page.locator('#site-readout')).toContainText('Velocity X / Y / Z');
 await expect(page.locator('#inspector-heading')).toHaveText('Spacecraft inspector');
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Result JSON',exact:true}).click();
 const body=JSON.parse(await readFile(await(await pending).path(),'utf8'));expect(body).toEqual(researchResult(requests[0]));
 await page.getByRole('button',{name:'Save alternative',exact:true}).click();await expect(page.locator('#saved-alternatives')).toContainText('Saved calculated alternatives (1)');
 await expect(page.getByRole('link',{name:'Delivery archive',exact:true})).toHaveAttribute('href','/?mode=archive');
});

test('custom location and distinct equipment heights create changed real request; old result is visibly stale',async({page})=>{
 const requests=await setup(page);await page.goto('/');await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 await page.getByRole('button',{name:'+ Custom site',exact:true}).click();
 await page.getByLabel('Latitude (° N)',{exact:true}).fill('14.123');await page.getByLabel('Longitude (° E)',{exact:true}).fill('-72.456');
 await page.getByLabel('Antenna height (m)',{exact:true}).fill('3.5');await page.getByLabel('Panel height (m)',{exact:true}).fill('1.25');
 await expect(page.locator('#research-status')).toContainText('previous study');await expect(page.getByRole('button',{name:'Result JSON',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Run analysis',exact:true}).click();await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 expect(requests.at(-1).sites.at(-1)).toMatchObject({latitude_deg:14.123,longitude_deg_east:-72.456,antenna_height_m:3.5,panel_height_m:1.25});
 await expect(page.locator('#site-count')).toHaveText('4 / 8');await expect(page.locator('#site-quality')).toContainText('panel height (1.25 m)');
});

test('stopping synchronous work explains cancellation boundary and late response cannot publish',async({page})=>{
 await setup(page,{ready:false});let release,entered;const gate=new Promise(resolve=>release=resolve);const started=new Promise(resolve=>entered=resolve);
 await page.route('**/api/research/analyze',async route=>{const body=route.request().postDataJSON();entered();await gate;try{await route.fulfill({json:researchResult(body)});}catch{}});
 await page.goto('/');await expect(page.locator('#site-count')).toHaveText('3 / 8');
 await page.getByRole('button',{name:'Run analysis',exact:true}).click();await started;
 await page.getByRole('button',{name:'Stop waiting',exact:true}).click();
 await expect(page.locator('#research-status')).toContainText('may continue on the server');release();
 await expect(page.locator('#selected-utc')).toHaveText('No calculated time samples');
 await expect(page.getByRole('button',{name:'Result JSON',exact:true})).toBeDisabled();
});

test('service error stays unavailable and does not generate fixture output',async({page})=>{
 await setup(page,{ready:false});await page.route('**/api/research/analyze',route=>route.fulfill({status:503,json:{detail:'Kernel source is not available'}}));
 await page.goto('/');await page.getByRole('button',{name:'Run analysis',exact:true}).click();
 await expect(page.locator('#research-status')).toContainText('Kernel source is not available');
 await expect(page.locator('#research-status')).toContainText('No replacement result');await expect(page.getByRole('button',{name:'Result JSON',exact:true})).toBeDisabled();
});

test('narrow layout retains inputs, charts, keyboard focus and avoids horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await setup(page);await page.goto('/');await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByLabel('Start UTC',{exact:true}).focus();await expect(page.getByLabel('Start UTC',{exact:true})).toBeFocused();
 await expect(page.locator('#geometry-chart svg')).toBeVisible();
});

test('real Cesium reference-sphere fallback renders without erasing scientific arrays',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await setup(page,{mockViewer:false});await page.goto('/');await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 await expect(page.locator('#research-map-status')).toContainText(/Reference-sphere context|rendering unavailable/i,{timeout:60000});
 await expect(page.locator('#site-comparison tbody tr')).toHaveCount(3);expect(errors).toEqual([]);
 await page.screenshot({path:'test-results/research-workbench-contract.png',fullPage:true});
});
