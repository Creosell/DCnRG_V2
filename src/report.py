import math
import yaml
from collections import defaultdict
import os
import glob
import json
from pathlib import Path

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
    print(f"json report name ok: {json_filename}")

    # Structure the data to save in the JSON file
    json_data = {
        "SerialNumber": sn,
        "MeasurementDateTime": t,
        "Results": {
            "Brightness": brightness,
            "BrightnessUniformity": brightness_uniformity,
            "CgByAreaRgb": cg_by_area_rgb,
            "CgByAreaNtsc": cg_by_area_ntsc,
            "CgRgb": cg_rgb,
            "CgNtsc": cg_ntsc,
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
    # Deletion of old Typ*.json files (from original script)

    pattern = os.path.join(str(input_folder), f"{device_name}_*.json")
    device_reports = glob.glob(pattern)
    # files_to_delete = glob.glob(pattern)
    # for file_path in files_to_delete:
    #     try:
    #         os.remove(file_path)
    #         print(f"Deleted file: {file_path}")
    #     except OSError as e:
    #         print(f"Error deleting file {file_path}: {e}")

    aggregated_data = defaultdict(list)  # Stores lists of values for each key path
    all_keys_paths = set()  # Stores all unique flattened key paths encountered
    serial_numbers = []

    for file in device_reports:
        if file.endswith(".json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from file {file}: {e}. Skipping file.")
                continue
            except Exception as e:
                print(f"Error reading file {file}: {e}. Skipping file.")
                continue

            if "SerialNumber" in data and data["SerialNumber"] is not None:
                serial_numbers.append(data["SerialNumber"])
            else:
                print(f"Warning: 'SerialNumber' not found or is null in {file}.")

            if "Results" not in data or not isinstance(data["Results"], dict):
                print(
                    f"Warning: 'Results' not found or not a dictionary in {file}. Skipping."
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
                            )  # Mark presence of this key with an empty dict
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
                            # Else: non-numeric/non-None items in list are skipped for this element's stats
                        aggregated_data[flat_key].append(sanitized_list)
                    # Other data types (e.g. strings) are noted by all_keys_paths but not aggregated for stats

            process_items(data["Results"], [])

    final_results_data = {}
    sorted_key_paths = sorted(list(all_keys_paths))

    for flat_key in sorted_key_paths:
        # values_list_for_key contains raw collected data for this flat_key:
        # e.g., [10, 20, None] for "MetricA"
        # or `[{}]` if "EmptyGroup" was `{"EmptyGroup": {}}` in one file
        # or `[]` if "Coordinates" was always a non-empty dict (purely structural parent)
        values_list_for_key = aggregated_data.get(flat_key, [])

        stat_package = {"avg": None, "min": None, "max": None}  # Default

        if not values_list_for_key:
            # Key path existed (e.g. "Coordinates") but never held a direct value/null/empty_dict.
            # It was purely structural. stat_package remains all None.
            pass
        elif all(
            v is None or (isinstance(v, dict) and not v) for v in values_list_for_key
        ):
            # All collected items for this key were None or empty dicts {}.
            # stat_package remains all None.
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

            if not has_any_list:  # Should be rare if any(isinstance(v,list)) was true
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
            # else: stat_package remains all None (e.g., values were [None, {}, "text"])

        # CRITICAL FIX: Skip setting stats for purely structural parent keys
        # A key is purely structural if no data was ever aggregated for it directly
        # (i.e., values_list_for_key is empty). Its stat_package will be all-nulls.
        if not values_list_for_key and is_effectively_all_null_stat_package(
            stat_package
        ):
            # print(f"Skipping set_nested_value for purely structural key: {flat_key}")
            continue

        set_nested_value(final_results_data, flat_key, stat_package)

    output_data = {
        "SerialNumber": sorted(list(set(s for s in serial_numbers if s is not None))),
        "Results": final_results_data,
    }

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)
        print(f"Full report with averages, min, and max values saved to {output_file}")
    except Exception as e:
        print(f"Error writing output JSON to file {output_file}: {e}")


def load_json_file(filepath):
    """Loads data from a JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        # These print statements are for script operational errors, not the report itself.
        print(f"Error: JSON file not found at {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {filepath}. Details: {e}")
        return None


def load_yaml_file(filepath):
    """Loads data from a YAML file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        print(f"Error: YAML file not found at {filepath}")
        return None
    except yaml.YAMLError as e:
        print(f"Error: Could not parse YAML from {filepath}. Details: {e}")
        return None


def generate_comparison_report(json_data_file, yaml_data_file, output_json_file):
    """
    Compares data from a JSON results file with expected values from a YAML file,
    includes all relevant data in the report, and saves it to a JSON file.
    """
    json_data = load_json_file(json_data_file)
    yaml_data = load_yaml_file(yaml_data_file)

    if json_data is None or yaml_data is None:
        print("Aborting comparison due to file loading errors.")
        error_report = {
            "error": "Failed to load input files.",
            "details": f"JSON file: '{json_data_file}', YAML file: '{yaml_data_file}'",
        }
        try:
            with open(output_json_file, "w", encoding="utf-8") as f:
                json.dump(error_report, f, indent=4)
            print(f"Error report saved to {output_json_file}")
        except IOError:
            print(
                f"Critical Error: Could not write error report to {output_json_file} after file loading failure."
            )
        return

    json_results_root = json_data.get("Results", {})
    expected_tests_yaml = yaml_data.get("main_tests", {})

    if not isinstance(json_results_root, dict):
        print(
            f"Warning: 'Results' key in JSON file '{json_data_file}' is not a dictionary or is missing. Treating as empty."
        )
        json_results_root = {}  # Proceed with empty results if key is bad/missing
    if not isinstance(expected_tests_yaml, dict):
        print(
            f"Error: 'main_tests' key in YAML file '{yaml_data_file}' is not a dictionary or is missing. Cannot generate report."
        )
        error_report = {
            "error": f"'main_tests' key missing or invalid in YAML: {yaml_data_file}."
        }
        try:
            with open(output_json_file, "w", encoding="utf-8") as f:
                json.dump(error_report, f, indent=4)
            print(f"Error report saved to {output_json_file}")
        except IOError:
            print(
                f"Critical Error: Could not write error report to {output_json_file} after YAML parsing failure."
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
        "Cg_rgb_area": "CgByAreaRgb",
        "Cg_ntsc_area": "CgByAreaNtsc",
        "Cg_rgb": "CgRgb",
        "Cg_ntsc": "CgNtsc",
        "Delta_e": "DeltaE",
        # Coordinate specific mappings from YAML key to JSON key (within "Coordinates" object in JSON)
        "White_x": "Center_x",  # JSON uses Center_x for White_x from YAML
        "White_y": "Center_y",  # JSON uses Center_y for White_y from YAML
    }

    full_report = {}

    for yaml_key, expected_values_dict in expected_tests_yaml.items():
        report_item = {
            "status": "N/A",  # Default status
            "reason": "Initialization or data issue",  # Default reason, will be overwritten
            "actual_values": None,  # Will be populated with relevant actuals from JSON
            "expected_values": expected_values_dict,  # Store the whole expected block from YAML
        }

        if not isinstance(expected_values_dict, dict):
            report_item["reason"] = (
                f"Expected values for '{yaml_key}' in YAML is not a dictionary."
            )
            full_report[yaml_key] = report_item
            continue

        is_coordinate_test = yaml_key in coordinate_yaml_keys
        # Determine the key to look up in the JSON data
        json_lookup_key = json_key_mapping.get(yaml_key, yaml_key)

        actual_data_dict_for_test = None  # This will hold the specific test data dict (e.g., content of "Brightness" or "Coordinates.Red_x")

        if is_coordinate_test:
            json_coordinates_data_root = json_results_root.get(
                "Coordinates", {}
            )  # Get the "Coordinates" object from JSON
            if isinstance(json_coordinates_data_root, dict):
                actual_data_dict_for_test = json_coordinates_data_root.get(
                    json_lookup_key
                )
            else:
                # 'Coordinates' key itself is missing or not a dict in JSON results
                report_item["reason"] = (
                    f"'Coordinates' object missing or invalid in JSON results; cannot evaluate '{yaml_key}' (looking for '{json_lookup_key}')."
                )
                # actual_data_dict_for_test remains None, leading to N/A status
        else:  # Non-coordinate test
            actual_data_dict_for_test = json_results_root.get(json_lookup_key)

        # Populate actual_values in report_item and handle cases where the specific test data is null/missing or not a dict
        if isinstance(actual_data_dict_for_test, dict):
            report_item["actual_values"] = (
                actual_data_dict_for_test.copy()
            )  # Store a copy of the actual data dict
        elif actual_data_dict_for_test is None:
            # This covers "IF key in result json - null - write N/A for it"
            # Also covers if the key was entirely missing.
            report_item["actual_values"] = None  # Explicitly set to None in report
            report_item["reason"] = (
                f"Actual data for '{json_lookup_key}' (from YAML key '{yaml_key}') is null or missing in JSON."
            )
            # Status remains N/A (default)
        else:  # Data for the test item is present but not a dictionary (e.g., a string, number)
            report_item["actual_values"] = {
                "raw_value_found": actual_data_dict_for_test
            }
            report_item["reason"] = (
                f"Actual data for '{json_lookup_key}' (from YAML key '{yaml_key}') is not a dictionary (type: {type(actual_data_dict_for_test).__name__}). Cannot process rules."
            )
            # Status remains N/A (default)

        # If actual_data_dict_for_test is not a dictionary at this point (i.e., it's None or some other non-dict type),
        # we cannot apply the comparison rules. The status is N/A, and reason/actual_values are set.
        if not isinstance(actual_data_dict_for_test, dict):
            full_report[yaml_key] = report_item
            continue

            # --- Proceed with comparisons now that actual_data_dict_for_test is confirmed to be a dictionary ---
        if is_coordinate_test:
            actual_min = actual_data_dict_for_test.get("min")
            actual_max = actual_data_dict_for_test.get("max")
            expected_min = expected_values_dict.get("min")
            expected_max = expected_values_dict.get("max")

            # N/A checks for essential numeric values needed for comparison
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
            # Comparison logic for coordinates
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
            else:  # "In other cases - PASS"
                report_item.update(
                    {"status": "PASS", "reason": "All coordinate checks passed."}
                )
        else:  # Non-coordinate test
            actual_avg = actual_data_dict_for_test.get("avg")
            actual_min_val = actual_data_dict_for_test.get(
                "min"
            )  # Renamed to avoid conflict with expected_min
            expected_typ = expected_values_dict.get("typ")
            expected_min_thresh = expected_values_dict.get("min")  # Renamed for clarity

            # N/A checks for essential numeric values
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
            # Comparison logic for non-coordinates (order of rules matters)
            elif (
                    actual_avg < expected_typ
            ):  # Rule: If avg value in result json less then typ in yaml file - FAIL
                report_item.update(
                    {
                        "status": "FAIL",
                        "reason": f"Actual avg ({actual_avg}) < Expected typ ({expected_typ})",
                    }
                )
            elif (
                    actual_min_val < expected_min_thresh
            ):  # Rule: If min value in result json less then min in yaml file - FAIL
                report_item.update(
                    {
                        "status": "FAIL",
                        "reason": f"Actual min ({actual_min_val}) < Expected min threshold ({expected_min_thresh})",
                    }
                )

            # Additional check for Temperature key: FAIL if max value in JSON > max in YAML
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
                elif (
                        actual_avg >= expected_typ
                ):  # If Temperature max check passes, apply standard PASS logic
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
            elif (
                    actual_avg >= expected_typ
            ):  # Rule: If avg value in result json equal or more then typ in yaml file - PASS
                report_item.update(
                    {
                        "status": "PASS",
                        "reason": f"Actual avg ({actual_avg}) >= Expected typ ({expected_typ})",
                    }
                )


            else:
                # This case implies:
                # NOT (actual_avg < expected_typ)           => actual_avg >= expected_typ
                # NOT (actual_min_val < expected_min_thresh) => actual_min_val >= expected_min_thresh
                # NOT (actual_avg >= expected_typ)          => actual_avg < expected_typ (This creates a contradiction)
                # This state should ideally not be reached if rules are mutually exclusive and cover all scenarios for valid data.
                # Given the specific PASS condition, if it didn't FAIL and doesn't meet this PASS, it's an issue.
                report_item.update(
                    {
                        "status": "ERROR",
                        "reason": "Logical error or unhandled case in non-coordinate test evaluation. Data might not fit defined PASS/FAIL rules.",
                    }
                )

        full_report[yaml_key] = report_item

    # Save the full report to a JSON file
    try:
        with open(output_json_file, "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=4, ensure_ascii=False)
        print(
            f"Report successfully saved to {output_json_file}"
        )  # User feedback on success
    except IOError as e:
        print(f"Error: Could not write report to {output_json_file}. Details: {e}")
    except TypeError as e:  # Handle non-serializable data if any slips through
        print(f"Error: Data in report is not JSON serializable. Details: {e}")
        # Attempt to save a simplified error report if main dump fails
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
            pass  # Already tried to print an error about writing

    # The function could return full_report if its content is needed by a calling process
    # return full_report


def analyze_json_files_for_min_fail(folder_path, expected_result_path, output_path, device_name):
    """
    Analyzes JSON files in a folder, compares their minimum values against expected values,
    and saves the failing data to an output JSON file.

    Args:
        folder_path (str): The path to the folder containing the JSON files.
        expected_result_path (str): The path to the YAML file containing the expected results.
        output_path (str): The path to the output JSON file.
    """

    try:
        with open(expected_result_path, "r") as yaml_file:
            expected_data = yaml.safe_load(yaml_file)
            expected_values = expected_data["main_tests"]
    except FileNotFoundError:
        print(f"Error: Expected result file not found at {expected_result_path}")
        return
    except yaml.YAMLError as e:
        print(f"Error: Could not parse YAML file: {e}")
        return
    except KeyError:
        print("Error: 'main_tests' key not found in the YAML file.")
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

                    # Extract values based on the key
                    if key in results:
                        value = results[key]
                        if isinstance(value, dict) and "min" in value:
                            min_value = value["min"]
                        else:
                            min_value = value
                    elif key in [
                        "Red_x",
                        "Red_y",
                        "Green_x",
                        "Green_y",
                        "Blue_x",
                        "Blue_y",
                        "Center_x",
                        "Center_y",
                    ]:
                        if "Coordinates" in results:
                            try:
                                min_value = results["Coordinates"][key]
                            except KeyError:
                                pass  # Key not found in Coordinates
                    else:
                        continue

                    # Compare with expected minimum
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
                            print(
                                f"Warning: Could not convert value to float in {file} for key {key}. Skipping."
                            )
                            continue

        except FileNotFoundError:
            print(f"Error: JSON file not found: {file}")
        except json.JSONDecodeError as e:
            print(f"Error: Could not decode JSON file {file}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {file}: {e}")

    try:
        with open(output_path, "w") as outfile:
            json.dump(output_data, outfile, indent=4)
    except IOError as e:
        print(f"Error: Could not write output file: {e}")
        return

    print(f"Analysis complete. Results saved to {output_path}")
