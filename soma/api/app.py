"""Bounded local jobs, with a fresh SPICE process for each scenario."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import json
import io
import multiprocessing
import os
from pathlib import Path
import queue
import signal
import tempfile
import threading
import time
import uuid
import zipfile

from fastapi import FastAPI, HTTPException, Request, Response

from soma.exports import create_run_package, display_payload, json_bytes, summary
from soma.validation import (ScenarioValidationError, _reject_constant, _unique_keys,
                             scenario_sha256, validate_document, validate_scenario)

STAGES = ("validation", "horizon_preparation", "contact_construction", "scheduling", "replay", "export")
MAX_REQUEST_BYTES = 2_000_000
MAX_RUN_BYTES = 8_000_000
MAX_RETAINED_BYTES = 128_000_000
MAX_JOB_SECONDS = 300


def _worker(scenario, directory, progress_queue, canceled, planner):
    if hasattr(os, "setsid"):
        os.setsid()
    def progress(stage, *args, **kwargs):
        if isinstance(stage, dict):
            stage = stage.get("stage")
        if stage in STAGES:
            try:
                progress_queue.put_nowait(stage)
            except queue.Full:
                pass
    try:
        if planner is None:
            from soma.engine import plan_run
            planner = plan_run
        run = planner(scenario, progress=progress, cancel_event=canceled)
        if canceled.is_set():
            return
        encoded = json_bytes(run)
        if len(encoded) > MAX_RUN_BYTES:
            raise ValueError("Run exceeds the local service result limit")
        Path(directory, "run.json").write_bytes(encoded)
    except Exception as error:
        Path(directory, "error.json").write_bytes(json_bytes({"error": f"{type(error).__name__}: {str(error)[:1000]}"}))


def _stop_process(process):
    # CBC and other worker children belong to the same isolated process group.
    grouped = False
    if hasattr(os, "getpgid"):
        try:
            grouped = os.getpgid(process.pid) == process.pid
        except ProcessLookupError:
            pass
    if grouped:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif process.is_alive():
        process.terminate()
    process.join(timeout=0.5)
    if grouped:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.is_alive():
        process.kill()
    process.join(timeout=0.5)


class JobStore:
    def __init__(self, *, planner, temp_root, max_workers, max_jobs):
        if not 1 <= max_workers <= 8 or not 1 <= max_jobs <= 128:
            raise ValueError("Require 1..8 workers and 1..128 retained jobs")
        self.context = multiprocessing.get_context("spawn")
        self.planner = planner
        self.max_workers, self.max_jobs = max_workers, max_jobs
        self.temp = tempfile.TemporaryDirectory(prefix="soma-jobs-", dir=temp_root)
        self.jobs = {}
        self.retained_bytes = 0
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._monitor, name="soma-jobs", daemon=True)
        self.thread.start()

    def submit(self, scenario):
        with self.lock:
            if len(self.jobs) >= self.max_jobs:
                raise HTTPException(429, "Local job retention limit reached; restart the service to clear retained jobs")
            identifier = uuid.uuid4().hex
            directory = Path(self.temp.name, identifier)
            directory.mkdir()
            self.jobs[identifier] = {"job_id": identifier, "status": "queued", "stage": "validation",
                "scenario_sha256": scenario_sha256(scenario), "result": None, "scenario": scenario,
                "directory": directory, "process": None, "run": None, "package": None,
                "queue": self.context.Queue(maxsize=64), "canceled": self.context.Event()}
            return {"job_id": identifier, "scenario_sha256": self.jobs[identifier]["scenario_sha256"]}

    def _release_worker_resources(self, job):
        process = job["process"]
        if process is not None:
            if process.is_alive():
                raise RuntimeError("Cannot release a live worker")
            process.join(timeout=0)
            process.close()
        progress_queue = job["queue"]
        if progress_queue is not None:
            progress_queue.close()
            # The parent never writes progress, so it has no pending feeder work.
            progress_queue.join_thread()
        # SemLock cleanup belongs to the creating parent and runs when these
        # references are released, including for workers killed during cancel.
        job.update(process=None, queue=None, canceled=None)

    def _monitor(self):
        while not self.stopping.wait(0.02):
            with self.lock:
                active = 0
                for job in self.jobs.values():
                    process = job["process"]
                    if job["status"] == "running":
                        while True:
                            try:
                                job["stage"] = job["queue"].get_nowait()
                            except queue.Empty:
                                break
                        if process.is_alive() and time.monotonic() - job["started_at"] > MAX_JOB_SECONDS:
                            _stop_process(process)
                            job.update(status="failed", error="Local worker time limit exceeded", result=None)
                            self._release_worker_resources(job)
                            continue
                        if process.is_alive():
                            active += 1
                            continue
                        process.join(timeout=0)
                        try:
                            if process.exitcode != 0:
                                raise ValueError(f"Worker exited with status {process.exitcode}")
                            error_path = job["directory"] / "error.json"
                            if error_path.exists():
                                raise ValueError(json.loads(error_path.read_text())["error"])
                            path = job["directory"] / "run.json"
                            if path.stat().st_size > MAX_RUN_BYTES:
                                raise ValueError("Run exceeds result limit")
                            run = json.loads(path.read_text())
                            validate_document(run["result"], "result")
                            if scenario_sha256(run["scenario"]) != job["scenario_sha256"] or run["result"]["scenario_sha256"] != job["scenario_sha256"]:
                                raise ValueError("Worker returned a different scenario")
                            job["stage"] = "export"
                            package = create_run_package(run)
                            if len(package) > MAX_RUN_BYTES * 2:
                                raise ValueError("Export exceeds package limit")
                            # Freeze display derivations with the same immutable completed run.
                            with zipfile.ZipFile(io.BytesIO(package)) as archive:
                                display_bytes = archive.read('display-data.json')
                                display = json.loads(display_bytes)
                            retained = path.stat().st_size * 2 + len(package) + len(display_bytes)
                            if self.retained_bytes + retained > MAX_RETAINED_BYTES:
                                raise ValueError("Local retained result byte limit reached")
                            self.retained_bytes += retained
                            job.update(run=run, result=deepcopy(run["result"]), package=package, display_data=display, status="completed")
                        except Exception as error:
                            job.update(status="failed", error=f"{type(error).__name__}: {str(error)[:1000]}")
                        finally:
                            self._release_worker_resources(job)
                for job in self.jobs.values():
                    if active >= self.max_workers:
                        break
                    if job["status"] != "queued":
                        continue
                    process = self.context.Process(target=_worker, args=(job["scenario"], str(job["directory"]), job["queue"], job["canceled"], self.planner))
                    try:
                        process.start()
                        job.update(process=process, status="running", worker_pid=process.pid, started_at=time.monotonic())
                        active += 1
                    except Exception as error:
                        process.close()
                        job.update(status="failed", error=f"Unable to start worker: {error}")
                        self._release_worker_resources(job)

    def get(self, identifier):
        job = self.jobs.get(identifier)
        if job is None:
            raise HTTPException(404, "Unknown job")
        return job

    def snapshot(self, identifier):
        with self.lock:
            job = self.get(identifier)
            return deepcopy({key: job[key] for key in ("job_id", "status", "stage", "scenario_sha256", "result", "error", "worker_pid") if key in job})

    def cancel(self, identifier):
        with self.lock:
            job = self.get(identifier)
            if job["status"] in ("completed", "failed", "canceled"):
                return self.snapshot(identifier)
            job["canceled"].set()
            process = job["process"]
            if process is not None:
                _stop_process(process)
            job.update(status="canceled", result=None, run=None, package=None)
            self._release_worker_resources(job)
            return self.snapshot(identifier)

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=1)
        for identifier in self.jobs:
            self.cancel(identifier)
        self.temp.cleanup()


def create_app(*, planner=None, temp_root=None, max_workers=2, max_jobs=32, moon_provider=None):
    """Planner injection is trusted startup configuration, never request data."""
    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs = JobStore(planner=planner, temp_root=temp_root, max_workers=max_workers, max_jobs=max_jobs)
        try:
            yield
        finally:
            await asyncio.to_thread(app.state.jobs.close)

    app = FastAPI(title="SOMA local planning service", lifespan=lifespan)
    from soma.api.moon import moon_router
    app.include_router(moon_router(moon_provider))

    @app.post("/plans", status_code=202)
    async def post_plan(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Scenario exceeds request limit")
        try:
            document = json.loads(body, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
            scenario = validate_scenario(document)
        except (ScenarioValidationError, ValueError, UnicodeError, RecursionError) as error:
            raise HTTPException(422, str(error)[:2000]) from error
        return app.state.jobs.submit(scenario)

    @app.get("/plans/{identifier}")
    def get_plan(identifier: str):
        return app.state.jobs.snapshot(identifier)

    @app.delete("/plans/{identifier}")
    def cancel_plan(identifier: str):
        return app.state.jobs.cancel(identifier)

    @app.get("/plans/{identifier}/export")
    def get_export(identifier: str):
        with app.state.jobs.lock:
            job = app.state.jobs.get(identifier)
            if job["status"] != "completed":
                raise HTTPException(409, "Export requires a completed job")
            return Response(job["package"], media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="soma-{identifier}.zip"', "X-SOMA-Scenario-SHA256": job['scenario_sha256']})

    @app.get("/plans/{identifier}/summary")
    def get_summary(identifier: str):
        with app.state.jobs.lock:
            job = app.state.jobs.get(identifier)
            if job["status"] != "completed":
                raise HTTPException(409, "Summary requires a completed job")
            return summary(job["run"])

    @app.get("/plans/{identifier}/display")
    def get_display(identifier: str):
        with app.state.jobs.lock:
            job = app.state.jobs.get(identifier)
            if job["status"] != "completed":
                raise HTTPException(409, "Display requires a completed job")
            return display_payload(job["run"])

    @app.get("/plans/{identifier}/display-data")
    def get_display_data(identifier: str):
        with app.state.jobs.lock:
            job = app.state.jobs.get(identifier)
            if job["status"] != "completed":
                raise HTTPException(409, "Display data requires a completed job")
            return deepcopy(job["display_data"])

    @app.get("/plans/{identifier}/renderer-registration")
    def get_registration(identifier: str):
        with app.state.jobs.lock:
            job = app.state.jobs.get(identifier)
            if job["status"] != "completed":
                raise HTTPException(409, "Registration requires a completed job")
            return deepcopy(job["display_data"]["registration"])

    return app


app = create_app()
