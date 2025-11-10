import datetime
import glob
import os
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

import src.calculate as cal
import src.helpers as h
import src.parse as parse
import src.report as r

# --- Step 0: Initialization and Settings ---

# Path configuration
CURRENT_TIME = datetime.datetime.now()
TIMESTAMP = CURRENT_TIME.strftime("%Y%m%d%H%M")

DATA_FOLDER = Path("data")
TEST_REPORTS_FOLDER = Path("test_reports")
ARCHIVE_REPORTS = Path("report_archive")
PICTURES_FOLDER = Path("pics")
LOGS_FOLDER = Path("logs")
RESULTS_FOLDER = Path("results")

MAIN_CONFIG = Path("config") / "main.yaml"
COLOR_SPACE_CONFIG = Path("config") / "color_space.yaml"
CIE_BACKGROUND_SVG = Path("config") / "CIExy1931.svg"
EXPECTED_RESULT = Path("config") / "expected_result.yaml"

# Logger configuration
logger.remove()
logger.add(sys.stderr, level="SUCCESS")
logger.add(LOGS_FOLDER / f"{TIMESTAMP}.log", level="DEBUG", encoding="utf-8")

# Parsing general settings
RGB = parse.coordinate_srgb(COLOR_SPACE_CONFIG)
NTSC = parse.coordinate_ntsc(COLOR_SPACE_CONFIG)
COLOR_SPACE = parse.parse_yaml(MAIN_CONFIG, "Task", "color_space", "type")
test = parse.parse_yaml(MAIN_CONFIG, "Task", "test", "type")

# Create working folders if they do not exist
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
TEST_REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
ARCHIVE_REPORTS.mkdir(parents=True, exist_ok=True)
PICTURES_FOLDER.mkdir(parents=True, exist_ok=True)
LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

# --- Step 1: File Collection and Grouping by Device Configuration ---
# Group files by DeviceConfiguration
device_groups = defaultdict(list)
files = os.listdir(DATA_FOLDER)
if not files:
    logger.warning(f"The folder {DATA_FOLDER} contains no files for processing.")
    exit()

logger.info(f"Found {len(files)} files for processing. Starting grouping...")

# Setting default flag for tested devices to false
is_tv_flag = False

for file_name in files:
    if file_name.endswith(".json"):
        file_path = DATA_FOLDER / file_name
        try:
            #Get device info
            device_config, is_tv_flag, sn = parse.get_device_info(file_path)

            # Add to group: path, TV flag, serial number
            device_groups[device_config].append((file_path, is_tv_flag, sn))

        except Exception as e:
            logger.error(f"Error parsing file {file_name}: {e}")

if not device_groups:
    logger.error("Failed to form device groups. Check the files.")
    exit()

# --- Step 2: Process Each Device Group ---

for current_device_name, file_list in device_groups.items():
    logger.info(f"--- Processing device configuration: {current_device_name} ({len(file_list)} files) ---")

    # 2.1 Dynamic path definition for the CURRENT device

    # Search for a specific requirements file config/device_configs/{name}.yaml
    current_expected_result = Path("config") / "device_configs" / f"{current_device_name}.yaml"
    if not current_expected_result.exists():
        logger.warning(
            f"Requirements configuration {current_expected_result} not found. Using general file: {EXPECTED_RESULT}")
        current_expected_result = EXPECTED_RESULT  # Fallback option

    # Dynamic report file names
    current_min_fail = Path("test_reports") / f"min_fail_{current_device_name}.json"
    current_report_from_all = Path("test_reports") / f"full_report_{current_device_name}.json"
    current_final_report = Path("test_reports") / f"final_report_{current_device_name}_{TIMESTAMP}.json"
    current_result_html = Path("results") / f"{current_device_name}.html"
    #current_result_html = Path("results") / f"{current_device_name}_{TIMESTAMP}.html"

    device_reports_list = []
    # 2.2 Process each file in the current group
    for file, is_tv_flag, sn in file_list:

        #Reading the current file with device measurements data
        try:
            current_device_report = parse.parse_one_file(file)
            if not current_device_report:
                logger.warning(f"File {file.name} is empty or corrupted. Skipping.")
                continue
        except Exception as e:
            logger.error(f"Cant read {file.name}: {e}. Skipping.")
            continue

        time = current_device_report.get("MeasurementDateTime", None)

        if test == "FullTest":
            logger.info(f"Processing FullTest for {file.name}")
            time = current_device_report.get("MeasurementDateTime", None) if current_device_report else None

            brightness_values = cal.brightness(current_device_report, is_tv_flag)
            brightness = brightness_values["typ"]
            brightness_uniformity = cal.brightness_uniformity(brightness_values)
            contrast = cal.contrast(current_device_report, is_tv_flag)
            cg_by_area = cal.cg_by_area(current_device_report, COLOR_SPACE)
            cg = cal.cg(current_device_report, COLOR_SPACE)
            temperature = cal.temperature(current_device_report)
            delta_e = cal.delta_e(current_device_report)
            coordinates = parse.get_coordinates(current_device_report, is_tv_flag)

            device_calculated_report = r.json_report(
                sn=sn,
                t=time,
                is_tv=is_tv_flag,
                brightness=brightness,
                brightness_uniformity=brightness_uniformity,
                cg_by_area_rgb=cg_by_area[0],
                cg_by_area_ntsc=cg_by_area[1],
                cg_rgb=cg[0],
                cg_ntsc=cg[1],
                contrast=contrast,
                temperature=temperature,
                delta_e=delta_e,
                coordinates=coordinates,
                device_name=current_device_name
            )

            device_reports_list.append(device_calculated_report)


        # elif test == "Contrast":
        #     logger.info(f"Processing Contrast test for {file.name}")
        #     contrast = cal.contrast(file, is_tv_flag)
        #     r.json_report(sn=sn, t=t, contrast=contrast, output_folder=DEVICE_REPORTS, device_name=current_device_name)
        #
        # elif test == "BrightnessUniformity":
        #     logger.info(f"Processing BrightnessUniformity test for {file.name}")
        #     brightness_values = cal.brightness(file, is_tv_flag)
        #     brightness = brightness_values["typ"]
        #     brightness_uniformity = cal.brightness_uniformity(brightness_values)
        #     coordinates = parse.get_coordinates(file, is_tv_flag)
        #     r.json_report(
        #         sn=sn,
        #         t=t,
        #         brightness=brightness,
        #         brightness_uniformity=brightness_uniformity,
        #         coordinates=coordinates,
        #         output_folder=DEVICE_REPORTS,
        #         device_name=current_device_name
        #     )
        #
        # elif test == "ColorGamut":
        #     logger.info(f"Processing ColorGamut test for {file.name}")
        #     cg_by_area = cal.cg_by_area(file, COLOR_SPACE)
        #     cg = cal.cg(file, COLOR_SPACE)
        #     coordinates = parse.get_coordinates(file, is_tv_flag)
        #     r.json_report(
        #         sn=sn,
        #         t=t,
        #         cg_by_area_rgb=cg_by_area[0],
        #         cg_by_area_ntsc=cg_by_area[1],
        #         cg_rgb=cg[0],
        #         cg_ntsc=cg[1],
        #         coordinates=coordinates,
        #         output_folder=DEVICE_REPORTS,
        #         device_name=current_device_name
        #     )

    # 2.3 --- Aggregation and Reporting for the CURRENT configuration ---
    logger.info(f"Creating final reports for {current_device_name}...")

    r.calculate_full_report(device_reports_list, current_report_from_all, current_device_name)
    r.analyze_json_files_for_min_fail(device_reports_list, current_expected_result, current_min_fail, current_device_name)
    r.generate_comparison_report(
        actual_result_file=current_report_from_all,
        expected_result_file=current_expected_result,
        output_json_file=current_final_report,
        is_tv_flag=is_tv_flag,
        device_reports=device_reports_list
    )

    # Call the new HTML report function
    h.create_html_report(
        input_file=current_final_report,
        output_file=current_result_html,
        device_reports = device_reports_list,
        min_fail_file=current_min_fail,
        cie_background_svg=CIE_BACKGROUND_SVG,
        rgb_coords=RGB,
        ntsc_coords=NTSC,
        test_type=test
    )

    # We no longer merge PDFs
    logger.success(f"HTML Report for {current_device_name} saved to {current_result_html}")

    # --- Step 3: Final Steps (Archiving and Cleanup) ---
    folder_to_archive = [TEST_REPORTS_FOLDER, DATA_FOLDER, RESULTS_FOLDER]
    h.archive_reports(
        current_device_name,
        TIMESTAMP,
        folder_to_archive
    )
    logger.info("--- Cleanup ---")
    #h.clear_folders(folder_to_archive)