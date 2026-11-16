from pathlib import Path
import runpy
import subprocess


def test_build_dependencies_are_available_before_scientific_preparation(monkeypatch):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs.get('env', {}).get('PYTHONPATH')))

    monkeypatch.setattr(subprocess, 'run', run)
    runpy.run_path('scripts/build-hosted.py')['main']()
    install = calls[0][0]
    assert install[1:4] == ['-m', 'pip', 'install']
    dependency_root = install[install.index('--target')+1]
    assert [Path(argv[1]).name for argv, _ in calls[1:4]] == [
        'prepare-hosted-runtime.py', 'prepare-research-data.py', 'prepare-delivery-data.py']
    assert all(search_path.split(':')[0] == dependency_root for _, search_path in calls[1:4])
    assert calls[-1][0] == ['npm', '--prefix', 'web', 'run', 'build']
