"""Bundle the build image's Expat library required by the Rasterio wheel."""

import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess


def prepare():
    if platform.system() != "Linux":
        print("Hosted native-library preparation skipped outside Linux")
        return
    source = next((p for p in (Path("/lib64/libexpat.so.1"),
                               Path("/usr/lib64/libexpat.so.1")) if p.is_file()), None)
    if source is None:
        raise RuntimeError("Build image is missing libexpat.so.1")
    source = source.resolve()
    package = subprocess.check_output(
        ["rpm", "-qf", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}", str(source)],
        text=True).strip()
    package_license = subprocess.check_output(
        ["rpm", "-qf", "--qf", "%{LICENSE}", str(source)], text=True).strip()
    files = subprocess.check_output(["rpm", "-ql", package], text=True).splitlines()
    licenses = [Path(p) for p in files if "/licenses/" in p and Path(p).is_file()]
    if not licenses:
        raise RuntimeError("Expat package license text is missing from the build image")
    output = Path(__file__).resolve().parents[1] / "api" / "_native"
    output.mkdir(parents=True, exist_ok=True)
    target = output / "libexpat.so.1"
    shutil.copyfile(source, target)
    license_records = []
    for number, license_path in enumerate(licenses):
        copied = output / f"expat-license-{number}.txt"
        shutil.copyfile(license_path, copied)
        license_records.append({"file": copied.name, "source": str(license_path),
                                "sha256": hashlib.sha256(copied.read_bytes()).hexdigest()})
    manifest = {"purpose": "Runtime dependency for Rasterio; no scientific algorithm changes",
                "platform": platform.system(), "architecture": platform.machine(),
                "package": package, "license": package_license,
                "upstream": "https://libexpat.github.io/", "source": str(source),
                "file": target.name, "size_bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "license_files": license_records}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared hosted Expat runtime dependency:", package)


if __name__ == "__main__":
    prepare()
