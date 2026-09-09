import numpy as np
from colormath2.color_conversions import convert_color
from colormath2.color_diff import delta_e_cie2000
from colormath2.color_objects import xyYColor, LabColor
from loguru import logger
from shapely.geometry import Polygon
from enum import Enum

import src.parse as parse


class ColorSpace(Enum):
    """Defines the supported color spaces."""
    NTSC = "NTSC"
    SRGB = "sRGB"
    DCI_P3 = "DCI-P3"
    REC2020 = "Rec.2020"

# Format: (Standard Name, [[Red_x, Red_y], [Green_x, Green_y], [Blue_x, Blue_y]])
COLOR_STANDARDS = {
    ColorSpace.NTSC: [
        [0.67, 0.33],
        [0.21, 0.71],
        [0.14, 0.08]
    ],
    ColorSpace.SRGB: [
        [0.64, 0.33],
        [0.3, 0.6],
        [0.15, 0.06]
    ],
    ColorSpace.DCI_P3: [
        [0.680, 0.320],
        [0.265, 0.690],
        [0.150, 0.060]
    ],
    ColorSpace.REC2020: [
        [0.708, 0.292],
        [0.170, 0.797],
        [0.131, 0.046]
    ]
}

# Suffix used to build JSON/YAML metric keys for each color space, e.g. "Cg_<suffix>_area".
# "rgb" is a legacy alias for sRGB kept for backward compatibility with existing reports/configs.
# Adding a new color space: add it to ColorSpace + COLOR_STANDARDS above and give it a suffix here -
# cg()/cg_by_area()/cg_uv()/cg_by_area_uv()/run_calculations() pick it up automatically.
COLOR_SPACE_KEY_SUFFIX = {
    ColorSpace.SRGB: "rgb",
    ColorSpace.NTSC: "ntsc",
    ColorSpace.DCI_P3: "dcip3",
    ColorSpace.REC2020: "rec2020",
}

# Human-readable display name for each color space, used in UI labels (UFN_MAPPING, legends).
COLOR_SPACE_DISPLAY_NAME = {
    ColorSpace.SRGB: "sRGB",
    ColorSpace.NTSC: "NTSC",
    ColorSpace.DCI_P3: "DCI-P3",
    ColorSpace.REC2020: "Rec.2020",
}

def area(p):
    """Calculates the area of a triangle defined by three points."""
    return 0.5 * abs(np.cross(p[1] - p[0], p[2] - p[0]))


def xy_to_uv(x, y):
    """Converts CIE 1931 xy chromaticity coordinates to CIE 1976 u'v'."""
    denom = -2 * x + 12 * y + 3
    return 4 * x / denom, 9 * y / denom


def coords_xy_to_uv(coords):
    """Converts flat [Rx, Ry, Gx, Gy, Bx, By] from CIE 1931 xy to CIE 1976 u'v'."""
    rx, ry, gx, gy, bx, by = coords
    ru, rv = xy_to_uv(rx, ry)
    gu, gv = xy_to_uv(gx, gy)
    bu, bv = xy_to_uv(bx, by)
    return [ru, rv, gu, gv, bu, bv]


def calculate_overlap_percentage(x1, y1, x2, y2, x3, y3, x4, y4, x5, y5, x6, y6):
    """Calculates the percentage for area of the first triangle covered by the second triangle."""
    triangle1 = np.array([[x1, y1], [x2, y2], [x3, y3]])
    triangle2 = np.array([[x4, y4], [x5, y5], [x6, y6]])

    # Check if the input data forms valid triangles
    if area(triangle1) == 0 or area(triangle2) == 0:
        return "Error: the input data does not form valid triangles."

    # Convert the triangles into Polygon objects using the Shapely library
    polygon1 = Polygon(triangle1)
    polygon2 = Polygon(triangle2)

    # Calculate the intersection area of the polygons
    intersection = polygon1.intersection(polygon2)

    intersection_area = intersection.area if not intersection.is_empty else 0.0

    # Calculate the percentage for area of the first triangle covered by the second triangle
    overlap_percentage = (intersection_area / polygon1.area) * 100

    return overlap_percentage


def brightness(device_report, is_tv):
    """
    Calculates the minimum (min) and maximum (max) brightness
    from all measurement points excluding color points (Red, Green, Blue, Black, White).
    Also calculates the typical (typ) brightness for the report,
    which is either 'WhiteColor' (for TV) or 'Center' (otherwise).
        Args:
            device_report (dict): Device report.
            is_tv (bool): True if the report is TV.

    """

    if device_report is None:
        return {"min": None, "typ": None, "max": None, "uniformity_center_lv": None}

    measurements = device_report.get("Measurements", [])

    # Map location names to their required keys
    brightness_calculation_point = "WhiteColor" if is_tv else "Center"

    # Collect all Lv values into a dictionary for quick access
    lv_values = {}
    for m in measurements:
        location = m.get("Location")
        try:
            lv_values[location] = float(m.get("Lv"))
        except (ValueError, TypeError, KeyError):
            continue

    # Collect values for min/max calculation
    excluded_locations = {"RedColor", "GreenColor", "BlueColor", "BlackColor", "WhiteColor"}

    # Use a filter to get all Lv except the excluded ones
    all_lv_values = [
        lv for loc, lv in lv_values.items()
        if loc not in excluded_locations
    ]

    # Calculate min, max
    min_lv = min(all_lv_values) if all_lv_values else None
    max_lv = max(all_lv_values) if all_lv_values else None
    typical_lv_for_report = lv_values.get(brightness_calculation_point)

    return {"min": min_lv, "typ": typical_lv_for_report, "max": max_lv}

def brightness_uniformity(brightness_value):
    """
    Calculates brightness uniformity using minimum brightness
    and Center brightness (uniformity_center_lv).
    """
    min_lv = brightness_value.get("min")
    max_lv = brightness_value.get("max")

    if min_lv is None or max_lv is None or max_lv == 0.0:
        return 0.0

    brightness_uniformity_percent = (min_lv / max_lv) * 100
    return brightness_uniformity_percent


def cg_by_area(device_report):
    coordinate = parse.coordinates_of_triangle(device_report)
    if len(coordinate) != 6:
        return None

    x1, y1, x2, y2, x3, y3 = coordinate
    dut_triangle = np.array([[x1, y1], [x2, y2], [x3, y3]])
    dut_triangle_area = area(dut_triangle)
    if dut_triangle_area == 0:
        return None

    return {
        color_space: (dut_triangle_area / area(np.array(standard_triangle))) * 100
        for color_space, standard_triangle in COLOR_STANDARDS.items()
    }


def _std_to_uv_flat(color_space):
    """Converts a COLOR_STANDARDS entry to flat u'v' list [u1, v1, u2, v2, u3, v3]."""
    flat = [coord for point in COLOR_STANDARDS[color_space] for coord in point]
    return coords_xy_to_uv(flat)


def _std_to_uv_triangle(color_space):
    """Converts a COLOR_STANDARDS entry to a numpy u'v' triangle array."""
    u1, v1, u2, v2, u3, v3 = _std_to_uv_flat(color_space)
    return np.array([[u1, v1], [u2, v2], [u3, v3]])


def cg_by_area_uv(device_report):
    """Calculates color gamut area ratio in CIE 1976 u'v' color space."""
    coordinate = parse.coordinates_of_triangle(device_report)
    if len(coordinate) != 6:
        return None

    u1, v1, u2, v2, u3, v3 = coords_xy_to_uv(coordinate)
    dut_triangle = np.array([[u1, v1], [u2, v2], [u3, v3]])
    dut_triangle_area = area(dut_triangle)
    if dut_triangle_area == 0:
        return None

    return {
        color_space: (dut_triangle_area / area(_std_to_uv_triangle(color_space))) * 100
        for color_space in COLOR_STANDARDS
    }


def cg_uv(device_report):
    """Calculates color gamut overlap percentage in CIE 1976 u'v' color space."""
    dut_coordinates = parse.coordinates_of_triangle(device_report)
    if len(dut_coordinates) != 6:
        return None

    u1, v1, u2, v2, u3, v3 = coords_xy_to_uv(dut_coordinates)

    overlaps = {
        color_space: calculate_overlap_percentage(*_std_to_uv_flat(color_space), u1, v1, u2, v2, u3, v3)
        for color_space in COLOR_STANDARDS
    }

    if any(isinstance(value, str) for value in overlaps.values()):
        return None

    return overlaps


def cg(device_report):
    dut_coordinates = parse.coordinates_of_triangle(device_report)
    if len(dut_coordinates) != 6:
        return None

    x1, y1, x2, y2, x3, y3 = dut_coordinates

    overlaps = {}
    for color_space, standard_triangle in COLOR_STANDARDS.items():
        flat_standard = [coord for point in standard_triangle for coord in point]
        overlaps[color_space] = calculate_overlap_percentage(*flat_standard, x1, y1, x2, y2, x3, y3)

    # Error handling if area is 0
    if any(isinstance(value, str) for value in overlaps.values()):
        # If there is an error (e.g., area is 0), return None
        return None

    return overlaps


def contrast(device_report, is_tv):
    """
    Calculates a contrast ratio.
    Uses WhiteColor/BlackColor for TV (is_tv=True) and Center/BlackColor otherwise.
    """

    if device_report is None:
        raise ValueError("Report is empty or could not be parsed.")

    measurements = device_report.get("Measurements", [])

    # Collect Lv for the required points
    lv_values = {}
    for m in measurements:
        location = m.get("Location")
        if location in ["Center", "WhiteColor", "BlackColor"]:
            try:
                lv_values[location] = float(m.get("Lv", 0.0))
            except (ValueError, TypeError, KeyError):
                lv_values[location] = 0.0

    # Determine the numerator based on the is_tv flag
    numerator_key = "WhiteColor" if is_tv else "Center"

    numerator_lv = lv_values.get(numerator_key, 0.0)
    black_lv = lv_values.get("BlackColor", 0.0)

    # Contrast calculation
    if black_lv == 0.0 or numerator_lv == 0.0:
        return 0.0

    return round(numerator_lv / black_lv, 2)


def temperature(device_report):

    if device_report is None:
        raise ValueError("Report is empty or could not be parsed.")

    measurements = device_report.get("Measurements", [])

    # Use next() to find "T" in "Center"
    temperature_str = next(
        (m.get("T") for m in measurements if m.get("Location") == "Center"),
        None
    )

    if temperature_str is None:
        # Preserve the original error, as required by the logic
        raise ZeroDivisionError("NO Temperature for Central DOT")

    try:
        return float(temperature_str)
    except (ValueError, TypeError):
        raise ValueError("Invalid temperature value found in report.")


def delta_e(device_report):
    """Calculates Delta E Color Uniformity for given locations."""
    locations_to_check = {
        "BottomLeft", "BottomCenter", "BottomRight",
        "MiddleLeft", "Center", "MiddleRight",
        "TopLeft", "TopCenter", "TopRight",
    }
    if device_report is None:
        raise ValueError("Report is empty or could not be parsed.")

    measurements = device_report.get("Measurements", [])

    # Use parse.find_closest_to_target to determine the reference point
    # Expected x/y are taken from Center
    center_data = next(
        (m for m in measurements if m.get('Location') == 'Center'),
        {}
    )

    expected_x = float(center_data.get('x', '0.0'))
    expected_y = float(center_data.get('y', '0.0'))

    ref = parse.find_closest_to_target(device_report, expected_x, expected_y)

    ref_x = ref.get("x")
    ref_y = ref.get("y")
    ref_lv = ref.get("Lv")
    reference_location = ref.get("Location")

    if ref_x is None or ref_y is None or ref_lv is None:
        raise ValueError("Missing reference color data for Center.")

    delta_e_values = []

    try:
        ref_color = xyYColor(float(ref_x), float(ref_y), float(ref_lv))
        ref_lab = convert_color(ref_color, LabColor)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid reference color data: {e}") from e

    for measurement in measurements:
        location = measurement.get("Location")

        # Skip if not in the list or is the reference point
        if (location not in locations_to_check) or location == reference_location:
            continue

        try:
            x = float(measurement.get("x"))
            y = float(measurement.get("y"))
            lv = float(measurement.get("Lv"))
        except (ValueError, TypeError, KeyError):
            continue  # Skip if conversion to float failed

        color = xyYColor(x, y, lv)
        color_lab = convert_color(color, LabColor)

        delta_e_value = delta_e_cie2000(ref_lab, color_lab)
        delta_e_values.append(delta_e_value)

    # Calculate average Delta E
    if not delta_e_values:
        raise ValueError("No valid Delta E values calculated.")
    avg_delta_e = sum(delta_e_values) / len(delta_e_values)
    return round(avg_delta_e, 2)

def run_calculations(device_report, is_tv):
    """
    Runs calculations based on the test_type and returns a results dictionary.
    Dictionary keys must match the arguments for r.json_report.
    """
    results = {}
    logger.debug("Running calculations...")

    try:
        brightness_values = brightness(device_report, is_tv)
        results["brightness"] = brightness_values["typ"]
        results["brightness_uniformity"] = brightness_uniformity(brightness_values)
    except Exception as e:
        logger.error(f"Failed 'brightness' calculation: {e}")
        results["brightness"] = None
        results["brightness_uniformity"] = None

    try:
        results["contrast"] = contrast(device_report, is_tv)
    except Exception as e:
        logger.error(f"Failed 'contrast' calculation: {e}")
        results["contrast"] = None

    try:
        cg_by_area_val = cg_by_area(device_report)
        cg_val = cg(device_report)
        cg_by_area_uv_val = cg_by_area_uv(device_report)
        cg_uv_val = cg_uv(device_report)

        # Build "cg_by_area_<suffix>" / "cg_<suffix>" / "cg_by_area_uv_<suffix>" / "cg_uv_<suffix>"
        # for every registered color space (see COLOR_SPACE_KEY_SUFFIX).
        for color_space, suffix in COLOR_SPACE_KEY_SUFFIX.items():
            results[f"cg_by_area_{suffix}"] = cg_by_area_val.get(color_space) if cg_by_area_val else None
            results[f"cg_{suffix}"] = cg_val.get(color_space) if cg_val else None
            results[f"cg_by_area_uv_{suffix}"] = cg_by_area_uv_val.get(color_space) if cg_by_area_uv_val else None
            results[f"cg_uv_{suffix}"] = cg_uv_val.get(color_space) if cg_uv_val else None

    except Exception as e:
        logger.error(f"Failed 'Color Gamut' calculation: {e}")
        for suffix in COLOR_SPACE_KEY_SUFFIX.values():
            results[f"cg_by_area_{suffix}"] = None
            results[f"cg_{suffix}"] = None
            results[f"cg_by_area_uv_{suffix}"] = None
            results[f"cg_uv_{suffix}"] = None

    try:
        results["temperature"] = temperature(device_report)
    except Exception as e:
        logger.error(f"Failed 'temperature' calculation: {e}")
        results["temperature"] = None

    try:
        results["delta_e"] = delta_e(device_report)
    except Exception as e:
        logger.error(f"Failed 'delta_e' calculation: {e}")
        results["delta_e"] = None

    try:
        results["coordinates"] = parse.get_coordinates(device_report)
    except Exception as e:
        logger.error(f"Failed 'get_coordinates': {e}")
        results["coordinates"] = None

    return results