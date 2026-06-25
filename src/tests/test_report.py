# tests/test_report.py

import json
from pathlib import Path
import yaml  # Make sure yaml is imported
import pytest

from src import report


# --------------------------------------------------------------------------------
# Helper Functions & Unchanged Tests
# --------------------------------------------------------------------------------

def test_set_nested_value_new_path():
    """Tests creating a new nested dictionary path."""
    d = {}
    report.set_nested_value(d, "Results.Brightness.min", 80.0)
    assert d["Results"]["Brightness"]["min"] == 80.0


def test_set_nested_value_merge_dict():
    """Tests merging (update) dictionaries at the final level."""
    d = {"Results": {"Brightness": {"min": 90.0}}}
    new_data = {"avg": 100.0, "max": 110.0}
    report.set_nested_value(d, "Results.Brightness", new_data)
    # min should remain, avg and max should be added
    assert d["Results"]["Brightness"] == {"min": 90.0, "avg": 100.0, "max": 110.0}


def test_is_effectively_all_null_stat_package():
    """Tests the check for an 'empty' statistics package."""
    # All None (should be True)
    assert report.is_effectively_all_null_stat_package({"avg": None, "min": None, "max": None}) is True
    # List with None (should be True)
    assert report.is_effectively_all_null_stat_package({"avg": [None, None], "min": None, "max": None}) is True
    # Scalar (should be False)
    assert report.is_effectively_all_null_stat_package({"avg": 100.0, "min": None, "max": None}) is False
    # List with number (should be False)
    assert report.is_effectively_all_null_stat_package({"avg": [None, 100.0], "min": None, "max": None}) is False


def create_mock_device_report_dict(sn, value):
    """
    REFACTORED: Helper function to create a mock device report *dictionary*.
    This mimics the *return value* of report.json_report.
    """
    return {
        "SerialNumber": sn,
        "MeasurementDateTime": "20250101",
        "Results": {
            "Brightness": value,
            "ArrayData": [value, value + 5]
        }
    }


# --------------------------------------------------------------------------------
# REFACTORED Core Tests
# --------------------------------------------------------------------------------

def test_json_report_returns_dict():
    """
    REFACTORED: Tests that json_report *returns* a dictionary
    with the correct structure.
    """
    report_data = report.json_report(
        sn="SN001",
        t="Time001",
        is_tv=False,
        brightness=100.5,
        contrast=1000,
        device_name="TestDevice"
    )

    # Check the returned dictionary
    assert report_data["SerialNumber"] == "SN001"
    assert report_data["Results"]["Brightness"] == 100.5
    assert report_data["Results"]["Contrast"] == 1000
    assert report_data["Results"]["DeltaE"] is None  # Not provided keys are None


def test_calculate_full_report_aggregator_logic(tmp_path):
    """
    REFACTORED: Tests the aggregator logic of calculate_full_report
    by passing it a list of report dictionaries.
    """
    # 1. Create mock input data (list of dictionaries)
    reports_list = [
        create_mock_device_report_dict("SN1", 100.0),
        create_mock_device_report_dict("SN2", 120.0),
        create_mock_device_report_dict("SN3", 110.0),
    ]

    output_file = tmp_path / "full_report.json"

    # 2. Call the function with the list
    report.calculate_full_report(
        device_reports=reports_list,
        output_file=str(output_file),
        device_name="Monitor"
    )

    # 3. Check the results in the output file
    with open(output_file, "r") as f:
        result_data = json.load(f)

    # Expectations: 100.0, 120.0, 110.0 -> Min: 100.0, Max: 120.0, Avg: 110.0

    # Check scalar stats (Brightness)
    brightness_stats = result_data["Results"]["Brightness"]
    assert brightness_stats["min"] == pytest.approx(100.0)
    assert brightness_stats["max"] == pytest.approx(120.0)
    assert brightness_stats["avg"] == pytest.approx(110.0)

    # Check list stats (ArrayData)
    # [100.0, 105.0], [120.0, 125.0], [110.0, 115.0]
    # Min: [100.0, 105.0], Max: [120.0, 125.0], Avg: [110.0, 115.0]
    array_stats = result_data["Results"]["ArrayData"]
    assert array_stats["min"] == pytest.approx([100.0, 105.0])
    assert array_stats["max"] == pytest.approx([120.0, 125.0])
    assert array_stats["avg"] == pytest.approx([110.0, 115.0])


def test_calculate_full_report_handles_bad_data(tmp_path):
    """
    REFACTORED: Tests calculate_full_report with problematic dictionaries in the list.
    """
    reports_list = [
        {"SerialNumber": "SN1", "Results": None},  # 'Results' is None
        {"SerialNumber": "SN2"},  # Missing 'Results'
        create_mock_device_report_dict("SN3", 100.0)  # Good data
    ]

    output_file = tmp_path / "full_report.json"

    report.calculate_full_report(reports_list, str(output_file), "Monitor")

    with open(output_file, "r") as f:
        result = json.load(f)

    # Serial numbers are still collected
    assert sorted(result["SerialNumber"]) == ["SN1", "SN2", "SN3"]
    # Only data from SN3 is aggregated
    assert result["Results"]["Brightness"]["avg"] == 100.0


def test_generate_comparison_report_logic(tmp_path, mock_yaml_data):
    """
    Tests the main logic (PASS/FAIL/N/A) of generate_comparison_report.
    """
    # 1. Create JSON with aggregated results
    full_report_data = {
        "Results": {
            "Brightness": {"avg": 110.0, "min": 85.0},
            "Temperature": {"avg": 6900, "max": 7000, "min": 6000},
            "Coordinates": {
                "Red_x": {"min": 0.61, "max": 0.65}
            }
        }
    }
    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    # 2. Create YAML with expectations
    # Temperature: only min/max should be checked, typ should be ignored
    mock_yaml_data["Temperature"]["min"] = 5500.0
    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        # Use yaml.safe_dump, not json.dump
        yaml.safe_dump(mock_yaml_data, f)

        # 3. Create mock device list
    mock_devices_list = [
        {"SerialNumber": "SN1", "Results": {"Brightness": 110}},
        {"SerialNumber": "SN2", "Results": {"Brightness": 112}}
    ]

    # 4. Run comparison
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(
        actual_result_file=str(json_file),
        expected_result_file=str(yaml_file),
        output_json_file=str(output_file),
        is_tv_flag=False,
        device_reports=mock_devices_list  # Pass the new argument
    )

    # 5. Check result
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result["Brightness"]["status"] == "PASS"
    # For monitors, -5% tolerance is applied to Brightness typ (100 -> 95)
    assert "Actual avg (110.0) >= Expected typ (95.0)" in result["Brightness"]["reason"]
    assert result["Brightness"]["tolerance_applied"]["percent"] == 5
    assert result["Brightness"]["tolerance_applied"]["original_typ"] == 100.0
    assert result["Brightness"]["tolerance_applied"]["adjusted_typ"] == 95.0

    assert result["Temperature"]["status"] == "FAIL"
    assert "Actual max (7000) > Expected max (6800.0)" in result["Temperature"]["reason"]

    assert result["Red_x"]["status"] == "FAIL"
    assert "Actual min (0.61) < Expected min (0.62)" in result["Red_x"]["reason"]

    assert result["White_x"]["status"] == "N/A"
    assert "is null or missing in JSON" in result["White_x"]["reason"]


def test_generate_comparison_report_min_violation_takes_priority_over_typ(tmp_path):
    """When avg is below both min and typ, the reason must cite the min violation, not typ."""
    full_report_data = {"Results": {"Brightness": {"avg": 251.0, "min": 240.0}}}
    yaml_data = {"Brightness": {"min": 260.0, "typ": 280.0}}

    json_file = tmp_path / "report.json"
    yaml_file = tmp_path / "expected.yaml"
    output_file = tmp_path / "comparison.json"

    json_file.write_text(json.dumps(full_report_data))
    yaml_file.write_text("Brightness:\n  min: 260.0\n  typ: 280.0")

    report.generate_comparison_report(str(json_file), str(yaml_file), str(output_file), is_tv_flag=False, device_reports=[])

    with open(output_file) as f:
        result = json.load(f)

    assert result["Brightness"]["status"] == "FAIL"
    assert "Expected min" in result["Brightness"]["reason"]
    assert "Expected typ" not in result["Brightness"]["reason"]


@pytest.mark.parametrize(
    "actual_avg, expected_status, expected_reason_part",
    [
        # Case 1: Clear PASS. Average is above expected.
        (1100.0, "PASS", "Actual avg (1100.0) >= Expected typ (935.0)"),

        # Case 2: Boundary PASS. Average is exactly at the tolerance limit (1000 - 6.5% = 935).
        (935.0, "PASS", "Actual avg (935.0) >= Expected typ (935.0)"),

        # Case 3: Boundary FAIL. Average is just below the tolerance limit.
        (934.9, "FAIL", "Actual avg (934.9) < Expected typ (935.0)"),

        # Case 4: Clear FAIL. Average is well below tolerance.
        (900.0, "FAIL", "Actual avg (900.0) < Expected typ (935.0)"),
    ],
)
def test_generate_comparison_report_tv_contrast_tolerance_scenarios(
        tmp_path, mock_yaml_data, actual_avg, expected_status, expected_reason_part
):
    """
    Tests various scenarios (PASS/FAIL) for TV contrast tolerance.
    """
    # 1. Setup data
    full_report_data = {
        "Results": {"Contrast": {"avg": actual_avg, "min": 850.0}}  # min always passes
    }
    mock_yaml_data["Contrast"] = {"min": 800.0, "typ": 1000.0}

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        # Use yaml.safe_dump
        yaml.safe_dump(mock_yaml_data, f)

        # 2. Execution
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(
        str(json_file),
        str(yaml_file),
        str(output_file),
        is_tv_flag=True,
        # We need to pass the new arg here too, even if empty
        device_reports=[]
    )

    # 3. Check result
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result["Contrast"]["status"] == expected_status
    assert expected_reason_part in result["Contrast"]["reason"]


@pytest.mark.parametrize("skipped_key_yaml", [
    key for key in report.AVG_FAIL_SKIP_KEYS_FOR_TV if key != "Temperature"
])
def test_generate_comparison_report_tv_avg_skip_pass_on_min(
        tmp_path, mock_yaml_data, skipped_key_yaml
):
    """
    Checks that for all skipped keys (except Temperature), TV gets PASS
    if min is ok, even if avg is below expected.
    Temperature has separate test coverage due to its special logic.
    """
    # 1. Setup data
    # avg is below typ, but min is above threshold
    actual_values = {"avg": 90.0, "min": 85.0}
    expected_values = {"min": 80.0, "typ": 100.0}

    # Map YAML key (e.g., Cg_rgb_area) to JSON key (e.g., CgByAreaRGB)
    key_in_json = report.YAML_TO_JSON_KEY_MAP.get(skipped_key_yaml, skipped_key_yaml)

    full_report_data = {"Results": {key_in_json: actual_values}}
    mock_yaml_data[skipped_key_yaml] = expected_values

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    # 2. Run comparison
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(
        str(json_file),
        str(yaml_file),
        str(output_file),
        is_tv_flag=True,
        device_reports=[]
    )

    # 3. Check
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result[skipped_key_yaml]["status"] == "PASS"
    assert "(TV) Actual min (85.0) >= Expected min (80.0)" in result[skipped_key_yaml]["reason"]


@pytest.mark.parametrize("skipped_key_yaml", [
    key for key in report.AVG_FAIL_SKIP_KEYS_FOR_TV if key != "Temperature"
])
def test_generate_comparison_report_tv_avg_skip_fail_on_min(
        tmp_path, mock_yaml_data, skipped_key_yaml
):
    """
    Checks that for all skipped keys (except Temperature), TV gets FAIL
    if min is below threshold, despite skipping the avg check.
    Temperature has separate test coverage due to its special logic.
    """
    # 1. Setup data
    # avg is below typ, AND min is also below threshold
    actual_values = {"avg": 90.0, "min": 75.0}
    expected_values = {"min": 80.0, "typ": 100.0}

    key_in_json = report.YAML_TO_JSON_KEY_MAP.get(skipped_key_yaml, skipped_key_yaml)

    full_report_data = {"Results": {key_in_json: actual_values}}
    mock_yaml_data[skipped_key_yaml] = expected_values

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    # 2. Run comparison
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(
        str(json_file),
        str(yaml_file),
        str(output_file),
        is_tv_flag=True,
        device_reports=[]
    )

    # 3. Check
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result[skipped_key_yaml]["status"] == "FAIL"
    assert "Actual min (75.0) < Expected min (80.0)" in result[skipped_key_yaml]["reason"]


@pytest.mark.parametrize(
    "cg_yaml_key,actual_avg,expected_status",
    [
        # PASS: avg exactly at tolerance boundary (typ=100, -2% → 98)
        ("Cg_dcip3_area", 98.0, "PASS"),
        ("Cg_dcip3", 98.0, "PASS"),
        # FAIL: avg just below tolerance boundary
        ("Cg_dcip3_area", 97.9, "FAIL"),
        ("Cg_dcip3", 97.9, "FAIL"),
    ],
)
def test_generate_comparison_report_corporate_dcip3_tolerance(
        tmp_path, mock_yaml_data, cg_yaml_key, actual_avg, expected_status
):
    """
    Tests that non-TV devices get 2% CG tolerance for DCI-P3 metrics.
    typ=100 → adjusted_typ=98. Boundary PASS at 98.0, boundary FAIL at 97.9.
    """
    key_in_json = report.YAML_TO_JSON_KEY_MAP.get(cg_yaml_key, cg_yaml_key)

    full_report_data = {"Results": {key_in_json: {"avg": actual_avg, "min": 80.0}}}
    mock_yaml_data[cg_yaml_key] = {"min": 70.0, "typ": 100.0}

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(
        str(json_file),
        str(yaml_file),
        str(output_file),
        is_tv_flag=False,
        device_reports=[]
    )

    with open(output_file, "r") as f:
        result = json.load(f)

    assert result[key_in_json]["status"] == expected_status
    assert result[key_in_json]["tolerance_applied"]["percent"] == 2
    assert result[key_in_json]["tolerance_applied"]["original_typ"] == 100.0
    assert result[key_in_json]["tolerance_applied"]["adjusted_typ"] == 98.0


def test_generate_comparison_report_tv_temperature_max_check(tmp_path, mock_yaml_data):
    """
    Tests that Temperature is checked ONLY by min/max for all devices (TV and non-TV).
    Temperature avg is NOT checked, typ is ignored.
    """
    # Case 1: Temperature max exceeds expected - should FAIL
    full_report_data_fail = {
        "Results": {
            "Temperature": {"avg": 6500.0, "min": 6400.0, "max": 6700.0}  # max exceeds 6600
        }
    }
    # Only min/max are used for Temperature, typ should be ignored
    mock_yaml_data["Temperature"] = {"min": 6200.0, "max": 6600.0}

    json_file_fail = tmp_path / "full_report_fail.json"
    with open(json_file_fail, "w") as f:
        json.dump(full_report_data_fail, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    output_file_fail = tmp_path / "comparison_fail.json"
    report.generate_comparison_report(
        str(json_file_fail),
        str(yaml_file),
        str(output_file_fail),
        is_tv_flag=True,
        device_reports=[]
    )

    with open(output_file_fail, "r") as f:
        result_fail = json.load(f)

    assert result_fail["Temperature"]["status"] == "FAIL"
    assert "Actual max (6700.0) > Expected max (6600.0)" in result_fail["Temperature"]["reason"]

    # Case 2: Temperature max is within bounds, min is OK - should PASS
    full_report_data_pass = {
        "Results": {
            "Temperature": {"avg": 6500.0, "min": 6400.0, "max": 6550.0}  # max within bounds
        }
    }

    json_file_pass = tmp_path / "full_report_pass.json"
    with open(json_file_pass, "w") as f:
        json.dump(full_report_data_pass, f)

    output_file_pass = tmp_path / "comparison_pass.json"
    report.generate_comparison_report(
        str(json_file_pass),
        str(yaml_file),
        str(output_file_pass),
        is_tv_flag=True,
        device_reports=[]
    )

    with open(output_file_pass, "r") as f:
        result_pass = json.load(f)

    assert result_pass["Temperature"]["status"] == "PASS"
    assert "Temperature checks passed" in result_pass["Temperature"]["reason"]
    assert "min (6400.0) >= 6200.0" in result_pass["Temperature"]["reason"]

    # Case 3: Temperature min fails - should FAIL (even if avg is good)
    full_report_data_min_fail = {
        "Results": {
            "Temperature": {"avg": 6500.0, "min": 6100.0, "max": 6550.0}  # min below 6200
        }
    }

    json_file_min_fail = tmp_path / "full_report_min_fail.json"
    with open(json_file_min_fail, "w") as f:
        json.dump(full_report_data_min_fail, f)

    output_file_min_fail = tmp_path / "comparison_min_fail.json"
    report.generate_comparison_report(
        str(json_file_min_fail),
        str(yaml_file),
        str(output_file_min_fail),
        is_tv_flag=True,
        device_reports=[]
    )

    with open(output_file_min_fail, "r") as f:
        result_min_fail = json.load(f)

    assert result_min_fail["Temperature"]["status"] == "FAIL"
    assert "Actual min (6100.0) < Expected min (6200.0)" in result_min_fail["Temperature"]["reason"]


def test_generate_comparison_report_temperature_ignores_typ(tmp_path):
    """
    Tests that Temperature completely ignores 'typ' value in YAML.
    Only min/max bounds are checked, avg is not evaluated against typ.
    """
    # Setup: avg is BELOW typ, but within min/max bounds
    full_report_data = {
        "Results": {
            "Temperature": {"avg": 6300.0, "min": 6250.0, "max": 6350.0}
        }
    }
    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    # YAML with typ value that is higher than avg (should be ignored)
    yaml_data = {
        "Temperature": {
            "min": 6200.0,
            "typ": 6500.0,  # avg (6300) < typ, but this should NOT cause FAIL
            "max": 6400.0
        }
    }
    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(yaml_data, f)

    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(
        str(json_file),
        str(yaml_file),
        str(output_file),
        is_tv_flag=False,
        device_reports=[]
    )

    with open(output_file, "r") as f:
        result = json.load(f)

    # Should PASS because min/max are within bounds, typ is ignored
    assert result["Temperature"]["status"] == "PASS"
    assert "Temperature checks passed" in result["Temperature"]["reason"]


# --------------------------------------------------------------------------------
# NEW TESTS for Return Values (bool validation)
# --------------------------------------------------------------------------------

def test_calculate_full_report_returns_true_on_success(tmp_path):
    """Tests that calculate_full_report returns True on successful execution."""
    reports_list = [
        create_mock_device_report_dict("SN1", 100.0),
        create_mock_device_report_dict("SN2", 120.0),
    ]
    output_file = tmp_path / "full_report.json"

    result = report.calculate_full_report(
        device_reports=reports_list,
        output_file=str(output_file),
        device_name="Monitor"
    )

    assert result is True
    assert output_file.exists()


def test_calculate_full_report_returns_false_on_write_error(tmp_path):
    """Tests that calculate_full_report returns False when file write fails."""
    reports_list = [create_mock_device_report_dict("SN1", 100.0)]

    # Use an invalid path that will cause write to fail
    invalid_output = tmp_path / "nonexistent_dir" / "full_report.json"

    result = report.calculate_full_report(
        device_reports=reports_list,
        output_file=str(invalid_output),
        device_name="Monitor"
    )

    assert result is False


def test_generate_comparison_report_returns_true_on_success(tmp_path):
    """Tests that generate_comparison_report returns True on success."""
    # Setup actual result file
    actual_file = tmp_path / "actual.json"
    actual_data = {
        "Results": {
            "Brightness": {"avg": 100.0, "min": 95.0, "max": 105.0}
        }
    }
    actual_file.write_text(json.dumps(actual_data))

    # Setup expected result file
    expected_file = tmp_path / "expected.yaml"
    expected_file.write_text("Brightness:\n  min: 90.0\n  typ: 100.0\n  max: 110.0")

    output_file = tmp_path / "comparison.json"

    result = report.generate_comparison_report(
        actual_result_file=actual_file,
        expected_result_file=expected_file,
        output_json_file=output_file,
        is_tv_flag=False,
        device_reports=[]
    )

    assert result is True
    assert output_file.exists()


def test_generate_comparison_report_returns_false_on_missing_actual_file(tmp_path):
    """Tests that generate_comparison_report returns False when actual file is missing."""
    nonexistent_actual = tmp_path / "nonexistent.json"  # Does not exist

    expected_file = tmp_path / "expected.yaml"
    expected_file.write_text("Brightness:\n  min: 90.0\n  typ: 100.0")

    output_file = tmp_path / "comparison.json"

    result = report.generate_comparison_report(
        actual_result_file=nonexistent_actual,
        expected_result_file=expected_file,
        output_json_file=output_file,
        is_tv_flag=False,
        device_reports=[]
    )

    assert result is False


def test_generate_comparison_report_returns_false_on_missing_expected_file(tmp_path):
    """Tests that generate_comparison_report returns False when expected file is missing."""
    actual_file = tmp_path / "actual.json"
    actual_file.write_text(json.dumps({"Results": {}}))

    nonexistent_expected = tmp_path / "nonexistent.yaml"  # Does not exist
    output_file = tmp_path / "comparison.json"

    result = report.generate_comparison_report(
        actual_result_file=actual_file,
        expected_result_file=nonexistent_expected,
        output_json_file=output_file,
        is_tv_flag=False,
        device_reports=[]
    )

    assert result is False


# --------------------------------------------------------------------------------
# expand_coordinates_tolerance tests
# --------------------------------------------------------------------------------

def test_expand_coordinates_tolerance_applies_tolerance():
    """Expands typ-only coordinate entries using coordinates_tolerance."""
    main_tests = {
        "Coordinates_tolerance": 0.030,
        "Red_x": {"typ": 0.638},
        "Red_y": {"typ": 0.335},
        "Brightness": {"min": 260, "typ": 280, "max": None},
    }
    result = report.expand_coordinates_tolerance(main_tests)

    assert "Coordinates_tolerance" not in result
    assert result["Red_x"] == {"min": round(0.638 - 0.030, 4), "typ": 0.638, "max": round(0.638 + 0.030, 4)}
    assert result["Red_y"] == {"min": round(0.335 - 0.030, 4), "typ": 0.335, "max": round(0.335 + 0.030, 4)}
    # Non-coordinate keys untouched
    assert result["Brightness"] == {"min": 260, "typ": 280, "max": None}


def test_expand_coordinates_tolerance_skips_entries_with_explicit_min_max():
    """Does not overwrite entries that already have min or max set."""
    main_tests = {
        "Coordinates_tolerance": 0.030,
        "Red_x": {"min": 0.608, "typ": 0.638, "max": 0.668},
    }
    result = report.expand_coordinates_tolerance(main_tests)
    # min/max already present — must not be overwritten
    assert result["Red_x"] == {"min": 0.608, "typ": 0.638, "max": 0.668}


def test_expand_coordinates_tolerance_no_tolerance_key():
    """Returns dict unchanged when coordinates_tolerance is absent."""
    main_tests = {
        "Red_x": {"typ": 0.638},
        "Brightness": {"min": 260, "typ": 280, "max": None},
    }
    result = report.expand_coordinates_tolerance(main_tests)
    # Without tolerance, coordinate entry stays as-is
    assert result["Red_x"] == {"typ": 0.638}
    assert result["Brightness"] == {"min": 260, "typ": 280, "max": None}


def test_expand_coordinates_tolerance_removes_key_from_result():
    """coordinates_tolerance sentinel is never present in the output."""
    main_tests = {"Coordinates_tolerance": 0.020, "Brightness": {"min": 100, "typ": 120, "max": None}}
    result = report.expand_coordinates_tolerance(main_tests)
    assert "Coordinates_tolerance" not in result


# --------------------------------------------------------------------------------
# adjusted_typ rounding tests
# --------------------------------------------------------------------------------

def _corporate_adjusted(yaml_key, typ, tolerance):
    """Expected adjusted_typ: applies safe_round with key's REPORT_PRECISION."""
    json_key = report.YAML_TO_JSON_KEY_MAP.get(yaml_key, yaml_key)
    prec = report.REPORT_PRECISION.get(json_key, 2)
    return report.safe_round(typ * (1 - tolerance), prec)


@pytest.mark.parametrize("yaml_key,typ", [
    # typ=83: raw 83*0.95 = 78.85000000000001 → floating-point artifact without rounding
    ("Brightness", 83),           # precision 0 → int
    ("Brightness_uniformity", 83),  # precision 1 → 1 decimal
    ("Contrast", 750),            # precision 0 → int; 712.5 → banker's rounding
])
def test_corporate_typ_tolerance_adjusted_typ_is_rounded(yaml_key, typ):
    """adjusted_typ is rounded per REPORT_PRECISION; no floating-point artifacts."""
    raw = typ * (1 - report.CORPORATE_DEVICES_TYP_TOLERANCE)
    actual = {"avg": typ * 2, "min": typ}
    expected = {"min": 0.0, "typ": float(typ)}
    _, _, tol = report.check_general_test_status(yaml_key, actual, expected, is_tv_flag=False, majority_check_data={})
    assert tol is not None
    assert tol["adjusted_typ"] == _corporate_adjusted(yaml_key, typ, report.CORPORATE_DEVICES_TYP_TOLERANCE)
    # Verify rounding actually changed the value when there was a FP artifact
    if raw != tol["adjusted_typ"]:
        assert str(raw) != str(tol["adjusted_typ"])


@pytest.mark.parametrize("yaml_key,typ", [
    # 97*0.98 = 95.05999999999999 → floating-point artifact without rounding
    ("Cg_rgb_area", 97),   # precision 1 → 95.1
    ("Cg_dcip3", 97),      # precision 1 → 95.1
])
def test_corporate_cg_tolerance_adjusted_typ_is_rounded(yaml_key, typ):
    """adjusted_typ for CG tolerance is rounded to 1 decimal, not raw float."""
    actual = {"avg": typ * 2, "min": 0.0}
    expected = {"min": 0.0, "typ": float(typ)}
    _, _, tol = report.check_general_test_status(yaml_key, actual, expected, is_tv_flag=False, majority_check_data={})
    assert tol is not None
    assert tol["adjusted_typ"] == _corporate_adjusted(yaml_key, typ, report.CORPORATE_DEVICES_CG_TOLERANCE)


def test_corporate_tolerance_not_applied_for_tv():
    """Corporate tolerance must not be applied when is_tv_flag=True."""
    actual = {"avg": 50.0, "min": 50.0}
    expected = {"min": 0.0, "typ": 83.0}
    _, _, tol = report.check_general_test_status("Brightness", actual, expected, is_tv_flag=True, majority_check_data={})
    assert tol is None


@pytest.mark.parametrize("device_name", [
    *report.CONTRAST_TYP_SKIP_CONFIGS,
    "SDNB-16iA_CH19",
    "SDNB-M16iA_FOX5",
])
def test_corporate_contrast_skip_typ_pass_on_min(device_name):
    """Contrast TYP skip: PASS when min is ok, even if avg is below expected typ."""
    actual = {"avg": 500.0, "min": 850.0}  # avg below typ, min above threshold
    expected = {"min": 800.0, "typ": 1000.0}
    status, reason, tol = report.check_general_test_status(
        "Contrast", actual, expected, is_tv_flag=False, majority_check_data={},
        device_config_name=device_name
    )
    assert status == "PASS"
    assert "(Corporate) Actual min (850.0) >= Expected min (800.0)" in reason
    assert tol is None


@pytest.mark.parametrize("device_name", [
    *report.CONTRAST_TYP_SKIP_CONFIGS,
    "SDNB-16iA_CH19",
    "SDNB-M16iA_FOX5",
])
def test_corporate_contrast_skip_typ_fail_on_min(device_name):
    """Contrast TYP skip: FAIL when min is below expected min."""
    actual = {"avg": 1200.0, "min": 700.0}  # avg passes but min fails
    expected = {"min": 800.0, "typ": 1000.0}
    status, reason, tol = report.check_general_test_status(
        "Contrast", actual, expected, is_tv_flag=False, majority_check_data={},
        device_config_name=device_name
    )
    assert status == "FAIL"
    assert "Actual min (700.0) < Expected min (800.0)" in reason
    assert tol is None


def test_corporate_contrast_skip_not_applied_for_tv():
    """Contrast TYP skip must not apply when is_tv_flag=True (TV has its own contrast tolerance)."""
    actual = {"avg": 950.0, "min": 850.0}  # avg passes TV-adjusted typ (1000 * 0.935 = 935)
    expected = {"min": 800.0, "typ": 1000.0}
    status, reason, tol = report.check_general_test_status(
        "Contrast", actual, expected, is_tv_flag=True, majority_check_data={},
        device_config_name="SDNB-16iA"
    )
    # TV contrast tolerance applies: adjusted typ = 935.0; avg=950 passes
    assert status == "PASS"
    assert "(Corporate)" not in reason


def test_corporate_contrast_skip_not_applied_for_other_devices():
    """Contrast TYP skip must not apply to devices not in CONTRAST_TYP_SKIP_CONFIGS."""
    actual = {"avg": 500.0, "min": 850.0}  # avg below typ — FAIL without skip, PASS with skip
    expected = {"min": 800.0, "typ": 1000.0}
    status, reason, tol = report.check_general_test_status(
        "Contrast", actual, expected, is_tv_flag=False, majority_check_data={},
        device_config_name="SomeOtherDevice"
    )
    assert status == "FAIL"
    assert "Actual avg" in reason
    assert "(Corporate)" not in reason