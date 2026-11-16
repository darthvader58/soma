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


@pytest.fixture(autouse=True)
def transport_clock(monkeypatch):
    state = {'now': 0.0, 'sleeps': []}

    def sleep(seconds):
        state['sleeps'].append(seconds)
        state['now'] += seconds

    monkeypatch.setattr('soma.datasets._transport_now', lambda: state['now'])
    monkeypatch.setattr('soma.datasets._transport_sleep', sleep)
    return state


def successful_response(request):
    start, end = map(int, request.headers['Range'][6:].split('-'))
    content = bytes(metadata()) if start == 0 else b'x'*(end-start+1)
    return Response(content, f'bytes {start}-{end}/800000')


def test_rate_limit_retries_respect_identification_and_retry_after(tmp_path, monkeypatch, transport_clock):
    from urllib.error import HTTPError
    calls = []

    def fetch(request, **kwargs):
        calls.append((request, transport_clock['now']))
        if len(calls) == 1:
            raise HTTPError(request.full_url, 403, 'Temporary service limit', {'Retry-After': '3'}, None)
        return successful_response(request)

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    path = _acquire_lola_elevation_tiles(tmp_path, parent())
    try:
        assert len(calls) == 11
        assert calls[1][1]-calls[0][1] == 3
        assert calls[0][0].headers['Range'] == calls[1][0].headers['Range']
        assert all('SOMA-scientific-acquisition/0.1' in call.headers['User-agent'] for call, _ in calls)
        assert all('Authorization' not in call.headers for call, _ in calls)
        assert all(b[1]-a[1] >= .349 for a,b in zip(calls,calls[1:]))
    finally:
        path.unlink()


@pytest.mark.parametrize('code', [403,429,500,503,None])
def test_transient_failure_stops_after_three_attempts(tmp_path, monkeypatch, transport_clock, code):
    from urllib.error import HTTPError
    calls = []

    def fetch(request, **kwargs):
        calls.append(request)
        if code is None:
            raise OSError('Transient connection failure')
        raise HTTPError(request.full_url, code, 'Temporary service limit', {}, None)

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    with pytest.raises(OSError):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert len(calls) == 3
    assert transport_clock['sleeps'] == [2,4]
    assert not list(tmp_path.iterdir())


def test_invalid_range_is_not_retried(tmp_path, monkeypatch):
    calls = []

    def fetch(request, **kwargs):
        calls.append(request)
        return Response(bytes(metadata()), 'bytes 1-396153/800000')

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    with pytest.raises(ValueError, match='exact bounded byte range'):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert len(calls) == 1


def test_budget_prevents_requesting_an_additional_range(tmp_path, monkeypatch):
    calls = []

    def fetch(request, **kwargs):
        calls.append(request)
        return successful_response(request)

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    monkeypatch.setattr('soma.datasets._LOLA_RANGE_BUDGET', 396154)
    with pytest.raises(ValueError, match='32 MiB transport budget'):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert len(calls) == 1
    assert not list(tmp_path.iterdir())


def test_excessive_retry_after_fails_without_ignoring_server_wait(tmp_path, monkeypatch, transport_clock):
    from urllib.error import HTTPError
    calls = []

    def fetch(request, **kwargs):
        calls.append(request)
        raise HTTPError(request.full_url, 429, 'Wait', {'Retry-After': '180'}, None)

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    with pytest.raises(TimeoutError, match='Retry-After'):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert len(calls) == 1 and transport_clock['sleeps'] == []


def test_total_transport_deadline_is_enforced(tmp_path, monkeypatch, transport_clock):
    calls = []

    def fetch(request, **kwargs):
        calls.append(request)
        transport_clock['now'] += 121
        return successful_response(request)

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    with pytest.raises(TimeoutError, match='120-second'):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert len(calls) == 1


def test_partial_failed_read_is_still_charged_to_transfer_budget(tmp_path, monkeypatch):
    calls = []

    class InterruptedResponse(Response):
        reads = 0

        def read1(self, length):
            self.reads += 1
            if self.reads == 2:
                raise OSError('Connection interrupted after payload bytes')
            return super().read1(length)

    def fetch(request, **kwargs):
        calls.append(request)
        return InterruptedResponse(bytes(metadata()), 'bytes 0-396152/800000')

    monkeypatch.setattr('soma.datasets.urlopen', fetch)
    monkeypatch.setattr('soma.datasets._LOLA_RANGE_BUDGET', 396154)
    with pytest.raises(ValueError, match='32 MiB transport budget'):
        _acquire_lola_elevation_tiles(tmp_path, parent())
    assert len(calls) == 1
    assert not list(tmp_path.iterdir())
