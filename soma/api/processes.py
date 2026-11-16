"""Private interpreter launch without fork callbacks in macOS native libraries."""
import os
import signal
import subprocess
import sys
import threading
import time


class SpawnedProcess:
    """The wait/poll subset used by synchronous scientific workers."""
    def __init__(self, argv, environment):
        self.args = argv
        self.returncode = None
        self._lock = threading.Lock()
        actions = [(os.POSIX_SPAWN_OPEN, fd, os.devnull, os.O_RDWR, 0o600) for fd in (0, 1, 2)]
        # Unlike Popen(start_new_session=True), this calls the platform spawn
        # syscall directly, without invoking native at-fork callbacks.
        self.pid = os.posix_spawn(argv[0], argv, environment, file_actions=actions, setsid=True,
                                  setsigmask=(), setsigdef=[getattr(signal, name) for name in
                                      ("SIGPIPE", "SIGXFZ", "SIGXFSZ") if hasattr(signal, name)])

    def poll(self):
        with self._lock:
            if self.returncode is None:
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid:
                    self.returncode = os.waitstatus_to_exitcode(status)
            return self.returncode

    def wait(self, timeout=None):
        deadline = None if timeout is None else time.monotonic()+timeout
        while self.poll() is None:
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self.args, timeout)
            time.sleep(.01)
        return self.returncode

    def terminate(self):
        os.kill(self.pid, signal.SIGTERM)

    def kill(self):
        os.kill(self.pid, signal.SIGKILL)


def start_private_interpreter(argv, *, env):
    if sys.platform == 'darwin':
        # If session-capable spawn is unavailable, fail explicitly; an unsafe
        # fork fallback would recreate the intermittent native-library crash.
        return SpawnedProcess(argv, env)
    return subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=os.name == 'posix')


def stop_private_interpreter(process):
    """Clean descendants even when their original interpreter already exited."""
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=1)
    elif process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)
