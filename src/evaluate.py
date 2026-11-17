"""
Per-device evaluation of measurements against a device specification.

The rules that decide whether a single device value is acceptable live here and nowhere else:
the HTML report highlights its cells with `get_cell_status`, and the `--evaluate` mode (used by the
measurement application while the inspector is still measuring) returns the statuses of `evaluate`.
Only the points measured so far are evaluated, so the result can be requested after every measurement.
"""
import math

import src.calculate as cal
import src.report as r

EVALUATE_SCHEMA_VERSION = 1

# Check statuses returned by `evaluate`
STATUS_PASS = "pass"
STATUS_WARNING = "warning"
STATUS_FAIL = "fail"
STATUS_PENDING = "pending"  # the points the metric needs are not measured yet
STATUS_UNAVAILABLE = "n/a"  # the points are measured, but the metric has no valid value

# Device verdicts returned by `evaluate`
VERDICT_PASS = "PASS"
VERDICT_WARN = "WARN"
VERDICT_FAIL = "FAIL"

UNIFORMITY_LOCATIONS = (
    "TopLeft", "TopCenter", "TopRight",
    "MiddleLeft", "Center", "MiddleRight",
    "BottomLeft", "BottomCenter", "BottomRight",
)
GAMUT_LOCATIONS = ("RedColor", "GreenColor", "BlueColor")

# Coordinate metric key -> measurement location it is taken from
COORDINATE_LOCATIONS = {
    "Red": "RedColor",
    "Green": "GreenColor",
    "Blue": "BlueColor",
    "White": "WhiteColor",
    "Center": "Center",
}


def _parse_spec_value(value):
    """Returns the spec value as is, or None for a missing value or the 'None' marker used in configs."""
    return None if value is None or value == "None" else value


def get_cell_status(key: str, value: float, expected_values: dict, is_coordinate: bool = False):
    """
    Determines the status of a single device value by comparing it with the expected values.

    The value is compared as displayed in the report, i.e. rounded to the report precision of the metric.

    Args:
        key: Internal JSON key (e.g., "Brightness", "Red_x")
        value: Actual measured value
        expected_values: Expected values from YAML config
        is_coordinate: If True, checks only min/max (for coordinates)

    Returns:
        str or None: "fail" (red), "warning" (yellow), or None (no remark)
    """
    if value is None:
        return None

    precision = r.REPORT_PRECISION.get(key)
    if precision is not None:
        value = r.safe_round(value, precision)

    expected = expected_values.get(key, {})
    min_val = _parse_spec_value(expected.get("min"))
    max_val = _parse_spec_value(expected.get("max"))
    typ_val = _parse_spec_value(expected.get("typ"))

    if key in r.LOWER_IS_BETTER_KEYS:
        # Higher value = worse: max is a hard bound, typ is a soft upper bound
        if max_val is not None and value > max_val:
            return STATUS_FAIL
        if is_coordinate:
            return None
        if typ_val is not None and value > typ_val:
            return STATUS_WARNING
        return None

    if min_val is not None and value < min_val:
        return STATUS_FAIL
    if max_val is not None and value > max_val:
        return STATUS_FAIL
    if is_coordinate:
        return None
    if typ_val is not None and value < typ_val:
        return STATUS_WARNING
    return None


def required_locations(key: str, is_tv: bool) -> tuple:
    """
    Returns the measurement locations a metric is calculated from.

    Args:
        key: Metric key (e.g., "Contrast", "Cg_rgb_area", "Red_x")
        is_tv: Whether the device is a TV (white point is the reference instead of the center)

    Returns:
        tuple: Location names; empty if the key is not a known metric.
    """
    reference = "WhiteColor" if is_tv else "Center"

    if key == "Brightness":
        return (reference,)
    if key == "Black_luminance":
        return ("BlackColor",)
    if key == "Contrast":
        return (reference, "BlackColor")
    if key in ("Brightness_uniformity", "Delta_e"):
        return UNIFORMITY_LOCATIONS
    if key == "Temperature":
        return ("Center",)
    if key.startswith("Cg_"):
        return GAMUT_LOCATIONS

    color, _, axis = key.partition("_")
    if axis in ("x", "y") and color in COORDINATE_LOCATIONS:
        return (COORDINATE_LOCATIONS[color],)
    return ()


def _measured_locations(device_data: dict) -> dict:
    """Maps every location with a numeric Lv, x and y to its measurement."""
    measured = {}
    for measurement in device_data.get("Measurements") or []:
        try:
            if all(math.isfinite(float(measurement[field])) for field in ("x", "y", "Lv")):
                measured[measurement["Location"]] = measurement
        except (KeyError, TypeError, ValueError):
            continue
    return measured


def _flat_results(device_data: dict, is_tv: bool) -> dict:
    """Calculates the report metrics of a device and flattens the coordinates into the metric dictionary."""
    results = r.json_report(**cal.run_calculations(device_data, is_tv))["Results"]
    flat = {key: value for key, value in results.items() if key != "Coordinates"}
    flat.update(results.get("Coordinates") or {})
    return flat


def _has_spec(expected: dict) -> bool:
    """Tells whether a spec entry has at least one usable min/typ/max value."""
    return isinstance(expected, dict) and any(
        _parse_spec_value(expected.get(bound)) is not None for bound in ("min", "typ", "max")
    )


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _worst_uniformity_location(measured: dict):
    """Returns the location with the lowest luminance among the uniformity points."""
    points = {loc: float(measured[loc]["Lv"]) for loc in UNIFORMITY_LOCATIONS if loc in measured}
    return min(points, key=points.get) if points else None


def _check(key: str, results: dict, measured: dict, expected_values: dict, is_tv: bool) -> dict:
    """Builds the check entry of one metric."""
    required = required_locations(key, is_tv)
    missing = [loc for loc in required if loc not in measured]
    expected = expected_values[key]
    entry = {
        "key": key,
        "min": _parse_spec_value(expected.get("min")),
        "typ": _parse_spec_value(expected.get("typ")),
        "max": _parse_spec_value(expected.get("max")),
        "locations": list(required),
    }

    if missing:
        return {**entry, "value": None, "status": STATUS_PENDING, "missing": missing}

    value = results.get(key)
    if not _is_number(value):
        return {**entry, "value": None, "status": STATUS_UNAVAILABLE, "missing": []}

    is_coordinate = key in r.COORDINATE_TEST_KEYS or key in ("Center_x", "Center_y")
    status = get_cell_status(key, value, expected_values, is_coordinate=is_coordinate) or STATUS_PASS

    if key == "Brightness_uniformity":
        entry["locations"] = [_worst_uniformity_location(measured)]

    precision = r.REPORT_PRECISION.get(key)
    return {**entry, "value": r.safe_round(value, precision) if precision is not None else value,
            "status": status, "missing": []}


def verdict_of(statuses) -> str:
    """
    Returns the device verdict for a set of check statuses (cell statuses of the report use the same names).

    Args:
        statuses: Iterable of "fail" / "warning" / other statuses.

    Returns:
        str: "FAIL" if any status is fail, "WARN" if any is warning, otherwise "PASS".
    """
    statuses = set(statuses)
    if STATUS_FAIL in statuses:
        return VERDICT_FAIL
    if STATUS_WARNING in statuses:
        return VERDICT_WARN
    return VERDICT_PASS


def evaluate(device_data: dict, expected_values: dict) -> dict:
    """
    Evaluates the measurements of one device against its specification.

    Only the metrics that have a spec are evaluated. A metric whose points are not measured yet gets the
    "pending" status, so the function can be called after every measurement.

    Args:
        device_data: Device measurement data as saved by the measurement application
            (SerialNumber, IsTV, Measurements, ...).
        expected_values: Specification loaded from the device YAML with the coordinate tolerance expanded.

    Returns:
        dict: {"schema", "device": PASS/WARN/FAIL over the evaluated checks, "complete": no check is pending,
        "checks": [{"key", "value", "min", "typ", "max", "status", "locations", "missing"}]}
    """
    is_tv = bool(device_data.get("IsTV", False))
    measured = _measured_locations(device_data)
    results = _flat_results(device_data, is_tv)

    checks = [
        _check(key, results, measured, expected_values, is_tv)
        for key, expected in expected_values.items()
        if required_locations(key, is_tv) and _has_spec(expected)
    ]

    statuses = {check["status"] for check in checks}

    return {
        "schema": EVALUATE_SCHEMA_VERSION,
        "device": verdict_of(statuses),
        "complete": STATUS_PENDING not in statuses,
        "checks": checks,
    }
