import datetime
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
DEVICE_REPORTS = Path("device_reports")
PDF_REPORTS_FOLDER = Path("pdf_reports")
TEST_REPORTS_FOLDER = Path("test_reports")
ARCHIVE_REPORTS = Path("report_archive")
PICTURES_FOLDER = Path("pics")
LOGS_FOLDER = Path("logs")
RESULTS_FOLDER = Path("results")

MAIN_CONFIG = Path("config") / "main.yaml"
COLOR_SPACE_CONFIG = Path("config") / "color_space.yaml"
COLOR_SPACE_PICTURE = Path("config") / "space.png"
EXPECTED_RESULT = Path("config") / "expected_result.yaml"

# Logger configuration
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(LOGS_FOLDER / f"{TIMESTAMP}.log", level="DEBUG", encoding="utf-8")

# Parsing general settings
RGB = parse.coordinate_srgb(COLOR_SPACE_CONFIG)
NTSC = parse.coordinate_ntsc(COLOR_SPACE_CONFIG)
COLOR_SPACE = parse.parse_yaml(MAIN_CONFIG, "Task", "color_space", "type")
test = parse.parse_yaml(MAIN_CONFIG, "Task", "test", "type")

# Create working folders if they do not exist
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
DEVICE_REPORTS.mkdir(parents=True, exist_ok=True)
PDF_REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
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

for file_name in files:
    if file_name.endswith(".json"):
        file_path = DATA_FOLDER / file_name
        try:
            data = h.parse_one_file(file_path)

            # Get key parameters
            device_config = data.get("DeviceConfiguration", "UnknownDevice")
            is_tv = data.get("IsTV", False)
            sn = data.get("SerialNumber", "UnknownSN")

            # Add to group: path, TV flag, serial number
            device_groups[device_config].append((file_path, is_tv, sn))

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
    current_plot_picture = Path("pics") / f"plot_{current_device_name}.png"
    current_pdf_report = Path("pdf_reports") / f"report_{current_device_name}.pdf"
    current_pdf_report_all = Path("pdf_reports") / f"all_reports_{current_device_name}.pdf"
    current_result = Path("results") / f"{current_device_name}_{TIMESTAMP}.pdf"

    # 2.2 Process each file in the current group
    for file, is_tv_flag, sn in file_list:
        t = cal.measurement_time(file)

        if test == "FullTest":
            logger.info(f"Processing FullTest for {file.name}")

            # --- UPDATED BRIGHTNESS/UNIFORMITY CALCULATION ---
            brightness_values = cal.brightness(file, is_tv_flag)  # Pass the is_tv_flag
            brightness = brightness_values["typ"]  # Typical (WhiteColor/Center)
            brightness_uniformity = cal.brightness_uniformity(brightness_values)  # Uses Center

            # --- UPDATED CONTRAST CALCULATION ---
            contrast = cal.contrast(file, is_tv_flag)  # Pass the is_tv_flag

            cg_by_area = cal.cg_by_area(file, COLOR_SPACE)
            cg = cal.cg(file, COLOR_SPACE, RGB, NTSC)
            temperature = cal.temperature(file)
            delta_e = cal.delta_e(file)
            coordinates = parse.get_coordinates(file,is_tv_flag)

            r.json_report(
                sn=sn,
                t=t,
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
                output_folder=DEVICE_REPORTS,
                device_name=current_device_name
            )

        elif test == "Contrast":
            logger.info(f"Processing Contrast test for {file.name}")
            contrast = cal.contrast(file, is_tv_flag)
            r.json_report(sn=sn, t=t, contrast=contrast, output_folder=DEVICE_REPORTS, device_name=current_device_name)

        elif test == "BrightnessUniformity":
            logger.info(f"Processing BrightnessUniformity test for {file.name}")
            brightness_values = cal.brightness(file, is_tv_flag)
            brightness = brightness_values["typ"]
            brightness_uniformity = cal.brightness_uniformity(brightness_values)
            coordinates = parse.get_coordinates(file)
            r.json_report(
                sn=sn,
                t=t,
                brightness=brightness,
                brightness_uniformity=brightness_uniformity,
                coordinates=coordinates,
                output_folder=DEVICE_REPORTS,
                device_name=current_device_name
            )

        elif test == "ColorGamut":
            logger.info(f"Processing ColorGamut test for {file.name}")
            cg_by_area = cal.cg_by_area(file, COLOR_SPACE)
            cg = cal.cg(file, COLOR_SPACE, RGB, NTSC)
            coordinates = parse.get_coordinates(file)
            r.json_report(
                sn=sn,
                t=t,
                cg_by_area_rgb=cg_by_area[0],
                cg_by_area_ntsc=cg_by_area[1],
                cg_rgb=cg[0],
                cg_ntsc=cg[1],
                coordinates=coordinates,
                output_folder=DEVICE_REPORTS,
                device_name=current_device_name
            )

    # 2.3 --- Aggregation and Reporting for the CURRENT configuration ---
    logger.info(f"Creating final reports for {current_device_name}...")

    # ATTENTION: For calculate_full_report and analyze_json_files_for_min_fail to work correctly,
    # these functions must be able to filter files by current_device_name internally.
    r.calculate_full_report(DEVICE_REPORTS, current_report_from_all, current_device_name)
    r.analyze_json_files_for_min_fail(DEVICE_REPORTS, current_expected_result, current_min_fail, current_device_name)
    r.generate_comparison_report(current_report_from_all, current_expected_result, current_final_report)

    # PDF Report Generation
    h.device_reports_to_pdf(str(DEVICE_REPORTS), str(current_pdf_report_all), current_device_name)  # Add filter

    h.create_pdf(
        str(current_final_report),
        str(current_pdf_report),
        RGB,
        NTSC,
        current_plot_picture,
        COLOR_SPACE_PICTURE,
        current_min_fail,
        test,
    )

    h.merge_pdfs((current_pdf_report, current_pdf_report_all), current_result)

    logger.success(f"Reports for {current_device_name} saved to {current_result}")

# --- Step 3: Final Steps (Archiving and Cleanup) ---
logger.info("--- Finalization and cleanup ---")

FOLDERS_TO_PROCESS = [DEVICE_REPORTS, PDF_REPORTS_FOLDER, TEST_REPORTS_FOLDER, DATA_FOLDER, PICTURES_FOLDER]
ARCHIVE_SUMMARY_NAME = "Full_Report_Summary"

h.archive_reports(
    ARCHIVE_SUMMARY_NAME,
    TIMESTAMP,
    FOLDERS_TO_PROCESS
)

h.clear_folders(FOLDERS_TO_PROCESS)