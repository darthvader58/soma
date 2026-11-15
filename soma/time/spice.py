"""UTC boundary conversion through the active, checksummed SPICE LSK."""
from . import parse_utc, format_utc


def utc_to_et(value):
    import spiceypy as spice
    normalized = format_utc(parse_utc(value))
    return float(spice.str2et(normalized.removesuffix("Z").replace("T", " ") + " UTC"))
