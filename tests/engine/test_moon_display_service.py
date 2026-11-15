import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine
from fastapi.testclient import TestClient

from soma.api.app import create_app
from soma.api.moon import RegisteredMoon, corrected_bounds, correct_tileset, valid_path


MODEL = json.loads((Path(__file__).resolve().parents[2]/'data/renderer-conversion.manifest.json').read_text())
BOX = {'box': [0,0,0,1800000,0,0,0,1800000,0,0,0,1800000]}


@pytest.fixture
def grid(tmp_path):
    path = tmp_path/'grid.tif'
    with rasterio.open(path, 'w', driver='GTiff', width=1440, height=721, count=1,
                       dtype='float32', transform=Affine(.25,0,-180.125,0,-.25,90.125)) as dataset:
        dataset.write(np.full((721,1440),17,dtype='float32'),1)
    return path


@pytest.mark.parametrize('path', ['../tileset.json','Moon_85s_90s/../tileset.json',
    'Moon_85s_90s/%2e%2e/tileset.json','https://example.com/tileset.json',
    'Moon_85s_90s/1/2/3.b3dm?token=secret','Moon_85s_90s//tileset.json',
    'foreign/tileset.json', '/tileset.json', 'Moon_85s_90s/file.exe'])
def test_foreign_or_escaping_tile_paths_fail(path):
    with pytest.raises(ValueError): valid_path(path)


def test_root_rewrites_only_internal_display_paths_and_preserves_attribution(grid):
    document = {'asset':{'version':'1.1','copyright':'NASA source attribution'},'geometricError':1.7976931348623157e308,
                'root':{'boundingVolume':BOX,'geometricError':100,'children':[
                    {'boundingVolume':BOX,'geometricError':10,'content':{'uri':'Moon_85s_90s/tileset.json'}}]}}
    output = correct_tileset(document,'tileset.json',grid,MODEL)
    assert output['asset'] == document['asset']
    assert output['root']['children'][0]['content']['uri'] == '/api/moon/tiles/Moon_85s_90s/tileset.json'
    assert document['root']['children'][0]['content']['uri'] == 'Moon_85s_90s/tileset.json'
    assert np.isfinite(output['geometricError'])
    assert output['root']['boundingVolume']['box'][3] > document['root']['boundingVolume']['box'][3]
    document['root']['children'][0]['content']['uri'] = 'https://example.com/tileset.json'
    with pytest.raises(ValueError): correct_tileset(document,'tileset.json',grid,MODEL)


def test_fine_bound_moves_with_surface_and_retains_all_corrected_vertices(grid):
    from soma.geometry.renderer_mesh import correct_mesh_positions
    a,e = MODEL['semimajor_m'],MODEL['eccentricity_squared']
    uv = np.array([[0,0],[1,0],[0,1],[1,1]],dtype=float)
    lat = np.radians(-90+(8300+1-uv[:,1])*180/16384)
    lon = np.radians(-180+(16489+uv[:,0])*180/16384)
    n=a/np.sqrt(1-e*np.sin(lat)**2); h=np.array([-3900,-3850,-3930,-3890])
    points=np.column_stack(((n+h)*np.cos(lat)*np.cos(lon),(n+h)*np.cos(lat)*np.sin(lon),(n*(1-e)+h)*np.sin(lat)))
    center=(points.min(axis=0)+points.max(axis=0))/2
    half=(points.max(axis=0)-points.min(axis=0))/2+1
    box={'box':[*center.tolist(),half[0],0,0,0,half[1],0,0,0,half[2]]}
    fixed=corrected_bounds(box,'Moon_85s_90s/14/16489/8300.b3dm',grid,MODEL)['box']
    corrected=correct_mesh_positions(points,uv,'Moon_85s_90s/14/16489/8300.b3dm',grid,MODEL)
    assert np.all(np.abs(corrected-np.array(fixed[:3]))<=np.array([fixed[3],fixed[7],fixed[11]]))
    assert np.linalg.norm(np.array(fixed[:3])-center)>500
    assert max(np.array([fixed[3],fixed[7],fixed[11]])-half)<50


def test_provider_retains_version_query_without_retaining_cesium_objects(grid):
    calls=[]
    root={'asset':{'version':'1.1'},'geometricError':1,'root':{'boundingVolume':BOX,'geometricError':1}}
    endpoint={'url':'https://assets.ion.cesium.com/us-east-1/asset_depot/2684829/Moon/v6/tileset.json?v=7',
              'accessToken':'ephemeral-secret'}
    def fetch(url,bearer=None):
        calls.append((url,bearer))
        return json.dumps(endpoint if '/endpoint' in url else root).encode()
    provider=RegisteredMoon(fetch=fetch,token_provider=lambda:'scoped-secret',geoid_path=grid)
    provider.model['status']='candidate_pending_corrected_scene_landmarks'
    provider.model['geoid']['sha256']=hashlib.sha256(grid.read_bytes()).hexdigest()
    first=provider.get('tileset.json');assert first==provider.get('tileset.json')
    assert len(calls)==3 and calls[-1][0].endswith('?v=7')
    assert b'secret' not in first[0]


def test_display_failures_do_not_expose_credentials_or_affect_planning():
    class FailedMoon:
        model={};model_sha='0'*64
        def get(self,path): raise RuntimeError('https://example.com/?access_token=secret')
    app=create_app(moon_provider=FailedMoon())
    with TestClient(app) as client:
        response=client.get('/moon/tiles/tileset.json')
        assert response.status_code==502 and 'secret' not in response.text
        assert client.get('/moon/conversion').status_code==200
        assert client.get('/plans/does-not-exist').status_code==404
        assert client.get('/moon/tiles/tileset.json?conversion='+'f'*64).status_code==409


def test_changed_source_snapshot_blocks_registered_tiles_before_publication(grid):
    endpoint={'url':'https://assets.ion.cesium.com/us-east-1/asset_depot/2684829/Moon/v6/tileset.json?v=7',
              'accessToken':'ephemeral-secret'}
    def fetch(url,bearer=None):
        return json.dumps(endpoint).encode() if '/endpoint' in url else b'changed source'
    provider=RegisteredMoon(fetch=fetch,token_provider=lambda:'scoped-secret',geoid_path=grid)
    provider.model['geoid']['sha256']=hashlib.sha256(grid.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='root changed'):
        provider.get('tileset.json')
    assert not provider.snapshot_verified


def test_corrected_tile_response_disables_storage_even_with_conversion_hash():
    class Moon:
        model={};model_sha='0'*64
        def get(self,path): return b'{}','application/json','1'*64
    with TestClient(create_app(moon_provider=Moon())) as client:
        response=client.get('/moon/tiles/tileset.json?conversion='+'0'*64)
        assert response.status_code==200
        assert response.headers['cache-control']=='private, no-store'
        assert response.headers['x-soma-conversion-sha256']=='0'*64


def test_bad_geoid_checksum_cannot_enter_display_conversion(grid):
    provider=RegisteredMoon(geoid_path=grid)
    with pytest.raises(ValueError,match='grid checksum'):
        provider.prepare()
