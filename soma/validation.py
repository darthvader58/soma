"""JSON Schema validation and cross-field checks for standalone scenarios."""

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
import rfc8785


class ScenarioValidationError(ValueError):
    """An input violates the versioned contract or supported validation domain."""


def resource_directory(name: str) -> Path:
    """Locate source-checkout resources or wheel-installed shared resources."""
    source = Path(__file__).resolve().parent.parent / name
    if source.is_dir():
        return source
    installed = Path(sys.prefix) / "share" / "soma" / name
    if installed.is_dir():
        return installed
    raise RuntimeError(f"SOMA {name} resources are missing; reinstall soma-lunar")


def _reject_constant(value):
    raise ScenarioValidationError(f"Non-finite JSON number is unsupported: {value}")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScenarioValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | Path):
    """Read strict JSON, rejecting ambiguous duplicate keys and non-finite values."""
    try:
        document = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_keys,
        )
        _check_json_values(document)
        return document
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ScenarioValidationError(f"Invalid JSON: {exc}") from exc


def _check_json_values(value, path="$"):
    if value is None or type(value) in (str, bool):
        return
    if type(value) in (int, float):
        if type(value) is float and not math.isfinite(value):
            raise ScenarioValidationError(f"{path}: numbers must be finite")
        if abs(value) > 9_007_199_254_740_991:
            raise ScenarioValidationError(f"{path}: number exceeds the interoperable JSON safe range")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _check_json_values(item, f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise ScenarioValidationError(f"{path}: JSON object keys must be strings")
            _check_json_values(item, f"{path}.{key}")
        return
    raise ScenarioValidationError(f"{path}: unsupported JSON value type {type(value).__name__}")


def schema_registry():
    """Load only bundled schemas; unresolved URIs cannot trigger network retrieval."""
    schemas = {}
    resources = []
    for path in sorted(resource_directory("schemas").glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name.removesuffix(".schema.json")] = schema
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return schemas, Registry().with_resources(resources)


def validate_document(document, schema_name: str) -> None:
    """Check structural contract validity; this does not replay a schedule."""
    _check_json_values(document)
    schemas, registry = schema_registry()
    name = schema_name.removesuffix(".schema.json")
    if name not in schemas:
        raise ValueError(f"Unknown schema: {schema_name}")
    checker = FormatChecker()

    @checker.checks("date-time", raises=ValueError)
    def check_epoch(value):
        from soma.time import parse_utc

        if not isinstance(value, str):
            return True
        parse_utc(value)
        return True

    validator = Draft202012Validator(schemas[name], registry=registry, format_checker=checker)
    errors = sorted(validator.iter_errors(document), key=lambda error: str(list(error.path)))
    if errors:
        error = errors[0]
        path = ".".join(map(str, error.absolute_path)) or "$"
        raise ScenarioValidationError(f"{path}: {error.message}")


def _interval(value, label):
    from soma.time import parse_utc

    start, end = parse_utc(value["start_utc"]), parse_utc(value["end_utc"])
    if start >= end:
        raise ScenarioValidationError(f"{label}: start_utc must precede end_utc")
    return start, end


def _check_intervals(value, path="$"):
    if isinstance(value, dict):
        if "start_utc" in value and "end_utc" in value:
            _interval(value, path)
        for key, item in value.items():
            _check_intervals(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_intervals(item, f"{path}[{index}]")


def _indexed(profiles, label):
    index = {}
    for profile in profiles:
        key = profile["id"]
        if key in index:
            raise ScenarioValidationError(f"{label}: duplicate identifier {key}")
        index[key] = profile
    return index


def data_volume_bytes(volume: dict) -> int:
    """Convert only supported explicit integer file-volume units."""
    if (type(volume) is not dict or set(volume) != {"value", "unit"}
            or type(volume["value"]) is not int or volume["value"] <= 0):
        raise ScenarioValidationError("data_volume requires a positive integer value and explicit unit")
    if volume["unit"] == "byte":
        return volume["value"]
    if volume["unit"] == "MiB":
        return volume["value"] * 1_048_576
    raise ScenarioValidationError(f"Unsupported data volume unit: {volume['unit']}")


def _validate_scenario_semantics(scenario):
    from soma.time import parse_utc

    _check_intervals(scenario)
    start, end = _interval(scenario["analysis_horizon"], "analysis_horizon")
    ready = parse_utc(scenario["data_ready_utc"])
    deadline = parse_utc(scenario["deadline_utc"])
    if not start <= ready < deadline <= end:
        raise ScenarioValidationError("Require horizon start <= data ready < deadline <= horizon end")
    if scenario["analysis_mode"] != "synthetic_fixture":
        raise ScenarioValidationError("terrain_ephemeris analysis is not implemented; no physical coverage is available")
    manifest = load_json(resource_directory("data") / "datasets.manifest.json")
    datasets = _indexed(manifest["datasets"], "dataset manifest")
    dataset = datasets.get(scenario["dataset_manifest_ref"])
    if dataset is None or dataset["status"] != "synthetic_fixture_only":
        raise ScenarioValidationError("Dataset is unavailable for Phase 1 synthetic fixture validation")
    coverage_start, coverage_end = _interval(dataset["coverage"], "dataset fixture coverage")
    if start < coverage_start or end > coverage_end:
        raise ScenarioValidationError("Unsupported dates: horizon is outside the declared synthetic fixture domain")
    lander = scenario["lander"]
    lat_min, lat_max = dataset["latitude_bounds_deg"]
    lon_min, lon_max = dataset["longitude_bounds_deg_east"]
    if not lat_min <= lander["latitude_deg"] <= lat_max or not lon_min <= lander["longitude_deg_east"] < lon_max:
        raise ScenarioValidationError("Unsupported coordinates: outside the declared synthetic fixture domain")
    if lander["frame"] != dataset["frame"] or lander["reference_radius_m"] != dataset["reference_radius_m"]:
        raise ScenarioValidationError("Lander frame/reference radius must match the declared dataset")
    if lander["reference_radius_m"] + lander["elevation_m"] <= 0:
        raise ScenarioValidationError("Lander elevation must give a positive radius")

    profiles = scenario["profiles"]
    hardware = _indexed(profiles["hardware"], "hardware profiles")
    relays = _indexed(profiles["relays"], "relay profiles")
    stations = _indexed(profiles["stations"], "station profiles")
    if scenario["hardware_profile_ref"] not in hardware:
        raise ScenarioValidationError("hardware_profile_ref does not resolve")
    for field, index in (("relay_refs", relays), ("station_refs", stations)):
        for reference in scenario[field]:
            if reference not in index:
                raise ScenarioValidationError(f"{field}: unresolved reference {reference}")
    if "single_lunar_relay" in scenario["route_families"] and not scenario["relay_refs"]:
        raise ScenarioValidationError("single_lunar_relay requires a configured relay")
    node_ids = [lander["id"], *relays, *stations]
    if len(node_ids) != len(set(node_ids)):
        raise ScenarioValidationError("Lander, relay, and station node identifiers must be distinct")

    for profile in profiles["hardware"]:
        battery = profile["battery"]
        if not battery["reserve_wh"] <= battery["initial_energy_wh"] <= battery["capacity_wh"]:
            raise ScenarioValidationError("Battery requires reserve <= initial energy <= capacity")
        norm = math.hypot(*profile["panel"]["normal_local_enu"])
        if not math.isclose(norm, 1, abs_tol=1e-9):
            raise ScenarioValidationError("Fixed panel normal_local_enu must be a unit vector")
    if hardware[scenario["hardware_profile_ref"]]["storage_capacity_bytes"] < data_volume_bytes(scenario["data_volume"]):
        raise ScenarioValidationError("Lander storage_capacity_bytes cannot hold the ready dataset")
    for profile in [*profiles["hardware"], *profiles["relays"], *profiles["stations"]]:
        _indexed(profile["terminals"], f"{profile['id']} terminals")
        intervals = sorted(_interval(window, "service window") for window in profile["service"]["windows"])
        if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
            raise ScenarioValidationError(f"{profile['id']}: overlapping service windows")
    for reference in scenario["relay_refs"]:
        relay = relays[reference]
        coverage_start, coverage_end = _interval(relay["trajectory"]["coverage"], "relay trajectory coverage")
        if coverage_start > start or coverage_end < end:
            raise ScenarioValidationError("Relay trajectory coverage must contain the analysis horizon")
        if relay["trajectory"]["kind"] != "synthetic_contact_fixture":
            raise ScenarioValidationError("Phase 1 supports only synthetic_contact_fixture trajectories")


def validate_scenario(scenario: dict) -> dict:
    """Validate structure and supported inputs, returning a detached snapshot."""
    snapshot = deepcopy(scenario)
    validate_document(snapshot, "scenario")
    try:
        _validate_scenario_semantics(snapshot)
    except ScenarioValidationError:
        raise
    except ValueError as exc:
        raise ScenarioValidationError(str(exc)) from exc
    return snapshot


def load_scenario(path: str | Path) -> dict:
    return validate_scenario(load_json(path))


def scenario_sha256(scenario: dict) -> str:
    """Hash RFC 8785 canonical JSON bytes identically in Python and JavaScript."""
    _check_json_values(scenario)
    try:
        canonical = rfc8785.dumps(scenario)
    except rfc8785.CanonicalizationError as exc:
        raise ScenarioValidationError(f"Input cannot be canonicalized: {exc}") from exc
    return hashlib.sha256(canonical).hexdigest()
