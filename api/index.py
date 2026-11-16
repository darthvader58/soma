"""Vercel Moon display and bounded live geometry analysis adapters."""

import gzip
import ctypes
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import FastAPI
from starlette.responses import JSONResponse

from soma.api.research_jobs import configure_numerical_threads

# Bound native allocation before importing geometry/NumPy for display or studies.
configure_numerical_threads()

from soma.api.moon import MAX_OBJECT, RegisteredMoon, moon_router

# Leave headroom beneath Vercel's buffered 4.5 MB response limit.
MAX_HOSTED_RESPONSE = 4_000_000
_native_handles = []


def preload_hosted_libraries(directory=None):
    directory = Path(directory) if directory is not None else Path(__file__).parent / "_native"
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        if os.environ.get("VERCEL") == "1":
            raise ImportError("Hosted native dependency manifest is missing")
        return
    manifest = json.loads(manifest_path.read_text())
    library = directory / "libexpat.so.1"
    if manifest.get("file") != library.name or hashlib.sha256(library.read_bytes()).hexdigest() != manifest.get("sha256"):
        raise ImportError("Hosted Expat dependency checksum mismatch")
    _native_handles.append(ctypes.CDLL(str(library.resolve()), mode=ctypes.RTLD_GLOBAL))


preload_hosted_libraries()


def hosted_token():
    token = os.environ.get("SOMA_CESIUM_ION_TOKEN", "").strip()
    if not token:
        raise ValueError("Scoped Moon asset access is not configured")
    return token


def hosted_origin():
    origin = os.environ.get("SOMA_PUBLIC_ORIGIN", "").rstrip("/")
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.path
            or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("An HTTPS public origin is required")
    return origin


def hosted_fetch(url, bearer=None):
    headers = {"Referer": hosted_origin() + "/", "Accept-Encoding": "identity"}
    if url == "https://api.cesium.com/v1/assets/2684829/endpoint" and bearer:
        url += "?" + urlencode({"access_token": bearer})
        bearer = None
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            content = response.read(MAX_OBJECT + 1)
    except HTTPError as error:
        try:
            code = json.loads(error.read(4096)).get("code", "unknown")
        except (ValueError, AttributeError):
            code = "unknown"
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", code):
            code = "unknown"
        logging.getLogger(__name__).error("Moon upstream returned HTTP %s from %s (%s)", error.code, urlsplit(url).hostname, code)
        raise
    if len(content) > MAX_OBJECT:
        raise ValueError("Display object exceeds the source limit")
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
        if len(content) > MAX_OBJECT:
            raise ValueError("Decoded display object exceeds the source limit")
    return content


class HostedMoon(RegisteredMoon):
    def get(self, path):
        try:
            content, media, source_sha = super().get(path)
        except ImportError as error:
            logging.getLogger(__name__).error("Moon dependency import failed: %s", error)
            raise
        except Exception as error:
            # Log only the failure class; transport messages may contain signed URLs.
            logging.getLogger(__name__).error("Moon display preparation failed: %s", type(error).__name__)
            raise
        if len(content) > MAX_HOSTED_RESPONSE:
            raise ValueError("Converted display object exceeds the hosted response limit")
        return content, media, source_sha


def create_app(provider=None, *, research_planner=None, research_data_root=None,
               research_capabilities=None, research_catalog=None):
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @application.middleware("http")
    async def private_display(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        return response

    @application.exception_handler(Exception)
    async def unavailable(request, error):
        # Neither signed upstream URLs nor credentials belong in public errors.
        message = ("Research service is unavailable" if request.url.path.startswith("/api/research")
                   else "Registered Moon display is unavailable")
        return JSONResponse({"detail": message},
                            status_code=503, headers={"Cache-Control": "private, no-store"})

    application.include_router(moon_router(provider=provider or HostedMoon(
        fetch=hosted_fetch, token_provider=hosted_token)), prefix="/api")
    from soma.api.research import research_router
    application.include_router(research_router(service_mode="serverless",
        data_root=research_data_root or str(Path(__file__).parent / "_data"),
        planner=research_planner, capabilities_provider=research_capabilities,
        catalog_provider=research_catalog), prefix="/api")
    return application


app = create_app()
