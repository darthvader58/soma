"""Seed verified image sources on a persistent volume, then start one store owner."""

import hashlib
import json
import os
from pathlib import Path
import shutil


def main():
    data_root = Path(os.environ.get('SOMA_DATA_ROOT', '/data/sources'))
    data_root.mkdir(parents=True, exist_ok=True)
    bundled = Path('/opt/soma-sources')
    manifest = json.loads((bundled / 'prepared-sources.json').read_bytes())
    for item in manifest['files']:
        if 'size_bytes' not in item:
            continue
        relative = Path(item['path'])
        target = (data_root / relative).resolve()
        if relative.is_absolute() or not target.is_relative_to(data_root.resolve()):
            raise ValueError('Bundled source path is outside data root')
        source = bundled / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Bundled scientific source checksum mismatch')
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.partial')
            shutil.copyfile(source, temporary)
            temporary.replace(target)
        if target.stat().st_size != item['size_bytes'] or hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Persistent scientific source checksum mismatch')
    port = int(os.environ.get('PORT', '8000'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be 1..65535')
    os.execvp('uvicorn', ['uvicorn', 'soma.api.app:app', '--host', '0.0.0.0', '--port', str(port), '--workers', '1'])


if __name__ == '__main__':
    main()
