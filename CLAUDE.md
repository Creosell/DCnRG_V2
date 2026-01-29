# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DCnRG_V2** (Display Device Report Generator) analyzes display device test results from TVs and monitors. It parses JSON measurement logs containing photometric and colorimetric data, calculates performance metrics, compares against expected standards, and generates interactive HTML reports with CIE chromaticity diagrams.

**Core workflow**: JSON measurement files → parse → calculate → compare against YAML specs → generate HTML report → archive results

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running
```bash
# Run the application
python main.py

# Run with command line options
python main.py --verbose              # Enable DEBUG logging
python main.py --noclean              # Skip archiving and cleanup
python main.py --device "DeviceName"  # Process only specific device
python main.py --no-timestamp         # Generate files without timestamp
python main.py --version              # Show version and exit

# Run tests
pytest src/tests/

# Run specific test file
pytest src/tests/test_calculate.py

# Run tests with verbose output
pytest -v src/tests/
```

**Command Line Arguments**:
- `--verbose, -v`: Enable DEBUG level logging (default: INFO)
- `--noclean, -nc`: Skip archiving and file cleanup steps
- `--device NAME, -d NAME`: Process only the specified device configuration
- `--no-timestamp`: Generate output files without timestamp for easier regeneration
- `--version`: Display application version and exit

### Building Executable
```bash
# Install UV if not already installed
pip install uv

# Build, zip, and upload release (includes config folder)
uv run --active release_manager.py zip build\dist\ReportGenerator report_generator 1.0.0 --include config --build --upload

# Build only (no upload)
uv run --active release_manager.py zip build\dist\ReportGenerator report_generator 1.0.0 --include config --build
```

**Optional**: For smaller executables, place `upx.exe` in `.venv\Scripts\` for automatic compression during PyInstaller build.

## Architecture Overview

### Data Flow Pipeline
```
data/*.json (Input)
    ↓
parse.py → Extract device info, measurements
    ↓
calculate.py → Run photometric/colorimetric calculations
    ↓
report.py → Generate intermediate JSON reports
    ↓
helpers.py → Render HTML + create archives
    ↓
results/*.html (Output)
report_archive/*.zip (Archive)
```

### Module Responsibilities

**parse.py** - Data Extraction
- `get_device_info()`: Extracts `DeviceConfiguration` name, `IsTV` flag, and `SerialNumber` from JSON
- `parse_one_file()`: Loads and validates JSON measurement files
- `get_coordinates()`: Extracts RGB color point coordinates from measurements
- `coordinates_of_triangle()`: Gets RGB triangle vertices for gamut calculations

**calculate.py** - Photometric & Colorimetric Calculations
- `brightness()`: Calculates min/typ/max brightness from Lv measurements
- `brightness_uniformity()`: Uniformity percentage across display
- `contrast()`: Contrast ratio (WhiteColor/BlackColor for TV, Center/BlackColor for monitor)
- `cg()` / `cg_by_area()`: Color gamut coverage for sRGB, NTSC, DCI-P3 color spaces
- `delta_e()`: Color uniformity via Delta E CIE 2000
- `temperature()`: Color temperature extraction
- `run_calculations()`: Orchestrates all calculations with graceful error handling

**report.py** - Report Generation & Comparison
- `json_report()`: Creates individual device report JSON structure
- `calculate_full_report() -> bool`: Aggregates multiple device reports, returns `True` on success, `False` on error
- `analyze_json_files_for_min_fail() -> bool`: Identifies minimum/fail threshold violations, returns `True` on success
- `generate_comparison_report() -> bool`: Compares measurements against YAML standards, returns `True` on success
- Contains `REPORT_PRECISION` dict for metric rounding
- TV-specific tolerances: `CONTRAST_TOLERANCE_FOR_TV`, `AVG_FAIL_SKIP_KEYS_FOR_TV`, `MAJORITY_TYP_CHECK_KEYS_FOR_TV`
- Legacy YAML key mapping: `YAML_TO_JSON_KEY_MAP` (maintains backward compatibility)
- **All report generation functions return bool to enable proper error handling**

**helpers.py** - HTML Generation & File Operations
- `create_html_report() -> bool`: Renders Jinja2 template (`config/report_template.html`) with report data, returns `True` on success
- `archive_specific_files() -> str | None`: Creates zip archives of processed files, returns archive path or `None` on error
- `clear_specific_files()`: Cleans up intermediate files after archiving
- `_get_cell_status()`: Evaluates cell status for color-coded highlighting (critical/warning/normal)
- `process_device_reports()`: Processes device reports with cell status flags for visual indication
- `should_display_metric()`: Determines metric visibility based on expected values in YAML config
- `UFN_MAPPING`: Maps technical metric names to user-friendly display names
- `DYNAMIC_VISIBILITY_KEYS`: Metrics requiring expected values to be displayed (e.g., color gamut)
- **Handles both development and compiled (PyInstaller) modes for config path resolution using `sys.frozen` detection**

**graphics_helper.py** - SVG Coordinate System
- `SvgCoordinator`: Converts CIE xy chromaticity coordinates → SVG pixel coordinates
- Handles axis calibration (X: 0.0-0.8, Y: 0.0-0.9 CIE ranges)
- Inverts Y-axis for correct SVG rendering

**main.py** - Application Entry Point
1. Creates required directories
2. Sets up logging (console + rotating file logs)
3. Groups JSON files by `DeviceConfiguration` name
4. For each device group:
   - Loads device-specific YAML config (or falls back to `configuration_example.yaml`)
   - Parses measurement files
   - Runs calculations
   - **Checks return values of all report generation functions**
   - Generates min/fail, full report, and comparison JSON reports (skips group on failure)
   - Renders HTML from Jinja2 template (skips group on failure)
   - Archives results with timestamp (only if successful)
   - Cleans up intermediate files (only after successful archiving)
5. Returns exit code: `SUCCESS (0)`, `GENERAL_ERROR (1)`, `NO_DATA_FOUND (2)`, or `CONFIG_ERROR (3)`

**Exit Code Logic**:
- `SUCCESS (0)`: At least one device group was successfully processed
- `GENERAL_ERROR (1)`: Unhandled exception in main loop
- `NO_DATA_FOUND (2)`: No JSON files found OR no groups successfully processed
- `CONFIG_ERROR (3)`: Failed to create required directories

**Error Handling**: Each report generation step is validated. If any step fails (returns `False`), the error is logged, and processing continues with the next device group. Only successfully completed groups increment `processed_count`.

### Key Architectural Patterns

**Device Grouping**: Files are grouped by `DeviceConfiguration` name extracted from JSON. All measurements with the same config name are aggregated into a single report. This enables batch processing of multiple test runs per device model.

**Configuration Fallback Chain**:
```
config/device_configs/{DeviceConfiguration}.yaml
    ↓ (if not found)
config/configuration_example.yaml (default fallback)
```

**TV vs Monitor Branching**: The `IsTV` boolean flag controls calculation logic:
- TV: Uses `WhiteColor` for brightness/contrast calculations
- Monitor: Uses `Center` for the same calculations
- Some metrics (e.g., `BrightnessUniformity`) skip fail checks for TVs

**Graceful Error Handling**: Failed calculations set metric values to `None` rather than crashing. Pipeline continues processing other files. Errors are logged but don't halt batch processing.

**Legacy Compatibility**: `YAML_TO_JSON_KEY_MAP` in `report.py` maintains backward compatibility with older snake_case YAML keys (e.g., `Brightness_uniformity` → `BrightnessUniformity`, `White_x` → `Center_x`).

**Path Resolution for Compiled Executables**: When running as a PyInstaller-compiled executable (`sys.frozen == True`), the application resolves paths relative to the executable location rather than the Python script location. This ensures that the `config/` folder (included via `--include config` during build) is correctly located in production deployments.

## Error Handling & Return Values

All critical functions in the report generation pipeline return boolean values to enable proper error propagation:

### Return Value Pattern
```python
# Success case
if create_html_report(...):
    logger.success("Report generated")
    processed_count += 1
else:
    logger.error("Failed to create report")
    continue  # Skip to next device group
```

### Functions with Bool Returns
- `helpers.create_html_report() -> bool`
  - Returns `False` on: missing input files, YAML parsing errors, template loading failures, render/write errors
  - Returns `True` only when HTML file is successfully written

- `report.calculate_full_report() -> bool`
  - Returns `False` on: aggregation errors, file write failures
  - Returns `True` when aggregated report is successfully saved

- `report.analyze_json_files_for_min_fail() -> bool`
  - Returns `False` on: missing YAML, YAML parsing errors, write failures
  - Returns `True` when min/fail analysis is complete

- `report.generate_comparison_report() -> bool`
  - Returns `False` on: missing files, YAML parsing errors, write failures, serialization errors
  - Returns `True` when comparison report is successfully saved

### Error Recovery Strategy
1. **Per-Group Isolation**: If any report generation step fails for a device group, processing continues with the next group
2. **Logged Errors**: All failures are logged with context (device name, error details)
3. **Partial Success Allowed**: Application returns `SUCCESS (0)` if at least one group completed successfully
4. **File Preservation**: If archiving fails, intermediate files are NOT deleted to prevent data loss

## Configuration Files

- **`config/expected_result.yaml`**: Measurement specification standards (min/typ/max values for all metrics)
- **`config/configuration_example.yaml`**: Default expected result template when device-specific config not found
- **`config/device_configs/*.yaml`**: Per-device expected values (named by `DeviceConfiguration` field from JSON). Allows customized thresholds for different device models.
- **`config/report_view.yaml`**: Boolean flags controlling which columns appear in HTML reports
- **`config/color_space.yaml`**: Color space definitions (sRGB, NTSC, DCI-P3 primaries as CIE xy coordinates)
- **`config/report_template.html`**: Jinja2 template for HTML report rendering. Includes CSS for color-coded cell highlighting and legends.
- **`config/CIExy1931.svg`**: CIE 1931 chromaticity diagram SVG background for visualizations

## Testing

Tests use pytest with pytest-mock. Fixtures in `conftest.py` provide mock TV and monitor measurement data.

**Test coverage** (71 tests total):
- `test_calculate.py` (14 tests): Math validation, brightness, contrast, color gamut, delta E, temperature
- `test_report.py` (34 tests): JSON report generation, min/fail analysis, comparison reports, **return value validation**
- `test_parse.py` (10 tests): JSON parsing, device info extraction, coordinate extraction
- `test_helpers.py` (13 tests): HTML generation, archiving, cleanup operations, **return value validation**, cell status logic, dynamic metric visibility

### Return Value Tests (Added 2025-01-23)
New tests validate that report generation functions correctly return `True` on success and `False` on errors:

**helpers.py tests:**
- `test_create_html_report_returns_true_on_success`
- `test_create_html_report_returns_false_on_missing_input_file`
- `test_create_html_report_returns_false_on_missing_expected_yaml`
- `test_create_html_report_returns_false_on_template_load_error`
- `test_get_cell_status`: Validates color-coded status logic (critical/warning/normal)
- `test_process_device_reports_with_cell_status`: Ensures cell_status flags are correctly computed
- `test_should_display_metric`: Validates dynamic metric visibility based on YAML expected values
- `test_process_main_report_dynamic_cg_filter`: Tests Color Gamut metric filtering

**report.py tests:**
- `test_calculate_full_report_returns_true_on_success`
- `test_calculate_full_report_returns_false_on_write_error`
- `test_analyze_json_files_for_min_fail_returns_true_on_success`
- `test_analyze_json_files_for_min_fail_returns_false_on_missing_yaml`
- `test_analyze_json_files_for_min_fail_returns_false_on_write_error`
- `test_generate_comparison_report_returns_true_on_success`
- `test_generate_comparison_report_returns_false_on_missing_actual_file`
- `test_generate_comparison_report_returns_false_on_missing_expected_file`

These tests ensure that exit codes are correctly propagated based on actual success/failure of operations.

## Important Implementation Details

**Color-Coded Cell Highlighting** (Added v1.1.2): Device reports tables use visual status indicators:
- **Red (critical)**: Values outside min/max bounds (fail condition)
- **Yellow (warning)**: Values below typical target but within min/max range
- **White (normal)**: Values meeting or exceeding typical target
- Coordinate tables only use red/white (no typ check)
- Status logic in `helpers._get_cell_status()`, applied via CSS classes in template
- Color legend displayed below each Device reports table

**Dynamic Metric Visibility** (Added v1.1.2): Some metrics only appear if expected values exist in YAML config:
- Color gamut metrics (sRGB_by_area, NTSC_by_area, DCIP3_by_area) require corresponding expected values
- Controlled via `DYNAMIC_VISIBILITY_KEYS` in `helpers.py`
- Prevents empty columns when certain color spaces aren't specified in device config
- Checked by `should_display_metric()` function

**Coordinate Tests**: Metrics like `Red_x`, `Red_y`, `Green_x`, `Green_y`, `Blue_x`, `Blue_y`, `White_x`, `White_y` are validated against min/max bounds (not typ values). These are listed in `report.py::COORDINATE_TEST_KEYS`.

**Color Gamut Calculations**: Two methods available:
- `cg()`: Overlap percentage using Shapely polygon intersection
- `cg_by_area()`: Area-based calculation (triangle area formula)

**Timestamp-based Output**: All output files include timestamp (`YYYYMMDD_HHMM`) to prevent overwrites. Archives preserve complete processing history.

**Logging**: Uses loguru with dual output:
- Console: INFO level with colored timestamps
- File: DEBUG level in `logs/report_generator.log` (1 MB rotation, 2 file retention, zip compression)

## Dependencies

**Core Processing**:
- `numpy`: Numerical calculations
- `colormath2`: Color space conversions (Delta E CIE 2000)
- `shapely`: Polygon intersection for gamut overlap calculations
- `PyYAML`: Configuration file parsing

**Reporting**:
- `Jinja2`: HTML template rendering

**Build & Distribution**:
- `PyInstaller`: Executable compilation (configured via `ReportGenerator.spec`)
- `nc_py_api`, `requests`, `urllib3`: Nextcloud release uploads

**Testing**:
- `pytest`: Test framework
- `pytest-mock`: Mocking utilities

## Common Pitfalls & Solutions

### Issue: Exit Code 0 Despite Report Generation Failure
**Symptom**: Application logs errors (e.g., "Template not found") but returns exit code 0 (SUCCESS).

**Root Cause**: Report generation functions weren't returning bool values, so `main.py` couldn't detect failures.

**Solution**: All report generation functions now return `True`/`False`. The `main.py` checks these return values and only increments `processed_count` on success. Exit code is `NO_DATA_FOUND (2)` if no groups complete successfully.

### Issue: Template Not Found in Compiled Executable
**Symptom**: `'report_template.html' not found in search path` when running the `.exe` file.

**Root Cause**: PyInstaller changes how file paths are resolved. Using `Path(__file__).parent` in compiled mode points to temporary extraction directory, not the executable's directory.

**Solution**: Check `sys.frozen` flag:
```python
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent  # Compiled: use exe location
else:
    base_dir = Path(__file__).parent.parent  # Development: use script location
```

The `config/` folder must be included in releases using `--include config` flag.

### Issue: Files Not Cleaned Up After Processing
**Symptom**: Intermediate JSON files remain in `test_reports/` and `data/` after successful runs.

**Cause**: Archiving could fail silently, but cleanup ran anyway, potentially causing data loss.

**Solution**: Check archive result before cleanup:
```python
archive_result = h.archive_specific_files(zip_path, all_files, Path.cwd())
if archive_result:
    h.clear_specific_files(intermediate_files)
else:
    logger.warning("Archiving failed, preserving files")
```

### When Writing New Report Functions
1. **Always return bool**: `return True` on success, `return False` on error
2. **Check in main.py**: Use `if not function(...): continue` pattern
3. **Add tests**: Create both success and failure test cases
4. **Log errors**: Include context (device name, file paths) in error messages
5. **Preserve data**: Never delete source files if downstream steps fail
