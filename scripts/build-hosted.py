"""Prepare scientific assets before the separate Vercel function packaging step."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    print('Scientific build interpreter:', sys.version, flush=True)
    with tempfile.TemporaryDirectory(prefix='soma-build-dependencies-') as directory:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                        '--target', directory, '-r', str(ROOT/'requirements.txt')], check=True)
        environment = os.environ.copy()
        environment['PYTHONPATH'] = os.pathsep.join([directory, str(ROOT)])
        for script, arguments in (
            ('prepare-hosted-runtime.py', []),
            ('prepare-research-data.py', []),
            ('prepare-delivery-data.py', ['--output', str(ROOT/'api'/'_data')]),
        ):
            subprocess.run([sys.executable, str(ROOT/'scripts'/script), *arguments],
                           cwd=ROOT, env=environment, check=True)
    subprocess.run(['npm', '--prefix', 'web', 'run', 'build'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
