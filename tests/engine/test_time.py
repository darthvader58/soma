from datetime import datetime, timedelta, timezone

import pytest

from soma.time import format_utc, parse_utc


@pytest.mark.parametrize("timestamp", [
    "2026-11-14T08:50:00Z",
    "2026-11-14T01:50:00-07:00",
    "2026-11-14T14:20:00+05:30",
    "2026-11-15T00:20:00+15:30",
])
def test_offsets_normalize_to_utc(timestamp):
    assert parse_utc(timestamp) == datetime(2026, 11, 14, 8, 50, tzinfo=timezone.utc)
    assert parse_utc(timestamp).tzinfo is timezone.utc


@pytest.mark.parametrize("timestamp", [
    None, True, 123, "", "2026-11-14", "2026-11-14T08:50:00",
    "2026-11-14 08:50:00Z", "2026-11-14t08:50:00z",
    "2026-11-14T08:50Z", "2026-11-14T08:50:00+0530",
    "2026-11-14T08:50:00-00:00", "2026-11-14T08:50:00+24:00",
    "2026-11-14T08:50:00+00:60", "2026-11-14T24:00:00Z",
    "2026-02-29T08:50:00Z", "2026-11-14T08:50:60Z",
    "2026-11-14T08:50:00.1234567Z", "2026-11-14T08:50:00.Z",
    "2026-11-14T08:50:00Z\n", "0001-01-01T00:00:00+01:00",
    "9999-12-31T23:59:59-01:00", "２０２６-11-14T08:50:00Z",
])
def test_invalid_boundary_timestamps_fail(timestamp):
    with pytest.raises(ValueError):
        parse_utc(timestamp)


@pytest.mark.parametrize("fraction", ["1", "123456", "000001"])
def test_fractional_seconds_preserved(fraction):
    parsed = parse_utc(f"2024-02-29T23:59:59.{fraction}Z")
    assert parsed.microsecond == int(fraction.ljust(6, "0"))
    assert parse_utc(format_utc(parsed)) == parsed


def test_formatter_normalizes_offset_and_keeps_seconds():
    value = datetime(2026, 11, 14, 1, 50, 0, 123456, timezone(timedelta(hours=-7)))
    assert format_utc(value) == "2026-11-14T08:50:00.123456Z"
    assert format_utc(value.replace(microsecond=0)) == "2026-11-14T08:50:00Z"


@pytest.mark.parametrize("value", [datetime(2026, 11, 14), None, True, "2026-11-14T00:00:00Z"])
def test_formatter_requires_aware_datetime(value):
    with pytest.raises(ValueError, match="timezone-aware"):
        format_utc(value)
