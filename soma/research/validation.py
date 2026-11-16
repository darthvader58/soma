"""Versioned, detached geometry-study inputs with bounded sampling."""
from copy import deepcopy
from datetime import timedelta
import math

from soma.time import format_utc, parse_utc
from soma.validation import ScenarioValidationError, scenario_sha256, validate_document


class StudyValidationError(ValueError):
    """The request violates the study contract or provider domain."""


REQUEST_BUDGETS = {
    "maximum_duration_s": 31 * 86400,
    "minimum_step_s": 10,
    "maximum_epochs": 2000,
    "maximum_sites": 8,
    "maximum_site_epochs": 5000,
}


def study_epochs(request):
    """Include both interval endpoints; the final step may be shorter."""
    start = parse_utc(request["time"]["start_utc"])
    end = parse_utc(request["time"]["end_utc"])
    step = request["time"]["step_s"]
    duration = (end - start).total_seconds()
    count = math.ceil(duration / step)
    return [format_utc(start + timedelta(seconds=min(i * step, duration))) for i in range(count + 1)]


def validate_study(document):
    """Return a normalized snapshot, rejecting unsupported or ambiguous units.

    Dates use the shared civil UTC boundary. Provider binary coverage is checked
    when evaluating a study; validation never fetches or loads kernel files.
    """
    request = deepcopy(document)
    try:
        validate_document(request, "study")
        start = parse_utc(request["time"]["start_utc"])
        end = parse_utc(request["time"]["end_utc"])
        if start >= end:
            raise StudyValidationError("time.start_utc must precede time.end_utc")
        duration = (end - start).total_seconds()
        if duration > REQUEST_BUDGETS["maximum_duration_s"]:
            raise StudyValidationError("study duration exceeds the 31-day request budget")
        count = math.ceil(duration / request["time"]["step_s"]) + 1
        if count > REQUEST_BUDGETS["maximum_epochs"]:
            raise StudyValidationError("study exceeds the 2000-epoch request budget")
        if count * len(request["sites"]) > REQUEST_BUDGETS["maximum_site_epochs"]:
            raise StudyValidationError("study exceeds the 5000 site/epoch request budget")
        ids = [site["id"] for site in request["sites"]]
        if len(ids) != len(set(ids)):
            raise StudyValidationError("site IDs must be unique")
        for site in request["sites"]:
            if request["reference_radius_m"] + site["elevation_m"] <= 0:
                raise StudyValidationError("site elevation must produce a positive surface radius")
        request["time"]["start_utc"] = format_utc(start)
        request["time"]["end_utc"] = format_utc(end)
        scenario_sha256(request)
        return request
    except StudyValidationError:
        raise
    except (ScenarioValidationError, ValueError, OverflowError) as exc:
        raise StudyValidationError(str(exc)) from exc


def study_sha256(request):
    """RFC 8785 SHA256 of the validated, UTC-normalized study."""
    try:
        return scenario_sha256(validate_study(request))
    except ScenarioValidationError as exc:
        raise StudyValidationError(str(exc)) from exc
