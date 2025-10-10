import glob
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import yaml
from loguru import logger


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


def generate_comparison_report(json_data_file, yaml_data_file, output_json_file):
    """
    Compares data from a JSON results file with expected values from a YAML file,
    includes all relevant data in the report, and saves it to a JSON file.
    """
    json_data = load_json_file(json_data_file)
    yaml_data = load_yaml_file(yaml_data_file)

    if json_data is None or yaml_data is None:
        logger.error("Aborting comparison due to file loading errors.")
        error_report = {
            "error": "Failed to load input files.",
            "details": f"JSON file: '{json_data_file}', YAML file: '{yaml_data_file}'",
        }
        try:
            with open(output_json_file, "w", encoding="utf-8") as f:
                json.dump(error_report, f, indent=4)
            logger.error(f"Error report saved to {output_json_file}")
        except IOError:
            logger.critical(
                f"Could not write error report to {output_json_file} after file loading failure."
            )
        return

    json_results_root = json_data.get("Results", {})
    expected_tests_yaml = yaml_data.get("main_tests", {})

    if not isinstance(json_results_root, dict):
        logger.warning(
            f"'Results' key in JSON file '{json_data_file}' is not a dictionary or is missing. Treating as empty."
        )
        json_results_root = {}
    if not isinstance(expected_tests_yaml, dict):
        logger.error(
            f"'main_tests' key in YAML file '{yaml_data_file}' is not a dictionary or is missing. Cannot generate report."
        )
        error_report = {
            "error": f"'main_tests' key missing or invalid in YAML: {yaml_data_file}."
        }
        try:
            with open(output_json_file, "w", encoding="utf-8") as f:
                json.dump(error_report, f, indent=4)
            logger.error(f"Error report saved to {output_json_file}")
        except IOError:
            logger.critical(
                f"Could not write error report to {output_json_file} after YAML parsing failure."
            )
        return

    coordinate_yaml_keys = {
        "Red_x",
        "Red_y",
        "Green_x",
        "Green_y",
        "Blue_x",
        "Blue_y",
        "White_x",
        "White_y",
    }

    # Mapping for YAML keys to JSON keys if they differ.
    json_key_mapping = {
        "Brightness_uniformity": "BrightnessUniformity",
        "Cg_rgb_area": "CgByAreaRGB",
        "Cg_ntsc_area": "CgByAreaNTSC",
        "Cg_rgb": "CgRGB",
        "Cg_ntsc": "CgNTSC",
        "Delta_e": "DeltaE",
        # Coordinate specific mappings from YAML key to JSON key (within "Coordinates" object in JSON)
        "White_x": "Center_x",
        "White_y": "Center_y",
    }

    full_report = {}

    for yaml_key, expected_values_dict in expected_tests_yaml.items():
        report_item = {
            "status": "N/A",
            "reason": "Initialization or data issue",
            "actual_values": None,
            "expected_values": expected_values_dict,
        }

        if not isinstance(expected_values_dict, dict):
            report_item["reason"] = (
                f"Expected values for '{yaml_key}' in YAML is not a dictionary."
            )
            full_report[yaml_key] = report_item
            continue

        is_coordinate_test = yaml_key in coordinate_yaml_keys
        json_lookup_key = json_key_mapping.get(yaml_key, yaml_key)

        actual_data_dict_for_test = None

        if is_coordinate_test:
            json_coordinates_data_root = json_results_root.get(
                "Coordinates", {}
            )
            if isinstance(json_coordinates_data_root, dict):
                actual_data_dict_for_test = json_coordinates_data_root.get(
                    json_lookup_key
                )
            else:
                report_item["reason"] = (
                    f"'Coordinates' object missing or invalid in JSON results; cannot evaluate '{yaml_key}' (looking for '{json_lookup_key}')."
                )
        else:
            actual_data_dict_for_test = json_results_root.get(json_lookup_key)

        if isinstance(actual_data_dict_for_test, dict):
            report_item["actual_values"] = (
                actual_data_dict_for_test.copy()
            )
        elif actual_data_dict_for_test is None:
            report_item["actual_values"] = None
            report_item["reason"] = (
                f"Actual data for '{json_lookup_key}' (from YAML key '{yaml_key}') is null or missing in JSON."
            )
        else:
            report_item["actual_values"] = {
                "raw_value_found": actual_data_dict_for_test
            }
            report_item["reason"] = (
                f"Actual data for '{json_lookup_key}' (from YAML key '{yaml_key}') is not a dictionary (type: {type(actual_data_dict_for_test).__name__}). Cannot process rules."
            )

        if not isinstance(actual_data_dict_for_test, dict):
            full_report[yaml_key] = report_item
            continue

        if is_coordinate_test:
            actual_min = actual_data_dict_for_test.get("min")
            actual_max = actual_data_dict_for_test.get("max")
            expected_min = expected_values_dict.get("min")
            expected_max = expected_values_dict.get("max")

            if actual_min is None:
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Actual 'min' value missing in JSON for coordinate test.",
                    }
                )
            elif actual_max is None:
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Actual 'max' value missing in JSON for coordinate test.",
                    }
                )
            elif expected_min is None:
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Expected 'min' value missing in YAML for coordinate test.",
                    }
                )
            elif expected_max is None:
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Expected 'max' value missing in YAML for coordinate test.",
                    }
                )
            elif not all(
                    isinstance(v, (int, float))
                    for v in [actual_min, actual_max, expected_min, expected_max]
            ):
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Non-numeric data encountered for coordinate comparison.",
                    }
                )
            elif actual_min < expected_min:
                report_item.update(
                    {
                        "status": "FAIL",
                        "reason": f"Actual min ({actual_min}) < Expected min ({expected_min})",
                    }
                )
            elif actual_max > expected_max:
                report_item.update(
                    {
                        "status": "FAIL",
                        "reason": f"Actual max ({actual_max}) > Expected max ({expected_max})",
                    }
                )
            else:
                report_item.update(
                    {"status": "PASS", "reason": "All coordinate checks passed."}
                )
        else:
            actual_avg = actual_data_dict_for_test.get("avg")
            actual_min_val = actual_data_dict_for_test.get("min")
            expected_typ = expected_values_dict.get("typ")
            expected_min_thresh = expected_values_dict.get("min")

            if actual_avg is None:
                report_item.update(
                    {"status": "N/A", "reason": "Actual 'avg' value missing in JSON."}
                )
            elif actual_min_val is None:
                report_item.update(
                    {"status": "N/A", "reason": "Actual 'min' value missing in JSON."}
                )
            elif expected_typ is None:
                report_item.update(
                    {"status": "N/A", "reason": "Expected 'typ' value missing in YAML."}
                )
            elif expected_min_thresh is None:
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Expected 'min' threshold missing in YAML.",
                    }
                )
            elif not all(
                    isinstance(v, (int, float))
                    for v in [actual_avg, actual_min_val, expected_typ, expected_min_thresh]
            ):
                report_item.update(
                    {
                        "status": "N/A",
                        "reason": "Non-numeric data encountered for general test comparison.",
                    }
                )
            elif actual_avg < expected_typ:
                report_item.update(
                    {
                        "status": "FAIL",
                        "reason": f"Actual avg ({actual_avg}) < Expected typ ({expected_typ})",
                    }
                )
            elif actual_min_val < expected_min_thresh:
                report_item.update(
                    {
                        "status": "FAIL",
                        "reason": f"Actual min ({actual_min_val}) < Expected min threshold ({expected_min_thresh})",
                    }
                )

            elif yaml_key == "Temperature":
                actual_max_val = actual_data_dict_for_test.get("max")
                expected_max_thresh = expected_values_dict.get("max")

                if (actual_max_val is not None and expected_max_thresh is not None and
                        isinstance(actual_max_val, (int, float)) and isinstance(expected_max_thresh, (int, float)) and
                        actual_max_val > expected_max_thresh):
                    report_item.update(
                        {
                            "status": "FAIL",
                            "reason": f"Actual max ({actual_max_val}) > Expected max ({expected_max_thresh}) for Temperature",
                        }
                    )
                elif actual_avg >= expected_typ:
                    report_item.update(
                        {
                            "status": "PASS",
                            "reason": f"Actual avg ({actual_avg}) >= Expected typ ({expected_typ})",
                        }
                    )
                else:
                    report_item.update(
                        {
                            "status": "ERROR",
                            "reason": "Temperature test: max check could not be performed or logical error occurred.",
                        }
                    )
            elif actual_avg >= expected_typ:
                report_item.update(
                    {
                        "status": "PASS",
                        "reason": f"Actual avg ({actual_avg}) >= Expected typ ({expected_typ})",
                    }
                )
            else:
                report_item.update(
                    {
                        "status": "ERROR",
                        "reason": "Logical error or unhandled case in non-coordinate test evaluation. Data might not fit defined PASS/FAIL rules.",
                    }
                )
        full_report[yaml_key] = report_item

    try:
        with open(output_json_file, "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=4, ensure_ascii=False)
        logger.success(
            f"Comparison report successfully saved to {output_json_file}"
        )
    except IOError as e:
        logger.error(f"Could not write report to {output_json_file}. Details: {e}")
    except TypeError as e:
        logger.error(f"Data in report is not JSON serializable. Details: {e}")
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