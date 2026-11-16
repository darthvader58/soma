"""Hosted display paths preserve the engine's registration and tile contract."""

import hashlib
import json

from fastapi.testclient import TestClient
import pytest

from api import index
from soma.api.moon import RegisteredMoon, valid_path
from soma.geometry.registration import load_renderer_registration


class TileProvider:
    model = {"status": "validated_for_region"}
    model_sha = "a" * 64

    def __init__(self):
        self.paths = []

    def get(self, path):
        valid_path(path)
        self.paths.append(path)
        return b"tile", "application/octet-stream", hashlib.sha256(b"tile").hexdigest()


def test_hosted_paths_and_pinned_registration():
    provider = TileProvider()
    with TestClient(index.create_app(provider)) as client:
        registration = client.get("/api/moon/registration")
        assert registration.status_code == 200
        assert registration.json() == load_renderer_registration()
        assert registration.headers["cache-control"] == "private, no-store"
        conversion = client.get("/api/moon/conversion").json()
        assert conversion["tile_base"] == "/api/moon/tiles/"
        assert conversion["sha256"] == provider.model_sha
        tile = client.get("/api/moon/tiles/Moon_85s_90s/0/0/0.b3dm?conversion=" + provider.model_sha)
        assert tile.status_code == 200 and tile.content == b"tile"
        assert provider.paths == ["Moon_85s_90s/0/0/0.b3dm"]
        assert tile.headers["cache-control"] == "private, no-store"
        assert client.get("/api/moon/tiles/tileset.json?conversion=stale").status_code == 409
        assert client.post("/api/plans", json={}).status_code == 404


def test_invalid_objects_do_not_reach_upstream():
    with TestClient(index.create_app(TileProvider())) as client:
        response = client.get("/api/moon/tiles/foreign/0.b3dm")
        assert response.status_code == 502
        assert "foreign" not in response.text


def test_hosted_fetch_uses_configured_origin_and_server_token(monkeypatch):
    monkeypatch.setenv("SOMA_PUBLIC_ORIGIN", "https://soma-atlas-two.vercel.app")
    monkeypatch.setenv("SOMA_CESIUM_ION_TOKEN", "server-only")
    requests = []

    class Upstream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return b"{}"

    def open_request(request, timeout):
        requests.append(request)
        assert timeout == 30
        return Upstream()

    monkeypatch.setattr(index, "urlopen", open_request)
    assert index.hosted_fetch("https://api.cesium.com/v1/assets/2684829/endpoint", index.hosted_token()) == b"{}"
    assert requests[0].get_header("Referer") == "https://soma-atlas-two.vercel.app/"
    assert requests[0].full_url == "https://api.cesium.com/v1/assets/2684829/endpoint?access_token=server-only"
    assert requests[0].get_header("Authorization") is None
    assert index.hosted_fetch("https://assets.cesium.com/2684829/Moon/v6/tileset.json", "endpoint-only") == b"{}"
    assert requests[1].get_header("Authorization") == "Bearer endpoint-only"
    monkeypatch.delenv("SOMA_CESIUM_ION_TOKEN")
    with pytest.raises(ValueError):
        index.hosted_token()
    monkeypatch.setenv("SOMA_PUBLIC_ORIGIN", "http://127.0.0.1:5173")
    with pytest.raises(ValueError):
        index.hosted_origin()


def test_hosted_response_limit_fails_closed(monkeypatch):
    monkeypatch.setattr(RegisteredMoon, "get", lambda self, path:
                        (b"x" * (index.MAX_HOSTED_RESPONSE + 1), "application/octet-stream", "a" * 64))
    with TestClient(index.create_app(index.HostedMoon())) as client:
        response = client.get("/api/moon/tiles/Moon_85s_90s/0/0/0.b3dm")
        assert response.status_code == 502
        assert len(response.content) < 1000


def test_deployment_routes_keep_api_out_of_spa():
    with open("vercel.json") as source:
        config = json.load(source)
    assert config["outputDirectory"] == "web/dist"
    assert config["rewrites"][0] == {"source": "/api/moon/:path*", "destination": "/api/index"}
    assert config["functions"]["api/index.py"]["maxDuration"] <= 300
    assert "api/_native/**" in config["functions"]["api/index.py"]["includeFiles"]
    assert config["buildCommand"] == "python3 scripts/build-hosted.py"


def test_native_preload_checks_hash_and_uses_global_symbols(tmp_path, monkeypatch):
    library = tmp_path / "libexpat.so.1"
    library.write_bytes(b"test shared library")
    manifest = {"file": library.name, "sha256": hashlib.sha256(library.read_bytes()).hexdigest()}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    loaded = []
    monkeypatch.setattr(index.ctypes, "CDLL", lambda path, mode: loaded.append((path, mode)))
    index.preload_hosted_libraries(tmp_path)
    assert loaded == [(str(library.resolve()), index.ctypes.RTLD_GLOBAL)]
    library.write_bytes(b"corrupted")
    with pytest.raises(ImportError, match="checksum mismatch"):
        index.preload_hosted_libraries(tmp_path)
    assert len(loaded) == 1


def test_hosted_native_manifest_is_required_only_on_vercel(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    index.preload_hosted_libraries(tmp_path)
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(ImportError, match="manifest is missing"):
        index.preload_hosted_libraries(tmp_path)
