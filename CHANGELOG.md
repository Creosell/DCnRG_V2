# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.1.0] - 2025-01-23

### Fixed
- **Exit code accuracy**: Application now returns correct exit codes based on actual success/failure of report generation
  - Previously returned `SUCCESS (0)` even when report generation failed
  - Now returns `NO_DATA_FOUND (2)` if no device groups complete successfully
- **Template path resolution in compiled executable**: Fixed "template not found" error when running as `.exe`
  - Application now detects PyInstaller frozen mode using `sys.frozen`
  - Config files are correctly located relative to executable in production builds
- **Data preservation on archiving failure**: Intermediate files are no longer deleted if archiving fails
  - Prevents data loss when zip creation encounters errors

### Changed
- **Report generation functions now return bool values**:
  - `helpers.create_html_report() -> bool`
  - `report.calculate_full_report() -> bool`
  - `report.analyze_json_files_for_min_fail() -> bool`
  - `report.generate_comparison_report() -> bool`
- **Enhanced error handling in main.py**:
  - Each report generation step is validated before proceeding
  - Failed device groups are logged and skipped (processing continues with next group)
  - Only successfully completed groups increment the success counter
  - Archive result is checked before cleanup operations

### Added
- **12 new tests for return value validation**:
  - 4 tests for `create_html_report()` success and error scenarios
  - 8 tests for report generation functions (`calculate_full_report`, `analyze_json_files_for_min_fail`, `generate_comparison_report`)
  - Tests verify correct return of `True` on success and `False` on various error conditions
- **Comprehensive error logging**: All report generation failures now include device name and error context

### Documentation
- Updated `CLAUDE.md` with:
  - Error handling patterns and return value conventions
  - Exit code documentation
  - Path resolution behavior for compiled executables
  - Common pitfalls and solutions section
  - Return value test coverage details
- Updated `README.md` with exit codes section for user reference
- Created `CHANGELOG.md` to track project changes

## [1.0.0] - 2025-01-23

### Initial Release
- Report generation for display devices (TVs and monitors)
- JSON measurement parsing and validation
- Photometric and colorimetric calculations
- HTML report generation with CIE chromaticity diagrams
- YAML-based configuration system
- Device grouping and batch processing
- Archive and cleanup functionality
- PyInstaller executable compilation support
- Comprehensive test suite (53 tests)
