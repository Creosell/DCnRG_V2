# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.5.0] - 2026-11-17

### Added
- `--evaluate PATH` mode (`-` reads the device JSON from stdin): evaluates one device against the spec of its `DeviceConfiguration` and prints the result as JSON to stdout, without generating reports or writing any file or directory. Intended for the measurement application, which can request it after every measurement. The result is `{"schema", "device": PASS/WARN/FAIL, "complete", "checks": [...]}`; each check carries `key`, rounded `value`, spec `min`/`typ`/`max`, `status` (`pass`, `warning`, `fail`, `pending` when the needed points are not measured yet, `n/a` when the points are measured but the metric has no valid value), the measurement `locations` it comes from (for uniformity: the darkest point) and the `missing` locations. Exit codes: 0 result printed, 3 spec not found, 1 invalid input; errors are printed as `{"schema", "error"}`
- Attempts of a point in `--evaluate`: a measurement of the device JSON may carry an optional `Attempts` list (each with `x`, `y`, `Lv`, `T`). The point is evaluated by its best attempt: the best status of the point's own checks first (pass, then warning, then fail), then for the red/green/blue points the smaller distance from the typical coordinates, then the higher luminance. The result gets `attempts: {location: {count, best, deviated}}` (`best` is the index in `Attempts`, `deviated` tells whether any attempt had a remark against the spec). Files without `Attempts` behave as before and the report generation ignores the list
- New module `src/evaluate.py` with the per-device rules (`get_cell_status`, `evaluate`, `verdict_of`, `required_locations`); `tests/test_evaluate.py` includes a test that the statuses of `--evaluate` equal the cell highlighting of the HTML report
- Device verdict in the HTML report: the Serial Number cell of every device row is highlighted red (a failing cell) or yellow (a cell below typ) according to the worst cell status of the device, with the verdict in the tooltip

### Changed
- Color Temperature is no longer highlighted yellow when it is below `typ`: it is checked against `min`/`max` only (as in the verdict rules), so a value inside the window is not flagged
- The cell status rules moved from `helpers.py` to `src/evaluate.py`; `helpers._get_cell_status` stays as an alias, report output is unchanged

### Fixed
- Printing the report to PDF from a browser added the browser's own header (date, title) and footer (file path) on every page: the small page margins did not suppress them. The print stylesheet now defines its own running header (report title, device and inspection date) and footer (generator version, `Page N of M`) as `@page` margin boxes; defining margin boxes also stops Chromium-based browsers (Chrome, Edge) from printing their default header and footer, whatever the print dialog option says. Browsers without margin box support ignore the rules and fall back to their own header and footer

## [1.4.3] - 2026-11-16

### Added
- **Black Luminance (cd/m²)** column in the Device Reports Main Data table, right after Brightness: `Lv` of the `BlackColor` measurement shown with 4 decimals, without tolerance check. Files without a `BlackColor` measurement show `—`
- **Colorimeter** line in the report header next to the inspection date (`Konica Minolta CA-410, S/N 81026182, Channel 2`), built from the optional `Colorimeter` object of the measurement JSON. Different colorimeters within one report are listed once each, separated by `; `; the line is hidden for files without the object
- Print stylesheet of the HTML report (`@page` A4 portrait + `@media print`; page top/bottom margins are below ~10 mm, so Chromium-based browsers do not add their own date/title header and file path footer) so that it can be saved as PDF from a browser or an HTML-to-PDF converter: cell status colors and table header backgrounds are kept (`print-color-adjust: exact`), table headers repeat on every page, rows, summary tables and the plot are not split across pages, sort arrows are hidden and only the ticked plot checkboxes are printed as the legend of the drawn triangles, scroll/zoom clipping is removed and the Device reports section follows the plot without a forced page break. The on-screen view is unchanged

### Changed
- Device Reports Main Data column order: Brightness, Black Luminance, Contrast Ratio, Brightness Uniformity, Color Temperature, ΔE (Contrast Ratio now precedes Brightness Uniformity)

### Fixed
- Gamut plot triangles are ticked by default also for color spaces that the device spec defines only through coverage (`Cg_<space>`, `Cg_<space>_uv`); before, only the area metrics (`Cg_<space>_area`, `Cg_<space>_uv_area`) were considered. Area still comes first, coverage is the fallback
- Sort arrow of the Device Reports table headers is vertically centered in the header cell; it used to drop to the last line when a long title (e.g. `Black Luminance (cd/m²)`) wrapped

## [1.4.2] - 2026-11-16

### Fixed
- Release build produced an `ReportGenerator.exe` without project dependencies (`ModuleNotFoundError: No module named 'colormath2'` at start; `numpy`, `PyYAML`, `shapely`, `Jinja2` were missing too). `release_manager.py` runs under `uv run`, which builds its own environment from the `# /// script` header, and that header listed only the release script's own dependencies; the build was complete only when run from an activated `.venv`. The header now declares the project dependencies

## [1.4.1] - 2026-11-09

### Added
- `tools/excel_converter.py` (renamed from `excel_import.py`): `--device-config` option (config name or YAML path) sets `DeviceConfiguration` in the generated JSON files and builds the HTML report next to them

### Fixed
- `safe_round()` rounded report statistics with built-in `round()`, which works on the binary float and rounds integers half to even: exact 4th-decimal halves of instrument readings went either way (`0.1515` -> `0.151`, `0.0525` -> `0.052`, `380.5` -> `380`), flipping PASS/FAIL at spec bounds and disagreeing with the Excel QC template. Statistics are now rounded half up in decimal notation (`Decimal` + `ROUND_HALF_UP`), same as Excel `ROUND`
- Device Reports cell highlighting (`_get_cell_status()`) compared the raw value while the cell shows it rounded to `REPORT_PRECISION` and the verdict uses the rounded value: e.g. brightness `359.58` displayed as `360` was marked below TYP `360`, coordinate `0.2723` displayed as `0.272` was marked above MAX `0.272`. The value is now rounded half up to `REPORT_PRECISION` before comparison

## [1.4.0] - 2026-09-09

### Added
- **Rec.2020 color gamut support**: full pipeline coverage for a 4th color space alongside sRGB/NTSC/DCI-P3 — `Cg_rec2020_area`, `Cg_rec2020`, `Cg_rec2020_uv_area`, `Cg_rec2020_uv` metrics, `configuration_example.yaml` block, Device Reports table columns, and a Rec.2020 triangle overlay (with toggle checkbox) on the Color Gamut Plot
- `tools/validate_device_configs.py::OPTIONAL_KEYS`: reference keys a device config may omit without a "missing key" validation error, so introducing a new metric (starting with the Rec.2020 block) no longer requires touching every existing `config/device_configs/*.yaml` file

### Changed
- Color space handling in `calculate.py` refactored to a single registry (`ColorSpace`, `COLOR_STANDARDS`, `COLOR_SPACE_KEY_SUFFIX`, `COLOR_SPACE_DISPLAY_NAME`) driving `cg()`/`cg_by_area()`/`cg_uv()`/`cg_by_area_uv()`/`run_calculations()`, instead of per-space copy-pasted code
- `report.py` (`REPORT_PRECISION`, `MAJORITY_TYP_CHECK_KEYS_FOR_TV`, `CORPORATE_DEVICES_CG_TOLERANCE_LIST`) and `helpers.py` (`UFN_MAPPING`, `GAMUT_KEYS_XY`/`GAMUT_KEYS_UV`, `DYNAMIC_VISIBILITY_KEYS`) now derive their color-gamut metric keys from the same registry, so adding a future color space no longer means editing key lists in multiple files

### Fixed
- `sanitize_filename()` duplicated the factory/order suffix in output file and archive names when `DeviceConfiguration` encoded a `device_configs` subfolder matching that suffix (e.g. `CH30\SDF-65RGB9000MGAW_CH30` produced `CH30_SDF-65RGB9000MGAW_CH30.html`) — the subfolder segment is now dropped when the device's own name already ends with it

## [1.3.0] - 2026-08-12

### Fixed
- Report generation crashed with `FileNotFoundError` when `DeviceConfiguration` encoded a `device_configs` subfolder path (e.g. `EL29\SDX-65U8133_EL29`), since output file/archive names were built directly from the raw value

### Added
- `resolve_expected_yaml()` in `main.py` resolves device YAML configs located in `device_configs` subfolders, with path-traversal protection
- `sanitize_filename()` in `main.py` flattens path separators and strips characters invalid in Windows filenames before building output file/archive names

## [1.2.5] - 2026-07-22

### Added
- Cursor CIE xy coordinate readout badge on the Color Gamut Plot, backed by calibration constants exported from `SvgCoordinator`

### Changed
- Panning on the zoomed Color Gamut Plot now eases toward the cursor via `requestAnimationFrame` instead of snapping the transform origin on every `mousemove`

### Fixed
- Column sorting was broken for the Gamut Data tables (CIE 1931 xy / CIE 1976 u'v') because `sortDirections` was missing their keys, throwing a `TypeError` on click
- "Fails description" table under Main Test Results and Color Coordinates no longer renders when every entry has status `PASS`

## [1.2.4] - 2026-07-17

### Fixed
- UTF-8 decoding for reports on non-default Windows locales
- `NameError` in TV majority logic

### Changed
- Refactored `get_coordinates`: removed unused `is_tv_flag`, added docstrings
- Migrated project tooling to `pyproject.toml` and `uv.lock`

## [1.2.3] - 2026-06-29

### Changed
- Converted dictionary keys to standard `snake_case` format across all configuration and parsing files
- Corporate devices now dynamically fallback to `White_x/White_y` if `Center_x/Center_y` is missing from the configuration file

### Fixed
- Fixed a bug where TV devices were incorrectly skipping Color Gamut validation checks due to key mismatches
- Removed Color Gamut parameters from `AVG_FAIL_SKIP_KEYS_FOR_TV` to enforce strict validation against the `typ` value for TVs
- Restored original mapping `Center_x,y` and `White_x,y` coordinates for their respective device types

## [1.2.2] - 2026-06-25

### Added
- `AVG_FAIL_SKIP_KEYS_FOR_CORPORATE` (`{"Contrast"}`) and `CONTRAST_TYP_SKIP_CONFIGS` (`{"SDNB-16iA", "SDNB-M16iA"}`) in `report.py`: for these specific device configs (including factory-suffix variants), the TYP/avg check for Contrast is skipped — only `min` is evaluated
- `device_config_name` parameter added to `generate_comparison_report` and `check_general_test_status` for device-specific rule dispatch

## [1.2.1] - 2026-05-29

### Fixed
- `adjusted_typ` in corporate device tolerance info was stored as a raw float with floating-point artifacts (e.g. `78.85000000000001`); now rounded via `safe_round` using `REPORT_PRECISION` for the corresponding metric

## [1.2.0] - 2026-05-06

### Added
- **CIE 1976 u'v' color gamut calculations**: new `xy_to_uv`, `coords_xy_to_uv`, `cg_uv`, `cg_by_area_uv` functions in `calculate.py`
- **6 new gamut metrics** exposed through the full pipeline: `CgByAreaUVRGB`, `CgByAreaUVNTSC`, `CgByAreaUVDCI-P3`, `CgUVRGB`, `CgUVNTSC`, `CgUVDCI-P3`
- Corresponding YAML keys (`Cg_*_uv_area`, `Cg_*_uv`) added to `configuration_example.yaml` with descriptions
- **Gamut Data split into two subtables** in Device reports: CIE 1931 xy and CIE 1976 u'v' (conditional — hidden when no u'v' expected values defined)
- Cell status legend visually attached to each table via `div.table-with-legend` wrapper
- **`Coordinates_tolerance` YAML key**: single tolerance value that automatically computes `min`/`max` as `typ ± tolerance` for all color coordinate metrics — replaces per-coordinate `min`/`max` fields in device configs
- **`expand_coordinates_tolerance()`** utility in `report.py`: applied transparently at all YAML loading points
- 21 new tests covering u'v' calculations, dynamic visibility, coordinate tolerance expansion, and plot triangle visibility

### Breaking Changes
- **`main_tests:` root key removed from YAML device configs**: metrics are now defined at the top level of the file — existing configs must be updated by removing the `main_tests:` wrapper and de-indenting content
- **`parse_yaml()` signature changed**: `dictionary` parameter removed; function now reads the root YAML dict directly

### Changed
- **`report_view.yaml` removed from visibility chain**: metric visibility is now driven exclusively by expected values presence in YAML config (dynamic visibility). Metrics in `DYNAMIC_VISIBILITY_KEYS` are shown only when at least one of min/typ/max is defined
- `DeltaE` added to `DYNAMIC_VISIBILITY_KEYS` — hidden when not specified in device config
- `process_device_reports` now returns 4-tuple `(main, gamut_xy, gamut_uv, coordinates)` instead of 3-tuple
- `create_html_report` and `process_main_report` no longer accept `report_view_config` parameter
- **Color gamut keys in `configuration_example.yaml` regrouped by color space**: sRGB → NTSC → DCI-P3, each group containing `_area`, standard, `_uv_area`, `_uv` variants
- Coordinate entries in `configuration_example.yaml` simplified to `typ`-only using `Coordinates_tolerance: 0.030`
- **CIE diagram color space triangles** now activate when either the CIE 1931 xy or CIE 1976 u'v' area metric has expected values (previously only xy was checked)

### Fixed
- **Min violation priority in comparison report**: when actual avg is below both `min` and `typ` thresholds, the FAIL reason now cites the min bound violation (more critical) instead of the typ check
- **`coordinates_of_triangle()`** in `parse.py` now guards against missing or invalid `x`/`y` keys — previously raised `KeyError` on malformed measurement data
- **`group_is_tv` flag** in `main.py` now taken from the first file in a group instead of being overwritten on each iteration

### Changed
- **`delta_e()`** in `calculate.py` now raises `ValueError` on all error conditions instead of returning error strings — consistent with all other calculation functions
- **TV majority check block** in `report.py` now gated behind `is_tv_majority_report` flag and only executes when enabled — pending customer confirmation for production use

### Removed
- `REPORT_VIEW_CONFIG` constant and `report_view.yaml` from the processing pipeline (file preserved but no longer read)
- **Fail on Minimum Values Report** section removed from HTML output — individual min violations are already visible via red highlighting and column sorting in Device reports, making this section redundant
- `analyze_json_files_for_min_fail()` function removed from `report.py`
- `min_fail_file` parameter removed from `create_html_report()` in `helpers.py`

---

## [1.1.4] - 2026-01-30

### Fixed
- **Inverted comparison logic for DeltaE**: lower values are better — FAIL now triggers when value exceeds `max`, WARNING when value exceeds `typ`
- Added `LOWER_IS_BETTER_KEYS` constant in `helpers.py` and `report.py` to control inverted evaluation logic
- `_get_cell_status()` updated to apply inverted highlighting for DeltaE in Device reports
- `check_general_test_status()` updated with dedicated DeltaE branch in comparison report

---

## [1.1.3] - 2026-01-29

### Added
- **Expected value triangles on CIE diagram**: specification color coordinates now rendered as a reference triangle on the chromaticity plot
- `prepare_specification_plot_coordinates()` helper added to `helpers.py`
- `expected_yaml` parameter added to `create_html_report()`

### Changed
- `COORD_HEADERS_UFN` renamed to `COORD_KEYS_INTERNAL` — now uses internal key names instead of display names for coordinate identification
- Legacy snake_case YAML keys (`Brightness_uniformity`, `White_x`, etc.) restored to backward compatibility via `YAML_TO_JSON_KEY_MAP`

### Removed
- `manifests/report_generator_1.0.0.json` removed from repository

---

## [1.1.2] - 2026-01-29

### Added
- **Color-coded cell highlighting** in Device reports tables:
  - Red (critical): values outside min/max bounds
  - Yellow (warning): values below typical target but within min/max
  - White (normal): values meeting or exceeding typical target
- **Dynamic Color Gamut metric visibility**: gamut columns appear only when expected values are defined in YAML config
- **Command line arguments** for flexible report generation:
  - `--verbose` / `-v`: enable DEBUG logging
  - `--noclean` / `-nc`: skip archiving and cleanup
  - `--device` / `-d`: process only specified device
  - `--no-timestamp`: generate output files without timestamp
  - `--version`: display version and exit
- `_get_cell_status()` helper for cell status evaluation logic
- `_should_display_metric()` helper for dynamic visibility checks

### Fixed
- Inverted comparison logic for DeltaE metric (lower is better)
- Temperature validation now uses only min/max bounds, ignoring typ

### Changed
- DCI-P3 added to gamut calculations and reports
- Tolerance visualization added to HTML reports for corporate device thresholds
- Corporate device tolerance rules adapted for updated requirements
- Device reports table split into Main Data, Gamut Data, and Coordinates sections
- Common "Device reports" heading extracted above individual tables

---

## [1.1.1] - 2026-01-26

### Fixed
- Temperature validation logic corrected to check only min/max bounds

### Changed
- Version aligned after 1.1.0 refactor

---

## [1.1.0] - 2026-01-23

### Fixed
- **Exit code accuracy**: application now returns correct codes based on actual success/failure
  - Previously returned `SUCCESS (0)` even when report generation failed
  - Now returns `NO_DATA_FOUND (2)` if no device groups complete successfully
- **Template path resolution in compiled executable**: fixed "template not found" error when running as `.exe` via `sys.frozen` detection
- **Data preservation on archiving failure**: intermediate files no longer deleted if zip creation fails

### Changed
- Report generation functions now return `bool` for proper error propagation: `create_html_report`, `calculate_full_report`, `analyze_json_files_for_min_fail`, `generate_comparison_report`
- Each report generation step validated before proceeding; failed device groups are skipped, not fatal
- Archive result checked before cleanup operations

### Added
- 12 new tests for return value validation (success and failure scenarios)
- Legacy YAML key mapping (`YAML_TO_JSON_KEY_MAP`) for backward compatibility with snake_case config keys
- Comprehensive error logging with device name context on failures

---

## [1.0.0]

Initial working release. Core pipeline: JSON measurement files → parse → calculate → compare against YAML specs → generate HTML report → archive.
