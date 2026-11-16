import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');
test.use({ reducedMotion: 'reduce' });

async function settleGlobalView(page) {
 await page.evaluate(async()=>{for(let frame=0;frame<4;frame++)await new Promise(requestAnimationFrame)});
 await page.getByRole('button',{name:'Global',exact:true}).click();
 await page.evaluate(async()=>{for(let frame=0;frame<4;frame++)await new Promise(requestAnimationFrame)});
}

test('prepared real DE421 and LRO sources calculate new custom global study through the browser',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const scientific=[];page.on('response',async response=>{if(response.url().endsWith('/research/analyze')&&response.ok())scientific.push(await response.json());});
 await page.goto('/');await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 await expect(page.locator('.site-row')).toHaveCount(15);
 await expect(page.getByLabel('Start UTC',{exact:true})).toHaveValue(/^2026-04-01T00:00(?::00)?$/);
 await expect(page.getByRole('button',{name:'Follow spacecraft',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Inspect stored state',exact:true}).click();
 await expect(page.locator('#site-readout')).toContainText('Velocity X / Y / Z');
 const first=await page.locator('#site-readout').textContent();
 await page.getByRole('button',{name:'Next stored sample'}).click();await expect(page.locator('#site-readout')).not.toHaveText(first);
 await page.getByRole('button',{name:'Follow spacecraft',exact:true}).click();
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();await page.getByRole('button',{name:'Pause',exact:true}).click();
 await page.getByRole('button',{name:'+ Custom site',exact:true}).click();
 await page.getByLabel('Latitude (° N)',{exact:true}).fill('21.1827');await page.getByLabel('Longitude (° E)',{exact:true}).fill('68.2714');
 await page.getByLabel('Panel height (m)',{exact:true}).fill('1.7');
 await page.getByRole('button',{name:'Run analysis',exact:true}).click();await expect(page.locator('#research-status')).toContainText('Calculated in Python');
 await expect(page.locator('#site-comparison tbody tr')).toHaveCount(4);
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Result JSON',exact:true}).click();
 const downloaded=JSON.parse(await readFile(await(await pending).path(),'utf8'));
 expect(downloaded.request.sites.at(-1)).toMatchObject({latitude_deg:21.1827,longitude_deg_east:68.2714,panel_height_m:1.7});
 expect(downloaded.provenance.provider).toContain('SpiceGeometry');expect(downloaded.spacecraft[0].input_class).toBe('reconstructed_ephemeris');
 expect(downloaded.spacecraft[0].samples[0].position_m).not.toEqual(downloaded.spacecraft[0].samples[1].position_m);
 expect(downloaded.study_sha256).not.toEqual(scientific[0].study_sha256);
 expect(errors).toEqual([]);
 await page.getByRole('button',{name:'Global',exact:true}).click();
 await page.screenshot({path:'test-results-research-live/real-research-workbench.png',fullPage:true});
 await page.setViewportSize({width:1440,height:900});
 await settleGlobalView(page);
 for(const appearance of ['light','dark']){
  await page.getByLabel('Appearance',{exact:true}).selectOption(appearance);
  await expect(page.locator('html')).toHaveAttribute('data-theme',appearance);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  await page.getByRole('button',{name:'Run analysis',exact:true}).screenshot({path:`test-results-research-live/dashboard-${appearance}-run-button.png`});
  await page.screenshot({path:`test-results-research-live/dashboard-${appearance}-desktop.png`,fullPage:true});
 }
 await page.setViewportSize({width:390,height:844});
 await settleGlobalView(page);
 for(const appearance of ['light','dark']){
  await page.getByLabel('Appearance',{exact:true}).selectOption(appearance);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  await page.screenshot({path:`test-results-research-live/dashboard-${appearance}-mobile.png`,fullPage:true});
 }
});
