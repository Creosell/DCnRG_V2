# helpers.py
import json
import os
import zipfile
from pathlib import Path
import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

import src.graphics_hepler as gfx  # Import our new helper
import src.report as r
import src.calculate as calc

HTML_TEMPLATE_NAME = "report_template.html"

# User-Friendly Name mapping for keys in the JSON results
UFN_MAPPING = {
    "Brightness": "Brightness (cd/m²)",
    "Contrast": "Contrast Ratio",
    "Temperature": "Color Temperature (K)",

    "BrightnessUniformity": "Brightness Uniformity (%)",
    "CgByAreaRGB": "sRGB Gamut Area (%)",
    "CgByAreaNTSC": "NTSC Gamut Area (%)",
    "CgRGB": "sRGB Gamut Coverage (%)",
    "CgNTSC": "NTSC Gamut Coverage (%)",
    "DeltaE": "ΔE",

    # Coordinates (flattened)
    "Red_x": "Red (x)",
    "Red_y": "Red (y)",
    "Green_x": "Green (x)",
    "Green_y": "Green (y)",
    "Blue_x": "Blue (x)",
    "Blue_y": "Blue (y)",
    "White_x": "White (x)",
    "White_y": "White (y)",
    "Center_x": "Center (x)",
    "Center_y": "Center (y)",
}

COORD_HEADERS_UFN = {
    "Red (x)", "Red (y)", "Green (x)", "Green (y)", "Blue (x)", "Blue (y)",
    "White (x)", "White (y)", "Center (x)", "Center (y)"
}

def create_html_report(
        input_file: Path,
        output_file: Path,
        min_fail_file: Path,
        cie_background_svg: Path,
        device_reports: list,
        current_device_name: str
):
    """
    Generates an interactive HTML report from a JSON test result file
    using a Jinja2 template.

    Args:
        input_file (Path): Path to the main JSON report data.
        output_file (Path): Path to save the final .html report.
        min_fail_file (Path): Path to the min_fail JSON file.
        cie_background_svg (Path): Path to the SVG background image.
        device_reports (list): List of device reports.
        current_device_name (str): Name of the current device.

    """
    logger.debug(f"Generating HTML report for {input_file.name}")

    # --- 1. Load Data ---
    try:
        with open(input_file, "r") as f:
            main_report_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading/parsing main report file {input_file}: {e}")
        return

    try:
        with open(min_fail_file, "r") as f:
            min_fail_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Error reading min_fail file {min_fail_file}: {e}")
        min_fail_data = {"error": f"Could not load {min_fail_file}"}

    # --- 1.5. SVG LOAD ---
    raw_svg_background = ""
    try:
        with open(cie_background_svg, "r", encoding="utf-8") as f:
            raw_svg_background = f.read()
        logger.debug(f"Successfully read SVG background: {cie_background_svg}")
    except Exception as e:
        logger.error(f"Error reading SVG background file {cie_background_svg}: {e}")

    # --- 2. Prepare Plot Coordinates ---
    coord_mapper = gfx.SvgCoordinator()
    device_points = ""

    try:
        # Helper function to get avg value
        def get_avg_coord(name):
            return main_report_data.get(name, {}).get("actual_values", {}).get("avg")

        # Get individual coordinates
        r_x = get_avg_coord("Red_x")
        r_y = get_avg_coord("Red_y")
        g_x = get_avg_coord("Green_x")
        g_y = get_avg_coord("Green_y")
        b_x = get_avg_coord("Blue_x")
        b_y = get_avg_coord("Blue_y")

        all_coords = [r_x, r_y, g_x, g_y, b_x, b_y]

        # Check if all 6 coordinates were successfully found
        if all(c is not None for c in all_coords):

            # Assemble them in the NEW format: [[x,y], [x,y], [x,y]]
            device_coords_list = [
                [r_x, r_y],
                [g_x, g_y],
                [b_x, b_y]
            ]

            # Pass the new list structure to the updated function
            device_points = coord_mapper.get_triangle_pixel_points(device_coords_list)
        else:
            logger.warning("Could not get all device coordinates for plot (some values were missing).")
    except Exception as e:
        logger.error(f"Error processing device coordinates for plot: {e}")

    # Calculate points for standard triangles
    srgb_points = coord_mapper.get_triangle_pixel_points(calc.COLOR_STANDARDS.get(calc.ColorSpace.SRGB))
    ntsc_points = coord_mapper.get_triangle_pixel_points(calc.COLOR_STANDARDS.get(calc.ColorSpace.NTSC))
    debug_points = json.loads(coord_mapper.get_debug_grid_points())

    # --- 3. Set up Jinja2 Environment ---
    # Assuming template is in 'config/' folder, relative to project root
    template_dir = Path("config")
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )

    try:
        template = env.get_template(HTML_TEMPLATE_NAME)
    except Exception as e:
        logger.error(f"Error loading template '{HTML_TEMPLATE_NAME}' from '{template_dir}': {e}")
        return

        # --- 4. Define Template Context ---

    # 1. Collect and process raw device reports for the new table
    all_device_reports_data = process_device_reports(device_reports, UFN_MAPPING)

    # 2. Get the list of all unique UFN keys for the table header, preserving UFN order
    unique_ufn_keys = set()
    for report in all_device_reports_data.values():
        unique_ufn_keys.update(report["results"].keys())

    # 3. NEW: Calculate inspection date
    inspection_date = get_inspection_date_range(all_device_reports_data)

    # Sort keys based on the order defined in UFN_MAPPING values
    ufn_order = {name: i for i, name in enumerate(UFN_MAPPING.values())}
    sorted_ufn_keys = sorted(list(unique_ufn_keys),
                             key=lambda x: ufn_order.get(x, float('inf')))

    context = {
        "main_report": main_report_data,
        "min_fail_data_json": json.dumps(min_fail_data, indent=4),
        "raw_svg_background": raw_svg_background,
        "srgb_points": srgb_points,
        "ntsc_points": ntsc_points,
        "device_points": device_points,
        "debug_points": debug_points,
        'individual_reports': all_device_reports_data,
        'report_headers': sorted_ufn_keys,
        'current_device_name': current_device_name,
        'inspection_date': inspection_date
    }

    # --- 5. Render and Save HTML ---
    try:
        html_content = template.render(context)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.debug(f"Successfully created HTML report: {output_file}")
    except Exception as e:
        logger.error(f"Error rendering or saving HTML report: {e}")

def process_device_reports(device_reports: list, ufn_mapping: dict) -> dict:
    """
    Loads raw device reports, flattens coordinates, applies UFN mapping,
    and formats values using precision from report.REPORT_PRECISION.

    Returns:
        dict: Processed reports keyed by SerialNumber.
    """
    all_reports_data = {}

    for data in device_reports:
        if data and "SerialNumber" in data and "Results" in data:
            serial_number = data["SerialNumber"]
            raw_results = data["Results"]
            processed_results = {}

            # Flatten results and apply UFN/Formatting
            for key, value in raw_results.items():
                if key == "Coordinates":
                    # Flatten coordinates from dictionary
                    for coord_key, coord_value in value.items():
                        ufn_key = ufn_mapping.get(coord_key, coord_key)
                        # Get precision from report.py, default to 3 for coordinates
                        precision = r.REPORT_PRECISION.get(coord_key, 3)

                        try:
                            # Format value using the specified precision
                            formatted_value = f"{coord_value:.{precision}f}"
                        except (TypeError, ValueError):
                            formatted_value = str(coord_value)

                        processed_results[ufn_key] = formatted_value

                # Skip the verbose Measurements array
                elif key != "Measurements":
                    ufn_key = ufn_mapping.get(key, key)
                    # Get precision from report.py, default to 0 for top-level keys
                    precision = r.REPORT_PRECISION.get(key, 0)

                    try:
                        # Format value using the specified precision
                        formatted_value = f"{value:.{precision}f}"
                    except (TypeError, ValueError):
                        formatted_value = str(value)

                    processed_results[ufn_key] = formatted_value

            # Store metadata and processed results
            all_reports_data[serial_number] = {
                "results": processed_results,
                # Use MeasurementDateTime for display
                "measurement_date": data.get("MeasurementDateTime", "N/A").replace('_', ''),
                "is_tv": data.get("IsTV", False)
            }

    return all_reports_data


def archive_specific_files(zip_path, files_to_archive, base_folder):
    """
    Archives a specific list of files into a zip file, preserving
    their relative path structure from the base_folder.
    """
    logger.debug(f"Archiving {len(files_to_archive)} specific files to {zip_path}...")

    try:
        files_added = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_archive:
                if not file_path.exists() or not file_path.is_file():
                    logger.warning(f"File {file_path} not found, skipping for archive.")
                    continue

                # Ensure we don't archive the archive itself
                if file_path.resolve() == zip_path.resolve():
                    continue

                try:
                    # Calculate path inside the zip
                    # e.g., 'data/report.json' or 'results/device.html'
                    name_in_archive = file_path.resolve().relative_to(base_folder.resolve())

                    zipf.write(file_path, name_in_archive)
                    files_added += 1
                except ValueError as e:
                    # Fallback if relative_to fails (e.g., different drives)
                    logger.error(f"Cannot calculate relative path for {file_path}: {e}. Using flat name.")
                    zipf.write(file_path, file_path.name)

        if files_added == 0:
            logger.warning("No valid files were added to the archive.")
            if zip_path.exists():
                zip_path.unlink()
            return None

        logger.success(f"Archive created with {files_added} files: {zip_path}")
        return str(zip_path)

    except Exception as e:
        logger.error(f"Error during archive creation: {e}")
        return None


def clear_specific_files(files_to_delete):
    """
    Deletes a specific list of files.
    """
    removed_count = 0
    logger.debug(f"Cleaning up {len(files_to_delete)} specific files...")

    for file_path in files_to_delete:
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                removed_count += 1
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        else:
            logger.warning(f"File {file_path} not found, skipping cleanup.")

    logger.debug(f"Total files removed during cleanup: {removed_count}")

# helpers.py

def get_day_suffix(day):
    """Returns the English ordinal suffix (st, nd, rd, th) for a day."""
    if 11 <= day <= 13:
        return 'th'
    if day % 10 == 1:
        return 'st'
    if day % 10 == 2:
        return 'nd'
    if day % 10 == 3:
        return 'rd'
    return 'th'

def get_inspection_date_range(all_device_reports_data: dict) -> str:
    """
    Parses all 'measurement_date' fields and returns a formatted date string.
    """
    if not all_device_reports_data:
        return "N/A"

    dates = set()
    # Format based on 'measurement_date' in process_device_reports
    date_format = "%Y%m%d%H%M%S"

    for report in all_device_reports_data.values():
        date_str = report.get("measurement_date")
        if date_str and date_str != "N/A":
            try:
                # We only care about the date part
                dt = datetime.datetime.strptime(date_str, date_format).date()
                dates.add(dt)
            except ValueError:
                logger.warning(f"Invalid date format skipped: {date_str}")
                continue

    if not dates:
        return "N/A"

    min_date = min(dates)
    max_date = max(dates)

    # Helper for formatting: e.g., "1st November 2025"
    def format_date(dt):
        day = dt.day
        suffix = get_day_suffix(day)
        # %B gives full month name (e.g., November)
        return dt.strftime(f"{day}{suffix} %B %Y")

    if min_date == max_date:
        # Condition 1: Single date
        return format_date(min_date)
    else:
        # Condition 2: Date range
        min_day = min_date.day
        max_day = max_date.day
        min_suffix = get_day_suffix(min_day)
        max_suffix = get_day_suffix(max_day)

        # Check if they are in the same month/year
        if min_date.month == max_date.month and min_date.year == max_date.year:
            # e.g., "1st - 3rd November 2025"
            return f"{min_day}{min_suffix} - {max_day}{max_suffix} {min_date.strftime('%B %Y')}"
        else:
            # e.g., "30th November - 2nd December 2025"
            return f"{format_date(min_date)} - {format_date(max_date)}"