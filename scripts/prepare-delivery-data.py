"""Prepare only pinned delivery inputs at build time; requests never download data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _verified(path, entry):
    if not path.is_file() or path.stat().st_size != entry["size_bytes"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == entry["sha256"]


def prepare(output, *, source_root=None):
    from soma.api.research_jobs import configure_numerical_threads
    configure_numerical_threads()
    from soma.api.native import preload_hosted_libraries
    preload_hosted_libraries()
    from soma.api.delivery import SOURCE_MANIFESTS, source_entries, solver_identity
    from soma.datasets import extract_lola_far_cap, extract_lola_window, fetch_kernels
    from soma.terrain.physical import acquire_polar_window
    from soma.validation import load_json
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    entries = source_entries()
    if sum(item["size_bytes"] for item in entries) > 100_000_000:
        raise ValueError("Pinned delivery inputs exceed the 100 MB source budget")
    source_root = Path(source_root).resolve() if source_root is not None else None
    for entry in entries:
        relative = Path(entry["path"])
        path = (output/relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(output):
            raise ValueError("Delivery source path escapes the output directory")
        if not _verified(path, entry) and source_root is not None:
            cached = (source_root/relative).resolve()
            if not cached.is_relative_to(source_root):
                raise ValueError("Delivery source path escapes the cache directory")
            if _verified(cached, entry):
                shutil.copyfile(cached, path)
    fetch_kernels(ROOT/"data"/SOURCE_MANIFESTS[0], output)
    terrain_entries = [entry for entry in entries if "role" in entry and entry["role"] in ("elevation", "count")]
    if any(not _verified(output/entry["path"], entry) for entry in terrain_entries):
        # Parent count mosaics and raw range extracts are build temporaries, not function assets.
        with tempfile.TemporaryDirectory(prefix="soma-delivery-acquisition-") as directory:
            scratch = Path(directory)
            for entry in terrain_entries:
                if _verified(output/entry["path"], entry):
                    shutil.copyfile(output/entry["path"], scratch/entry["path"])
            extract_lola_window(scratch, expected_manifest=load_json(ROOT/"data"/SOURCE_MANIFESTS[1]))
            extract_lola_far_cap(scratch, expected_manifest=load_json(ROOT/"data"/SOURCE_MANIFESTS[2]))
            acquire_polar_window(scratch, manifest=load_json(ROOT/"data"/SOURCE_MANIFESTS[3]))
            for entry in terrain_entries:
                if not _verified(scratch/entry["path"], entry):
                    raise ValueError("Reconstructed terrain source differs from its pinned bytes")
                shutil.copyfile(scratch/entry["path"], output/entry["path"])
    records = []
    for entry in entries:
        if not _verified(output/entry["path"], entry):
            raise ValueError("Prepared delivery source failed its final checksum")
        records.append({key: entry[key] for key in ("path", "sha256", "size_bytes", "manifest_ref")})
    solver = solver_identity(smoke=True)
    metadata = {"prepared_version": "1.0.0", "source_bytes": sum(item["size_bytes"] for item in entries),
                "files": records, "solver": solver,
                "scope": "Pinned regional LOLA/DE421 inputs; no captured schedule or result is bundled"}
    (output/"prepared-delivery-sources.json").write_text(json.dumps(metadata, indent=2)+"\n")
    print(f"Verified {len(records)} delivery sources ({metadata['source_bytes']} bytes) and CBC integer smoke test")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"api/_data")
    parser.add_argument("--source-root", type=Path, help="Reuse separately acquired files only after pinned hash verification")
    args = parser.parse_args()
    prepare(args.output, source_root=args.source_root)
