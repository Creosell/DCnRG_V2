import numpy as np
from colormath2.color_conversions import convert_color
from colormath2.color_diff import delta_e_cie2000
from colormath2.color_objects import xyYColor, LabColor
from shapely.geometry import Polygon

import src.helpers as h
import src.parse as parse

# Format: (Standard Name, [[Red_x, Red_y], [Green_x, Green_y], [Blue_x, Blue_y]])
COLOR_STANDARDS = {
    "NTSC": [
        [0.67, 0.33],
        [0.21, 0.71],
        [0.14, 0.08]
    ],
    "sRGB": [
        [0.64, 0.33],
        [0.3, 0.6],
        [0.15, 0.06]
    ],
    "DCI-P3": [
        [0.680, 0.320],
        [0.265, 0.690],
        [0.150, 0.060]
    ]
}

def area(p):
    """Calculates the area of a triangle defined by three points."""
    return 0.5 * abs(np.cross(p[1] - p[0], p[2] - p[0]))


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


def cg_by_area(device_report, color_space):
    coordinate = parse.coordinates_of_triangle(device_report)
    if len(coordinate) != 6:
        return None

    x1, y1, x2, y2, x3, y3 = coordinate
    dut_triangle = np.array([[x1, y1], [x2, y2], [x3, y3]])
    dut_triangle_area = area(dut_triangle)
    if dut_triangle_area == 0:
        return None

    srgb_triangle = np.array(COLOR_STANDARDS.get("sRGB"))
    ntsc_triangle = np.array(COLOR_STANDARDS.get("NTSC"))
    dci_p3_triangle = np.array(COLOR_STANDARDS.get("DCI-P3"))
    srgb_triangle_area = area(srgb_triangle)
    ntsc_triangle_area = area(ntsc_triangle)
    dci_p3_triangle_area = area(dci_p3_triangle)

    # color_gamut_srgb = (dut_triangle_area / 0.112) * 100
    # color_gamut_ntsc = (dut_triangle_area / 0.158) * 100

    color_gamut_srgb = (dut_triangle_area / srgb_triangle_area) * 100
    color_gamut_ntsc = (dut_triangle_area / ntsc_triangle_area) * 100
    color_gamut_dci_p3 = (dut_triangle_area / dci_p3_triangle_area) * 100

    # Use a dictionary for concise return
    return_map = {
        "sRGB, NTSC": (float(color_gamut_srgb), float(color_gamut_ntsc)),
        "sRGB": (float(color_gamut_srgb), None),
        "NTSC": (None, float(color_gamut_ntsc)),
        "DCI-P3": (float(color_gamut_dci_p3), None)
    }

    # Return (None, None) by default
    return return_map.get(color_space, (None, None))


def cg(device_report, color_space):
    dut_coordinates = parse.coordinates_of_triangle(device_report)
    if len(dut_coordinates) != 6:
        return None

    x1, y1, x2, y2, x3, y3 = dut_coordinates
    ntsc = [coord for point in COLOR_STANDARDS.get("NTSC") for coord in point]
    srgb = [coord for point in COLOR_STANDARDS.get("sRGB") for coord in point]
    dci_p3 = [coord for point in COLOR_STANDARDS.get("DCI-P3") for coord in point]

    # Calculate overlap percentage once
    ntsc_overlap = calculate_overlap_percentage(*ntsc, x1, y1, x2, y2, x3, y3)
    rgb_overlap = calculate_overlap_percentage(*srgb, x1, y1, x2, y2, x3, y3)
    dci_p3_overlap = calculate_overlap_percentage(*dci_p3, x1, y1, x2, y2, x3, y3)

    # Error handling if area is 0
    if isinstance(ntsc_overlap, str) or isinstance(rgb_overlap, str):
        # If there is an error (e.g., area is 0), return None, None
        return None, None

    # Use a dictionary for concise return
    return_map = {
        "sRGB, NTSC": (rgb_overlap, ntsc_overlap),
        "sRGB": (rgb_overlap, None),
        "NTSC": (None, ntsc_overlap),
        "DCI-P3": (dci_p3_overlap, None)
    }

    # Return (None, None) by default
    return return_map.get(color_space, (None, None))


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
        return "Error: Report is empty or could not be parsed."

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
        return "Error: Missing reference color data for Center."

    delta_e_values = []

    try:
        ref_color = xyYColor(float(ref_x), float(ref_y), float(ref_lv))
        ref_lab = convert_color(ref_color, LabColor)
    except (ValueError, TypeError):
        return "Error: Invalid reference color data."

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
    if delta_e_values:
        avg_delta_e = sum(delta_e_values) / len(delta_e_values)
        return avg_delta_e
    else:
        return "Error: No valid Delta E values calculated."
