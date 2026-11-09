# Graph Report - DCnRG_V2  (2026-11-09)

## Corpus Check
- 112 files · ~46,440 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .example 1, .spec 1)

## Summary
- 594 nodes · 1013 edges · 59 communities (57 shown, 2 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 86 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2b4917ad`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- release_manager.py
- test_calculate.py
- parse.py
- json
- calculate_full_report
- CLAUDE.md
- _should_display_metric
- Report Generator
- process_device_reports
- test_helpers.py
- calculate.py
- configuration_example.yaml
- Module Responsibilities
- Return Value Tests (Added 2025-01-23)
- test_report.py
- create_html_report
- SvgCoordinator
- validate_device_configs.py
- Changelog
- cg_uv
- check_general_test_status
- conftest.py
- expand_coordinates_tolerance
- _get_cell_status
- brightness
- contrast
- _corporate_adjusted
- temperature
- get_inspection_date_range
- json_report
- [1.1.2] - 2026-01-29
- safe_round
- Brightness
- Brightness_uniformity
- Cg_dcip3
- Cg_dcip3_area
- Cg_dcip3_uv
- Cg_dcip3_uv_area
- Cg_ntsc
- Cg_ntsc_area
- Cg_ntsc_uv
- Cg_ntsc_uv_area
- Cg_rec2020
- Cg_rec2020_area
- Cg_rec2020_uv
- Cg_rec2020_uv_area
- Cg_rgb
- Cg_rgb_area
- Cg_rgb_uv
- Cg_rgb_uv_area
- Contrast
- Delta_e
- Temperature
- [1.1.1] - 2026-01-26
- [1.1.3] - 2026-01-29
- [1.2.3] - 2026-06-29
- [1.4.0] - 2026-09-09
- report-generator

## God Nodes (most connected - your core abstractions)
1. `create_html_report()` - 25 edges
2. `generate_comparison_report()` - 24 edges
3. `Module Responsibilities` - 20 edges
4. `run_calculations()` - 17 edges
5. `main()` - 15 edges
6. `Changelog` - 15 edges
7. `check_general_test_status()` - 14 edges
8. `Return Value Tests (Added 2025-01-23)` - 14 edges
9. `calculate_full_report()` - 13 edges
10. `cg_by_area()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Changed` --references--> `delta_e()`  [INFERRED]
  CHANGELOG.md → src/calculate.py
- `Сквозной workflow` --references--> `delta_e()`  [INFERRED]
  .claude/skills/excel-converter/SKILL.md → src/calculate.py
- `Removed` --references--> `create_html_report()`  [INFERRED]
  CHANGELOG.md → src/helpers.py
- `Fixed` --references--> `coordinates_of_triangle()`  [INFERRED]
  CHANGELOG.md → src/parse.py
- `Changed` --references--> `get_coordinates()`  [INFERRED]
  CHANGELOG.md → src/parse.py

## Import Cycles
- None detected.

## Communities (59 total, 2 thin omitted)

### Community 0 - "release_manager.py"
Cohesion: 0.05
Nodes (27): Added, Формат листа "9 points" (для доработки/отладки скрипта), ensure_directories(), ExitCode, main(), parse_args(), resolve_expected_yaml(), sanitize_filename() (+19 more)

### Community 1 - "test_calculate.py"
Cohesion: 0.10
Nodes (13): ColorSpace, test_brightness_logic_display(), test_brightness_uniformity(), test_cg_by_area_logic(), test_cg_by_area_uv_returns_values(), test_cg_overlap_dcip3_value(), test_cg_returns_none_on_dci_p3_overlap_error(), test_cg_uv_returns_values() (+5 more)

### Community 2 - "parse.py"
Cohesion: 0.10
Nodes (13): Breaking Changes, find_closest_to_target(), get_device_info(), parse_one_file(), parse_yaml(), test_find_closest_to_target(), test_get_coordinates_logic(), test_get_coordinates_tv_logic() (+5 more)

### Community 3 - "json"
Cohesion: 0.11
Nodes (10): check_coordinate_bounds(), generate_comparison_report(), load_json_file(), write_error_report(), test_create_html_report_plot_triangles_checked(), test_generate_comparison_report_logic(), test_generate_comparison_report_min_violation_takes_priority_over_typ(), test_generate_comparison_report_returns_false_on_missing_expected_file() (+2 more)

### Community 4 - "calculate_full_report"
Cohesion: 0.10
Nodes (12): calculate_full_report(), process_items(), is_effectively_all_null_stat_package(), set_nested_value(), create_mock_device_report_dict(), test_calculate_full_report_aggregator_logic(), test_calculate_full_report_handles_bad_data(), test_calculate_full_report_returns_false_on_write_error() (+4 more)

### Community 5 - "CLAUDE.md"
Cohesion: 0.09
Nodes (20): Architecture Overview, Building Executable, Common Pitfalls & Solutions, Configuration Files, Data Flow Pipeline, Dependencies, Development Commands, Error Handling & Return Values (+12 more)

### Community 6 - "_should_display_metric"
Cohesion: 0.10
Nodes (12): [1.2.0] - 2026-05-06, Changed, Changed, Fixed, Removed, process_main_report(), _should_display_metric(), test_process_main_report() (+4 more)

### Community 7 - "Report Generator"
Cohesion: 0.10
Nodes (19): 1. Create local environment, 2\. Activation of venv, 3\. Install dependencies, Color coordinate tolerance, Command Syntax, Device Configuration, Dynamic visibility, Environment Setup (+11 more)

### Community 8 - "process_device_reports"
Cohesion: 0.11
Nodes (11): `data/` — важные нюансы, Excel Converter ("9 points" sheet → data/*.json → report), Когда использовать, Связанный фикс в коде (уже в основной ветке, коммит `f561c64`), Сквозной workflow, archive_specific_files(), clear_specific_files(), process_device_reports() (+3 more)

### Community 9 - "test_helpers.py"
Cohesion: 0.18
Nodes (5): collect_tolerance_legend(), load_yaml_file(), test_collect_tolerance_legend(), test_collect_tolerance_legend_empty(), test_rec2020_registered_in_gamut_key_sets()

### Community 10 - "calculate.py"
Cohesion: 0.16
Nodes (6): area(), calculate_overlap_percentage(), cg_by_area_uv(), _std_to_uv_triangle(), test_area_valid_triangle(), test_calculate_overlap_percentage_invalid_triangle()

### Community 11 - "configuration_example.yaml"
Cohesion: 0.11
Nodes (17): Blue_x, typ, Blue_y, typ, Coordinates_tolerance, Green_x, typ, Green_y (+9 more)

### Community 12 - "Module Responsibilities"
Cohesion: 0.21
Nodes (12): Changed, Important Implementation Details, Module Responsibilities, Известные ограничения данных, brightness_uniformity(), cg(), cg_by_area(), delta_e() (+4 more)

### Community 13 - "Return Value Tests (Added 2025-01-23)"
Cohesion: 0.12
Nodes (9): Return Value Tests (Added 2025-01-23), test_create_html_report_returns_false_on_missing_input_file(), test_create_html_report_returns_false_on_template_load_error(), test_get_cell_status(), test_process_device_reports_with_cell_status(), test_process_main_report_dynamic_cg_filter(), test_should_display_metric(), test_generate_comparison_report_returns_false_on_missing_actual_file() (+1 more)

### Community 14 - "test_report.py"
Cohesion: 0.17
Nodes (7): test_cg_metric_keys_include_all_registered_color_spaces(), test_corporate_contrast_skip_typ_fail_on_min(), test_corporate_contrast_skip_typ_pass_on_min(), test_generate_comparison_report_corporate_dcip3_tolerance(), test_generate_comparison_report_tv_avg_skip_fail_on_min(), test_generate_comparison_report_tv_avg_skip_pass_on_min(), test_generate_comparison_report_tv_contrast_tolerance_scenarios()

### Community 15 - "create_html_report"
Cohesion: 0.14
Nodes (8): Added, Changed, create_html_report(), prepare_device_plot_coordinates(), prepare_specification_plot_coordinates(), test_create_html_report(), test_create_html_report_returns_false_on_missing_expected_yaml(), test_create_html_report_returns_true_on_success()

### Community 16 - "SvgCoordinator"
Cohesion: 0.18
Nodes (5): [1.2.5] - 2026-07-22, Added, Changed, Fixed, SvgCoordinator

### Community 17 - "validate_device_configs.py"
Cohesion: 0.35
Nodes (9): check_coordinate_entry(), check_filename(), check_metric_dict(), collect_config_files(), is_none_marker(), is_number(), load_yaml(), main() (+1 more)

### Community 18 - "Changelog"
Cohesion: 0.18
Nodes (10): [1.0.0], [1.1.0] - 2026-01-23, [1.2.4] - 2026-07-17, [1.3.0] - 2026-08-12, Added, Changed, Changelog, Fixed (+2 more)

### Community 19 - "cg_uv"
Cohesion: 0.25
Nodes (6): Added, cg_uv(), coords_xy_to_uv(), _std_to_uv_flat(), xy_to_uv(), test_coords_xy_to_uv_format()

### Community 20 - "check_general_test_status"
Cohesion: 0.20
Nodes (6): [1.2.2] - 2026-06-25, Added, check_general_test_status(), test_corporate_contrast_skip_not_applied_for_other_devices(), test_corporate_contrast_skip_not_applied_for_tv(), test_corporate_tolerance_not_applied_for_tv()

### Community 21 - "conftest.py"
Cohesion: 0.27
Nodes (4): mock_black_lv(), mock_display_data(), mock_tv_data(), mock_yaml_data()

### Community 22 - "expand_coordinates_tolerance"
Cohesion: 0.20
Nodes (5): expand_coordinates_tolerance(), test_expand_coordinates_tolerance_applies_tolerance(), test_expand_coordinates_tolerance_no_tolerance_key(), test_expand_coordinates_tolerance_removes_key_from_result(), test_expand_coordinates_tolerance_skips_entries_with_explicit_min_max()

### Community 23 - "_get_cell_status"
Cohesion: 0.29
Nodes (4): [1.1.4] - 2026-01-30, Fixed, _get_cell_status(), test_get_cell_status_dcip3()

### Community 24 - "brightness"
Cohesion: 0.33
Nodes (3): brightness(), test_brightness_empty_report(), test_brightness_logic_tv()

### Community 25 - "contrast"
Cohesion: 0.33
Nodes (3): contrast(), test_contrast_logic(), test_contrast_zero_lv()

### Community 26 - "_corporate_adjusted"
Cohesion: 0.33
Nodes (3): _corporate_adjusted(), test_corporate_cg_tolerance_adjusted_typ_is_rounded(), test_corporate_typ_tolerance_adjusted_typ_is_rounded()

### Community 27 - "temperature"
Cohesion: 0.40
Nodes (3): temperature(), test_temperature_extraction(), test_temperature_missing_data()

### Community 28 - "get_inspection_date_range"
Cohesion: 0.50
Nodes (3): get_day_suffix(), get_inspection_date_range(), format_date()

### Community 29 - "json_report"
Cohesion: 0.40
Nodes (3): json_report(), test_json_report_includes_rec2020(), test_json_report_returns_dict()

### Community 30 - "[1.1.2] - 2026-01-29"
Cohesion: 0.50
Nodes (4): [1.1.2] - 2026-01-29, Added, Changed, Fixed

### Community 31 - "safe_round"
Cohesion: 0.50
Nodes (3): [1.2.1] - 2026-05-29, Fixed, safe_round()

### Community 32 - "Brightness"
Cohesion: 0.50
Nodes (4): Brightness, max, min, typ

### Community 33 - "Brightness_uniformity"
Cohesion: 0.50
Nodes (4): Brightness_uniformity, max, min, typ

### Community 34 - "Cg_dcip3"
Cohesion: 0.50
Nodes (4): Cg_dcip3, max, min, typ

### Community 35 - "Cg_dcip3_area"
Cohesion: 0.50
Nodes (4): Cg_dcip3_area, max, min, typ

### Community 36 - "Cg_dcip3_uv"
Cohesion: 0.50
Nodes (4): Cg_dcip3_uv, max, min, typ

### Community 37 - "Cg_dcip3_uv_area"
Cohesion: 0.50
Nodes (4): Cg_dcip3_uv_area, max, min, typ

### Community 38 - "Cg_ntsc"
Cohesion: 0.50
Nodes (4): Cg_ntsc, max, min, typ

### Community 39 - "Cg_ntsc_area"
Cohesion: 0.50
Nodes (4): Cg_ntsc_area, max, min, typ

### Community 40 - "Cg_ntsc_uv"
Cohesion: 0.50
Nodes (4): Cg_ntsc_uv, max, min, typ

### Community 41 - "Cg_ntsc_uv_area"
Cohesion: 0.50
Nodes (4): Cg_ntsc_uv_area, max, min, typ

### Community 42 - "Cg_rec2020"
Cohesion: 0.50
Nodes (4): Cg_rec2020, max, min, typ

### Community 43 - "Cg_rec2020_area"
Cohesion: 0.50
Nodes (4): Cg_rec2020_area, max, min, typ

### Community 44 - "Cg_rec2020_uv"
Cohesion: 0.50
Nodes (4): Cg_rec2020_uv, max, min, typ

### Community 45 - "Cg_rec2020_uv_area"
Cohesion: 0.50
Nodes (4): Cg_rec2020_uv_area, max, min, typ

### Community 46 - "Cg_rgb"
Cohesion: 0.50
Nodes (4): Cg_rgb, max, min, typ

### Community 47 - "Cg_rgb_area"
Cohesion: 0.50
Nodes (4): Cg_rgb_area, max, min, typ

### Community 48 - "Cg_rgb_uv"
Cohesion: 0.50
Nodes (4): Cg_rgb_uv, max, min, typ

### Community 49 - "Cg_rgb_uv_area"
Cohesion: 0.50
Nodes (4): Cg_rgb_uv_area, max, min, typ

### Community 50 - "Contrast"
Cohesion: 0.50
Nodes (4): Contrast, max, min, typ

### Community 51 - "Delta_e"
Cohesion: 0.50
Nodes (4): Delta_e, max, min, typ

### Community 52 - "Temperature"
Cohesion: 0.50
Nodes (4): Temperature, max, min, typ

### Community 53 - "[1.1.1] - 2026-01-26"
Cohesion: 0.67
Nodes (3): [1.1.1] - 2026-01-26, Changed, Fixed

### Community 54 - "[1.1.3] - 2026-01-29"
Cohesion: 0.67
Nodes (3): [1.1.3] - 2026-01-29, Changed, Removed

### Community 55 - "[1.2.3] - 2026-06-29"
Cohesion: 0.67
Nodes (3): [1.2.3] - 2026-06-29, Changed, Fixed

### Community 56 - "[1.4.0] - 2026-09-09"
Cohesion: 0.67
Nodes (3): [1.4.0] - 2026-09-09, Added, Fixed

## Knowledge Gaps
- **1 isolated node(s):** `report-generator`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 295 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Module Responsibilities` connect `Module Responsibilities` to `parse.py`, `json`, `CLAUDE.md`, `process_device_reports`, `SvgCoordinator`, `check_general_test_status`, `_get_cell_status`, `brightness`, `contrast`, `temperature`, `json_report`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `create_html_report()` (e.g. with `Added` and `Changed`) actually correct?**
  _`create_html_report()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `report-generator` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `release_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.050724637681159424 - nodes in this community are weakly interconnected._
- **Why does `create_html_report()` connect `create_html_report` to `release_manager.py`, `json`, `_should_display_metric`, `process_device_reports`, `test_helpers.py`, `Return Value Tests (Added 2025-01-23)`, `SvgCoordinator`, `expand_coordinates_tolerance`, `get_inspection_date_range`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `generate_comparison_report()` (e.g. with `Added` and `Changed`) actually correct?**
  _`generate_comparison_report()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_calculate.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10052910052910052 - nodes in this community are weakly interconnected._