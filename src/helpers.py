# helpers.py
import json
import sys
import yaml
import zipfile
from pathlib import Path
import datetime
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

import src.graphics_helper as gfx  # Import our new helper
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

COORD_KEYS_INTERNAL = {
    "Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y",
    "White_x", "White_y", "Center_x", "Center_y"
}

# Reverse mapping: JSON keys → YAML keys
JSON_TO_YAML_KEY_MAP = {
    "BrightnessUniformity": "Brightness_uniformity",
    "CgByAreaRGB": "Cg_rgb_area",
    "CgByAreaNTSC": "Cg_ntsc_area",
    "CgRGB": "Cg_rgb",
    "CgNTSC": "Cg_ntsc",
    "DeltaE": "Delta_e",
    "Center_x": "White_x",
    "Center_y": "White_y",
}

# Metrics with dynamic visibility based on expected values presence
DYNAMIC_VISIBILITY_KEYS = {"CgByAreaRGB", "CgByAreaNTSC", "CgRGB", "CgNTSC"}

# Metrics where lower values are better (inverted logic)
LOWER_IS_BETTER_KEYS = {"DeltaE"}


def _get_cell_status(key: str, value: float, expected_values: dict, is_coordinate: bool = False):
    """
    Determines cell status based on expected value comparison.

    Args:
        key: Internal JSON key (e.g., "Brightness", "Red_x")
        value: Actual measured value
        expected_values: Expected values from YAML config
        is_coordinate: If True, checks only min/max (for coordinates)

    Returns:
        str or None: "fail" (red), "warning" (yellow), or None (white)
    """
    if value is None:
        return None

    # Map internal key to YAML key
    yaml_key = JSON_TO_YAML_KEY_MAP.get(key, key)
    expected = expected_values.get(yaml_key, {})

    min_val = expected.get("min")
    max_val = expected.get("max")
    typ_val = expected.get("typ")

    # Parse string 'None' as None
    def parse_val(v):
        return None if v == 'None' or v is None else v

    min_val = parse_val(min_val)
    max_val = parse_val(max_val)
    typ_val = parse_val(typ_val)

    # Inverted logic for metrics where lower is better (e.g., DeltaE)
    is_inverted = key in LOWER_IS_BETTER_KEYS

    if is_inverted:
        # For DeltaE: higher value = worse, only check max and typ as upper bounds
        if max_val is not None and value > max_val:
            return "fail"

        # For coordinates, only check min/max
        if is_coordinate:
            return None

        # Check typ as upper bound (warning if exceeds typical)
        if typ_val is not None and value > typ_val:
            return "warning"
    else:
        # Standard logic: higher is better
        if min_val is not None and value < min_val:
            return "fail"
        if max_val is not None and value > max_val:
            return "fail"

        # For coordinates, only check min/max
        if is_coordinate:
            return None

        # For non-coordinates, check typ (warning - yellow)
        if typ_val is not None and value < typ_val:
            return "warning"

    return None


def _should_display_metric(key: str, expected_values: dict) -> bool:
    """
    Determines if a metric should be displayed based on expected values.

    Args:
        key: Internal JSON key (e.g., "CgByAreaRGB")
        expected_values: Expected values from YAML config

    Returns:
        bool: True if metric should be displayed, False otherwise.

    Logic:
        - Metrics NOT in DYNAMIC_VISIBILITY_KEYS: always display
        - Metrics in DYNAMIC_VISIBILITY_KEYS: display only if at least one
          expected value (min/typ/max) is not None and not string 'None'
    """
    if key not in DYNAMIC_VISIBILITY_KEYS:
        return True

    yaml_key = JSON_TO_YAML_KEY_MAP.get(key)
    if not yaml_key:
        return True

    expected = expected_values.get(yaml_key, {})

    def _is_valid_value(v):
        """Checks if value is not None and not string 'None'"""
        return v is not None and v != 'None'

    return any(_is_valid_value(expected.get(k)) for k in ["min", "typ", "max"])


def collect_tolerance_legend(main_report_data: dict, ufn_mapping: dict) -> dict:
    """
    Collects tolerance information from the report and groups metrics by tolerance percent.

    Args:
        main_report_data: Comparison report data with tolerance_applied fields
        ufn_mapping: Mapping from internal keys to user-friendly names

    Returns:
        dict: {percent: [list of metric names]} e.g., {5: ["Brightness", "Contrast"], 2: ["sRGB Gamut"]}
    """
    tolerance_groups = defaultdict(list)

    for key, data in main_report_data.items():
        tolerance_info = data.get("tolerance_applied")
        if tolerance_info and isinstance(tolerance_info, dict):
            percent = tolerance_info.get("percent")
            if percent is not None:
                metric_name = ufn_mapping.get(key, key)
                tolerance_groups[percent].append(metric_name)

    # Sort by percent descending for consistent display
    return dict(sorted(tolerance_groups.items(), key=lambda x: x[0], reverse=True))


def create_html_report(
        input_file: Path,
        output_file: Path,
        min_fail_file: Path,
        cie_background_svg: Path,
        report_view_config: Path,
        device_reports: list,
        current_device_name: str,
        app_version: str,
        expected_yaml: Path,
) -> bool:
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
        app_version (str): Version of the app.
        report_view_config (Path): Path to the report view config.
        expected_yaml (Path): Path to the expected YAML file.

    Returns:
        bool: True if report was successfully generated, False otherwise.
    """
    logger.debug(f"Generating HTML report for {input_file.name}")

    # --- 1. Load Data ---
    try:
        with open(input_file, "r") as f:
            main_report_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading/parsing main report file {input_file}: {e}")
        return False

    try:
        with open(min_fail_file, "r") as f:
            min_fail_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Error reading min_fail file {min_fail_file}: {e}")
        min_fail_data = []

    try:
        with open(expected_yaml, "r") as yaml_file:
            expected_data = yaml.safe_load(yaml_file)
            expected_values = expected_data["main_tests"]
    except FileNotFoundError:
        logger.error(f"Expected result file not found at {expected_yaml}")
        return False
    except yaml.YAMLError as e:
        logger.error(f"Could not parse YAML file: {e}")
        return False
    except KeyError:
        logger.error("'main_tests' key not found in the YAML file.")
        return False

    # Collect tolerance legend before filtering
    tolerance_legend = collect_tolerance_legend(main_report_data, UFN_MAPPING)

    main_report_data_filtered, main_report_coordinates_filtered = process_main_report(
        main_report_data, UFN_MAPPING, report_view_config, expected_values
    )

    main_report_filtered = {
        "data": main_report_data_filtered,
        "coordinates": main_report_coordinates_filtered
    }

    # --- 1.2. Process Min Fail Data (Grouping) ---
    min_fail_grouped = defaultdict(list)

    if min_fail_data:
        for item in min_fail_data:
            for sn, info in item.items():
                raw_key = info.get("key")
                # Convert to User Friendly Name
                ufn_name = UFN_MAPPING.get(raw_key, raw_key)

                min_fail_grouped[ufn_name].append({
                    "sn": sn,
                    "min_value": info.get("min_value"),
                    "expected_min": info.get("expected_min")
                })

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
    specification_points = ""

    device_coordinates = prepare_device_plot_coordinates(main_report_data)
    specification_coordinates = prepare_specification_plot_coordinates(expected_values)

    # If coordinates exists build plot points for them
    if device_coordinates is not None:
        device_points = coord_mapper.get_triangle_pixel_points(device_coordinates)
    if specification_coordinates is not None:
        specification_points = coord_mapper.get_triangle_pixel_points(specification_coordinates)

    # Calculate points for standard triangles
    srgb_points = coord_mapper.get_triangle_pixel_points(calc.COLOR_STANDARDS.get(calc.ColorSpace.SRGB))
    ntsc_points = coord_mapper.get_triangle_pixel_points(calc.COLOR_STANDARDS.get(calc.ColorSpace.NTSC))
    debug_points = json.loads(coord_mapper.get_debug_grid_points())

    summary_plot_points = {
        "device": device_points,
        "srgb": srgb_points,
        "ntsc": ntsc_points,
        "specification": specification_points,
        "debug": debug_points,
    }

    # --- 3. Set up Jinja2 Environment ---
    # Determine base directory: if frozen (compiled), use executable's parent folder
    # Otherwise use project root (for development)
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = Path(sys.executable).parent
    else:
        # Running as script
        base_dir = Path(__file__).parent.parent

    template_dir = base_dir / "config"

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )

    try:
        template = env.get_template(HTML_TEMPLATE_NAME)
    except Exception as e:
        logger.error(f"Error loading template '{HTML_TEMPLATE_NAME}' from '{template_dir}': {e}")
        return False

    # --- 4. Define Template Context ---

    # 1. Collect and process device reports for the new table
    device_reports_data_filtered, device_reports_coordinates_filtered = process_device_reports(
        device_reports, UFN_MAPPING, expected_values
    )

    device_reports_filtered = {
        "data": device_reports_data_filtered,
        "coordinates": device_reports_coordinates_filtered
    }

    # 2. Calculate inspection date
    inspection_date = get_inspection_date_range(device_reports_data_filtered)

    context = {
        "main_report": main_report_filtered,
        "min_fail_grouped": min_fail_grouped,
        "min_fail_data_json": json.dumps(min_fail_data, indent=4),
        "raw_svg_background": raw_svg_background,
        "summary_plot_points": summary_plot_points,
        'device_reports': device_reports_filtered,
        'current_device_name': current_device_name,
        'inspection_date': inspection_date,
        'app_version': app_version,
        'tolerance_legend': tolerance_legend
    }

    # --- 5. Render and Save HTML ---
    try:
        html_content = template.render(context)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.debug(f"Successfully created HTML report: {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error rendering or saving HTML report: {e}")
        return False


def prepare_device_plot_coordinates(main_report_data):
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

        all_coordinates = [r_x, r_y, g_x, g_y, b_x, b_y]

        # Check if all 6 coordinates were successfully found
        if all(c is not None for c in all_coordinates):
            # Assemble them in the NEW format: [[x,y], [x,y], [x,y]]
            device_coordinates_list = [
                [r_x, r_y],
                [g_x, g_y],
                [b_x, b_y]
            ]
            return device_coordinates_list
        else:
            logger.warning("Could not get all device coordinates for plot (some values were missing).")
    except Exception as e:
        logger.error(f"Error processing device coordinates for plot: {e}")


def prepare_specification_plot_coordinates(expected_values):
    try:
        # Helper function to get avg value
        def get_coord(name):
            return expected_values.get(name, {}).get("typ", {})

        # Get individual coordinates
        r_x = get_coord("Red_x")
        r_y = get_coord("Red_y")
        g_x = get_coord("Green_x")
        g_y = get_coord("Green_y")
        b_x = get_coord("Blue_x")
        b_y = get_coord("Blue_y")

        all_coordinates = [r_x, r_y, g_x, g_y, b_x, b_y]

        # Check if all 6 coordinates were successfully found
        if all(c is not None for c in all_coordinates):

            # Assemble them in the NEW format: [[x,y], [x,y], [x,y]]
            specification_coordinates = [
                [r_x, r_y],
                [g_x, g_y],
                [b_x, b_y]
            ]

            # Pass the new list structure to the updated function
            return specification_coordinates
        else:
            logger.warning("Could not get all specification coordinates for plot (some values were missing).")
    except Exception as e:
        logger.error(f"Error processing specification coordinates for plot: {e}")


def process_main_report(main_report_data: dict, ufn_mapping: dict, config_path: Path, expected_values: dict):
    """
    Processes the main aggregated report data.
    - Filters keys based on config (YAML).
    - Filters metrics with dynamic visibility based on expected values presence.
    - Sorts keys based on config order.
    - Maps internal keys to UFN names.
    - Splits into Main and Coordinate rows.

    Args:
        main_report_data: Aggregated report data
        ufn_mapping: Mapping from internal keys to user-friendly names
        config_path: Path to report_view.yaml
        expected_values: Expected values from device configuration YAML

    Returns:
        tuple: (main_summary_rows, coord_summary_rows)
        Returns DICTIONARIES where keys are UFN names and values are data objects.
    """
    summary_keys = []

    # 1. Determine keys from config
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                view_conf = yaml.safe_load(f)
                columns_config = view_conf.get("columns", {})

            if isinstance(columns_config, dict):
                # Filter enabled keys, preserving YAML order
                summary_keys = [k for k, enabled in columns_config.items() if enabled]
            elif isinstance(columns_config, list):
                summary_keys = columns_config

            # Validate keys exist
            summary_keys = [k for k in summary_keys if k in main_report_data]

        except Exception as e:
            logger.warning(f"Config error: {e}. Showing all columns.")
            summary_keys = list(main_report_data.keys())
    else:
        summary_keys = list(main_report_data.keys())

    # 1.5. Filter metrics by expected values presence (dynamic visibility)
    summary_keys = [k for k in summary_keys if _should_display_metric(k, expected_values)]

    # 2. Build ROWS as DICTIONARIES (not lists)
    # Используем словари {}, чтобы в шаблоне работал метод .items()
    main_rows = {}
    coord_rows = {}

    for key in summary_keys:
        ufn_name = ufn_mapping.get(key, key)
        data_payload = main_report_data.get(key)

        # Check if it belongs to coordinates table using the UFN set
        if key in COORD_KEYS_INTERNAL:
            coord_rows[ufn_name] = data_payload
        else:
            main_rows[ufn_name] = data_payload

    return main_rows, coord_rows


def process_device_reports(device_reports: list, ufn_mapping: dict, expected_values: dict):
    """
    Loads raw device reports, flattens coordinates, applies UFN mapping,
    separates main data from coordinates, and marks cells that are below expected values.

    Args:
        device_reports: List of device report dictionaries
        ufn_mapping: Mapping from internal keys to user-friendly names
        expected_values: Expected values from device configuration YAML

    Returns:
        tuple: (main_reports, coord_reports) with cell status flags
    """
    main_reports = {}
    coord_reports = {}

    for data in device_reports:
        # Basic validation
        if not (data and "SerialNumber" in data and "Results" in data):
            continue

        sn = data["SerialNumber"]
        # Common metadata for both tables
        meta = {
            "measurement_date": data.get("MeasurementDateTime", "N/A").replace('_', ''),
            "is_tv": data.get("IsTV", False)
        }

        processed_main = {}
        processed_coords = {}
        cell_status_main = {}  # "fail", "warning", or None
        cell_status_coords = {}

        # Process Results
        for key, value in data["Results"].items():
            if key == "Measurements":
                continue

            # Helper logic for formatting
            def format_val(k, v, default_prec):
                ufn_key = ufn_mapping.get(k, k)
                prec = r.REPORT_PRECISION.get(k, default_prec)
                try:
                    return ufn_key, f"{v:.{prec}f}"
                except (TypeError, ValueError):
                    return ufn_key, str(v)

            if key == "Coordinates":
                for c_key, c_val in value.items():
                    name, val = format_val(c_key, c_val, 3)
                    processed_coords[name] = val
                    # Check coordinate bounds (min/max only)
                    status = _get_cell_status(c_key, c_val, expected_values, is_coordinate=True)
                    if status:
                        cell_status_coords[name] = status
            else:
                name, val = format_val(key, value, 0)
                processed_main[name] = val
                # Check main metric bounds (min/typ/max)
                status = _get_cell_status(key, value, expected_values, is_coordinate=False)
                if status:
                    cell_status_main[name] = status

        # Save results once per device
        main_reports[sn] = {"results": processed_main, "cell_status": cell_status_main, **meta}
        coord_reports[sn] = {"results": processed_coords, "cell_status": cell_status_coords, **meta}

    return main_reports, coord_reports


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
