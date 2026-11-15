"""Strict civil-time boundary; SPICE UTC/TDB conversion is not implemented yet."""

from datetime import datetime, timezone
import re

__all__ = ["parse_utc", "format_utc"]

_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?P<clock_hour>[0-9]{2}):(?P<clock_minute>[0-9]{2}):"
    r"(?P<second>[0-9]{2})(?:\.[0-9]{1,6})?"
    r"(?P<offset>Z|[+-](?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}))"
)


def parse_utc(value: str) -> datetime:
    """Parse seconds-resolution RFC 3339 input and normalize it to aware UTC.

    Fractional seconds support at most six digits. Leap seconds require a
    future kernel-backed time layer and are rejected rather than rounded.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a timezone-qualified RFC 3339 string")
    match = _TIMESTAMP.fullmatch(value)
    if match is None:
        raise ValueError("timestamp requires YYYY-MM-DDTHH:MM:SS[.ffffff] and Z or ±HH:MM")
    if match["offset"] == "-00:00":
        raise ValueError("unknown UTC offset -00:00 is not supported")
    if match["offset"] != "Z" and (
        int(match["hour"]) > 23 or int(match["minute"]) > 59
    ):
        raise ValueError("timestamp timezone offset is out of range")
    if match["second"] == "60":
        raise ValueError("leap seconds are not supported by the civil-time boundary")
    if int(match["clock_hour"]) > 23 or int(match["clock_minute"]) > 59 or int(match["second"]) > 59:
        raise ValueError("timestamp clock time is out of range")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise ValueError("timestamp has an invalid calendar date, time, or UTC range") from error


def format_utc(value: datetime) -> str:
    """Format an aware datetime in UTC with its microsecond value preserved."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("format_utc requires a timezone-aware datetime")
    try:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError) as error:
        raise ValueError("datetime cannot be represented within the supported UTC range") from error
