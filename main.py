import argparse
import datetime
import sys
from collections import defaultdict
from pathlib import Path
from enum import IntEnum

from loguru import logger

import src.calculate as cal
import src.helpers as h
import src.parse as parse
import src.report as r

# --- Constants & Configuration ---
APP_VERSION = "1.1.3"


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    NO_DATA_FOUND = 2
    CONFIG_ERROR = 3


# Paths
DATA_DIR = Path("data")
REPORT_DIR = Path("test_reports")
ARCHIVE_DIR = Path("report_archive")
LOG_DIR = Path("logs")
RESULT_DIR = Path("results")
CONFIG_DIR = Path("config")

CIE_BG_SVG = CONFIG_DIR / "CIExy1931.svg"
DEFAULT_EXPECTED_YAML = CONFIG_DIR / "configuration_example.yaml"
REPORT_VIEW_CONFIG = CONFIG_DIR / "report_view.yaml"


def parse_args():
    """
    Parses command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Display Device Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging (default: INFO level)'
    )

    parser.add_argument(
        '--noclean', '-nc',
        action='store_true',
        help='Skip archiving and cleanup operations'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {APP_VERSION}'
    )

    parser.add_argument(
        '--device',
        metavar='NAME',
        help='Process only the specified device configuration'
    )

    parser.add_argument(
        '--no-timestamp',
        action='store_true',
        help='Generate files without timestamp for quick regeneration'
    )

    return parser.parse_args()


def setup_logging(verbose: bool = False):
    """
    Configures logger settings.

    Args:
        verbose: If True, sets console logging to DEBUG level
    """
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
    )
    logger.add(
        LOG_DIR / "report_generator.log",
        level="DEBUG",
        encoding="utf-8",
        rotation="1 MB",
        retention=2,
        compression="zip"
    )


def ensure_directories() -> bool:
    """Creates the necessary directories. Returns False on failure."""
    try:
        for d in [DATA_DIR, REPORT_DIR, ARCHIVE_DIR, LOG_DIR, RESULT_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.critical(f"Failed to create directories: {e}")
        return False


def main() -> int:
    """Main execution flow."""
    args = parse_args()

    if not ensure_directories():
        return ExitCode.CONFIG_ERROR

    setup_logging(verbose=args.verbose)
    timestamp = "" if args.no_timestamp else datetime.datetime.now().strftime("%Y%m%d_%H%M")
    logger.info(f"Report Generator v{APP_VERSION} started.")

    if args.verbose:
        logger.debug("Debug logging enabled")
    if args.noclean:
        logger.info("Archiving and cleanup disabled (--noclean)")
    if args.no_timestamp:
        logger.info("Timestamp disabled for output files (--no-timestamp)")
    if args.device:
        logger.info(f"Filtering for device: {args.device}")

    # 1. Find and group files
    json_files = list(DATA_DIR.glob("*.json"))
    if not json_files:
        logger.warning(f"No .json files found in {DATA_DIR}.")
        return ExitCode.NO_DATA_FOUND

    device_groups = defaultdict(list)

    for file_path in json_files:
        try:
            dev_config, is_tv, sn = parse.get_device_info(file_path)
            if dev_config:
                device_groups[dev_config].append((file_path, is_tv, sn))
            else:
                logger.error(f"Skipping {file_path.name}: Unable to parse device config.")
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {e}")

    if not device_groups:
        logger.error("No valid device groups formed.")
        return ExitCode.NO_DATA_FOUND

    # 2. Process groups
    processed_count = 0

    try:
        for dev_name, files in device_groups.items():
            # Filter by device if specified
            if args.device and dev_name != args.device:
                logger.debug(f"Skipping {dev_name} (--device filter)")
                continue

            logger.debug(f"Processing group: {dev_name} ({len(files)} files)")

            # Path setup
            expected_yaml = CONFIG_DIR / "device_configs" / f"{dev_name}.yaml"
            if not expected_yaml.exists():
                logger.warning(f"Config for {dev_name} not found. Using default.")
                expected_yaml = DEFAULT_EXPECTED_YAML

            # Output file paths (with or without timestamp)
            f_min_fail = REPORT_DIR / f"min_fail_{dev_name}.json"
            f_full_report = REPORT_DIR / f"full_report_{dev_name}.json"

            if timestamp:
                f_final_json = REPORT_DIR / f"final_report_{dev_name}_{timestamp}.json"
                f_html_result = RESULT_DIR / f"{dev_name}_{timestamp}.html"
            else:
                f_final_json = REPORT_DIR / f"final_report_{dev_name}.json"
                f_html_result = RESULT_DIR / f"{dev_name}.html"

            device_reports = []
            source_files_to_archive = []
            group_is_tv = False

            # Process individual files
            for f_path, is_tv, sn in files:
                group_is_tv = is_tv
                try:
                    data = parse.parse_one_file(f_path)
                    if not data: continue

                    calc_res = cal.run_calculations(data, is_tv)
                    report_entry = r.json_report(
                        sn=sn,
                        t=data.get("MeasurementDateTime"),
                        is_tv=is_tv,
                        device_name=dev_name,
                        **calc_res
                    )
                    device_reports.append(report_entry)
                    source_files_to_archive.append(f_path)
                except Exception as e:
                    logger.error(f"Calculation failed for {sn}: {e}")

            if not device_reports:
                logger.warning(f"No reports generated for {dev_name}.")
                continue

            # Aggregate and generate reports
            if not r.calculate_full_report(device_reports, f_full_report, dev_name):
                logger.error(f"Failed to calculate full report for {dev_name}")
                continue

            if not r.analyze_json_files_for_min_fail(device_reports, expected_yaml, f_min_fail, dev_name):
                logger.error(f"Failed to analyze min/fail for {dev_name}")
                continue

            if not r.generate_comparison_report(f_full_report, expected_yaml, f_final_json, group_is_tv, device_reports):
                logger.error(f"Failed to generate comparison report for {dev_name}")
                continue

            if not h.create_html_report(
                input_file=f_final_json,
                output_file=f_html_result,
                device_reports=device_reports,
                min_fail_file=f_min_fail,
                cie_background_svg=CIE_BG_SVG,
                report_view_config=REPORT_VIEW_CONFIG,
                current_device_name=dev_name,
                app_version=APP_VERSION,
                expected_yaml = expected_yaml,
            ):
                logger.error(f"Failed to create HTML report for {dev_name}")
                continue

            logger.success(f"Report generated: {f_html_result}")
            processed_count += 1

            # Archive and Cleanup (skip if --noclean)
            if not args.noclean:
                generated_files = [f_min_fail, f_full_report, f_final_json, f_html_result]
                all_files = source_files_to_archive + generated_files

                if timestamp:
                    zip_path = ARCHIVE_DIR / f"{dev_name}_{timestamp}.zip"
                else:
                    zip_path = ARCHIVE_DIR / f"{dev_name}.zip"

                archive_result = h.archive_specific_files(zip_path, all_files, Path.cwd())
                if archive_result:
                    h.clear_specific_files(source_files_to_archive + [f_min_fail, f_full_report, f_final_json])
                else:
                    logger.warning(f"Archiving failed for {dev_name}, skipping cleanup to preserve files")

    except Exception as e:
        logger.exception(f"Critical error in main loop: {e}")
        return ExitCode.GENERAL_ERROR

    if processed_count > 0:
        logger.success(f"Completed. Groups processed: {processed_count}")
        return ExitCode.SUCCESS

    return ExitCode.NO_DATA_FOUND


if __name__ == "__main__":
    sys.exit(main())