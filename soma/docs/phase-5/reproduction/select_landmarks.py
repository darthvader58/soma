"""Freeze terrain-feature locations before querying the renderer."""
from pathlib import Path
import argparse, json, math
import numpy as np, rasterio
from rasterio.windows import Window
from pyproj import Transformer
from soma.terrain.dem import POLAR_CRS

parser=argparse.ArgumentParser(description='Select four terrain peaks using source rasters only')
parser.add_argument('height20');parser.add_argument('count20');parser.add_argument('height5');parser.add_argument('count5');parser.add_argument('output',type=Path)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
with rasterio.open(args.height20) as dataset:height20=dataset.read(1)
with rasterio.open(args.count20) as dataset:counts20=dataset.read(1)
inverse=Transformer.from_crs(POLAR_CRS,POLAR_CRS.geodetic_crs,always_xy=True)
landmarks=[];probes=[]
with rasterio.open(args.height20) as coarse,rasterio.open(args.height5) as fine,rasterio.open(args.count5) as counts:
    for quadrant,(cx,cy) in enumerate([(32000,32000),(32000,-32000),(-32000,-32000),(-32000,32000)]):
        cr,cc=coarse.index(cx,cy);r0,r1=cr-400,cr+400;c0,c1=cc-400,cc+400
        heights=height20[r0:r1,c0:c1];valid=counts20[r0:r1,c0:c1]>0;peak=valid.copy();score=np.full(heights.shape,np.inf)
        for dr,dc in [(dr,dc) for dr in [-1,0,1] for dc in [-1,0,1] if dr or dc]:
            peak &= heights>=np.roll(np.roll(heights,dr,0),dc,1)
            score=np.minimum(score,(heights.astype(float)-np.roll(np.roll(heights,dr*2,0),dc*2,1))*.5)
        candidates=[(float(score[r,c]),r0+int(r),c0+int(c)) for r,c in np.argwhere(peak&(score>1))]
        selected=None
        for strength,row20,col20 in sorted(candidates,reverse=True)[:100]:
            x,y=coarse.transform*(col20+.5,row20+.5);row,col=fine.index(x,y)
            region=fine.read(1,window=Window(col-12,row-12,25,25));dy,dx=np.unravel_index(np.argmax(region),region.shape);row=row-12+int(dy);col=col-12+int(dx)
            values=fine.read(1,window=Window(col-10,row-10,21,21)).astype(float)*.5
            quality=counts.read(1,window=Window(col-10,row-10,21,21))
            top=float(values.max());mask=values>=top-1.25
            edge=np.r_[values[0],values[-1],values[:,0],values[:,-1]]
            if top-float(edge.max())<2 or not 1<=int(mask.sum())<=100 or not np.any(quality[mask]>0):continue
            # The entire peak band must be connected to the global maximum.
            seen=set();queue=[tuple(np.unravel_index(np.argmax(values),values.shape))]
            while queue:
                rr,cl=queue.pop()
                if (rr,cl) in seen or not (0<=rr<21 and 0<=cl<21) or not mask[rr,cl]:continue
                seen.add((rr,cl));queue.extend((rr+dr,cl+dc) for dr in [-1,0,1] for dc in [-1,0,1] if dr or dc)
            if len(seen)!=int(mask.sum()):continue
            selected=(row,col,values,quality,top,mask,strength);break
        if selected is None:raise ValueError(f'No prequalified source landmark in quadrant {quadrant}')
        row,col,values,quality,top,mask,strength=selected
        samples=[]
        for rr in range(21):
            for cl in range(21):
                x,y=fine.transform*(col-10+cl+.5,row-10+rr+.5);lon,lat=inverse.transform(x,y);lo,la=map(math.radians,[lon,lat]);u=[math.cos(la)*math.cos(lo),math.cos(la)*math.sin(lo),math.sin(la)]
                identifier=f'landmark-{quadrant}-{rr}-{cl}'
                probes.append({'id':identifier,'position_m':[1737400*v for v in u]})
                samples.append({'id':identifier,'grid_row':rr,'grid_column':cl,'source_row':row-10+rr,'source_column':col-10+cl,'height_m':float(values[rr,cl]),'count':int(quality[rr,cl]),'source_position_m':[(1737400+float(values[rr,cl]))*v for v in u],'latitude_deg':lat,'longitude_deg_east':lon})
        landmark={'id':f'polar-peak-{quadrant}','quadrant':quadrant,'source_center_row':row,'source_center_column':col,'coarse_selection_minimum_40m_drop_m':strength,'source_peak_height_m':top,'source_edge_height_drop_m':top-float(edge.max()),'top_band_m':1.25,'source_peak_band_pixels':int(mask.sum()),'positive_count_peak_band_pixels':int(np.sum(quality[mask]>0)),'samples':samples}
        landmarks.append(landmark);print(json.dumps({k:v for k,v in landmark.items() if k!='samples'}),flush=True)
reference={'artifact_type':'soma_source_selected_terrain_landmarks','source_frame':'MOON_ME_DE421','reference_radius_m':1737400,'source_pixel_size_m':5,'selection':'Fixed quadrant windows; source-only sharp peak selection before any corrected-scene query. Connected top 1.25m band, no boundary maximum, positive-count peak support.','predeclared_tolerance_m':10,'horizontal_grid_resolution_allowance_m':math.sqrt(2)*2.5,'landmarks':landmarks}
request={'format_version':'0.1.0','request_id':'four-source-selected-terrain-landmarks-v1','source_frame':'MOON_ME_DE421','candidate_bridge':'identity_for_measurement_only','probes':probes}
(args.output/'renderer-landmark-reference.manifest.json').write_text(json.dumps(reference,indent=2)+'\n')
(args.output/'landmarks-probes.json').write_text(json.dumps(request,indent=2)+'\n')
