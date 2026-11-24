# Graph Report - DCnRG_V2  (2026-11-24)

## Corpus Check
- 154 files · ~93,809 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 4, .lock 2, .in 1)

## Summary
- 856 nodes · 1580 edges · 80 communities (66 shown, 14 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e4c2fc31`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- release_manager.py
- _should_display_metric
- test_attempts_stats.py
- calculate_full_report
- CLAUDE.md
- safe_round
- Report Generator
- process_device_reports
- Changelog
- calculate.py
- configuration_example.yaml
- test_evaluate.py
- evaluate.py
- report.py
- brightness
- expand_coordinates_tolerance
- cg_uv
- excel_converter.py
- Module Responsibilities
- Return Value Tests (Added 2025-01-23)
- conftest.py
- black_luminance
- set_nested_value
- _Metric
- make_attempts_real_demo.py
- get_coordinates
- main.py
- is_effectively_all_null_stat_package
- yaml
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
- create_html_report
- make_attempts_demo.py
- report.py
- paths.py
- report-generator
- pytest
- SvgCoordinator
- _parse_spec_value
- required_locations
- get_cell_status
- ColorSpace
- contrast
- process_main_report
- temperature
- collect_tolerance_legend
- [1.2.5] - 2026-07-22
- [1.4.3] - 2026-11-16
- delta_e
- _check
- [1.1.3] - 2026-01-29
- [1.2.3] - 2026-06-29
- [1.4.0] - 2026-09-09
- [1.5.0] - 2026-11-17

## God Nodes (most connected - your core abstractions)
1. `create_html_report()` - 29 edges
2. `evaluate()` - 26 edges
3. `Module Responsibilities` - 24 edges
4. `generate_comparison_report()` - 24 edges
5. `run_calculations()` - 22 edges
6. `Changelog` - 20 edges
7. `device()` - 17 edges
8. `main()` - 16 edges
9. `process_device_reports()` - 16 edges
10. `attempt()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Added` --references--> `SvgCoordinator`  [INFERRED]
  CHANGELOG.md → src/graphics_helper.py
- `Changed` --references--> `delta_e()`  [INFERRED]
  CHANGELOG.md → src/calculate.py
- `Сквозной workflow` --references--> `delta_e()`  [INFERRED]
  .claude/skills/excel-converter/SKILL.md → src/calculate.py
- `Fixed` --references--> `coordinates_of_triangle()`  [INFERRED]
  CHANGELOG.md → src/parse.py
- `Removed` --references--> `create_html_report()`  [INFERRED]
  CHANGELOG.md → src/helpers.py

## Import Cycles
- None detected.

## Communities (80 total, 14 thin omitted)

### Community 1 - "release_manager.py"
Cohesion: 0.11
Nodes (12): ensure_remote_dir(), get_nc_client(), get_sha256(), list_store_blobs(), main(), prepare_package(), store_path(), upload_all() (+4 more)

### Community 2 - "_should_display_metric"
Cohesion: 0.13
Nodes (9): [1.1.2] - 2026-01-29, Added, Changed, Fixed, _has_gamut_spec(), _should_display_metric(), test_should_display_metric_dcip3(), test_should_display_metric_delta_e() (+1 more)

### Community 3 - "test_attempts_stats.py"
Cohesion: 0.09
Nodes (36): [1.1.4] - 2026-01-30, [1.2.2] - 2026-06-25, Added, Fixed, build_attempts_stats(), check_general_test_status(), attempt(), build() (+28 more)

### Community 4 - "calculate_full_report"
Cohesion: 0.14
Nodes (11): [1.1.0] - 2026-01-23, Added, Changed, Fixed, calculate_full_report(), process_items(), create_mock_device_report_dict(), test_calculate_full_report_aggregator_logic() (+3 more)

### Community 5 - "CLAUDE.md"
Cohesion: 0.09
Nodes (21): Architecture Overview, Building Executable, Common Pitfalls & Solutions, Configuration Files, Data Flow Pipeline, Dependencies, Development Commands, Error Handling & Return Values (+13 more)

### Community 6 - "safe_round"
Cohesion: 0.25
Nodes (4): safe_round(), test_safe_round_half_up(), test_safe_round_non_numeric_unchanged(), test_safe_round_numpy_float()

### Community 7 - "Report Generator"
Cohesion: 0.09
Nodes (21): 1. Create local environment, 2\. Activation of venv, 3\. Install dependencies, Color coordinate tolerance, Command Syntax, Device Configuration, Dynamic visibility, Environment Setup (+13 more)

### Community 8 - "process_device_reports"
Cohesion: 0.11
Nodes (12): get_colorimeter_summary(), process_device_reports(), _report_with(), test_black_luminance_column_follows_brightness(), test_black_luminance_missing_value_is_shown_as_dash(), test_clear_specific_files(), test_colorimeter_summary_is_empty_for_legacy_reports(), test_colorimeter_summary_lists_unique_devices() (+4 more)

### Community 9 - "Changelog"
Cohesion: 0.13
Nodes (14): [1.0.0], [1.1.1] - 2026-01-26, [1.2.1] - 2026-05-29, [1.4.1] - 2026-11-09, [1.4.2] - 2026-11-16, [1.5.1] - 2026-11-23, Added, Changed (+6 more)

### Community 10 - "calculate.py"
Cohesion: 0.17
Nodes (6): area(), calculate_overlap_percentage(), cg_by_area_uv(), _std_to_uv_flat(), _std_to_uv_triangle(), test_area_valid_triangle()

### Community 11 - "configuration_example.yaml"
Cohesion: 0.11
Nodes (17): Blue_x, typ, Blue_y, typ, Coordinates_tolerance, Green_x, typ, Green_y (+9 more)

### Community 12 - "test_evaluate.py"
Cohesion: 0.06
Nodes (45): _attempts_of(), best_attempt_index(), evaluate(), _flat_results(), resolve_attempts(), verdict_of(), json_report(), attempt() (+37 more)

### Community 13 - "evaluate.py"
Cohesion: 0.23
Nodes (6): _attempt_status_rank(), _attempt_value(), score(), _is_number(), _measured_locations(), _typ_distance()

### Community 14 - "report.py"
Cohesion: 0.08
Nodes (16): check_coordinate_bounds(), generate_comparison_report(), load_json_file(), write_error_report(), test_cg_metric_keys_include_all_registered_color_spaces(), test_generate_comparison_report_corporate_dcip3_tolerance(), test_generate_comparison_report_logic(), test_generate_comparison_report_min_violation_takes_priority_over_typ() (+8 more)

### Community 15 - "brightness"
Cohesion: 0.25
Nodes (4): brightness(), test_brightness_empty_report(), test_brightness_logic_display(), test_brightness_logic_tv()

### Community 16 - "expand_coordinates_tolerance"
Cohesion: 0.20
Nodes (5): expand_coordinates_tolerance(), test_expand_coordinates_tolerance_applies_tolerance(), test_expand_coordinates_tolerance_no_tolerance_key(), test_expand_coordinates_tolerance_removes_key_from_result(), test_expand_coordinates_tolerance_skips_entries_with_explicit_min_max()

### Community 17 - "cg_uv"
Cohesion: 0.28
Nodes (5): Added, coords_xy_to_uv(), xy_to_uv(), test_coords_xy_to_uv_format(), test_xy_to_uv_known_values()

### Community 18 - "excel_converter.py"
Cohesion: 0.09
Nodes (25): Формат листа "9 points" (для доработки/отладки скрипта), build_expected_yaml(), _build_report(), convert(), _device_name_from_filename(), extract_expected(), _extract_sample(), _fmt() (+17 more)

### Community 19 - "Module Responsibilities"
Cohesion: 0.38
Nodes (9): Changed, Important Implementation Details, Module Responsibilities, Известные ограничения данных, cg(), cg_by_area(), cg_uv(), run_calculations() (+1 more)

### Community 20 - "Return Value Tests (Added 2025-01-23)"
Cohesion: 0.14
Nodes (8): Return Value Tests (Added 2025-01-23), Testing, test_create_html_report_returns_false_on_missing_input_file(), test_create_html_report_returns_false_on_template_load_error(), test_create_html_report_returns_true_on_success(), test_get_cell_status(), test_process_device_reports_with_cell_status(), test_should_display_metric()

### Community 21 - "conftest.py"
Cohesion: 0.19
Nodes (7): mock_black_lv(), mock_display_data(), mock_tv_data(), mock_yaml_data(), configs(), app_main(), spec_dir()

### Community 22 - "black_luminance"
Cohesion: 0.15
Nodes (7): black_luminance(), test_black_luminance_invalid_lv_returns_none(), test_black_luminance_missing_black_color_returns_none(), test_black_luminance_returns_black_color_lv(), test_calculate_overlap_percentage_invalid_triangle(), test_cg_returns_none_on_dci_p3_overlap_error(), test_run_calculations_handles_error()

### Community 23 - "set_nested_value"
Cohesion: 0.33
Nodes (3): set_nested_value(), test_set_nested_value_merge_dict(), test_set_nested_value_new_path()

### Community 24 - "_Metric"
Cohesion: 0.13
Nodes (5): _Metric, _outcome(), _scale(), _strip_svg(), _verdict()

### Community 26 - "make_attempts_real_demo.py"
Cohesion: 0.21
Nodes (7): generate_report(), build_devices(), by_location(), load_batch(), main(), number(), usable()

### Community 27 - "get_coordinates"
Cohesion: 0.14
Nodes (10): [1.2.4] - 2026-07-17, Changed, Fixed, Excel Converter ("9 points" sheet → data/*.json → report), Когда использовать, Связанный фикс в коде (уже в основной ветке, коммит `f561c64`), Сквозной workflow, get_coordinates() (+2 more)

### Community 28 - "main.py"
Cohesion: 0.06
Nodes (24): [1.3.0] - 2026-08-12, Added, Fixed, `data/` — важные нюансы, ensure_directories(), ExitCode, main(), parse_args() (+16 more)

### Community 31 - "yaml"
Cohesion: 0.17
Nodes (8): find_closest_to_target(), get_device_info(), parse_one_file(), test_find_closest_to_target(), test_get_device_info_failure(), test_get_device_info_success(), test_parse_one_file_failure(), test_parse_one_file_success()

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

### Community 53 - "create_html_report"
Cohesion: 0.14
Nodes (8): Added, create_html_report(), prepare_device_plot_coordinates(), prepare_specification_plot_coordinates(), create(), test_create_html_report(), test_create_html_report_plot_triangles_checked(), test_create_html_report_returns_false_on_missing_expected_yaml()

### Community 54 - "make_attempts_demo.py"
Cohesion: 0.24
Nodes (10): attempt(), base_points(), best_index(), black(), color(), grid(), main(), prepare_config() (+2 more)

### Community 55 - "report.py"
Cohesion: 0.22
Nodes (5): parse_yaml(), load_yaml_file(), test_parse_yaml_success(), test_a_value_is_judged_as_it_is_shown(), test_every_metric_of_the_example_specification_has_an_explicit_precision()

### Community 56 - "paths.py"
Cohesion: 0.25
Nodes (5): resolve_root(), test_empty_sct_root_is_ignored(), test_frozen_build_uses_the_executable_folder(), test_script_run_uses_the_current_directory(), test_sct_root_has_the_highest_priority()

### Community 60 - "pytest"
Cohesion: 0.13
Nodes (7): brightness_uniformity(), test_brightness_uniformity(), test_cg_by_area_logic(), test_run_calculations_fulltest(), test_run_calculations_includes_black_luminance(), test_coordinates_of_triangle_missing_color(), test_coordinates_of_triangle_success()

### Community 64 - "required_locations"
Cohesion: 0.33
Nodes (4): Added, required_locations(), _single_point_keys(), test_required_locations()

### Community 66 - "ColorSpace"
Cohesion: 0.22
Nodes (4): ColorSpace, test_cg_by_area_uv_returns_values(), test_cg_overlap_dcip3_value(), test_cg_uv_returns_values()

### Community 67 - "contrast"
Cohesion: 0.33
Nodes (3): contrast(), test_contrast_logic(), test_contrast_zero_lv()

### Community 69 - "process_main_report"
Cohesion: 0.14
Nodes (10): [1.2.0] - 2026-05-06, Breaking Changes, Changed, Changed, Fixed, Removed, process_main_report(), test_process_main_report() (+2 more)

### Community 70 - "temperature"
Cohesion: 0.40
Nodes (3): temperature(), test_temperature_extraction(), test_temperature_missing_data()

### Community 71 - "collect_tolerance_legend"
Cohesion: 0.33
Nodes (3): collect_tolerance_legend(), test_collect_tolerance_legend(), test_collect_tolerance_legend_empty()

### Community 72 - "[1.2.5] - 2026-07-22"
Cohesion: 0.50
Nodes (4): [1.2.5] - 2026-07-22, Added, Changed, Fixed

### Community 73 - "[1.4.3] - 2026-11-16"
Cohesion: 0.50
Nodes (4): [1.4.3] - 2026-11-16, Added, Changed, Fixed

### Community 76 - "[1.1.3] - 2026-01-29"
Cohesion: 0.67
Nodes (3): [1.1.3] - 2026-01-29, Changed, Removed

### Community 77 - "[1.2.3] - 2026-06-29"
Cohesion: 0.67
Nodes (3): [1.2.3] - 2026-06-29, Changed, Fixed

### Community 78 - "[1.4.0] - 2026-09-09"
Cohesion: 0.67
Nodes (3): [1.4.0] - 2026-09-09, Added, Fixed

### Community 79 - "[1.5.0] - 2026-11-17"
Cohesion: 0.67
Nodes (3): [1.5.0] - 2026-11-17, Changed, Fixed

## Knowledge Gaps
- **1 isolated node(s):** `report-generator`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 392 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Module Responsibilities` connect `Module Responsibilities` to `required_locations`, `get_cell_status`, `contrast`, `test_attempts_stats.py`, `CLAUDE.md`, `temperature`, `process_device_reports`, `delta_e`, `test_evaluate.py`, `pytest`, `brightness`, `report.py`, `get_coordinates`, `main.py`, `SvgCoordinator`, `yaml`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `create_html_report()` (e.g. with `Added` and `Changed`) actually correct?**
  _`create_html_report()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `report-generator` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `release_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11375661375661375 - nodes in this community are weakly interconnected._
- **Why does `Changelog` connect `Changelog` to `_should_display_metric`, `test_attempts_stats.py`, `calculate_full_report`, `process_main_report`, `[1.2.5] - 2026-07-22`, `[1.4.3] - 2026-11-16`, `[1.1.3] - 2026-01-29`, `[1.2.3] - 2026-06-29`, `[1.4.0] - 2026-09-09`, `[1.5.0] - 2026-11-17`, `get_coordinates`, `main.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Module Responsibilities` (e.g. with `run_evaluate()` and `brightness()`) actually correct?**
  _`Module Responsibilities` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Should `_should_display_metric` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._