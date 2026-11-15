import json
import struct

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from soma.geometry.renderer_mesh import correct_b3dm, correct_mesh_positions

MODEL = {'semimajor_m': 1738042.3511433182, 'eccentricity_squared': .002412566753187137}
PATH = 'Moon_85s_90s/4/17/8.b3dm'


@pytest.fixture
def geoid(tmp_path):
    path = tmp_path / 'geoid.tif'
    grid = np.full((721, 1440), 17.25, dtype='float32')
    with rasterio.open(path, 'w', driver='GTiff', width=1440, height=721, count=1,
                       dtype='float32', transform=Affine(.25, 0, -180.125, 0, -.25, 90.125)) as ds:
        ds.write(grid, 1)
    return path


def source_vertices(uv, path=PATH):
    level, x, y = map(int, path.split('/')[-3:-1] + [path.split('/')[-1].split('.')[0]])
    lat = np.radians(-90+(y+1-uv[:, 1])*180/2**level)
    lon = np.radians(-180+(x+uv[:, 0])*180/2**level)
    a, e = MODEL['semimajor_m'], MODEL['eccentricity_squared']
    n = a / np.sqrt(1-e*np.sin(lat)**2)
    h = np.array([-2000., 140., 1500.])[:len(uv)]
    v = np.column_stack(((n+h)*np.cos(lat)*np.cos(lon), (n+h)*np.cos(lat)*np.sin(lon), (n*(1-e)+h)*np.sin(lat)))
    normal = np.column_stack((np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)))
    return v, (1737400+h-17.25)[:, None]*normal


def make_tile(vertices, uv):
    center = vertices.mean(axis=0)
    pos = (vertices-center).astype('<f4'); uv = uv.astype('<f4')
    binary = pos.tobytes()+uv.tobytes()+np.array([0,1,2], dtype='<u2').tobytes()+b'\0\0'
    doc = {'asset': {'version':'2.0'}, 'buffers':[{'byteLength':len(binary)}],
           'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':pos.nbytes}, {'buffer':0,'byteOffset':pos.nbytes,'byteLength':uv.nbytes}, {'buffer':0,'byteOffset':pos.nbytes+uv.nbytes,'byteLength':6}],
           'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3'}, {'bufferView':1,'componentType':5126,'count':3,'type':'VEC2'}, {'bufferView':2,'componentType':5123,'count':3,'type':'SCALAR'}],
           'nodes':[{'children':[1],'matrix':[1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1]}, {'mesh':0,'matrix':[1,0,0,0,0,1,0,0,0,0,1,0,*center.tolist(),1]}],
           'meshes':[{'primitives':[{'attributes':{'POSITION':0,'TEXCOORD_0':1}, 'indices':2}]}], 'scenes':[{'nodes':[0]}]}
    js=json.dumps(doc,separators=(',',':')).encode(); js+=b' '*(-len(js)%4)
    glb=struct.pack('<4sII',b'glTF',2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary
    ft=b'{"BATCH_LENGTH":0}';ft+=b' '*(-(28+len(ft))%8)
    return struct.pack('<4s6I',b'b3dm',1,28+len(ft)+len(glb),len(ft),0,0,0)+ft+glb


def read_vertices(tile):
    h=struct.unpack_from('<4s6I',tile); glb=tile[28+h[3]:]; n=struct.unpack_from('<I',glb,12)[0]
    doc=json.loads(glb[20:20+n]); binary=glb[20+n+8:]; pos=np.frombuffer(binary,dtype='<f4',count=9).reshape(3,3).copy()
    return pos+np.array(doc['nodes'][1]['matrix'][12:15]), binary[36:]


def test_correct_b3dm_roundtrip_and_preserves_nonposition(geoid):
    uv=np.array([[0,0],[1,0],[0,1]],dtype=float); vertices, expected=source_vertices(uv)
    payload=make_tile(vertices,uv); actual=correct_b3dm(payload,PATH,geoid,MODEL)
    got, other=read_vertices(actual); _,original_other=read_vertices(payload)
    np.testing.assert_allclose(got,expected,atol=.01); assert other == original_other
    assert correct_b3dm(payload,PATH,geoid,MODEL)==actual


@pytest.mark.parametrize('path', ['Moon_85s_90s/4/17/8.b3dm','Moon_85n_90n/4/17/15.b3dm','Moon_85s_85n/4/17/8.b3dm'])
def test_positions_polar_and_global(path,geoid):
    uv=np.array([[0,0],[1,0],[0,1]],dtype=float); source,expected=source_vertices(uv,path)
    if '85s_85n' in path: expected/=1739300/1737400
    np.testing.assert_allclose(correct_mesh_positions(source,uv,path,geoid,MODEL),expected,atol=1e-6)


def test_rejects_wrong_geometry_and_unsupported_path(geoid):
    uv=np.array([[0,0],[1,0],[0,1]],dtype=float); source,_=source_vertices(uv)
    with pytest.raises(ValueError): correct_mesh_positions(source+100,uv,PATH,geoid,MODEL)
    with pytest.raises(ValueError): correct_mesh_positions(source,uv,'Moon/4/17/8.b3dm',geoid,MODEL)
    with pytest.raises(ValueError): correct_b3dm(b'bad',PATH,geoid,MODEL)


def test_geoid_periodic_bilinear_sampling(monkeypatch):
    from soma.geometry import renderer_mesh
    grid=np.zeros((721,1440)); grid[360,1439]=4; grid[360,0]=8; grid[361,1439]=12; grid[361,0]=16
    monkeypatch.setattr(renderer_mesh, '_geoid_grid', lambda _: grid)
    result=renderer_mesh._geoid(np.radians(np.array([179.875,-180.125])), np.radians(np.array([-.125,-.125])), 'unused')
    np.testing.assert_allclose(result, [10,10])


def test_rejects_unquantized_uv(geoid):
    uv=np.array([[0,0],[1,0],[0,1]],dtype=float); source,_=source_vertices(uv)
    uv[0,0]=.123456
    with pytest.raises(ValueError, match='quantization'):
        correct_mesh_positions(source,uv,PATH,geoid,MODEL)


def test_rejects_index_outside_vertex_array(geoid):
    uv = np.array([[0, 0], [1, 0], [0, 1]], dtype=float)
    source, _ = source_vertices(uv)
    payload = bytearray(make_tile(source, uv))
    struct.pack_into('<H', payload, len(payload) - 8, 3)
    with pytest.raises(ValueError, match='mesh buffers'):
        correct_b3dm(bytes(payload), PATH, geoid, MODEL)
