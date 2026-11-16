"""Acquire pinned scientific sources at build/setup time, never during requests."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CORE_ROLES = {'planetary_ephemeris', 'leap_seconds', 'lunar_frame', 'lunar_orientation'}
MAX_TOTAL_BYTES = 64_000_000


def verified(path, item):
    if not path.is_file() or path.stat().st_size != item['size_bytes']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256']


def prepare(output, *, source_root=None, include_lro=True):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / 'data/de421-phase2.manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    items = [item for item in manifest['kernels'] if item['role'] in CORE_ROLES]
    if {item['role'] for item in items} != CORE_ROLES:
        raise ValueError('Pinned manifest does not contain a complete four-role DE421 set')
    records = [{'path': manifest_path.name, 'sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}]
    lro_path = ROOT / 'data/research-lro.manifest.json'
    if include_lro and lro_path.is_file():
        lro = json.loads(lro_path.read_bytes())
        items.append(lro)
        records.append({'path': lro_path.name, 'sha256': hashlib.sha256(lro_path.read_bytes()).hexdigest()})
    if sum(item['size_bytes'] for item in items) > MAX_TOTAL_BYTES:
        raise ValueError('Pinned research sources exceed the 64MB build-time acquisition budget')
    for item in items:
        relative = Path(item['path'])
        destination = (output / relative).resolve()
        if relative.is_absolute() or not destination.is_relative_to(output):
            raise ValueError('Source path must remain beneath the output directory')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not verified(destination, item):
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.source-', delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    cached = Path(source_root) / relative if source_root else None
                    if cached is not None and verified(cached, item):
                        with cached.open('rb') as source:
                            shutil.copyfileobj(source, stream)
                    else:
                        parsed = urlsplit(item['source_url'])
                        if parsed.scheme != 'https' or parsed.hostname != 'naif.jpl.nasa.gov':
                            raise ValueError('Research source is not a pinned HTTPS NAIF archive object')
                        start, total = time.monotonic(), 0
                        with urlopen(Request(item['source_url'], headers={'User-Agent': 'SOMA-research-data/1'}), timeout=60) as source:
                            while chunk := source.read(1024 * 1024):
                                total += len(chunk)
                                if total > item['size_bytes'] or time.monotonic() - start > 180:
                                    raise ValueError('Research source acquisition exceeded size or time budget')
                                stream.write(chunk)
                    stream.flush()
                    if not verified(temporary, item):
                        raise ValueError('Research source SHA256 or size mismatch: ' + relative.name)
                    temporary.replace(destination)
                finally:
                    temporary.unlink(missing_ok=True)
        records.append({'path': str(relative), 'sha256': item['sha256'], 'size_bytes': item['size_bytes'],
                        'source_url': item['source_url']})
    (output / 'prepared-sources.json').write_text(json.dumps({'version': '1.0.0', 'files': records}, indent=2) + '\n')
    print(f'Verified {len(items)} research source files ({sum(item["size_bytes"] for item in items)} bytes)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'api/_data')
    parser.add_argument('--source-root', type=Path, help='Reuse already acquired files after checksum verification')
    parser.add_argument('--without-lro', action='store_true', help='Prepare the Sun/Earth core without the optional archived LRO source')
    args = parser.parse_args()
    prepare(args.output, source_root=args.source_root, include_lro=not args.without_lro)
