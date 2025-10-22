import glob
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import yaml
from loguru import logger

REPORT_PRECISION = {
    "Brightness": 0,
    "Contrast": 0,
    "Temperature": 0,

    "BrightnessUniformity": 1,
    "CgByAreaRGB": 1,
    "CgByAreaNTSC": 1,
    "cgRGB": 1,
    "cgNTSC": 1,
    "DeltaE": 1,

    "Red_x": 3,
    "Red_y": 3,
    "Green_x": 3,
    "Green_y": 3,
    "Blue_x": 3,
    "Blue_y": 3,
    "White_x": 3,
    "White_y": 3,
    "Center_x":3,
    "Center_y":3,
}

# Special requirements for TV's
TOLERANCE_FOR_TV = 0.065 # Tolerance 6.5% for some TV checks
AVG_FAIL_SKIP_KEYS_FOR_TV = { # Keys which we skip while checking for FAIL by avg
    "Brightness",
    "Brightness_uniformity",
    "Cg_rgb_area",
    "Cg_ntsc_area",
    "Cg_rgb",
    "Cg_ntsc"
}


# Keys that are considered coordinate tests (using min/max bounds)
COORDINATE_TEST_KEYS = {
    "Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y", "White_x", "White_y",
}
# Mapping from YAML keys (e.g., 'Cg_rgb_area') to JSON keys (e.g., 'CgByAreaRGB')
YAML_TO_JSON_KEY_MAP = {
    "Brightness_uniformity": "BrightnessUniformity",
    "Cg_rgb_area": "CgByAreaRGB",
    "Cg_ntsc_area": "CgByAreaNTSC",
    "Cg_rgb": "CgRGB",
    "Cg_ntsc": "CgNTSC",
    "Delta_e": "DeltaE",
    # Special case: 'White_x' and 'White_y' are used for Center_x/y in JSON
    "White_x": "Center_x",
    "White_y": "Center_y",
}


def json_report(
    sn=None,
    t=None,
    brightness=None,
    brightness_uniformity=None,
    cg_by_area_rgb=None,
    cg_by_area_ntsc=None,
    cg_rgb=None,
    cg_ntsc=None,
    contrast=None,
    temperature=None,
    delta_e=None,
    coordinates=None,
    output_folder=Path("device_reports"),
    device_name=None
):
    # Define the JSON file name
    json_filename = f"{device_name}_{sn}_{t}.json"
    logger.debug(f"JSON report name: {json_filename}")

    # Structure the data to save in the JSON file
    json_data = {
        "SerialNumber": sn,
        "MeasurementDateTime": t,
        "Results": {
            "Brightness": brightness,
            "BrightnessUniformity": brightness_uniformity,
            "CgByAreaRGB": cg_by_area_rgb,
            "CgByAreaNTSC": cg_by_area_ntsc,
            "CgRGB": cg_rgb,
            "CgNTSC": cg_ntsc,
            "Contrast": contrast,
            "Temperature": temperature,
            "DeltaE": delta_e,
            "Coordinates": coordinates,
        },
    }

    # Save the JSON file in the output folder
    output_path = output_folder / json_filename
    with open(output_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

def safe_round(value, decimals=0):
    """Rounds the value only if it is an int or float. Otherwise, returns the original value (e.g., None)."""
    if isinstance(value, (int, float)):
        if decimals == 0:
            value = int(round(value))
        else:
            value = round(value, decimals)
    return value

def set_nested_value(d, path_str, value):
    """
    Sets a value in a nested dictionary using a dot-separated path string.
    If the path leads to an existing dictionary and the value is also a dictionary,
    it attempts to update the existing dictionary with the new one (merge).
    """
    parts = path_str.split(".")
    current = d
    for i, part in enumerate(parts[:-1]):
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]

    last_part = parts[-1]
    if (
        last_part in current
        and isinstance(current[last_part], dict)
        and isinstance(value, dict)
    ):
        current[last_part].update(value)
    else:
        current[last_part] = value


def is_effectively_all_null_stat_package(pkg):
    """
    Checks if a stat_package (dict with avg, min, max) contains all None values,
    considering that avg/min/max could be scalars or lists.
    """
    if not isinstance(pkg, dict):
        return False
    for stat_key in ["avg", "min", "max"]:
        val = pkg.get(stat_key)
        if val is None:
            continue
        if isinstance(val, list):
            if any(
                x is not None for x in val
            ):  # If any element in the list is not None
                return False
        elif val is not None:  # Scalar value is not None
            return False
    return True


def calculate_full_report(input_folder, output_file, device_name):
    """
    Aggregates data from multiple device-specific JSON reports (filtered by device_name),
    calculates element-wise statistics (min, avg, max) for all numeric and list values,
    and saves the aggregated results to a new JSON file.

    Args:
        input_folder (str/Path): The directory containing the individual JSON reports.
        output_file (str/Path): The path to save the final aggregated JSON report.
        device_name (str): The name of the device used to filter the reports.
    """

    pattern = os.path.join(str(input_folder), f"{device_name}_*.json")
    device_reports = glob.glob(pattern)

    aggregated_data = defaultdict(list)  # Stores lists of values for each key path
    all_keys_paths = set()  # Stores all unique flattened key paths encountered
    serial_numbers = []

    for file in device_reports:
        if file.endswith(".json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from file {file}: {e}. Skipping file.")
                continue
            except Exception as e:
                logger.error(f"Error reading file {file}: {e}. Skipping file.")
                continue

            if "SerialNumber" in data and data["SerialNumber"] is not None:
                serial_numbers.append(data["SerialNumber"])
            else:
                logger.warning(f"'SerialNumber' not found or is null in {file}.")

            if "Results" not in data or not isinstance(data["Results"], dict):
                logger.warning(
                    f"'Results' not found or not a dictionary in {file}. Skipping."
                )
                continue

            def process_items(current_dict, current_path_parts):
                for key, value in current_dict.items():
                    new_path_parts = current_path_parts + [key]
                    flat_key = ".".join(new_path_parts)
                    all_keys_paths.add(flat_key)

                    if isinstance(value, dict):
                        if not value:  # Empty dictionary
                            aggregated_data[flat_key].append(
                                {}
                            )  # Mark the presence of this key with an empty dict
                        process_items(value, new_path_parts)  # Recurse
                    elif value is None:
                        aggregated_data[flat_key].append(None)
                    elif isinstance(value, (int, float)):
                        if math.isnan(value) or math.isinf(value):
                            aggregated_data[flat_key].append(None)
                        else:
                            aggregated_data[flat_key].append(value)
                    elif isinstance(value, list):
                        sanitized_list = []
                        for item_in_list in value:
                            if isinstance(item_in_list, float) and (
                                math.isnan(item_in_list) or math.isinf(item_in_list)
                            ):
                                sanitized_list.append(None)
                            elif isinstance(
                                item_in_list, (int, float, type(None))
                            ):  # Allow numbers and None
                                sanitized_list.append(item_in_list)
                            # Else: non-numeric/non-None items in a list are skipped for this element's stats
                        aggregated_data[flat_key].append(sanitized_list)
                    # Other data types (e.g., strings) are noted by all_keys_paths but not aggregated for stats

            process_items(data["Results"], [])

    final_results_data = {}
    sorted_key_paths = sorted(list(all_keys_paths))

    for flat_key in sorted_key_paths:
        values_list_for_key = aggregated_data.get(flat_key, [])

        stat_package = {"avg": None, "min": None, "max": None}  # Default

        if not values_list_for_key:
            pass
        elif all(
            v is None or (isinstance(v, dict) and not v) for v in values_list_for_key
        ):
            pass
        elif any(isinstance(v, list) for v in values_list_for_key):
            # Handles list-based statistics (element-wise)
            valid_lists_data = []
            max_len = 0
            has_any_list = False
            for item in values_list_for_key:
                if isinstance(item, list):  # Already sanitized during process_items
                    valid_lists_data.append(item)
                    max_len = max(max_len, len(item))
                    has_any_list = True
                elif item is None:  # A file had 'null' for this list-type key
                    valid_lists_data.append(None)

            if not has_any_list:
                numeric_values = [
                    v
                    for v in values_list_for_key
                    if isinstance(v, (int, float)) and v is not None
                ]
                if numeric_values:
                    stat_package["avg"] = sum(numeric_values) / len(numeric_values)
                    stat_package["min"] = min(numeric_values)
                    stat_package["max"] = max(numeric_values)
            elif max_len == 0:  # All lists were empty
                stat_package = {"avg": [], "min": [], "max": []}
            else:
                avg_list, min_list, max_list = ([None] * max_len for _ in range(3))
                for i in range(max_len):
                    column_elements = [
                        lst[i]
                        for lst in valid_lists_data
                        if isinstance(lst, list)
                        and i < len(lst)
                        and isinstance(lst[i], (int, float))
                    ]
                    if column_elements:
                        avg_list[i] = sum(column_elements) / len(column_elements)
                        min_list[i] = min(column_elements)
                        max_list[i] = max(column_elements)
                stat_package = {"avg": avg_list, "min": min_list, "max": max_list}
        else:  # Scalar processing (list of numbers, possibly with Nones, empty dicts {})
            numeric_values = [
                v
                for v in values_list_for_key
                if isinstance(v, (int, float)) and v is not None
            ]
            if numeric_values:
                stat_package["avg"] = sum(numeric_values) / len(numeric_values)
                stat_package["min"] = min(numeric_values)
                stat_package["max"] = max(numeric_values)

        if not values_list_for_key and is_effectively_all_null_stat_package(
            stat_package
        ):
            continue

        precision = REPORT_PRECISION.get(flat_key.split('.')[-1], 2)

        for stat_key in ["avg", "min", "max"]:
            value = stat_package[stat_key]

            if isinstance(value, (int, float)):
                stat_package[stat_key] = safe_round(value, precision)
            elif isinstance(value, list):
                stat_package[stat_key] = [
                    safe_round(v, precision)
                    for v in value
                ]

        set_nested_value(final_results_data, flat_key, stat_package)

    output_data = {
        "SerialNumber": sorted(list(set(s for s in serial_numbers if s is not None))),
        "Results": final_results_data,
    }

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)
        logger.success(f"Full report with averages, min, and max values saved to {output_file}")
    except Exception as e:
        logger.error(f"Error writing output JSON to file {output_file}: {e}")


def load_json_file(filepath):
    """Loads data from a JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logger.error(f"JSON file not found at {filepath}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Could not decode JSON from {filepath}. Details: {e}")
        return None


def load_yaml_file(filepath):
    """Loads data from a YAML file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        logger.error(f"YAML file not found at {filepath}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Could not parse YAML from {filepath}. Details: {e}")
        return None


# Helper function for writing error reports
def write_error_report(output_file, error_report_data, error_context):
    """Helper function to write an error report to a JSON file."""
    logger.error(f"Aborting comparison due to {error_context}.")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(error_report_data, f, indent=4)
        logger.error(f"Error report saved to {output_file}")
    except IOError:
        logger.critical(f"Could not write error report to {output_file} after {error_context}.")


# Helper function for coordinate checks
def check_coordinate_bounds(actual_min, actual_max, expected_min, expected_max):
    """
    Checks coordinate data for presence (None), type (numeric), and boundary adherence (min/max).
    Returns (status, reason).
    """

    # --- N/A CHECKS ---

    # 1. Check for data presence
    missing_map = {
        (actual_min is None): "Actual 'min' value missing in JSON for coordinate test.",
        (actual_max is None): "Actual 'max' value missing in JSON for coordinate test.",
        (expected_min is None): "Expected 'min' value missing in YAML for coordinate test.",
        (expected_max is None): "Expected 'max' value missing in YAML for coordinate test.",
    }
    for condition, reason in missing_map.items():
        if condition:
            return "N/A", reason

    # 2. Check for data type (must be numeric)
    all_values = [actual_min, actual_max, expected_min, expected_max]
    if not all(isinstance(v, (int, float)) for v in all_values):
        return "N/A", "Non-numeric data encountered for coordinate comparison."

    # --- FAIL CHECKS ---

    # 3. Check lower bound
    if actual_min < expected_min:
        return "FAIL", f"Actual min ({actual_min}) < Expected min ({expected_min})"

    # 4. Check upper bound
    if actual_max > expected_max:
        return "FAIL", f"Actual max ({actual_max}) > Expected max ({expected_max})"

    # --- PASS ---
    return "PASS", "All coordinate checks passed."


# Helper function for general test checks
def check_general_test_status(yaml_key, actual_data_dict_for_test, expected_values_dict, is_tv_flag):
    """
    Checks general tests (avg/typ/min-threshold) for rule compliance.
    Returns (status, reason).

    Args:
        yaml_key (str): Key of the YAML file.
        actual_data_dict_for_test (dict): Actual test data.
        expected_values_dict (dict): Expected test data.
        is_tv_flag (bool): Whether the device under test is TV or not.
    """
    actual_avg = actual_data_dict_for_test.get("avg")
    actual_min_val = actual_data_dict_for_test.get("min")
    expected_typ = expected_values_dict.get("typ")
    expected_min_thresh = expected_values_dict.get("min")

    # 1. N/A Checks (presence)
    general_checks = [
        (actual_avg is None, "Actual 'avg' value missing in JSON."),
        (actual_min_val is None, "Actual 'min' value missing in JSON."),
        (expected_typ is None, "Expected 'typ' value missing in YAML."),
        (expected_min_thresh is None, "Expected 'min' threshold missing in YAML."),
    ]
    for condition, reason_msg in general_checks:
        if condition:
            return "N/A", reason_msg

    # 2. N/A Check (data type)
    all_values = [actual_avg, actual_min_val, expected_typ, expected_min_thresh]
    if not all(isinstance(v, (int, float)) for v in all_values):
        return "N/A", "Non-numeric data encountered for general test comparison."


    # 3. FAILS by min and avg values

    # Special rules for TV
    # Applying tolerance for contrast value
    if yaml_key == "Contrast" and is_tv_flag:
        tolerance_for_contract = expected_typ * TOLERANCE_FOR_TV
        expected_typ = expected_typ-tolerance_for_contract
    # Skipping checks for typical values according to a TV quality standard
    # if is_tv_flag and yaml_key in AVG_FAIL_SKIP_KEYS_FOR_TV:
    #     if actual_min_val < expected_min_thresh:
    #         return "FAIL", f"Actual min ({actual_min_val}) < Expected min threshold ({expected_min_thresh})"
    #     else:
    #         return "PASS", f"(TV) Actual min ({actual_min_val}) >= Expected min ({expected_min_thresh})"

    if actual_avg < expected_typ:
        return "FAIL", f"Actual avg ({actual_avg}) < Expected typ ({expected_typ})"
    if actual_min_val < expected_min_thresh:
        return "FAIL", f"Actual min ({actual_min_val}) < Expected min threshold ({expected_min_thresh})"

    # 4. Check for FAIL on max for Temperature
    if yaml_key == "Temperature":
        actual_max_val = actual_data_dict_for_test.get("max")
        expected_max_thresh = expected_values_dict.get("max")

        # Validation of max values before comparison
        is_valid_max_check = (
                actual_max_val is not None
                and expected_max_thresh is not None
                and isinstance(actual_max_val, (int, float))
                and isinstance(expected_max_thresh, (int, float))
        )

        if is_valid_max_check and actual_max_val > expected_max_thresh:
            return "FAIL", f"Actual max ({actual_max_val}) > Expected max ({expected_max_thresh}) for Temperature"

        # If no FAIL, and avg meets typ, then PASS
        if actual_avg >= expected_typ:
            return "PASS", f"Actual avg ({actual_avg}) >= Expected typ ({expected_typ})"

        return "ERROR", "Temperature test: logical error or max check was invalid."

    # 5. General PASS condition
    if actual_avg >= expected_typ:
        return "PASS", f"Actual avg ({actual_avg}) >= Expected typ ({expected_typ})"

    # 6. General ERROR
    return "ERROR", "Logical error or unhandled case in non-coordinate test evaluation. Data might not fit defined PASS/FAIL rules."


def generate_comparison_report(actual_result_file, expected_result_file, output_json_file, is_tv_flag):
    """
    Compares data from a JSON results file with expected values from a YAML file,
    includes all relevant data in the report, and saves it to a JSON file.

    Args:
        actual_result_file (Path): Path to the JSON file containing the actual data.
        expected_result_file (Path): Path to the JSON file containing the expected data.
        output_json_file (Path): Path to the output JSON file containing the report.
        is_tv_flag (bool): Whether the report from TV or not.
    """
    actual_result_data = load_json_file(actual_result_file)
    expected_result_data = load_yaml_file(expected_result_file)

    # --- 1. FILE LOADING CHECK ---
    if actual_result_data is None or expected_result_data is None:
        error_report = {
            "error": "Failed to load input files.",
            "details": f"JSON file: '{actual_result_file}', YAML file: '{expected_result_file}'",
        }
        write_error_report(output_json_file, error_report, "file loading errors")
        return

    # --- 2. ROOT KEY CHECK ---
    actual_result_root = actual_result_data.get("Results", {})
    expected_result_root = expected_result_data.get("main_tests", {})

    if not isinstance(actual_result_root, dict):
        logger.warning(
            f"'Results' key in JSON file '{actual_result_file}' is not a dictionary or is missing. Treating as empty."
        )
        actual_result_root = {}

    if not isinstance(expected_result_root, dict):
        error_report = {
            "error": f"'main_tests' key missing or invalid in YAML: {expected_result_file}."
        }
        write_error_report(output_json_file, error_report, "YAML parsing failure")
        return

    full_report = {}

    # --- 4. MAIN COMPARISON LOOP ---
    for test_name, expected_test_data in expected_result_root.items():
        report_item = {
            "status": "N/A",
            "reason": "Initialization or data issue",
            "actual_values": None,
            "expected_values": expected_test_data,
        }

        if not isinstance(expected_test_data, dict):
            report_item["reason"] = f"Expected values for '{test_name}' in YAML is not a dictionary."
            full_report[test_name] = report_item
            continue

        is_coordinate_test = test_name in COORDINATE_TEST_KEYS
        actual_data_key = YAML_TO_JSON_KEY_MAP.get(test_name, test_name)
        actual_test_details = None

        # A. GET ACTUAL DATA
        if is_coordinate_test:
            actual_coordinates_root = actual_result_root.get("Coordinates", {})
            if isinstance(actual_coordinates_root, dict):
                actual_test_details = actual_coordinates_root.get(actual_data_key)
            else:
                report_item[
                    "reason"] = f"'Coordinates' object missing or invalid in JSON results; cannot evaluate '{test_name}' (looking for '{actual_data_key}')."
        else:
            actual_test_details = actual_result_root.get(actual_data_key)

        # B. CHECK ACTUAL DATA TYPE
        if isinstance(actual_test_details, dict):
            report_item["actual_values"] = actual_test_details.copy()
        elif actual_test_details is None:
            report_item[
                "reason"] = f"Actual data for '{actual_data_key}' (from YAML key '{test_name}') is null or missing in JSON."
        else:
            report_item["actual_values"] = {"raw_value_found": actual_test_details}
            report_item[
                "reason"] = f"Actual data for '{actual_data_key}' (from YAML key '{test_name}') is not a dictionary (type: {type(actual_test_details).__name__}). Cannot process rules."

        if not isinstance(actual_test_details, dict):
            full_report[test_name] = report_item
            continue

        # C. DETERMINE STATUS (using helper functions)
        if is_coordinate_test:
            actual_min = actual_test_details.get("min")
            actual_max = actual_test_details.get("max")
            expected_min = expected_test_data.get("min")
            expected_max = expected_test_data.get("max")

            # Helper function: check_coordinate_bounds(...)
            status, reason = check_coordinate_bounds(actual_min, actual_max, expected_min, expected_max)
        else:
            # Helper function: check_general_test_status(...)
            status, reason = check_general_test_status(test_name, actual_test_details, expected_test_data, is_tv_flag)

        # D. SINGLE REPORT UPDATE
        report_item.update({"status": status, "reason": reason})
        full_report[test_name] = report_item

    # --- 5. SAVE REPORT ---
    try:
        with open(output_json_file, "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=4, ensure_ascii=False)
        logger.success(f"Comparison report successfully saved to {output_json_file}")
    except IOError as e:
        logger.error(f"Could not write report to {output_json_file}. Details: {e}")
    except TypeError as e:
        logger.error(f"Data in report is not JSON serializable. Details: {e}")
        # Logic to write a serialization error report (kept as is)
        try:
            with open(output_json_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "error": "Failed to serialize report data due to TypeError.",
                        "details": str(e),
                    },
                    f,
                    indent=4,
                )
        except IOError:
            pass


def analyze_json_files_for_min_fail(folder_path, expected_result_path, output_path, device_name):
    """
    Analyzes JSON files in a folder, compares their minimum values against expected values,
    and saves the failing data to an output JSON file.
    """

    try:
        with open(expected_result_path, "r") as yaml_file:
            expected_data = yaml.safe_load(yaml_file)
            expected_values = expected_data["main_tests"]
    except FileNotFoundError:
        logger.error(f"Expected result file not found at {expected_result_path}")
        return
    except yaml.YAMLError as e:
        logger.error(f"Could not parse YAML file: {e}")
        return
    except KeyError:
        logger.error("'main_tests' key not found in the YAML file.")
        return

    output_data = []

    pattern = os.path.join(str(folder_path), f"{device_name}_*.json")
    device_reports = glob.glob(pattern)

    for file in device_reports:
        try:
            with open(file, "r") as json_file:
                data = json.load(json_file)
                serial_number = data.get("SerialNumber", "Unknown")
                results = data.get("Results", {})

                for key, expected in expected_values.items():
                    min_value = None

                    if key in results:
                        value = results[key]
                        if isinstance(value, dict) and "min" in value:
                            min_value = value["min"]
                        else:
                            min_value = value
                    elif key in [
                        "Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y",
                        "Center_x", "Center_y",
                    ]:
                        if "Coordinates" in results:
                            try:
                                min_value = results["Coordinates"][key]
                            except KeyError:
                                pass
                    else:
                        continue

                    if min_value is not None:
                        try:
                            min_value = float(min_value)
                            if min_value < expected["min"]:
                                output_data.append(
                                    {
                                        serial_number: {
                                            "key": key,
                                            "min_value": min_value,
                                            "expected_min": expected["min"],
                                        }
                                    }
                                )
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Could not convert value to float in {file} for key {key}. Skipping."
                            )
                            continue

        except FileNotFoundError:
            logger.error(f"JSON file not found: {file}")
        except json.JSONDecodeError as e:
            logger.error(f"Could not decode JSON file {file}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing {file}: {e}")

    try:
        with open(output_path, "w") as outfile:
            json.dump(output_data, outfile, indent=4)
    except IOError as e:
        logger.error(f"Could not write output file: {e}")
        return

    logger.success(f"Analysis complete. Results saved to {output_path}")