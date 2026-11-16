"""HTTP adapters for bounded geometry studies; science stays in soma.research."""

import asyncio
import json
import os
from pathlib import Path
import sys
import threading

from fastapi import APIRouter, HTTPException, Request, Response

from soma.api.research_jobs import (MAX_RESULT_BYTES, MAX_RETAINED_BYTES,
                                    MAX_WORKER_MEMORY_BYTES, run_sync)
from soma.validation import _reject_constant, _unique_keys

MAX_REQUEST_BYTES = 128_000
MAX_SYNC_RESPONSE_BYTES = 4_000_000
MAX_SYNC_SECONDS = 60


def configured_data_root():
    value = os.environ.get('SOMA_DATA_ROOT') or os.environ.get('SOMA_RESEARCH_DATA_ROOT')
    return str(Path(value).resolve()) if value else None


async def _request_study(request):
    from soma.research import validate_study
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_REQUEST_BYTES:
            raise HTTPException(413, 'Research request exceeds 128000-byte budget')
    try:
        document = json.loads(content, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
        return validate_study(document)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise HTTPException(422, str(error)[:2000]) from error


def research_router(*, data_root=None, planner=None, capabilities_provider=None,
                    catalog_provider=None, service_mode='persistent', sync_seconds=MAX_SYNC_SECONDS):
    """Providers are trusted startup configuration, never selected by HTTP input."""
    if service_mode not in ('persistent', 'serverless'):
        raise ValueError('Unsupported research service mode')
    if not 0 < sync_seconds <= MAX_SYNC_SECONDS:
        raise ValueError('Synchronous research time budget cannot exceed 60 seconds')
    router = APIRouter(prefix='/research', tags=['research'])
    synchronous_slot = threading.BoundedSemaphore(1)

    def store(request):
        jobs = getattr(request.app.state, 'research_jobs', None)
        if service_mode == 'serverless':
            raise HTTPException(503, 'Durable jobs are unavailable in this synchronous Vercel service')
        if jobs is None:
            raise HTTPException(503, 'Durable research jobs unavailable; configure a local research run directory')
        return jobs

    @router.get('/catalog')
    def catalog():
        if catalog_provider is not None:
            return catalog_provider()
        from soma.research.catalog import site_catalog
        return site_catalog()

    @router.get('/capabilities')
    def capabilities(request: Request):
        try:
            if capabilities_provider is None:
                from soma.research import runtime_capabilities
                report = runtime_capabilities(data_root=data_root)
            else:
                report = capabilities_provider(data_root=data_root)
        except Exception:
            report = {'ready': False, 'coverage': None, 'spacecraft': [],
                      'limitations': ['Research source readiness could not be verified']}
        # Provider readiness errors can include operating-system source paths.
        if isinstance(report.get('unavailable_reason'), str) and any(char in report['unavailable_reason'] for char in ('/', '\\')):
            report['unavailable_reason'] = 'Scientific source verification failed'
        for profile in report.get('spacecraft', []):
            reason = profile.get('unavailable_reason')
            if isinstance(reason, str) and any(char in reason for char in ('/', '\\')):
                profile['unavailable_reason'] = 'Spacecraft source verification failed'
        jobs = getattr(request.app.state, 'research_jobs', None)
        available = jobs is not None and service_mode == 'persistent'
        return {**report, 'service_mode': service_mode,
                'synchronous_available': True, 'async_available': available,
                'persistence': {'available': available, 'kind': 'sqlite_local_volume' if available else 'none',
                                'retention_seconds': jobs.retention_seconds if available else None},
                'service_limits': {'max_request_bytes': MAX_REQUEST_BYTES,
                    'max_sync_response_bytes': MAX_SYNC_RESPONSE_BYTES, 'max_sync_seconds': sync_seconds,
                    'max_async_result_bytes': MAX_RESULT_BYTES if available else None,
                    'max_job_seconds': jobs.max_seconds if available else None,
                    'max_retained_bytes': MAX_RETAINED_BYTES if available else None,
                    'max_retained_jobs': jobs.max_jobs if available else None,
                    'max_workers': jobs.max_workers if available else 1,
                    'worker_memory_limit_bytes': MAX_WORKER_MEMORY_BYTES if sys.platform.startswith('linux') else None},
                'cancellation': {'synchronous': 'server deadline only; disconnect does not guarantee cancellation',
                                 'jobs': 'isolated worker termination' if available else 'unavailable'}}

    @router.post('/analyze')
    async def analyze(request: Request):
        study = await _request_study(request)
        if not synchronous_slot.acquire(blocking=False):
            raise HTTPException(429, 'One synchronous research calculation is already active')
        # The slot stays occupied if a caller disconnects while its worker is still alive.
        task = asyncio.create_task(asyncio.to_thread(run_sync, study, data_root=data_root, planner=planner,
                                             timeout_s=sync_seconds, result_limit=MAX_SYNC_RESPONSE_BYTES))
        task.add_done_callback(lambda finished: synchronous_slot.release())
        content = await asyncio.shield(task)
        return Response(content, media_type='application/json', headers={'Cache-Control': 'private, no-store'})

    @router.post('/jobs', status_code=202)
    async def submit(request: Request):
        jobs = store(request)
        study = await _request_study(request)
        return jobs.submit(study)

    @router.get('/jobs/{identifier}')
    def snapshot(identifier: str, request: Request):
        return store(request).snapshot(identifier)

    @router.delete('/jobs/{identifier}')
    def cancel(identifier: str, request: Request):
        return store(request).cancel(identifier)

    @router.get('/jobs/{identifier}/export')
    def export(identifier: str, request: Request):
        content, digest = store(request).package(identifier)
        return Response(content, media_type='application/zip', headers={
            'Content-Disposition': f'attachment; filename="soma-research-{identifier}.zip"',
            'X-SOMA-Study-SHA256': digest, 'Cache-Control': 'private, no-store'})

    return router
