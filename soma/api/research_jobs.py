"""Single-host durable research jobs with process-isolated scientific workers."""

import hashlib
import io
import importlib
import json
import multiprocessing
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile

from fastapi import HTTPException

from soma.api.native import preload_hosted_libraries
from soma.api.processes import start_private_interpreter, stop_private_interpreter

MAX_RESULT_BYTES = 16_000_000
MAX_EXPORT_BYTES = 32_000_000
MAX_RETAINED_BYTES = 128_000_000
MAX_JOB_SECONDS = 300
MAX_WORKER_MEMORY_BYTES = 1536 * 1024 * 1024
RETENTION_SECONDS = 7 * 24 * 3600
TERMINAL = ('completed', 'failed', 'canceled')
NUMERICAL_THREAD_VARIABLES = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                              'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def configure_numerical_threads():
    # Native thread stacks count against the worker's address-space budget.
    # Override inherited host defaults such as OPENBLAS_NUM_THREADS=32 before spawn.
    for variable in NUMERICAL_THREAD_VARIABLES:
        os.environ[variable] = '1'


def encode(document):
    return json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()


def _atomic_write(path, content):
    temporary = path.with_suffix(path.suffix + '.partial')
    with temporary.open('wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _worker(study, directory, data_root, progress_queue, canceled, planner, result_limit):
    configure_numerical_threads()
    if hasattr(os, 'setsid') and os.getpgrp() != os.getpid():
        os.setsid()
    try:
        preload_hosted_libraries()
        if sys.platform.startswith('linux'):
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (MAX_WORKER_MEMORY_BYTES, MAX_WORKER_MEMORY_BYTES))
            resource.setrlimit(resource.RLIMIT_CPU, (MAX_JOB_SECONDS, MAX_JOB_SECONDS))
        if planner is None:
            from soma.research import analyze_study
            planner = analyze_study

        def progress(value, *args, **kwargs):
            stage = value.get('stage') if isinstance(value, dict) else value
            if progress_queue is not None and isinstance(stage, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', stage):
                try:
                    progress_queue.put_nowait(stage)
                except queue.Full:
                    pass

        result = planner(study, data_root=data_root, progress=progress, cancel_event=canceled)
        if canceled is not None and canceled.is_set():
            return
        content = encode(result)
        if len(content) > result_limit:
            raise OverflowError('Research result exceeds response limit')
        _atomic_write(Path(directory, 'result.json'), content)
    except BaseException as error:
        # Scientific library messages may contain private source paths or signed URLs.
        failure = {'error_type': type(error).__name__}
        if failure['error_type'] == 'StudyValidationError':
            message = str(error).lower()
            if 'coverage' in message or 'interval' in message:
                failure.update(status_code=422, detail='Requested interval is outside configured kernel or spacecraft coverage')
            elif 'missing' in message or 'sha256' in message or 'size' in message:
                failure.update(status_code=503, detail='Required scientific source is missing or failed checksum verification')
            elif 'spacecraft reference' in message:
                failure.update(status_code=422, detail='Spacecraft reference is not a configured public source')
            else:
                failure.update(status_code=422, detail='Study cannot be evaluated with the configured scientific sources')
        _atomic_write(Path(directory, 'error.json'), encode(failure))


def _stop(process):
    grouped = False
    if hasattr(os, 'getpgid') and process.pid:
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


def _release(process, progress_queue):
    if process is not None:
        process.join(timeout=0)
        process.close()
    progress_queue.close()
    progress_queue.join_thread()


def _read_result(directory, limit):
    error = directory / 'error.json'
    if error.exists():
        failure = json.loads(error.read_bytes())
        kind = failure.get('error_type', 'WorkerError')
        if kind == 'OverflowError':
            raise HTTPException(413, 'Research result exceeds response budget; reduce sites or epochs')
        raise HTTPException(failure.get('status_code', 503), failure.get('detail',
                            'Scientific calculation unavailable; check data coverage and capabilities'))
    path = directory / 'result.json'
    if not path.is_file() or path.stat().st_size > limit:
        raise HTTPException(503, 'Scientific worker produced no bounded result')
    return path.read_bytes()


def _verify_result(study, content):
    from soma.research import study_sha256
    result = json.loads(content)
    if (result.get('study_sha256') != study_sha256(study)
            or result.get('request') != study or result.get('status') != 'completed'):
        raise ValueError('Worker result does not match the submitted study')
    return result


def _stop_subprocess(process):
    stop_private_interpreter(process)

def _sync_worker_main(control_path):
    """Read parent-created control metadata; this is never an HTTP input format."""
    control_path = Path(control_path)
    control = json.loads(control_path.read_bytes())
    planner = None
    if control['planner'] is not None:
        planner = importlib.import_module(control['planner']['module'])
        for name in control['planner']['qualname'].split('.'):
            planner = getattr(planner, name)
    _worker(control['study'], str(control_path.parent), control['data_root'], None, None,
            planner, control['result_limit'])


def run_sync(study, *, data_root=None, planner=None, timeout_s=60, result_limit=4_000_000):
    """Execute a private interpreter without re-importing the server's __main__."""
    configure_numerical_threads()
    planner_reference = None
    if planner is not None:
        if '<' in planner.__qualname__ or planner.__module__ == '__main__':
            raise ValueError('Injected synchronous planner must be an importable module-level callable')
        planner_reference = {'module': planner.__module__, 'qualname': planner.__qualname__}
    with tempfile.TemporaryDirectory(prefix='soma-research-sync-') as directory:
        control_path = Path(directory, 'input.json')
        _atomic_write(control_path, encode({'study': study, 'data_root': str(data_root) if data_root else None,
                                           'planner': planner_reference, 'result_limit': result_limit}))
        environment = os.environ.copy()
        # Retain the function's installed/bundled module paths without inheriting its bootstrap.
        environment['PYTHONPATH'] = os.pathsep.join(str(path or os.getcwd()) for path in sys.path)
        process = start_private_interpreter([sys.executable, '-m', 'soma.api.research_jobs', str(control_path)], env=environment)
        try:
            try:
                process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                _stop_subprocess(process)
                raise HTTPException(504, 'Synchronous research time budget exceeded; reduce study size') from None
            if process.returncode != 0:
                raise HTTPException(503, 'Scientific worker exited before producing a result')
            content = _read_result(Path(directory), result_limit)
            _verify_result(study, content)
            return content
        finally:
            _stop_subprocess(process)


def create_package(study, result_content):
    files = {'study.json': encode(study), 'result.json': result_content}
    manifest = {'package_version': '1.0.0', 'study_sha256': json.loads(result_content)['study_sha256'],
                'files': {name: {'sha256': hashlib.sha256(value).hexdigest(), 'size_bytes': len(value)}
                          for name, value in files.items()}}
    files['run-manifest.json'] = encode(manifest)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, value)
    return buffer.getvalue()


class ResearchJobStore:
    """One service owner per local volume; completed SQLite artifacts survive restart."""

    def __init__(self, root, *, planner=None, data_root=None, max_workers=1, max_jobs=32,
                 max_seconds=MAX_JOB_SECONDS, retention_seconds=RETENTION_SECONDS):
        if not 1 <= max_workers <= 4 or not 1 <= max_jobs <= 128:
            raise ValueError('Research service requires 1..4 workers and 1..128 jobs')
        if not 0 < max_seconds <= MAX_JOB_SECONDS or not 0 < retention_seconds <= RETENTION_SECONDS:
            raise ValueError('Research service time and retention bounds cannot be increased')
        import fcntl
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.owner = (self.root / '.owner.lock').open('a+b')
        try:
            fcntl.flock(self.owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.owner.close()
            raise RuntimeError('Research job volume already has an owner; use one Uvicorn process') from None
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / 'jobs.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, study_hash TEXT NOT NULL, request BLOB NOT NULL,
            status TEXT NOT NULL, stage TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
            result BLOB, package BLOB, error TEXT, worker_pid INTEGER)''')
        self.db.execute("UPDATE jobs SET status='failed', stage='interrupted', error='Service restarted before job completion', updated=? WHERE status IN ('queued','running')", (time.time(),))
        self.db.commit()
        self.planner, self.data_root = planner, str(data_root) if data_root else None
        self.max_workers, self.max_jobs = max_workers, max_jobs
        self.max_seconds, self.retention_seconds = max_seconds, retention_seconds
        self.context = multiprocessing.get_context('spawn')
        self.active = {}
        self.stopping = threading.Event()
        for directory in self.root.glob('worker-*'):
            if directory.is_dir() and not directory.is_symlink():
                shutil.rmtree(directory)
        self._prune()
        self.thread = threading.Thread(target=self._monitor, name='soma-research-jobs', daemon=True)
        self.thread.start()

    def _prune(self):
        self.db.execute("DELETE FROM jobs WHERE status IN ('completed','failed','canceled') AND updated < ?",
                        (time.time() - self.retention_seconds,))
        self.db.commit()
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def submit(self, study):
        from soma.research import study_sha256
        with self.lock:
            self._prune()
            count, retained = self.db.execute('SELECT COUNT(*), COALESCE(SUM(length(request)+COALESCE(length(result),0)+COALESCE(length(package),0)),0) FROM jobs').fetchone()
            if count >= self.max_jobs or retained + len(encode(study)) > MAX_RETAINED_BYTES:
                raise HTTPException(429, 'Research job retention budget reached')
            identifier, now, digest = uuid.uuid4().hex, time.time(), study_sha256(study)
            self.db.execute('INSERT INTO jobs (id,study_hash,request,status,stage,created,updated) VALUES (?,?,?,?,?,?,?)',
                            (identifier, digest, encode(study), 'queued', 'validation', now, now))
            self.db.commit()
            return {'job_id': identifier, 'study_sha256': digest, 'status': 'queued'}

    def _row(self, identifier):
        if not re.fullmatch(r'[a-f0-9]{32}', identifier):
            raise HTTPException(404, 'Unknown research job')
        row = self.db.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise HTTPException(404, 'Unknown research job')
        return row

    def snapshot(self, identifier):
        with self.lock:
            row = self._row(identifier)
            return {'job_id': row['id'], 'study_sha256': row['study_hash'], 'status': row['status'],
                    'stage': row['stage'], 'result': json.loads(row['result']) if row['result'] else None,
                    'error': row['error'], 'worker_pid': row['worker_pid']}

    def package(self, identifier):
        with self.lock:
            row = self._row(identifier)
            if row['status'] != 'completed':
                raise HTTPException(409, 'Export requires a completed research job')
            return bytes(row['package']), row['study_hash']

    def _update(self, identifier, **values):
        values['updated'] = time.time()
        columns = ','.join(f'{key}=?' for key in values)
        self.db.execute(f'UPDATE jobs SET {columns} WHERE id=?', (*values.values(), identifier))
        self.db.commit()

    def _cleanup(self, identifier):
        active = self.active.pop(identifier)
        _release(active['process'], active['queue'])
        shutil.rmtree(active['directory'])

    def _poll(self):
        for identifier, active in list(self.active.items()):
            process = active['process']
            while True:
                try:
                    stage = active['queue'].get_nowait()
                    self._update(identifier, stage=stage)
                except queue.Empty:
                    break
            if process.is_alive() and time.monotonic() - active['started'] > self.max_seconds:
                active['canceled'].set()
                _stop(process)
                self._update(identifier, status='failed', stage='timeout', error='Research worker time budget exceeded')
                self._cleanup(identifier)
                continue
            if process.is_alive():
                continue
            try:
                if process.exitcode != 0:
                    raise RuntimeError('Research worker exited before producing a result')
                content = _read_result(active['directory'], MAX_RESULT_BYTES)
                study = json.loads(self._row(identifier)['request'])
                _verify_result(study, content)
                package = create_package(study, content)
                retained = self.db.execute('SELECT COALESCE(SUM(length(request)+COALESCE(length(result),0)+COALESCE(length(package),0)),0) FROM jobs').fetchone()[0]
                if len(package) > MAX_EXPORT_BYTES or retained + len(content) + len(package) > MAX_RETAINED_BYTES:
                    raise OverflowError('Research retained artifact byte budget exceeded')
                self._update(identifier, status='completed', stage='export', result=content, package=package)
            except HTTPException as error:
                self._update(identifier, status='failed', stage='failed', error=error.detail)
            except Exception:
                self._update(identifier, status='failed', stage='failed', error='Research worker result could not be accepted')
            finally:
                self._cleanup(identifier)
        queued = self.db.execute("SELECT id,request FROM jobs WHERE status='queued' ORDER BY created").fetchall()
        for row in queued:
            if len(self.active) >= self.max_workers:
                break
            identifier = row['id']
            directory = self.root / ('worker-' + identifier)
            directory.mkdir(mode=0o700)
            progress_queue, canceled = self.context.Queue(maxsize=64), self.context.Event()
            process = self.context.Process(target=_worker, args=(json.loads(row['request']), str(directory),
                            self.data_root, progress_queue, canceled, self.planner, MAX_RESULT_BYTES))
            try:
                configure_numerical_threads()
                process.start()
                self.active[identifier] = {'process': process, 'queue': progress_queue, 'canceled': canceled,
                                          'directory': directory, 'started': time.monotonic()}
                self._update(identifier, status='running', stage='geometry', worker_pid=process.pid)
            except Exception:
                if process.pid:
                    _stop(process)
                    _release(process, progress_queue)
                else:
                    process.close()
                    progress_queue.close()
                shutil.rmtree(directory)
                self._update(identifier, status='failed', stage='failed', error='Unable to start research worker')

    def _monitor(self):
        while not self.stopping.wait(0.05):
            with self.lock:
                self._poll()

    def cancel(self, identifier):
        with self.lock:
            row = self._row(identifier)
            if row['status'] in TERMINAL:
                return self.snapshot(identifier)
            if identifier in self.active:
                active = self.active[identifier]
                active['canceled'].set()
                _stop(active['process'])
                self._cleanup(identifier)
            self._update(identifier, status='canceled', stage='canceled')
            return self.snapshot(identifier)

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=2)
        with self.lock:
            for identifier, active in list(self.active.items()):
                active['canceled'].set()
                _stop(active['process'])
                self._update(identifier, status='failed', stage='interrupted', error='Service stopped before job completion')
                self._cleanup(identifier)
            self.db.execute("UPDATE jobs SET status='failed',stage='interrupted',error='Service stopped before job completion',updated=? WHERE status='queued'", (time.time(),))
            self.db.commit()
            self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            self.db.close()
            self.owner.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Expected a parent-created research worker control file')
    _sync_worker_main(sys.argv[1])
