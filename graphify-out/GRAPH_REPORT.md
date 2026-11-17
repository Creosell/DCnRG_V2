# Graph Report - DCnRG_V2  (2026-11-17)

## Corpus Check
- 112 files · ~49,159 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 3, .example 1, .spec 1)

## Summary
- 648 nodes · 1104 edges · 55 communities (46 shown, 9 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 88 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8daf0e9f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_calculate.py
- test_parse.py
- json
- calculate_full_report
- CLAUDE.md
- _should_display_metric
- Report Generator
- test_helpers.py
- Changelog
- calculate.py
- configuration_example.yaml
- parametrize
- excel_converter.py
- safe_round
- process_main_report
- SvgCoordinator
- main
- get_inspection_date_range
- test_rec2020_registered_in_gamut_key_sets
- yaml
- conftest.py
- is_effectively_all_null_stat_package
- expand_coordinates_tolerance
- create_html_report
- generate_comparison_report
- collect_tolerance_legend
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
- set_nested_value
- report-generator

## God Nodes (most connected - your core abstractions)
1. `create_html_report()` - 26 edges
2. `generate_comparison_report()` - 24 edges
3. `Module Responsibilities` - 20 edges
4. `run_calculations()` - 19 edges
5. `Changelog` - 18 edges
6. `main()` - 15 edges
7. `check_general_test_status()` - 14 edges
8. `process_device_reports()` - 14 edges
9. `Return Value Tests (Added 2025-01-23)` - 14 edges
10. `calculate_full_report()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Changed` --references--> `delta_e()`  [INFERRED]
  CHANGELOG.md → src/calculate.py
- `Сквозной workflow` --references--> `delta_e()`  [INFERRED]
  .claude/skills/excel-converter/SKILL.md → src/calculate.py
- `Fixed` --references--> `coordinates_of_triangle()`  [INFERRED]
  CHANGELOG.md → src/parse.py
- `Fixed` --references--> `safe_round()`  [INFERRED]
  CHANGELOG.md → src/report.py
- `Removed` --references--> `create_html_report()`  [INFERRED]
  CHANGELOG.md → src/helpers.py

## Import Cycles
- None detected.

## Communities (55 total, 9 thin omitted)

### Community 1 - "test_calculate.py"
Cohesion: 0.05
Nodes (29): Module Responsibilities, black_luminance(), brightness(), brightness_uniformity(), contrast(), delta_e(), run_calculations(), temperature() (+21 more)

### Community 2 - "test_parse.py"
Cohesion: 0.06
Nodes (23): [1.2.0] - 2026-05-06, [1.2.4] - 2026-07-17, Breaking Changes, Changed, Changed, Fixed, Fixed, Removed (+15 more)

### Community 3 - "json"
Cohesion: 0.16
Nodes (8): Return Value Tests (Added 2025-01-23), load_json_file(), write_error_report(), test_create_html_report_returns_false_on_missing_expected_yaml(), test_create_html_report_returns_false_on_template_load_error(), test_create_html_report_returns_true_on_success(), test_generate_comparison_report_returns_false_on_missing_expected_file(), test_generate_comparison_report_returns_true_on_success()

### Community 4 - "calculate_full_report"
Cohesion: 0.18
Nodes (8): Changed, calculate_full_report(), process_items(), create_mock_device_report_dict(), test_calculate_full_report_aggregator_logic(), test_calculate_full_report_handles_bad_data(), test_calculate_full_report_returns_false_on_write_error(), test_calculate_full_report_returns_true_on_success()

### Community 5 - "CLAUDE.md"
Cohesion: 0.09
Nodes (21): Architecture Overview, Building Executable, Common Pitfalls & Solutions, Configuration Files, Data Flow Pipeline, Dependencies, Development Commands, Error Handling & Return Values (+13 more)

### Community 6 - "_should_display_metric"
Cohesion: 0.12
Nodes (10): [1.1.2] - 2026-01-29, Added, Changed, Fixed, _has_gamut_spec(), _should_display_metric(), test_should_display_metric(), test_should_display_metric_dcip3() (+2 more)

### Community 7 - "Report Generator"
Cohesion: 0.10
Nodes (19): 1. Create local environment, 2\. Activation of venv, 3\. Install dependencies, Color coordinate tolerance, Command Syntax, Device Configuration, Dynamic visibility, Environment Setup (+11 more)

### Community 8 - "test_helpers.py"
Cohesion: 0.15
Nodes (9): get_colorimeter_summary(), process_device_reports(), _report_with(), test_black_luminance_column_follows_brightness(), test_black_luminance_missing_value_is_shown_as_dash(), test_colorimeter_summary_is_empty_for_legacy_reports(), test_colorimeter_summary_lists_unique_devices(), test_process_device_reports() (+1 more)

### Community 9 - "Changelog"
Cohesion: 0.05
Nodes (39): [1.0.0], [1.1.0] - 2026-01-23, [1.1.1] - 2026-01-26, [1.1.3] - 2026-01-29, [1.1.4] - 2026-01-30, [1.2.1] - 2026-05-29, [1.2.2] - 2026-06-25, [1.2.3] - 2026-06-29 (+31 more)

### Community 10 - "calculate.py"
Cohesion: 0.07
Nodes (22): Added, Changed, Important Implementation Details, Известные ограничения данных, ExitCode, area(), calculate_overlap_percentage(), cg() (+14 more)

### Community 11 - "configuration_example.yaml"
Cohesion: 0.11
Nodes (17): Blue_x, typ, Blue_y, typ, Coordinates_tolerance, Green_x, typ, Green_y (+9 more)

### Community 12 - "parametrize"
Cohesion: 0.18
Nodes (5): test_corporate_contrast_skip_typ_fail_on_min(), test_corporate_contrast_skip_typ_pass_on_min(), test_generate_comparison_report_tv_avg_skip_fail_on_min(), test_generate_comparison_report_tv_avg_skip_pass_on_min(), test_generate_comparison_report_tv_contrast_tolerance_scenarios()

### Community 13 - "excel_converter.py"
Cohesion: 0.06
Nodes (33): Формат листа "9 points" (для доработки/отладки скрипта), resolve_expected_yaml(), build_expected_yaml(), _build_report(), convert(), _device_name_from_filename(), extract_expected(), _extract_sample() (+25 more)

### Community 14 - "safe_round"
Cohesion: 0.15
Nodes (8): safe_round(), _corporate_adjusted(), test_cg_metric_keys_include_all_registered_color_spaces(), test_corporate_cg_tolerance_adjusted_typ_is_rounded(), test_corporate_typ_tolerance_adjusted_typ_is_rounded(), test_safe_round_half_up(), test_safe_round_non_numeric_unchanged(), test_safe_round_numpy_float()

### Community 15 - "process_main_report"
Cohesion: 0.22
Nodes (5): Changed, process_main_report(), test_process_main_report(), test_process_main_report_dynamic_cg_filter(), test_process_main_report_dynamic_dcip3_filter()

### Community 16 - "SvgCoordinator"
Cohesion: 0.18
Nodes (5): [1.2.5] - 2026-07-22, Added, Changed, Fixed, SvgCoordinator

### Community 17 - "main"
Cohesion: 0.07
Nodes (17): `data/` — важные нюансы, Excel Converter ("9 points" sheet → data/*.json → report), Когда использовать, Сквозной workflow, ensure_directories(), main(), parse_args(), setup_logging() (+9 more)

### Community 18 - "get_inspection_date_range"
Cohesion: 0.50
Nodes (3): get_day_suffix(), get_inspection_date_range(), format_date()

### Community 20 - "yaml"
Cohesion: 0.18
Nodes (5): load_yaml_file(), test_generate_comparison_report_corporate_dcip3_tolerance(), test_generate_comparison_report_logic(), test_generate_comparison_report_temperature_ignores_typ(), test_generate_comparison_report_tv_temperature_max_check()

### Community 21 - "conftest.py"
Cohesion: 0.27
Nodes (4): mock_black_lv(), mock_display_data(), mock_tv_data(), mock_yaml_data()

### Community 24 - "expand_coordinates_tolerance"
Cohesion: 0.20
Nodes (5): expand_coordinates_tolerance(), test_expand_coordinates_tolerance_applies_tolerance(), test_expand_coordinates_tolerance_no_tolerance_key(), test_expand_coordinates_tolerance_removes_key_from_result(), test_expand_coordinates_tolerance_skips_entries_with_explicit_min_max()

### Community 27 - "create_html_report"
Cohesion: 0.15
Nodes (7): Added, create_html_report(), prepare_device_plot_coordinates(), prepare_specification_plot_coordinates(), test_create_html_report(), test_create_html_report_plot_triangles_checked(), test_create_html_report_returns_false_on_missing_input_file()

### Community 28 - "generate_comparison_report"
Cohesion: 0.14
Nodes (8): Added, check_general_test_status(), generate_comparison_report(), test_corporate_contrast_skip_not_applied_for_other_devices(), test_corporate_contrast_skip_not_applied_for_tv(), test_corporate_tolerance_not_applied_for_tv(), test_generate_comparison_report_min_violation_takes_priority_over_typ(), test_generate_comparison_report_returns_false_on_missing_actual_file()

### Community 30 - "collect_tolerance_legend"
Cohesion: 0.33
Nodes (3): collect_tolerance_legend(), test_collect_tolerance_legend(), test_collect_tolerance_legend_empty()

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

### Community 54 - "set_nested_value"
Cohesion: 0.33
Nodes (3): set_nested_value(), test_set_nested_value_merge_dict(), test_set_nested_value_new_path()

## Knowledge Gaps
- **1 isolated node(s):** `report-generator`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 325 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Module Responsibilities` connect `test_calculate.py` to `test_parse.py`, `CLAUDE.md`, `test_helpers.py`, `Changelog`, `calculate.py`, `SvgCoordinator`, `main`, `generate_comparison_report`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `create_html_report()` (e.g. with `Added` and `Changed`) actually correct?**
  _`create_html_report()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `report-generator` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_calculate.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05384150030248034 - nodes in this community are weakly interconnected._
- **Why does `Changelog` connect `Changelog` to `SvgCoordinator`, `test_parse.py`, `_should_display_metric`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `generate_comparison_report()` (e.g. with `Added` and `Changed`) actually correct?**
  _`generate_comparison_report()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_parse.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06006006006006006 - nodes in this community are weakly interconnected._