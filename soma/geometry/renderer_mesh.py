"""Reverse the observed v6 Moon tile ingestion artifact for display only.

The terrestrial geoid is an input to this renderer conversion, never a lunar
terrain or physics datum. Unsupported tile encodings fail closed.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
import re
import struct

import numpy as np
import rasterio

_TILE = re.compile(r"(?:^|/)(Moon_85s_90s|Moon_85n_90n|Moon_85s_85n)/(\d+)/(\d+)/(\d+)\.b3dm$")
_MAX_BYTES = 32 * 1024 * 1024
_MAX_VERTICES = 1_000_000


@lru_cache(maxsize=4)
def _geoid_grid(path: str):
    with rasterio.open(path) as dataset:
        if dataset.count != 1 or dataset.width != 1440 or dataset.height != 721:
            raise ValueError("Unsupported geoid grid dimensions")
        t = dataset.transform
        if not np.allclose([t.a, t.b, t.c, t.d, t.e, t.f], [.25, 0, -180.125, 0, -.25, 90.125], atol=1e-9):
            raise ValueError("Unsupported geoid grid transform")
        data = dataset.read(1, masked=True)
        if np.ma.getmaskarray(data).any() or not np.isfinite(data).all():
            raise ValueError("Geoid grid contains missing values")
        return np.asarray(data, dtype=np.float64)


def _geoid(lon, lat, path):
    grid = _geoid_grid(str(Path(path).resolve()))
    x = ((np.degrees(lon) + 180) / .25) % 1440
    y = np.clip((90 - np.degrees(lat)) / .25, 0, 720)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    x1 = (x0 + 1) % 1440; y1 = np.minimum(y0 + 1, 720)
    dx = x - x0; dy = y - y0
    return (grid[y0, x0] * (1-dx) * (1-dy) + grid[y0, x1] * dx * (1-dy)
            + grid[y1, x0] * (1-dx) * dy + grid[y1, x1] * dx * dy)


def correct_mesh_positions(positions, uv, relative_path, geoid_path, model):
    """Convert root-local tile positions into the declared spherical display frame."""
    match = _TILE.search(relative_path)
    if not match:
        raise ValueError("Unsupported tile path")
    region, level, x, y = match.groups(); level, x, y = int(level), int(x), int(y)
    if level > 24 or x >= 2 ** (level + 1) or y >= 2 ** level:
        raise ValueError("Invalid quadtree tile coordinates")
    positions = np.asarray(positions, dtype=np.float64); uv = np.asarray(uv, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] != 3 or uv.shape != (len(positions), 2) or not 0 < len(positions) <= _MAX_VERTICES:
        raise ValueError("Invalid vertex arrays")
    if not np.isfinite(positions).all() or not np.isfinite(uv).all() or (uv < 0).any() or (uv > 1).any():
        raise ValueError("Invalid vertex coordinates")
    quantized = np.rint(uv * 32767)
    if np.max(np.abs(uv - quantized / 32767)) > 1e-6:
        raise ValueError("Unsupported texture coordinate quantization")
    uv = quantized / 32767
    span = 180 / 2 ** level
    lat = np.radians(-90 + (y + 1 - uv[:, 1]) * span)
    lon = np.radians(-180 + (x + uv[:, 0]) * span)
    a = float(model['semimajor_m']); e2 = float(model['eccentricity_squared'])
    radius = float(model.get('reference_radius_m', 1737400))
    scale = float(model.get('global_root_scale', 1739300 / 1737400))
    if not (math.isfinite(a) and a > 0 and 0 <= e2 < 1 and math.isfinite(radius) and radius > 0 and math.isfinite(scale) and scale > 0):
        raise ValueError("Invalid renderer model")
    coslat = np.cos(lat); sinlat = np.sin(lat)
    normal = np.column_stack((coslat * np.cos(lon), coslat * np.sin(lon), sinlat))
    root = np.sqrt(1 - e2 * sinlat ** 2)
    h = np.sum(positions * normal, axis=1) - a * root
    n = a / root
    expected = np.column_stack(((n+h)*normal[:, 0], (n+h)*normal[:, 1], (n*(1-e2)+h)*sinlat))
    if np.max(np.linalg.norm(expected - positions, axis=1)) > .5:
        raise ValueError("Vertex does not match declared tile and ellipsoid")
    h -= _geoid(lon, lat, geoid_path)
    output = (radius + h)[:, None] * normal
    if region == 'Moon_85s_85n':
        output /= scale
    return output


def correct_b3dm(payload: bytes, relative_path: str, geoid_path, model: dict) -> bytes:
    """Rewrite the supported b3dm/glTF profile, preserving non-position data."""
    if not isinstance(payload, bytes) or len(payload) < 48 or len(payload) > _MAX_BYTES:
        raise ValueError("Invalid tile size")
    magic, version, size, ftjson, ftbin, btjson, btbin = struct.unpack_from('<4s6I', payload)
    if magic != b'b3dm' or version != 1 or size != len(payload) or any((ftbin, btjson, btbin)) or 28 + ftjson > len(payload):
        raise ValueError("Unsupported b3dm header")
    try:
        if json.loads(payload[28:28+ftjson]) != {'BATCH_LENGTH': 0}:
            raise ValueError("Unsupported feature table")
        glb = payload[28+ftjson:]
        if len(glb) < 28 or struct.unpack_from('<4sII', glb) != (b'glTF', 2, len(glb)):
            raise ValueError("Unsupported glTF header")
        length, kind = struct.unpack_from('<II', glb, 12)
        if kind != 0x4E4F534A or length % 4 or 20+length+8 > len(glb):
            raise ValueError("Invalid JSON chunk")
        doc = json.loads(glb[20:20+length]); start = 20+length
        binlen, bintype = struct.unpack_from('<II', glb, start)
        if bintype != 0x004E4942 or start+8+binlen != len(glb):
            raise ValueError("Invalid binary chunk")
        binary = bytearray(glb[start+8:])
        if doc['asset']['version'] != '2.0' or set(doc.get('extensionsUsed', [])) - {'KHR_materials_unlit'} or set(doc.get('extensionsRequired', [])) - {'KHR_materials_unlit'} or any(doc.get(k) for k in ('animations', 'skins', 'extensions')):
            raise ValueError("Unsupported glTF extensions")
        if len(doc['buffers']) != 1 or 'uri' in doc['buffers'][0] or doc['buffers'][0]['byteLength'] > binlen:
            raise ValueError("Unsupported buffers")
        nodes = doc['nodes']; scenes = doc['scenes']
        if len(nodes) != 2 or len(scenes) != 1 or scenes[0]['nodes'] != [0] or nodes[0].get('children') != [1] or set(nodes[0]) != {'children', 'matrix'} or set(nodes[1]) != {'matrix', 'mesh'}:
            raise ValueError("Unsupported node hierarchy")
        axis = [1,0,0,0, 0,0,-1,0, 0,1,0,0, 0,0,0,1]
        matrix = nodes[1]['matrix']
        if nodes[0]['matrix'] != axis or len(matrix) != 16 or matrix[:12] != [1,0,0,0,0,1,0,0,0,0,1,0] or matrix[15] != 1 or not np.isfinite(matrix).all():
            raise ValueError("Unsupported node transform")
        meshes = doc['meshes']
        if len(meshes) != 1 or nodes[1]['mesh'] != 0 or len(meshes[0]['primitives']) != 1:
            raise ValueError("Unsupported mesh")
        primitive = meshes[0]['primitives'][0]
        if set(primitive['attributes']) != {'POSITION', 'TEXCOORD_0'} or primitive.get('mode', 4) != 4 or primitive.get('targets') or primitive.get('extensions'):
            raise ValueError("Unsupported primitive")
        indices = doc['accessors'][primitive['indices']]
        index_view = doc['bufferViews'][indices['bufferView']]
        if (indices['type'] != 'SCALAR' or indices['componentType'] not in (5123, 5125)
                or indices.get('normalized') or indices.get('sparse')
                or index_view.get('buffer', 0) != 0 or index_view.get('extensions')
                or index_view.get('byteStride')):
            raise ValueError("Unsupported index accessor")
        index_size = 2 if indices['componentType'] == 5123 else 4
        index_start = index_view.get('byteOffset', 0) + indices.get('byteOffset', 0)
        index_count = indices['count']
        if (index_count <= 0 or index_count % 3 or index_start < 0
                or index_start + index_count * index_size > min(len(binary), index_view.get('byteOffset', 0) + index_view['byteLength'])):
            raise ValueError("Invalid index buffer bounds")
        def accessor(index, n):
            a = doc['accessors'][index]; view = doc['bufferViews'][a['bufferView']]
            if a['componentType'] != 5126 or a['type'] != f'VEC{n}' or a.get('normalized') or a.get('sparse') or view.get('buffer', 0) != 0 or view.get('extensions'):
                raise ValueError("Unsupported vertex accessor")
            count = a['count']; stride = view.get('byteStride', n*4); offset = view.get('byteOffset', 0)+a.get('byteOffset', 0)
            if not 0 < count <= _MAX_VERTICES or stride < n*4 or offset < 0 or offset + (count-1)*stride+n*4 > min(len(binary), view.get('byteOffset',0)+view['byteLength']):
                raise ValueError("Invalid vertex buffer bounds")
            return a, np.ndarray((count,n), dtype='<f4', buffer=binary, offset=offset, strides=(stride,4))
        pa, positions = accessor(primitive['attributes']['POSITION'], 3)
        _, uv = accessor(primitive['attributes']['TEXCOORD_0'], 2)
        index_values = np.frombuffer(binary, dtype='<u2' if index_size == 2 else '<u4', count=index_count, offset=index_start)
        if np.max(index_values) >= len(positions) or np.shares_memory(positions, uv) or np.shares_memory(positions, index_values):
            raise ValueError("Invalid or overlapping mesh buffers")
        corrected = correct_mesh_positions(positions.astype(float) + np.asarray(matrix[12:15]), uv, relative_path, geoid_path, model)
        center = (corrected.min(axis=0)+corrected.max(axis=0))/2
        positions[:] = (corrected-center).astype('<f4')
        matrix[12:15] = center.tolist(); pa['min'] = positions.min(axis=0).astype(float).tolist(); pa['max'] = positions.max(axis=0).astype(float).tolist()
        encoded = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode(); encoded += b' ' * (-len(encoded) % 4)
        outglb = struct.pack('<4sII', b'glTF', 2, 12+8+len(encoded)+8+len(binary)) + struct.pack('<II', len(encoded), 0x4E4F534A) + encoded + struct.pack('<II', len(binary), 0x004E4942) + binary
        feature = b'{"BATCH_LENGTH":0}'; feature += b' ' * (-(28+len(feature)) % 8)
        return struct.pack('<4s6I', b'b3dm', 1, 28+len(feature)+len(outglb), len(feature), 0, 0, 0) + feature + outglb
    except (KeyError, IndexError, TypeError, struct.error, json.JSONDecodeError) as exc:
        raise ValueError("Unsupported or malformed tile") from exc
