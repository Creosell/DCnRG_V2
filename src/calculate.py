import matplotlib.pyplot as plt
import numpy as np
from colormath2.color_conversions import convert_color
from colormath2.color_diff import delta_e_cie2000
from colormath2.color_objects import xyYColor, LabColor
from shapely.geometry import Polygon

import src.helpers as h
import src.parse as parse


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


def brightness(file, is_tv):
    """
    Calculates the minimum (min) and maximum (max) brightness
    from all measurement points excluding color points (Red, Green, Blue, Black, White).
    Also calculates the typical (typ) brightness for the report,
    which is either 'WhiteColor' (for TV) or 'Center' (otherwise).
    """
    report = h.parse_one_file(file)
    if report is None:
        return {"min": None, "typ": None, "max": None, "uniformity_center_lv": None}

    measurements = report.get("Measurements", [])

    # Map location names to their required keys
    report_typ_key = "WhiteColor" if is_tv else "Center"

    # Collect all Lv values into a dictionary for quick access
    lv_values = {}
    for m in measurements:
        location = m.get("Location")
        try:
            lv_values[location] = float(m.get("Lv"))
        except (ValueError, TypeError, KeyError):
            continue

    # Point for the typical value (typ)
    typical_lv_for_report = lv_values.get(report_typ_key)

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

    # Return the result
    return {
        "min": min_lv,
        "typ": typical_lv_for_report,
        "max": max_lv,
    }


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


def cg_by_area(file, color_space):
    coordinate = parse.coordinates_of_triangle(file)
    if len(coordinate) != 6:
        return None
    x1, y1, x2, y2, x3, y3 = coordinate
    triangle = np.array([[x1, y1], [x2, y2], [x3, y3]])
    triangle_area = area(triangle)

    if triangle_area == 0:
        return None

    color_gamut_srgb = (triangle_area / 0.112) * 100
    color_gamut_ntsc = (triangle_area / 0.158) * 100

    # Use a dictionary for concise return
    return_map = {
        "sRGB, NTSC": (float(color_gamut_srgb), float(color_gamut_ntsc)),
        "sRGB": (float(color_gamut_srgb), None),
        "NTSC": (None, float(color_gamut_ntsc)),
    }

    # Return (None, None) by default
    return return_map.get(color_space, (None, None))


def cg(file, color_space, srgb, ntsc):
    coordinate = parse.coordinates_of_triangle(file)
    if len(coordinate) != 6:
        return None
    x1, y1, x2, y2, x3, y3 = coordinate

    # Calculate overlap percentage once
    ntsc_overlap = calculate_overlap_percentage(*ntsc, x1, y1, x2, y2, x3, y3)
    rgb_overlap = calculate_overlap_percentage(*srgb, x1, y1, x2, y2, x3, y3)

    # Error handling if area is 0
    if isinstance(ntsc_overlap, str) or isinstance(rgb_overlap, str):
        # If there is an error (e.g., area is 0), return None, None
        return None, None

    # Use a dictionary for concise return
    return_map = {
        "sRGB, NTSC": (rgb_overlap, ntsc_overlap),
        "sRGB": (rgb_overlap, None),
        "NTSC": (None, ntsc_overlap),
    }

    # Return (None, None) by default
    return return_map.get(color_space, (None, None))


def contrast(file_path, is_tv):
    """
    Calculates a contrast ratio.
    Uses WhiteColor/BlackColor for TV (is_tv=True) and Center/BlackColor otherwise.
    """
    report = h.parse_one_file(file_path)
    if report is None:
        raise ValueError("Report is empty or could not be parsed.")

    measurements = report.get("Measurements", [])

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


def temperature(file):
    report = h.parse_one_file(file)
    if report is None:
        raise ValueError("Report is empty or could not be parsed.")

    measurements = report.get("Measurements", [])

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


def delta_e(file):
    """Calculates Delta E Color Uniformity for given locations."""
    locations_to_check = {
        "BottomLeft", "BottomCenter", "BottomRight",
        "MiddleLeft", "Center", "MiddleRight",
        "TopLeft", "TopCenter", "TopRight",
    }
    report = h.parse_one_file(file)
    if report is None:
        return "Error: Report is empty or could not be parsed."

    measurements = report.get("Measurements", [])

    # Use parse.find_closest_to_target to determine the reference point
    # Expected x/y are taken from Center
    center_data = next(
        (m for m in measurements if m.get('Location') == 'Center'),
        {}
    )

    expected_x = float(center_data.get('x', '0.0'))
    expected_y = float(center_data.get('y', '0.0'))

    ref = parse.find_closest_to_target(report, expected_x, expected_y)

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


def serial_number(file):
    report = h.parse_one_file(file)
    sn = report.get("SerialNumber", None) if report else None
    return sn


def measurement_time(file):
    report = h.parse_one_file(file)
    time = report.get("MeasurementDateTime", None) if report else None
    return time


def plot_color_space(rgb, ntsc, x1, y1, x2, y2, x3, y3, output_file, color_space_pic):
    """Plots the color space with sRGB and device triangles and a background image."""
    plt.figure(figsize=(8, 8))
    plt.title("Color Space with sRGB, NTSC and Device Triangles")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.xlim(0, 0.8)
    plt.ylim(0, 0.9)

    # Add the image to the background
    img = plt.imread(color_space_pic)
    plt.imshow(
        img, extent=[0, 0.77, 0, 0.82], aspect="auto"
    )

    # Draw the sRGB triangle
    srgb_triangle = np.array(
        [[rgb[0], rgb[1]], [rgb[2], rgb[3]], [rgb[4], rgb[5]], [rgb[0], rgb[1]]]
    )
    plt.plot(srgb_triangle[:, 0], srgb_triangle[:, 1], label="sRGB", color="blue")

    # Draw the device triangle
    device_triangle = np.array([[x1, y1], [x2, y2], [x3, y3], [x1, y1]])
    plt.plot(
        device_triangle[:, 0], device_triangle[:, 1], label="Device", color="green"
    )

    # BUG FIX: Use correct Y coordinates for NTSC
    ntsc_triangle = np.array(
        [[ntsc[0], ntsc[1]], [ntsc[2], ntsc[3]], [ntsc[4], ntsc[5]], [ntsc[0], ntsc[1]]]
    )
    plt.plot(ntsc_triangle[:, 0], ntsc_triangle[:, 1], label="NTSC", color="black")

    # Add the legend
    plt.legend()

    # Save the plot to a file
    plt.savefig(output_file)
    plt.close()