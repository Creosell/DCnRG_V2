"""
Statistics of repeated measurements for the HTML report.

A measurement file may carry an `Attempts` list for a point the inspector measured more than once. This module turns the lists of
all devices of a report into the data of the "Repeated measurements" section: per serial number a card with a strip plot of every
repeated point (where each attempt landed on the scale of its spec, which one is the best) and the numbers that tell whether the
repeats were worth it. The best attempt is chosen by `evaluate.best_attempt_index`, the only place that ranks the attempts.
"""
import math

import src.evaluate as ev

MIN_ATTEMPTS = 2  # a point with fewer attempts was not measured again

POINT_NAMES = {
    "WhiteColor": "White", "BlackColor": "Black", "RedColor": "Red", "GreenColor": "Green", "BlueColor": "Blue",
    "Center": "Center", "TopLeft": "Top left", "TopCenter": "Top center", "TopRight": "Top right",
    "MiddleLeft": "Middle left", "MiddleRight": "Middle right",
    "BottomLeft": "Bottom left", "BottomCenter": "Bottom center", "BottomRight": "Bottom right",
}
POINT_ORDER = list(POINT_NAMES)
COLOR_KEYS = {"RedColor": "Red", "GreenColor": "Green", "BlueColor": "Blue"}

# Strip plot geometry (SVG user units; the strip scales with the card)
STRIP_WIDTH, GUTTER, ROW_HEIGHT, ROW_PAD = 220, 11, 12, 2
FONT_SIZE, CHAR_WIDTH = 8.8, 5.6  # the type of the strip (SVG units) and the width the plate of a value reserves per character
STATUS_COLORS = {"ok": "#28a745", "warning": "#e0a800", "fail": "#dc3545", "none": "#6c757d"}
BAND_COLORS = {"ok": "#e6f4ea", "warning": "#fff3cd", "fail": "#ffdddd", "none": "#f1f3f5"}

OUTCOMES = {"rescued": "Fixed", "improved": "Improved", "same": "No effect"}


class _Metric:
    """What one point is plotted by: its kind, the value of an attempt, the spec bands and how an attempt is judged."""

    def __init__(self, location: str, expected_values: dict, is_tv: bool):
        reference = "WhiteColor" if is_tv else "Center"
        self.location = location
        self.kind = "free"  # free: the luminance, higher is better, no spec to judge by
        self.bounds = {}  # spec bounds of the metric
        self.lower_is_better = False
        self.unit = "cd/m²"
        self.label = "Brightness"
        if location == "BlackColor":
            self.kind, self.lower_is_better, self.label = "dark", True, "Luminance"
        elif location in COLOR_KEYS:
            self._init_color(COLOR_KEYS[location], expected_values)
        elif location == reference:
            expected = expected_values.get("Brightness", {})
            if ev._has_spec(expected):
                self.kind = "spec"
                self.bounds = {b: ev._parse_spec_value(expected.get(b)) for b in ("min", "typ", "max")}

    def _init_color(self, color: str, expected_values: dict):
        """The distance from the typical coordinates, judged by the min/max window of x and y."""
        try:
            self.typ = (float(ev._parse_spec_value(expected_values[f"{color}_x"]["typ"])),
                        float(ev._parse_spec_value(expected_values[f"{color}_y"]["typ"])))
            half = []
            for axis, typ in zip(("x", "y"), self.typ):
                spec = expected_values[f"{color}_{axis}"]
                low, high = ev._parse_spec_value(spec.get("min")), ev._parse_spec_value(spec.get("max"))
                half.append(min(typ - float(low), float(high) - typ))
            if min(half) <= 0:
                return
        except (KeyError, TypeError, ValueError):
            return
        self.kind, self.lower_is_better, self.unit, self.label = "xy", True, "", "Δxy"
        self.color = color
        self.window = half
        self.expected = expected_values

    def value(self, attempt: dict):
        """The plotted value of an attempt, or None when the attempt has no valid number."""
        try:
            if self.kind == "xy":
                return math.hypot(float(attempt["x"]) - self.typ[0], float(attempt["y"]) - self.typ[1])
            value = float(attempt["Lv"])
        except (KeyError, TypeError, ValueError):
            return None
        return value if math.isfinite(value) else None

    def status(self, attempt: dict, value: float) -> str:
        """ok, warning or fail by the spec of the point; none for a point without a spec."""
        if self.kind == "spec":
            status = ev.get_cell_status("Brightness", value, {"Brightness": {k: v for k, v in self.bounds.items()}})
        elif self.kind == "xy":
            statuses = [ev.get_cell_status(f"{self.color}_{axis}", float(attempt[axis]), self.expected, is_coordinate=True) for axis in ("x", "y")]
            status = ev.STATUS_FAIL if ev.STATUS_FAIL in statuses else None
        else:
            return "none"
        return {ev.STATUS_FAIL: "fail", ev.STATUS_WARNING: "warning"}.get(status, "ok")

    def bands(self, low: float, high: float) -> list:
        """The colored zones of the scale as (from, to, status)."""
        if self.kind == "spec":
            min_v, typ_v = self.bounds["min"], self.bounds["typ"]
            zones, start = [], low
            if min_v is not None and min_v > start:
                zones.append((start, min_v, "fail"))
                start = min_v
            if typ_v is not None and typ_v > start:
                zones.append((start, typ_v, "warning"))
                start = typ_v
            zones.append((start, high, "ok"))
            return zones
        if self.kind == "xy":
            inner, outer = min(self.window), math.hypot(*self.window)
            edges = [max(low, 0.0), min(inner, high), min(outer, high), high]
            return [(edges[i], edges[i + 1], name) for i, name in enumerate(("ok", "warning", "fail")) if edges[i + 1] > edges[i]]
        return [(low, high, "none")]

    def format(self, value: float) -> str:
        return f"{value:.0f}" if self.kind in ("spec", "free") else f"{value:.3f}"

    def delta(self, first: float, best: float) -> str:
        return f"{best - first:+.0f}" if self.kind in ("spec", "free") else f"{best - first:+.3f}"


def _outcome(metric: _Metric, statuses: list, values: list, best: int) -> str:
    """rescued: the first attempt had a remark and the best has none; improved: the best is better than the first (a better value
    counts inside the spec too: it moves the typical value of the batch); same: it is not."""
    first, chosen = statuses[0], statuses[best]
    if first in ("warning", "fail") and chosen == "ok":
        return "rescued"
    if best == 0:
        return "same"
    rank = {"fail": 0, "warning": 1, "ok": 2, "none": 2}
    if rank[chosen] > rank[first]:
        return "improved"
    better = values[best] < values[0] if metric.lower_is_better else values[best] > values[0]
    return "improved" if better else "same"


def _strip_svg(metric: _Metric, values: list, statuses: list, best: int, low: float, high: float) -> str:
    """
    The strip plot: the spec zones run through one row per attempt (1, 2, 3 ...), so attempts with close values never overlap;
    every dot carries its value, the path joins the dots in the order of the attempts, the best one is ringed.
    """
    rows = len(values)
    height = rows * ROW_HEIGHT + 2 * ROW_PAD
    left, right = GUTTER, STRIP_WIDTH - GUTTER / 2
    scale = lambda v: left + (v - low) / (high - low) * (right - left)
    row_y = lambda i: ROW_PAD + ROW_HEIGHT * i + ROW_HEIGHT / 2
    parts = [f'<svg class="attempt-strip" viewBox="0 0 {STRIP_WIDTH} {height}" role="img">']
    for start, end, name in metric.bands(low, high):
        parts.append(f'<rect x="{scale(start):.1f}" y="{ROW_PAD}" width="{scale(end) - scale(start):.1f}" height="{rows * ROW_HEIGHT}" fill="{BAND_COLORS[name]}"/>')
    xs = [scale(v) for v in values]
    parts.append('<polyline points="' + " ".join(f"{x:.1f},{row_y(i):.1f}" for i, x in enumerate(xs)) + '" fill="none" stroke="#9aa4b2" stroke-width="0.8" stroke-dasharray="2 2"/>')
    for i, x in enumerate(xs):
        ring, y = i == best, row_y(i)
        weight = "700" if ring else "400"
        parts.append(f'<text x="{GUTTER - 4}" y="{y + 3:.1f}" font-size="{FONT_SIZE}" font-weight="{weight}" text-anchor="end" fill="#555">{i + 1}</text>')
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.4 if ring else 3.2}" fill="{STATUS_COLORS[statuses[i]]}" stroke="{"#111" if ring else "#fff"}" stroke-width="{1.6 if ring else 1}"/>')
        label_left = x > left + (right - left) * 0.62  # the value goes to the free side of the dot
        text = metric.format(values[i])
        width = len(text) * CHAR_WIDTH + 4  # a plate under the value keeps the dashed path from running through the digits
        plate_x = x - 6 - width if label_left else x + 6
        parts.append(f'<rect x="{plate_x:.1f}" y="{y - ROW_HEIGHT / 2 + 1:.1f}" width="{width:.1f}" height="{ROW_HEIGHT - 2}" rx="2" fill="#fff" fill-opacity="0.9"/>')
        parts.append(f'<text x="{plate_x + width / 2:.1f}" y="{y + 3:.1f}" font-size="{FONT_SIZE}" font-weight="{weight}" text-anchor="middle" fill="#333">{text}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _scale(metric: _Metric, all_values: list) -> tuple:
    """One scale for every card of a point, so the strips of different devices can be compared."""
    low, high = min(all_values), max(all_values)
    if metric.kind == "spec":
        bounds = [v for v in (metric.bounds["min"], metric.bounds["typ"]) if v is not None]
        low, high = min([low] + bounds), max([high] + bounds)
    elif metric.kind == "xy":
        low, high = 0.0, max(high, math.hypot(*metric.window))  # a distance starts at 0; the padding keeps the dot at 0 inside the strip
    pad = (high - low) * 0.08 or max(abs(high) * 0.05, 0.001)
    return low - pad, high + pad


def build_attempts_stats(devices: list, expected_values: dict, total_devices: int):
    """
    Builds the data of the "Repeated measurements" section.

    Args:
        devices: (serial number, device data of the measurement file) of every device of the report; the IsTV flag of the data tells
            whether the white point (a TV) or the center is the brightness reference.
        expected_values: Specification with the coordinate tolerance expanded.
        total_devices: Number of devices in the report.

    Returns:
        dict or None: {"kpis", "cards"}; None when no point of any device was measured more than once.
    """
    entries = []  # (serial, location, metric, values, statuses, best)
    for serial, data in devices:
        is_tv = bool((data or {}).get("IsTV", False))
        for measurement in (data or {}).get("Measurements") or []:
            attempts = measurement.get("Attempts")
            location = measurement.get("Location")
            if not isinstance(attempts, list) or len(attempts) < MIN_ATTEMPTS or location not in POINT_NAMES:
                continue
            metric = _Metric(location, expected_values, is_tv)
            values = [metric.value(a) for a in attempts]
            if any(v is None for v in values):
                continue
            statuses = [metric.status(a, v) for a, v in zip(attempts, values)]
            best = ev.best_attempt_index(location, attempts, expected_values, is_tv)
            entries.append((serial, location, metric, values, statuses, best, attempts))

    if not entries:
        return None

    scales = {}
    for location in {e[1] for e in entries}:
        group = [e for e in entries if e[1] == location]
        scales[location] = _scale(group[0][2], [v for e in group for v in e[3]])

    cards = {}
    for serial, location, metric, values, statuses, best, attempts in entries:
        low, high = scales[location]
        outcome = _outcome(metric, statuses, values, best)
        cards.setdefault(serial, []).append({
            "location": location,
            "name": POINT_NAMES[location],
            "metric": metric.label,
            "scale": metric.unit or metric.label,  # what the numbers are: cd/m² or the color distance Δxy
            "attempts": len(values),
            "best": best + 1,
            "first": metric.format(values[0]),
            "best_value": metric.format(values[best]),
            "delta": metric.delta(values[0], values[best]),
            "outcome": outcome,
            "outcome_text": OUTCOMES[outcome],
            "svg": _strip_svg(metric, values, statuses, best, low, high),
            "gain": values[best] - values[0] if metric.kind == "spec" else None,
        })

    ordered = []
    for serial, points in cards.items():
        points.sort(key=lambda p: POINT_ORDER.index(p["location"]))
        outcomes = [p["outcome"] for p in points]
        overall = "rescued" if "rescued" in outcomes else "improved" if "improved" in outcomes else "same"
        counts = [f"{outcomes.count(o)} {OUTCOMES[o].lower()}" for o in ("rescued", "improved") if o in outcomes]
        ordered.append({"serial": serial, "outcome": overall, "summary": " · ".join(counts) or OUTCOMES["same"], "points": points})

    points_total = [p for card in ordered for p in card["points"]]
    gains = [p["gain"] for p in points_total if p["gain"] is not None]
    attempts_total = sum(p["attempts"] for p in points_total)
    return {
        "cards": ordered,
        "kpis": {
            "devices": len(ordered),
            "total_devices": total_devices,
            "devices_percent": round(100 * len(ordered) / total_devices) if total_devices else 0,
            "points": len(points_total),
            "attempts_average": round(attempts_total / len(points_total), 1),
            "rescued": sum(1 for p in points_total if p["outcome"] == "rescued"),
            "improved": sum(1 for p in points_total if p["outcome"] == "improved"),
            "gain_average": round(sum(gains) / len(gains)) if gains else None,
        },
    }
