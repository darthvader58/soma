"""Audit built archives, then test a fresh wheel install outside the checkout."""

import argparse
from pathlib import Path, PurePosixPath
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


def audit(path):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(path) as archive:
            names = [member.name for member in archive.getmembers() if member.isfile()]
    forbidden = {".env", ".git", ".venv", "__pycache__", "node_modules", "AGENTS.md", "AGENTS-B.md"}
    forbidden_suffixes = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".jp2", ".bsp"}
    for name in names:
        member = PurePosixPath(name)
        if (member.is_absolute() or ".." in member.parts or forbidden.intersection(member.parts)
                or member.name.startswith(".env.") or member.suffix.lower() in forbidden_suffixes
                or "soma/docs/" in name):
            raise ValueError(f"Unexpected distribution member: {name}")
    for suffix in ("schemas/scenario.schema.json", "schemas/result.schema.json",
                   "schemas/contact.schema.json", "schemas/allocation.schema.json",
                   "data/phase4-synthetic.manifest.json", "data/pinned/README.md",
                   "data/pinned/earth_000101_270208_261113.bpc",
                   "fixtures/synthetic-relay/scenario.json", "fixtures/synthetic-direct/scenario.json",
                   "LICENSE", "THIRD_PARTY_NOTICES.md"):
        if not any(name.endswith("/" + suffix) for name in names):
            raise ValueError(f"Distribution omits {suffix}: {path.name}")
    print(f"Archive audit passed: {path.name} ({path.stat().st_size:,} bytes)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    wheels = sorted(args.dist_dir.glob("*.whl"))
    sources = sorted(args.dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        parser.error("Expected exactly one wheel and one source distribution")
    for path in [*wheels, *sources]:
        audit(path)
    if args.audit_only:
        return
    test = Path(__file__).resolve().parents[1] / "tests/engine/test_distribution.py"
    with tempfile.TemporaryDirectory(prefix="soma-wheel-check-") as directory:
        root = Path(directory)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        working = root / "work"
        working.mkdir()
        subprocess.run([str(python), "-m", "pip", "install", f"{wheels[0].resolve()}[planning]", "pytest"],
                       cwd=working, check=True)
        subprocess.run([str(python), "-m", "pip", "check"], cwd=working, check=True)
        shutil.copyfile(test, working / "test_distribution.py")
        env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
        env["SOMA_INSTALLED_DISTRIBUTION_TEST"] = "1"
        subprocess.run([str(python), "-m", "pytest", "-q", "test_distribution.py"],
                       cwd=working, env=env, check=True)


if __name__ == "__main__":
    main()
