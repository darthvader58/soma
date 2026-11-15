"""Local, bounded display conversion of the authorized Moon tileset.

Only asset 2684829's declared revision is reachable. Credentials and licensed
binary content stay out of manifests, application results and exported runs.
"""

from collections import OrderedDict
from copy import deepcopy
import gzip
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote, parse_qs
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, Response


from soma.geometry.registration import _data_directory

DATA = _data_directory()
PUBLIC_BASE = '/api/moon/tiles/'
MAX_OBJECT = 32 * 1024 * 1024
MAX_CACHE = 128 * 1024 * 1024
REGIONS = ('Moon_85s_85n', 'Moon_85s_90s', 'Moon_85n_90n')


def _token():
    configured = os.environ.get('SOMA_CESIUM_ION_TOKEN')
    if configured:
        return configured.strip()
    path = Path(__file__).resolve().parents[2] / 'web/.env.local'
    if path.is_file():
        for line in path.read_text().splitlines():
            if line.startswith('VITE_CESIUM_ION_TOKEN='):
                return line.split('=', 1)[1].strip().strip('\"\'')
    raise ValueError('Scoped Moon asset access is not configured')


def _fetch(url, bearer=None):
    headers = {'Referer': 'http://127.0.0.1:5173/', 'Accept-Encoding': 'identity'}
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        content = response.read(MAX_OBJECT + 1)
    if len(content) > MAX_OBJECT:
        raise ValueError('Display object exceeds the local limit')
    if content[:2] == b'\x1f\x8b':
        content = gzip.decompress(content)
        if len(content) > MAX_OBJECT:
            raise ValueError('Decoded display object exceeds the local limit')
    return content


def valid_path(path):
    if (not isinstance(path, str) or not path or len(path) > 256 or unquote(path) != path
            or '\\' in path or '?' in path or '#' in path or path.startswith('/')
            or any(part in ('', '.', '..') for part in path.split('/'))):
        raise ValueError('Invalid Moon object path')
    if path == 'tileset.json':
        return path
    if not any(path.startswith(region + '/') for region in REGIONS):
        raise ValueError('Foreign Moon object path')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+\.(?:json|b3dm)', path):
        raise ValueError('Unsupported Moon object type')
    return path


def _region(path):
    return next((region for region in REGIONS if path.startswith(region + '/')), None)


def corrected_bounds(bounds, path, grid, model, *, world=False):
    """Move a display bound with its geometry and cover the residual deformation."""
    import numpy as np
    from soma.geometry.renderer_mesh import _geoid

    if not isinstance(bounds, dict) or set(bounds) != {'box'}:
        raise ValueError('Unsupported Moon bounding-volume encoding')
    box = np.asarray(bounds['box'], dtype=float)
    if box.shape != (12,) or not np.isfinite(box).all():
        raise ValueError('Invalid Moon bounding box')
    center, axes = box[:3].copy(), box[3:].reshape(3, 3).copy()
    lengths = np.linalg.norm(axes, axis=1)
    if (lengths <= 0).any():
        raise ValueError('Degenerate Moon bounding box')
    extent = float(sum(lengths))
    region = _region(path)
    local = center.copy()
    if world and region == 'Moon_85s_90s':
        local = np.array([-center[2], center[1], center[0]])
    elif world and region == 'Moon_85n_90n':
        local = np.array([center[2], center[1], -center[0]])
    elif world and region == 'Moon_85s_85n':
        local /= model['global_root_scale']
    if region and np.linalg.norm(local) > 1_500_000 and extent < 75_000:
        # Bound centers are not vertices and have no texture coordinate. The
        # inverse ellipsoid evaluates the same continuous display conversion.
        a, e2 = model['semimajor_m'], model['eccentricity_squared']
        rho = math.hypot(local[0], local[1])
        lon = math.atan2(local[1], local[0])
        lat = math.atan2(local[2], rho*(1-e2))
        for _ in range(6):
            n = a / math.sqrt(1-e2*math.sin(lat)**2)
            lat = math.atan2(local[2]+e2*n*math.sin(lat), rho)
        normal = np.array([math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)])
        height = float(local @ normal)-a*math.sqrt(1-e2*math.sin(lat)**2)
        height -= float(_geoid(np.array([lon]), np.array([lat]), grid)[0])
        target = (model['reference_radius_m']+height)*normal
        if region == 'Moon_85s_85n':
            target /= model['global_root_scale']
        if world and region == 'Moon_85s_90s':
            target = np.array([target[2], target[1], -target[0]])
        elif world and region == 'Moon_85n_90n':
            target = np.array([-target[2], target[1], target[0]])
        elif world and region == 'Moon_85s_85n':
            target *= model['global_root_scale']
        center = target
        margin = model['bound_displacement_lipschitz']*extent + 1
    else:
        margin = model['maximum_bound_displacement_m']
    axes *= ((lengths+margin)/lengths)[:, None]
    return {'box': [*center.tolist(), *axes.ravel().tolist()]}


def correct_tileset(document, path, grid, model, *, conversion_sha256=None):
    """Keep content attribution/transforms; rewrite only bounds and content paths."""
    output = deepcopy(document)
    if output.get('asset', {}).get('version') not in ('1.0', '1.1'):
        raise ValueError('Unsupported tileset version')
    world = path == 'tileset.json'
    def visit(tile):
        content = tile.get('content')
        linked_path = path
        if content:
            key = 'uri' if 'uri' in content else 'url'
            link = content[key]
            if not isinstance(link, str) or urlsplit(link).scheme or urlsplit(link).netloc or link.startswith('/'):
                raise ValueError('Foreign tile content URL')
            linked_path = str(PurePosixPath(path).parent / link)
            valid_path(linked_path)
            content[key] = PUBLIC_BASE + linked_path
            if conversion_sha256:
                content[key] += '?conversion=' + conversion_sha256
            if 'boundingVolume' in content:
                content['boundingVolume'] = corrected_bounds(content['boundingVolume'], linked_path, grid, model, world=world)
        tile['boundingVolume'] = corrected_bounds(tile['boundingVolume'], linked_path, grid, model, world=world)
        if 'geometricError' in tile:
            tile['geometricError'] = min(tile['geometricError']*1.05, 1.7976931348623157e308)
        for child in tile.get('children', []):
            visit(child)
    visit(output['root'])
    output['geometricError'] = min(output['geometricError']*1.05, 1.7976931348623157e308)
    return output


class RegisteredMoon:
    def __init__(self, *, fetch=_fetch, token_provider=_token, geoid_path=None):
        self.model_path = DATA / 'renderer-conversion.manifest.json'
        self.model = json.loads(self.model_path.read_text())
        self.model_sha = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        self.fetch, self.token_provider = fetch, token_provider
        self.grid = Path(geoid_path or os.environ.get('SOMA_RENDERER_GEOID',
            str(Path(tempfile.gettempdir()) / 'soma-renderer-data' / (self.model['geoid']['sha256']+'.tif'))))
        self.endpoint = None
        self.snapshot_verified = False
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.lock = threading.RLock()

    def prepare(self):
        with self.lock:
            if not self.grid.exists():
                content = self.fetch(self.model['geoid']['source_url'])
                if hashlib.sha256(content).hexdigest() != self.model['geoid']['sha256']:
                    raise ValueError('Renderer grid checksum mismatch')
                self.grid.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.grid.with_suffix('.partial')
                temporary.write_bytes(content)
                temporary.replace(self.grid)
            if hashlib.sha256(self.grid.read_bytes()).hexdigest() != self.model['geoid']['sha256']:
                raise ValueError('Renderer grid checksum mismatch')
            if self.endpoint is None:
                endpoint = json.loads(self.fetch('https://api.cesium.com/v1/assets/2684829/endpoint', self.token_provider()))
                target = urlsplit(endpoint['url'])
                if (target.scheme != 'https' or not target.hostname or not target.hostname.endswith('.cesium.com')
                        or '/2684829/Moon/v6/tileset.json' not in target.path
                        or set(parse_qs(target.query)) - {'v'}):
                    raise ValueError('Unrecognized Moon source revision')
                self.endpoint = endpoint
            if self.model['status'] == 'validated_for_region' and not self.snapshot_verified:
                controls = self.model.get('source_control_tiles', [])
                if len(controls) < 4 or len({c['path'] for c in controls}) != len(controls):
                    raise ValueError('Missing source snapshot controls')
                root = self.fetch(self.source_url('tileset.json'), self.endpoint['accessToken'])
                if hashlib.sha256(root).hexdigest() != self.model['source_root_sha256']:
                    raise ValueError('Moon source root changed')
                for control in controls:
                    valid_path(control['path'])
                    body = self.fetch(self.source_url(control['path']), self.endpoint['accessToken'])
                    if hashlib.sha256(body).hexdigest() != control['source_sha256']:
                        raise ValueError('Moon source landmark tile changed')
                self.snapshot_verified = True

    def source_url(self, path):
        target = urlsplit(urljoin(self.endpoint['url'], path))
        return urlunsplit((target.scheme, target.netloc, target.path, urlsplit(self.endpoint['url']).query, ''))

    def get(self, path):
        valid_path(path)
        self.prepare()
        with self.lock:
            if path in self.cache:
                self.cache.move_to_end(path)
                return self.cache[path]
        endpoint = self.endpoint
        content = self.fetch(self.source_url(path), endpoint['accessToken'])
        source_sha = hashlib.sha256(content).hexdigest()
        expected = (self.model.get('source_root_sha256') if path == 'tileset.json' else
                    next((c['source_sha256'] for c in self.model.get('source_control_tiles', []) if c['path'] == path), None))
        if self.model['status'] == 'validated_for_region' and expected and source_sha != expected:
            raise ValueError('Moon source snapshot control changed')
        if path.endswith('.json'):
            document = correct_tileset(json.loads(content), path, self.grid, self.model, conversion_sha256=self.model_sha)
            converted = json.dumps(document, separators=(',', ':'), allow_nan=False).encode()
            media = 'application/json'
        else:
            from soma.geometry.renderer_mesh import correct_b3dm
            converted = correct_b3dm(content, path, self.grid, self.model)
            media = 'application/octet-stream'
        item = converted, media, source_sha
        with self.lock:
            if path not in self.cache:
                while self.cache and self.cache_bytes+len(converted) > MAX_CACHE:
                    _, removed = self.cache.popitem(last=False)
                    self.cache_bytes -= len(removed[0])
                self.cache[path] = item
                self.cache_bytes += len(converted)
        return item


def moon_router(provider=None):
    router = APIRouter()
    provider = provider or RegisteredMoon()

    @router.get('/moon/conversion')
    def conversion():
        return {'model': provider.model, 'sha256': provider.model_sha,
                'representation': 'engine_corrected_mesh' if provider.model.get('status') == 'validated_for_region' else 'corrected_mesh_candidate',
                'tile_base': PUBLIC_BASE}

    @router.get('/moon/registration')
    def registration():
        from soma.geometry.registration import load_renderer_registration
        return load_renderer_registration()

    @router.get('/moon/tiles/{path:path}')
    def tile(path: str, conversion: str | None = None):
        if conversion is not None and conversion != provider.model_sha:
            raise HTTPException(409, 'Moon conversion changed; reload the verified scene')
        try:
            content, media, source_sha = provider.get(path)
            return Response(content, media_type=media, headers={
                'X-SOMA-Source-SHA256': source_sha, 'X-SOMA-Conversion-SHA256': provider.model_sha,
                'Cache-Control': 'private, max-age=3600, immutable' if conversion else 'private, no-store'})
        except ValueError as error:
            # Transport errors can carry signed ion URLs, so error messages are
            # never relayed to the browser or the planning result.
            raise HTTPException(502, 'Registered Moon display is unavailable or its source profile changed') from None
        except Exception:
            raise HTTPException(502, 'Registered Moon display could not be prepared') from None

    return router
