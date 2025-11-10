import json
import math
import yaml
from loguru import logger

def parse_yaml(yaml_file, dictionary, key_name, k):
    with open(yaml_file, "r") as file:
        yaml_data = yaml.safe_load(file)
    value = yaml_data[dictionary].get(key_name, {}).get(k, None)
    return value


def coordinate_srgb(file):
    coordinates_rgb = []
    for coordinates_list in ("Red", "Green", "Blue"):
        for z in ("x", "y"):
            temp = parse_yaml(file, "sRGB", coordinates_list, z)
            coordinates_rgb.append(temp)
    return coordinates_rgb


def coordinate_ntsc(file):
    coordinates_ntsc = []
    for coordinates_list in ("Red", "Green", "Blue"):
        for z in ("x", "y"):
            temp = parse_yaml(file, "NTSC", coordinates_list, z)
            coordinates_ntsc.append(temp)
    return coordinates_ntsc


def coordinates_of_triangle(device_report):
    # Initialize a dictionary to store the coordinates
    rgb_coordinates = {"RedColor": None, "GreenColor": None, "BlueColor": None}

    # Iterate through the measurements and extract coordinates
    for measurement in device_report["Measurements"]:
        location = measurement["Location"]
        if location in rgb_coordinates:
            x = float(measurement["x"])
            y = float(measurement["y"])
            rgb_coordinates[location] = (x, y)

    # Ensure the coordinates are extracted in the correct order: Red, Green, Blue
    result = []
    for color in ["RedColor", "GreenColor", "BlueColor"]:
        if rgb_coordinates[color] is not None:
            result.extend(rgb_coordinates[color])

    return result


def get_coordinates(device_report, is_tv_flag):
    """
    Extracts the x and y coordinates for RedColor, GreenColor, BlueColor, and Center
    from the given JSON file.

    Args:
        file (string): Path to the JSON file.
        is_tv_flag (bool): True if the coordinates should be calculated for TV.
    """
    if not device_report:
        return {}

    coordinates = {f"{color}_{axis}": None for color in ["Red", "Green", "Blue", "Center"] for axis in ["x", "y"]}

    # Define mapping based on is_tv_flag
    location_map = {
        "RedColor": "Red",
        "GreenColor": "Green",
        "BlueColor": "Blue",
        # Conditional mapping for the Center point
        "WhiteColor": "Center" if is_tv_flag else None,
        "Center": "Center" if not is_tv_flag else None
    }

    # Filter out None values in the map for efficiency
    location_map = {k: v for k, v in location_map.items() if v}

    for measurement in device_report["Measurements"]:
        location = measurement["Location"]
        target_key = location_map.get(location)

        if target_key:
            try:
                coordinates[f"{target_key}_x"] = float(measurement["x"])
                coordinates[f"{target_key}_y"] = float(measurement["y"])
            except ValueError:
                # Handle cases where 'x' or 'y' are not valid floats
                pass

    return coordinates


def find_closest_to_target(device_report, target_x, target_y):
    # Parse the JSON data if it's a string
    # Extract measurements
    measurements = device_report.get("Measurements", [])

    # Initialize variables to track the closest location
    closest_location = None
    closest_distance = float("inf")
    reference_x = None
    reference_y = None
    reference_lv = None

    # Iterate through the measurements to find the closest location
    for measurement in measurements:
        # Get x, y, and Lv values
        x = float(measurement["x"])
        y = float(measurement["y"])
        lv = float(measurement["Lv"])

        # Calculate the Euclidean distance to the target (x, y)
        distance = math.sqrt((x - target_x) ** 2 + (y - target_y) ** 2)

        # Update the closest location if this one is closer
        if distance < closest_distance:
            closest_distance = distance
            closest_location = measurement["Location"]
            reference_x = x
            reference_y = y
            reference_lv = lv

    # Return the closest location and its reference values
    return {
        "Location": closest_location,
        "x": reference_x,
        "y": reference_y,
        "Lv": reference_lv,
    }

def get_device_info(file_path):
    """
    Extracts the device configuration name (DeviceConfiguration), IsTV flag,
    and SerialNumber from the JSON file.

    Returns:
        tuple: (str/None device_config, bool is_tv, str/None serial_number)
    """
    data = parse_one_file(file_path)

    if data is None:
        # Return None and False if parsing failed
        return None, False, None

    # Extract data using .get() for safety (with default values)
    device_config = data.get("DeviceConfiguration", "UnknownDevice")
    is_tv = data.get("IsTV", False)
    serial_number = data.get("SerialNumber", "UnknownSN")

    # Return DeviceConfiguration, IsTV, and SerialNumber
    return device_config, is_tv, serial_number

def parse_one_file(file_path):
    """Loads and returns data from a single JSON file."""
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading/parsing file {file_path}: {e}")
        return None