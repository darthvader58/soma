"""Bounded byte staging must never accept an ignored range or changed TIFF layout."""
import io
import struct

import pytest

from soma.datasets import _acquire_lola_elevation_tiles


def metadata():
    value = bytearray(396153)
    value[:8] = b'II+\x00\x08\x00\x00\x00'
    struct.pack_into('<Q', value, 8, 16)
    struct.pack_into('<Q', value, 16, 20)
    tags = {256: (3,1,40000), 257: (3,1,40000), 322: (3,1,256),
            323: (3,1,256), 324: (16,24649,197624), 325: (16,24649,432)}
    for index, (tag, fields) in enumerate(tags.items()):
        struct.pack_into('<HHQQ', value, 24+index*20, tag, *fields)
    struct.pack_into('<24649Q', value, 197624, *[500000+i*8 for i in range(24649)])
    struct.pack_into('<24649Q', value, 432, *([8]*24649))
    return value


class Response(io.BytesIO):
    status = 206

    def __init__(self, content, content_range):
        super().__init__(content)
        self.headers = {'Content-Range': content_range}


def parent():
    return {'url': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldem_87s_5mpp.tif',
            'size_bytes': 800000}


def test_sparse_stage_preserves_metadata_and_only_selected_tiles(tmp_path, monkeypatch):
    source_metadata = metadata()
    requests = []

    def fetch(request, **kwargs):
        start, end = map(int, request.headers['Range'][6:].split('-'))
        requests.append((start, end))
        content = bytes(source_metadata) if start == 0 else b'x'*(end-start+1)
        return Response(content, f'bytes {start}-{end}/800000')

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    path = _acquire_lola_elevation_tiles(tmp_path, parent())
    try:
        assert path.stat().st_size == 800000
        with path.open('rb') as staged:
            assert staged.read(396153) == source_metadata
            staged.seek(500000+(50*157+74)*8)
            assert staged.read(9*8) == b'x'*(9*8)
            assert staged.read(8) == b'\x00'*8
        assert len(requests) == 10  # Metadata plus nine contiguous selected tile rows.
        assert sum(end-start+1 for start, end in requests) == 396153+81*8
    finally:
        path.unlink()


@pytest.mark.parametrize('failure', ['ignored_range', 'wrong_range', 'short_read', 'changed_header', 'bad_offset'])
def test_transport_rejects_invalid_remote_data(tmp_path, monkeypatch, failure):
    content = metadata()
    if failure == 'changed_header':
        content[0] = 0
    if failure == 'bad_offset':
        struct.pack_into('<Q', content, 197624+(50*157+74)*8, 900000)

    def fetch(request, **kwargs):
        response = Response(bytes(content), 'bytes 0-396152/800000')
        if failure == 'ignored_range':
            response.status = 200
        elif failure == 'wrong_range':
            response.headers['Content-Range'] = 'bytes 1-396153/800000'
        elif failure == 'short_read':
            response = Response(bytes(content[:-1]), 'bytes 0-396152/800000')
        return response

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    with pytest.raises(ValueError):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert not list(tmp_path.iterdir())
