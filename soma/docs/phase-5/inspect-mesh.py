"""Inspect the captured v6 south-polar mesh profile; unsupported glTF is rejected.

Only the observed uncompressed float-position/matrix-node profile is supported.
The result diagnoses CPU/GPU sampling, never landmark registration. Binary input
stays local; the output contains a few observed triangle coordinates and hashes.
"""
from pathlib import Path
import hashlib, json, struct, sys
import numpy as np

if len(sys.argv) != 3:
    raise SystemExit('Usage: python soma/docs/phase-5/inspect-mesh.py CAPTURE_DIRECTORY OUTPUT_JSON')
root=Path(sys.argv[1])
meta=json.loads((root/'metadata.json').read_text())
transforms={x['path']:np.array(x['transform']).reshape(4,4,order='F') for x in meta['tiles']}
axis=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]],dtype=float)
controls=meta['measurement']['probes']; directions=np.array([x['input_position_m'] for x in controls]);directions/=np.linalg.norm(directions,axis=1)[:,None]
hits=[[] for _ in controls]
for record in meta['responses']:
    if 'sha256' not in record or record['path'] not in transforms or '/Moon_85s_90s/' not in record['path']:continue
    level=int(record['path'].split('/')[-3])
    if level<13:continue
    raw=(root/(record['sha256']+'.bin')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==record['sha256'], 'Tile checksum mismatch'
    header=struct.unpack('<7I',raw[:28]);assert raw[:4]==b'b3dm' and header[1]==1 and header[2]==len(raw)
    assert header[4:]==(0,0,0), 'Unsupported feature or batch binary'
    assert json.loads(raw[28:28+header[3]])=={'BATCH_LENGTH':0}, 'Unsupported feature table'
    offset=28+sum(header[3:]);data=raw[offset:]
    assert data[:4]==b'glTF' and struct.unpack('<II',data[4:12])==(2,len(data))
    length,kind=struct.unpack('<II',data[12:20]);assert kind==0x4e4f534a
    gltf=json.loads(data[20:20+length]);base=20+length
    assert gltf['asset']['version']=='2.0'
    assert set(gltf.get('extensionsUsed',[]))<={'KHR_materials_unlit'}
    assert set(gltf.get('extensionsRequired',[]))<={'KHR_materials_unlit'}
    assert not gltf.get('animations') and not gltf.get('skins')
    binarylen,binarykind=struct.unpack('<II',data[base:base+8]);assert binarykind==0x004e4942
    binary=data[base+8:base+8+binarylen]
    assert base+8+binarylen==len(data)
    assert len(gltf['buffers'])==1 and 'uri' not in gltf['buffers'][0]
    assert gltf['buffers'][0]['byteLength']<=binarylen
    def accessor(index):
        a=gltf['accessors'][index];view=gltf['bufferViews'][a['bufferView']]
        assert not a.get('normalized') and not a.get('sparse') and view.get('buffer',0)==0
        dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']];n={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']]
        stride=view.get('byteStride',np.dtype(dtype).itemsize*n);start=view.get('byteOffset',0)+a.get('byteOffset',0)
        return np.ndarray((a['count'],n),dtype=dtype,buffer=binary,offset=start,strides=(stride,np.dtype(dtype).itemsize)).copy()
    def visit(index,parent):
        node=gltf['nodes'][index];assert not any(k in node for k in ['rotation','scale','translation','skin','weights','extensions'])
        transform=parent@np.array(node.get('matrix',np.eye(4).flatten(order='F').tolist())).reshape(4,4,order='F')
        if 'mesh' in node:
            for primitive in gltf['meshes'][node['mesh']]['primitives']:
                assert primitive.get('mode',4)==4 and not primitive.get('extensions') and not primitive.get('targets')
                position=gltf['accessors'][primitive['attributes']['POSITION']]
                assert position['componentType']==5126 and position['type']=='VEC3'
                assert not position.get('normalized') and not position.get('sparse')
                v=accessor(primitive['attributes']['POSITION']).astype(float);v=np.c_[v,np.ones(len(v))]@transform.T;v=v[:,:3]
                index_accessor=gltf['accessors'][primitive['indices']]
                assert index_accessor['type']=='SCALAR' and index_accessor['componentType'] in (5123,5125)
                faces=accessor(primitive['indices']).reshape(-1,3)
                assert int(faces.max())<len(v)
                a,b,c=v[faces[:,0]],v[faces[:,1]],v[faces[:,2]];e1=b-a;e2=c-a
                for i,d in enumerate(directions):
                    h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-9
                    inv=np.zeros(len(det));inv[valid]=1/det[valid];s=-a
                    u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);vv=inv*(q@d);t=inv*np.einsum('ij,ij->i',e2,q)
                    valid &= (u>=-1e-9)&(vv>=-1e-9)&(u+vv<=1+1e-9)&(t>1600000)&(t<1900000)
                    if any(valid):
                        chosen=int(np.argmax(np.where(valid,t,-np.inf)));radius=float(t[chosen]);gpu=np.array(controls[i]['renderer_position_m']);cpu=radius*d
                        hits[i].append({'tile_path':record['path'],'tile_sha256':record['sha256'],'level':level,'radius_m':radius,'cpu_position_m':cpu.tolist(),'cpu_gpu_difference_m':float(np.linalg.norm(cpu-gpu)), 'triangle_world_m':[a[chosen].tolist(),b[chosen].tolist(),c[chosen].tolist()], 'tile_transform_column_major':transforms[record['path']].flatten(order='F').tolist()})
        for child in node.get('children',[]):visit(child,transform)
    for node in gltf['scenes'][gltf.get('scene',0)]['nodes']:visit(node,transforms[record['path']]@axis)
report={'purpose':'CPU radial triangle intersections of decoded asset vertices, independent of GPU depth queries; no registration approval','origin':'MOON','position_unit':'m','renderer_frame':'unregistered_asset_world','source_frame':'MOON_ME_DE421','epoch':None,'time_scale':'not_applicable_static_mesh','registration_passed':False,'capture_metadata_sha256':hashlib.sha256((root/'metadata.json').read_bytes()).hexdigest(),'controls':[]}
for control,candidates in zip(controls,hits):
    if len(candidates)!=1:
        raise ValueError('Require one captured detailed tile hit per ray; ambiguous or missing geometry is unresolved')
    row={'id':control['id'],'hits':candidates};report['controls'].append(row)
    print(json.dumps({'id':control['id'],'hit_count':len(candidates),'cpu_gpu_difference_m':candidates[0]['cpu_gpu_difference_m'] if candidates else None}))
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
