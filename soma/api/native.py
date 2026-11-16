"""Load verified bundled native dependencies in each fresh hosted interpreter."""
import ctypes
import hashlib
import json
import os
from pathlib import Path

_native_handles = []


def preload_hosted_libraries(directory=None):
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parents[2]/'api'/'_native'
    manifest_path = directory/'manifest.json'
    if not manifest_path.is_file():
        if os.environ.get('VERCEL') == '1':
            raise ImportError('Hosted native dependency manifest is missing')
        return
    manifest = json.loads(manifest_path.read_text())
    library = directory/'libexpat.so.1'
    if manifest.get('file') != library.name or hashlib.sha256(library.read_bytes()).hexdigest() != manifest.get('sha256'):
        raise ImportError('Hosted Expat dependency checksum mismatch')
    _native_handles.append(ctypes.CDLL(str(library.resolve()), mode=ctypes.RTLD_GLOBAL))
