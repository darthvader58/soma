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
 await expect(page.locator('html')).toHaveCSS('color-scheme','dark');
 await expect(page.getByRole('button',{name:'Global',exact:true})).toHaveAttribute('aria-pressed','true');
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
 await expect(page.getByRole('button',{name:'Selected site',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('#result-handoff-text')).toContainText('Paused at');
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Result JSON',exact:true}).click();
 const downloaded=JSON.parse(await readFile(await(await pending).path(),'utf8'));
 expect(downloaded.request.sites.at(-1)).toMatchObject({latitude_deg:21.1827,longitude_deg_east:68.2714,panel_height_m:1.7});
 expect(downloaded.provenance.provider).toContain('SpiceGeometry');expect(downloaded.spacecraft[0].input_class).toBe('reconstructed_ephemeris');
 expect(downloaded.spacecraft[0].samples[0].position_m).not.toEqual(downloaded.spacecraft[0].samples[1].position_m);
 expect(downloaded.study_sha256).not.toEqual(scientific[0].study_sha256);
 await page.getByLabel('Sun / Earth schematics',{exact:true}).uncheck();
 await page.getByLabel('Stored spacecraft path',{exact:true}).uncheck();
 await page.getByLabel('Selected site labels',{exact:true}).uncheck();
 await page.getByRole('button',{name:/^Apollo 11/}).click();
 const canvas=page.locator('#research-moon canvas');
 await canvas.screenshot({path:'test-results-research-live/custom-evaluated-marker.png'});
 const markerPixel=async()=>{
  const encoded=(await canvas.screenshot({scale:'css'})).toString('base64');
  return page.evaluate(async value=>{
   const image=new Image();image.src=`data:image/png;base64,${value}`;await image.decode();
   const surface=document.createElement('canvas');surface.width=image.width;surface.height=image.height;
   const context=surface.getContext('2d');context.drawImage(image,0,0);const pixels=context.getImageData(0,0,surface.width,surface.height).data;
   let target=null,nearest=Infinity;
   for(let y=Math.floor(surface.height*.25);y<surface.height*.75;y++)for(let x=Math.floor(surface.width*.25);x<surface.width*.75;x++){
    const i=(y*surface.width+x)*4;
    if(pixels[i]>180&&pixels[i+1]>=130&&pixels[i+1]<=215&&pixels[i+2]>=50&&pixels[i+2]<=150){
     const distance=(x-surface.width/2)**2+(y-surface.height/2)**2;
     if(distance<nearest){nearest=distance;target={x,y};}
    }
   }
   return target;
  },encoded);
 };
 await expect.poll(markerPixel,{timeout:10000}).not.toBeNull();
 const target=await markerPixel();await canvas.click({position:target});
 await expect(page.locator('#site-inspector h3').first()).toHaveText('Custom site 1');
 await expect(page.locator('#site-quality')).toContainText('Terrain visibility');
 expect(errors).toEqual([]);
 await page.getByRole('button',{name:'Global',exact:true}).click();
 await page.screenshot({path:'test-results-research-live/real-research-workbench.png',fullPage:true});
 await page.setViewportSize({width:1440,height:900});
 await settleGlobalView(page);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await expect(page.locator('.workspace-title p')).toHaveText('Selenographic Observation and Mission Atlas');
 await page.screenshot({path:'test-results-research-live/dark-workbench-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await settleGlobalView(page);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await expect(page.locator('.workspace-title p')).toBeVisible();
 await page.screenshot({path:'test-results-research-live/dark-workbench-mobile.png',fullPage:true});
});
