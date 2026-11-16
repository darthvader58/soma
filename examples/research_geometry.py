"""Reproduce the live workbench's three-site reconstructed LRO study."""

import argparse
import json
from pathlib import Path

from soma.research import analyze_study, study_sha256
from soma.research.catalog import resolve_site


def study_request():
    fields = ("id", "name", "latitude_deg", "longitude_deg_east", "elevation_m",
              "antenna_height_m", "panel_height_m")
    sites = [resolve_site(identifier) for identifier in ("apollo-11", "shackleton", "tycho")]
    return {
        "study_version": "1.0.0", "analysis_type": "geometry", "frame": "MOON_ME_DE421",
        "reference_radius_m": 1737400, "surface_model": "reference_sphere",
        "sites": [{key: site[key] for key in fields} for site in sites],
        "time": {"start_utc": "2026-04-01T00:00:00Z", "end_utc": "2026-04-01T06:00:00Z", "step_s": 60},
        "spacecraft_refs": ["lro-reconstructed-2026-spring"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    request = study_request()
    result = analyze_study(request, data_root=args.data_root)
    assert result["study_sha256"] == study_sha256(request)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "study_sha256": result["study_sha256"], "status": result["status"],
        "epochs": len(result["epochs_utc"]), "frame": result["frame"],
        "sites": [{"id": site["id"], **site["summary"]} for site in result["sites"]],
        "spacecraft": [{"id": item["id"], "samples": len(item["samples"])} for item in result["spacecraft"]],
    }, indent=2))


if __name__ == "__main__":
    main()
