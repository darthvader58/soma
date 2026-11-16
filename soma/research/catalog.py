"""Published location catalog with explicit reference-sphere display positions."""

from copy import deepcopy
import hashlib

from soma.geometry.surface import surface_position
from soma.validation import load_json, resource_directory


def site_catalog():
    """Return detached source coordinates and Python-derived context markers.

    Zero marker elevation is a model choice, not a measured terrain height.
    Coordinate-realization notes remain attached to each published location.
    """
    path = resource_directory("data") / "research-sites.json"
    catalog = load_json(path)
    if catalog["frame"] != "MOON_ME_DE421" or catalog["reference_radius_m"] != 1737400:
        raise ValueError("unsupported research catalog frame or reference radius")
    identifiers = set()
    sites = []
    for source in catalog["sites"]:
        if source["id"] in identifiers or not source["source_urls"]:
            raise ValueError("catalog sites require unique identifiers and source URLs")
        identifiers.add(source["id"])
        site = deepcopy(source)
        site.update(
            elevation_m=0,
            antenna_height_m=2,
            panel_height_m=1,
            frame=catalog["frame"],
            reference_radius_m=catalog["reference_radius_m"],
            elevation_input_class="assumed_reference_sphere",
            terrain_alignment="context_only_not_registered",
            position_m=surface_position(site["latitude_deg"], site["longitude_deg_east"],
                                        catalog["reference_radius_m"]).tolist(),
        )
        sites.append(site)
    return {**catalog, "sites": sites, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def resolve_site(identifier):
    """Resolve a published catalog ID without relocating or inventing a site."""
    for site in site_catalog()["sites"]:
        if site["id"] == identifier:
            return site
    raise ValueError(f"unknown research catalog site: {identifier}")
