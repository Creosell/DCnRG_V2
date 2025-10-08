import json

import yaml
import math
import src.helpers as h

def parse_yaml(yaml_file, dictionary, key_name, k):
    with open(yaml_file, "r") as file:
        yaml_data = yaml.safe_load(file)
    value = yaml_data[dictionary].get(key_name, {}).get(k, None)
    return value


def coordinate_sRGB(file):
    coordinates_rgb = []
    for list in ("Red", "Green", "Blue"):
        for z in ("x", "y"):
            temp = parse_yaml(file, "sRGB", list, z)
            coordinates_rgb.append(temp)
    return coordinates_rgb


def coordinate_NTSC(file):
    coordinates_ntsc = []
    for list in ("Red", "Green", "Blue"):
        for z in ("x", "y"):
            temp = parse_yaml(file, "NTSC", list, z)
            coordinates_ntsc.append(temp)
    return coordinates_ntsc


def coordinates_of_triangle(file):
    data = h.parse_one_file(file)
    # Initialize a dictionary to store the coordinates
    rgb_coordinates = {"RedColor": None, "GreenColor": None, "BlueColor": None}

    # Iterate through the measurements and extract coordinates
    for measurement in data["Measurements"]:
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


def get_coordinates(file):
    """
    Extracts the x and y coordinates for RedColor, GreenColor, BlueColor, and Center
    from the given JSON file.

    Args:
        json_file_path (str): Path to the JSON file.

    Returns:
        dict: A dictionary containing the coordinates for RedColor, GreenColor,
              BlueColor, and Center in the format:
              {
                "Red": (x, y),
                "Green": (x, y),
                "Blue": (x, y),
                "Center": (x, y)
              }
    """
    # Open and load the JSON file
    with open(file, "r") as file:
        data = json.load(file)

    # Initialize a dictionary to store the required coordinates
    coordinates = {
        "Red_x": None,
        "Red_y": None,
        "Green_x": None,
        "Green_y": None,
        "Blue_x": None,
        "Blue_y": None,
        "Center_x": None,
        "Center_y": None,
    }

    # Iterate through the measurements to find the required locations
    for measurement in data["Measurements"]:
        location = measurement["Location"]
        if location == "RedColor":
            coordinates["Red_x"] = float(measurement["x"])
            coordinates["Red_y"] = float(measurement["y"])
        elif location == "GreenColor":
            coordinates["Green_x"] = float(measurement["x"])
            coordinates["Green_y"] = float(measurement["y"])
        elif location == "BlueColor":
            coordinates["Blue_x"] = float(measurement["x"])
            coordinates["Blue_y"] = float(measurement["y"])
        elif location == "Center":
            coordinates["Center_x"] = float(measurement["x"])
            coordinates["Center_y"] = float(measurement["y"])

    return coordinates


def find_closest_to_target(file, target_x, target_y):
    # Parse the JSON data if it's a string
    # Extract measurements
    measurements = file.get("Measurements", [])

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
    Извлекает имя конфигурации устройства (DeviceConfiguration), флаг IsTV
    и SerialNumber из JSON-файла.

    Returns:
        tuple: (str/None device_config, bool is_tv, str/None serial_number)
    """
    data = h.parse_one_file(file_path)

    if data is None:
        # Возвращаем None и False, если парсинг не удался
        return None, False, None

    # Извлекаем данные, используя .get() для безопасности (со значениями по умолчанию)
    device_config = data.get("DeviceConfiguration")
    is_tv = data.get("IsTV", False)
    serial_number = data.get("SerialNumber")

    # Возвращаем DeviceConfiguration, IsTV и SerialNumber
    return device_config, is_tv, serial_number
