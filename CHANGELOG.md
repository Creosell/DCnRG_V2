# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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

### Removed
- `REPORT_VIEW_CONFIG` constant and `report_view.yaml` from the processing pipeline (file preserved but no longer read)
- **Fail on Minimum Values Report** section removed from HTML output — individual min violations are already visible via red highlighting and column sorting in Device reports, making this section redundant
- `analyze_json_files_for_min_fail()` function removed from `report.py`
- `min_fail_file` parameter removed from `create_html_report()` in `helpers.py`

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
