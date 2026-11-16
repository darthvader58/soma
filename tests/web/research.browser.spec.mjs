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

test('methods disclosure exposes every supplied limitation, assumption and source safely on a narrow keyboard layout',async({page})=>{
 await page.setViewportSize({width:390,height:844});await setup(page);
 let supplied;
 await page.route('**/api/research/analyze',async route=>{
  supplied=researchResult(route.request().postDataJSON());
  supplied.limitations=['Terrain visibility was not evaluated.','Same-epoch geometric directions are not apparent directions.'];
  supplied.provenance.assumptions=['Sun uses panel height.','Future leap seconds remain unknown.'];
  supplied.provenance.kernels=[
   {path:'de421.bsp',sha256:'1'.repeat(64),source_url:'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp'},
   {path:'moon_080317.tf',sha256:'2'.repeat(64),source_url:'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf'},
   {path:'moon_pa_de421_1900-2050.bpc',sha256:'3'.repeat(64),source_url:'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc'},
   {path:'untrusted-test-only',sha256:'4'.repeat(64),source_url:'javascript:alert(1)'},
  ];
  supplied.provenance.spacecraft_sources=[{manifest:{name:'Test archived SPK',path:'test.bsp',sha256:'5'.repeat(64),source_url:'https://naif.jpl.nasa.gov/pub/naif/test-only.bsp',limitations:['Archived geometry grants no relay service.']}}];
  await route.fulfill({json:supplied});
 });
 await page.goto('/');await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 const disclosure=page.locator('#study-methods');const summary=disclosure.locator('summary');
 await expect(disclosure).not.toHaveAttribute('open','');await summary.focus();await expect(summary).toBeFocused();
 expect(await summary.evaluate(node=>getComputedStyle(node).outlineStyle)).not.toBe('none');
 await page.keyboard.press('Enter');await expect(disclosure).toHaveAttribute('open','');
 for(const text of [...supplied.limitations,...supplied.provenance.assumptions,'Archived geometry grants no relay service.',supplied.study_sha256,supplied.provenance.provider,supplied.frame,supplied.provenance.aberration])await expect(disclosure).toContainText(text);
 for(const kernel of supplied.provenance.kernels){await expect(disclosure).toContainText(kernel.path);await expect(disclosure).toContainText(kernel.sha256);}
 await expect(disclosure.locator('a')).toHaveCount(4);
 await expect(disclosure.locator('a[href^="javascript:"]')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const region=page.getByRole('region',{name:'Study methods and sources',exact:true});
 await region.focus();await expect(region).toBeFocused();
 expect(await region.evaluate(node=>node.clientHeight<=180&&node.scrollHeight>node.clientHeight)).toBe(true);
 await page.keyboard.press('PageDown');
 await expect.poll(()=>region.evaluate(node=>node.scrollTop)).toBeGreaterThan(0);
 await summary.focus();await page.keyboard.press('Enter');await expect(disclosure).not.toHaveAttribute('open','');
});

test('real Cesium reference-sphere fallback renders without erasing scientific arrays',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await setup(page,{mockViewer:false});await page.goto('/');await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 await expect(page.locator('#research-map-status')).toContainText(/Reference-sphere context|rendering unavailable/i,{timeout:60000});
 await expect(page.locator('#site-comparison tbody tr')).toHaveCount(3);expect(errors).toEqual([]);
 await page.screenshot({path:'test-results/research-workbench-contract.png',fullPage:true});
});

test('real Cesium global and polar cameras retain the whole context Moon after viewport height changes',async({page})=>{
 await page.setViewportSize({width:1440,height:900});await page.emulateMedia({reducedMotion:'reduce'});
 await setup(page,{mockViewer:false});await page.goto('/');
 await expect(page.locator('#research-map-status')).toContainText('no scoped ion token',{timeout:60000});
 const canvas=page.locator('#research-moon canvas');
 const bodyFits=async()=>{
  const png=(await canvas.screenshot()).toString('base64');
  return page.evaluate(async encoded=>{
   const image=new Image();image.src=`data:image/png;base64,${encoded}`;await image.decode();
   const sample=document.createElement('canvas');sample.width=image.width;sample.height=image.height;
   const context=sample.getContext('2d');context.drawImage(image,0,0);
   const pixels=context.getImageData(0,0,sample.width,sample.height).data;
   let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,count=0;
   for(let y=0;y<sample.height;y++)for(let x=0;x<sample.width;x++){
    const index=(y*sample.width+x)*4;
    if(Math.abs(pixels[index]-88)<=2&&Math.abs(pixels[index+1]-97)<=2&&Math.abs(pixels[index+2]-99)<=2){
     minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);count++;
    }
   }
   return count>1000&&[minX,minY,maxX,maxY].every(Number.isFinite)&&minX>10&&minY>10&&maxX<sample.width-10&&maxY<sample.height-10;
  },png);
 };
 await page.getByRole('button',{name:'Global',exact:true}).click();await expect.poll(bodyFits).toBe(true);
 await page.addStyleTag({content:'.scene-panel{height:260px;min-height:0}.research-moon{min-height:0}'});
 await expect(canvas).toHaveJSProperty('clientHeight',260);await expect.poll(bodyFits).toBe(true);
 await page.getByRole('button',{name:'South pole',exact:true}).click();await expect.poll(bodyFits).toBe(true);
});
