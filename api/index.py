"""Hosted display adapter; planning remains in the separately run engine."""

import gzip
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from fastapi import FastAPI
from starlette.responses import JSONResponse

from soma.api.moon import MAX_OBJECT, RegisteredMoon, moon_router

# Leave headroom beneath Vercel's buffered 4.5 MB response limit.
MAX_HOSTED_RESPONSE = 4_000_000


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
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        content = response.read(MAX_OBJECT + 1)
    if len(content) > MAX_OBJECT:
        raise ValueError("Display object exceeds the source limit")
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
        if len(content) > MAX_OBJECT:
            raise ValueError("Decoded display object exceeds the source limit")
    return content


class HostedMoon(RegisteredMoon):
    def get(self, path):
        content, media, source_sha = super().get(path)
        if len(content) > MAX_HOSTED_RESPONSE:
            raise ValueError("Converted display object exceeds the hosted response limit")
        return content, media, source_sha


def create_app(provider=None):
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @application.middleware("http")
    async def private_display(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        return response

    @application.exception_handler(Exception)
    async def unavailable(request, error):
        # Neither signed upstream URLs nor credentials belong in public errors.
        return JSONResponse({"detail": "Registered Moon display is unavailable"},
                            status_code=503, headers={"Cache-Control": "private, no-store"})

    application.include_router(moon_router(provider=provider or HostedMoon(
        fetch=hosted_fetch, token_provider=hosted_token)), prefix="/api")
    return application


app = create_app()
