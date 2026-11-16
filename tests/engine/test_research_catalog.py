"""Published coordinates remain distinct from assumed display elevation."""
import math

import pytest

from soma.research.catalog import resolve_site, site_catalog


def test_nasa_de421_coordinates_and_context_quality_survive_catalog():
    catalog = site_catalog()
    apollo = resolve_site("apollo-11")
    assert (apollo["latitude_deg"], apollo["longitude_deg_east"]) == (0.67416, 23.47314)
    assert apollo["frame"] == "MOON_ME_DE421"
    assert "NASA NSSDCA" in apollo["coordinate_notes"]
    assert apollo["source_urls"] == ["https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html"]
    for site in catalog["sites"]:
        assert site["source_urls"] and site["coordinate_notes"]
        assert math.isclose(math.hypot(*site["position_m"]), 1737400, abs_tol=1e-8)
        assert site["terrain_alignment"] == "context_only_not_registered"
        assert site["elevation_input_class"] == "assumed_reference_sphere"
    assert len({site["id"] for site in catalog["sites"]}) == len(catalog["sites"])


def test_catalog_is_detached_and_unknown_site_cannot_be_substituted():
    first = site_catalog()
    first["sites"][0]["source_urls"].clear()
    first["sites"][0]["latitude_deg"] = 90
    assert resolve_site("apollo-11")["latitude_deg"] == 0.67416
    assert resolve_site("apollo-11")["source_urls"]
    with pytest.raises(ValueError, match="unknown research catalog site"):
        resolve_site("invented-landing-region")
