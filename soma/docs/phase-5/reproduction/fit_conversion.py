"""Reproduce the height-independent conversion fit from private cached tiles."""
import argparse,json,struct,math,numpy as np
from pathlib import Path
parser=argparse.ArgumentParser(description='Fit the observed asset conversion without DEM heights')
parser.add_argument('capture_directory',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
root=args.capture_directory;m=json.loads((root/'metadata.json').read_text());rows=[]
for record in m['responses']:
 p=record['path'];
 if not ('/Moon_85s_85n/10/' in p or '/Moon_85s_90s/13/' in p or '/Moon_85s_90s/14/' in p) or 'sha256' not in record or not p.endswith('.b3dm'):continue
 d=(root/(record['sha256']+'.bin')).read_bytes();h=struct.unpack('<7I',d[:28]);d=d[28+sum(h[3:]):];l,k=struct.unpack('<II',d[12:20]);g=json.loads(d[20:20+l]);o=20+l;b=d[o+8:]
 def acc(i):
  a=g['accessors'][i];q=g['bufferViews'][a['bufferView']];n={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']];t={5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']];return np.ndarray((a['count'],n),dtype=t,buffer=b,offset=q.get('byteOffset',0)+a.get('byteOffset',0),strides=(q.get('byteStride',np.dtype(t).itemsize*n),np.dtype(t).itemsize)).copy()
 rootnode=g['nodes'][g['scenes'][0]['nodes'][0]];c=g['nodes'][rootnode['children'][0]];prim=g['meshes'][c['mesh']]['primitives'][0];v=acc(prim['attributes']['POSITION']).astype(float);uv=acc(prim['attributes']['TEXCOORD_0']).astype(float);mat=np.array(c['matrix']).reshape((4,4),order='F');v=(np.c_[v,np.ones(len(v))]@mat.T)[:,:3]; n=2**int(p.split('/')[-3]); y=int(p.split('/')[-1].split('.')[0]);x=int(p.split('/')[-2]);lat=-90+(y+1-np.round(uv[:,1]*32767)/32767)*180/n;phi=np.radians(lat); D=np.hypot(v[:,0],v[:,1])/np.cos(phi)-v[:,2]/np.sin(phi); mask=(abs(lat)>.1)&(abs(lat)<84.9)&np.isfinite(D);rows.append((p,lat[mask],D[mask],uv[mask]));
def fit(z):
 lat=np.concatenate([r[1] for r in z]);d=np.concatenate([r[2] for r in z]);s=np.sin(np.radians(lat))**2;X=np.c_[np.ones(len(s)),s];a0,b0=np.linalg.lstsq(X,1/d**2,rcond=None)[0];e=-b0/a0;a=1/math.sqrt(a0)/e;b=a*math.sqrt(1-e);res=d-a*e/np.sqrt(1-e*s);return a,b,e,lat,d,res
for name,subset in [('all',rows),('mid',[r for r in rows if '/Moon_85s_85n/' in r[0]]),('polar',[r for r in rows if '/Moon_85s_90s/' in r[0]])]:
 a,b,e,lat,d,res=fit(subset);print(name,'tiles',len(subset),'vertices',len(lat),'a',a,'b',b,'e2',e,'res-rms',np.sqrt(np.mean(res**2)),'median',np.median(res),'p1p99',np.quantile(res,[.01,.99]),'D range',d.min(),d.max())
for target in ['north','south','odd','even']:
 def choice(r):
  if target in ['north','south']: return (int(r[0].split('/')[-1].split('.')[0])%2==0)==(target=='north')
  return (int(r[0].split('/')[-2])%2==0)==(target=='even')
 train=[r for r in rows if choice(r)];test=[r for r in rows if not choice(r)];a,b,e,_,_,_=fit(train);lat=np.concatenate([r[1] for r in test]);D=np.concatenate([r[2] for r in test]);res=D-a*e/np.sqrt(1-e*np.sin(np.radians(lat))**2);print(target,'train',len(train),'test',len(test),'a,b',a,b,'holdout rms',np.sqrt(np.mean(res**2)),'p1p99',np.quantile(res,[.01,.99]))
a,b,e,lat,d,res=fit(rows)
result={'description':'Height-independent ellipsoid fit from snapped quantized glTF texture coordinates; local coordinates before regional child root transform','sample_count':len(lat),'tile_count':len(rows),'semimajor_m':float(a),'semiminor_m':float(b),'eccentricity_squared':float(e),'d_residual_rms_m':float(np.sqrt(np.mean(res**2))),'d_residual_p01_m':float(np.quantile(res,.01)),'d_residual_p99_m':float(np.quantile(res,.99)),'hypothesis_semimajor_wgs84_times_0_2725_m':6378137*.2725}
result['source_tiles']=[{'path':r[0], 'sha256':next(x['sha256'] for x in m['responses'] if x['path']==r[0])} for r in rows]
args.output.write_text(json.dumps(result,indent=2)+'\n')
