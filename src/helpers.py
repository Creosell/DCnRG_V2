# helpers.py
import glob
import json
import os
import zipfile
import src.calculate as cal  # Keep this import
import src.graphics_hepler as gfx  # Import our new helper

from pathlib import Path
from loguru import logger
from jinja2 import Environment, FileSystemLoader, select_autoescape

HTML_TEMPLATE_NAME = "report_template.html"

def parse_one_file(file_path):
    """Loads and returns data from a single JSON file."""
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading/parsing file {file_path}: {e}")
        return None


def create_html_report(
        input_file: Path,
        output_file: Path,
        min_fail_file: Path,
        cie_background_svg: Path,
        rgb_coords: list,
        ntsc_coords: list,
        device_reports: list,
        test_type: str
):
    """
    Generates an interactive HTML report from a JSON test result file
    using a Jinja2 template.

    Args:
        input_file (Path): Path to the main JSON report data.
        output_file (Path): Path to save the final .html report.
        min_fail_file (Path): Path to the min_fail JSON file.
        cie_background_svg (Path): Path to the SVG background image.
        rgb_coords (list): List of sRGB coordinates [x, y, x, y, x, y].
        ntsc_coords (list): List of NTSC coordinates [x, y, x, y, x, y].
        test_type (str): The type of test (e.g., "FullTest", "Contrast").
        device_reports (list): List of device reports.

    """
    logger.info(f"Generating HTML report for {input_file.name}")

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

    # Extract device coordinates only if not a Contrast test
    if test_type != "Contrast":
        try:
            coordinate_names = ["Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y"]
            device_coords = [
                main_report_data.get(name, {}).get("actual_values", {}).get("avg")
                for name in coordinate_names
            ]
            if all(c is not None for c in device_coords):
                device_points = coord_mapper.get_triangle_pixel_points(device_coords)
            else:
                logger.warning("Could not get all device coordinates for plot.")
        except Exception as e:
            logger.error(f"Error processing device coordinates for plot: {e}")

    # Calculate points for standard triangles
    srgb_points = coord_mapper.get_triangle_pixel_points(rgb_coords)
    ntsc_points = coord_mapper.get_triangle_pixel_points(ntsc_coords)
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

    context = {
        "main_report": main_report_data,
        "min_fail_data_json": json.dumps(min_fail_data, indent=4),
        "raw_svg_background": raw_svg_background,
        "srgb_points": srgb_points,
        "ntsc_points": ntsc_points,
        "device_points": device_points,
        "debug_points": debug_points
    }

    # --- 5. Render and Save HTML ---
    try:
        html_content = template.render(context)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.success(f"Successfully created HTML report: {output_file}")
    except Exception as e:
        logger.error(f"Error rendering or saving HTML report: {e}")


# (Keep archive_reports and clear_folders functions as they are)

def archive_reports(device_name, timestamp, source_folders):
    """
    Archives all files from the source folders into a single zip file
    in the report_archive folder.
    """
    archive_folder = Path('report_archive')
    archive_folder.mkdir(exist_ok=True)  # Create the folder if it doesn't exist

    zip_filename = f"{device_name}_{timestamp}.zip"
    zip_path = archive_folder / zip_filename

    try:
        files_added = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for folder_name in source_folders:
                folder_path = Path(folder_name)
                if folder_path.exists():
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_path = Path(root) / file
                            # Ensure we don't archive the archive itself
                            if file_path.resolve() == zip_path.resolve():
                                continue

                            # Use relative paths for cleaner archive structure
                            # This will create paths like 'html_reports/report.html'
                            name_in_archive = file_path.relative_to(Path.cwd())

                            # A simple check to avoid including parent folders
                            if any(folder_path.name in part for part in file_path.parts):
                                zipf.write(file_path, name_in_archive)
                                files_added += 1
                                logger.debug(f"File added to archive: {file_path} as {name_in_archive}")
                else:
                    logger.warning(f"Folder {folder_name} not found, skipping for archive.")

            if files_added == 0:
                logger.warning("No files found to archive. Deleting empty archive.")
                if zip_path.exists():
                    zip_path.unlink()
                return None

        logger.success(f"Archive created: {zip_path}")
        logger.info(f"Total files archived: {files_added}")
        return str(zip_path)

    except Exception as e:
        logger.error(f"Error during archive creation: {e}")
        return None


def clear_folders(folders):
    """
    Deletes all files from the specified folders using pathlib.Path.
    """
    removed_count = 0

    for folder_path in map(Path, folders):
        if not folder_path.is_dir():
            logger.warning(f"Folder {folder_path} not found or is not a directory, skipping cleanup.")
            continue

        for file_path in folder_path.glob('**/*'):
            # This check is important to not delete the .gitkeep file
            if file_path.is_file() and file_path.name != '.gitkeep':
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")

    logger.info(f"Total files removed during cleanup: {removed_count}")