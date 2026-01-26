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
    mock_yaml_data["main_tests"]["Temperature"]["min"] = 5500.0
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
    assert "Actual avg (110.0) >= Expected typ (100.0)" in result["Brightness"]["reason"]

    assert result["Temperature"]["status"] == "FAIL"
    assert "Actual max (7000) > Expected max (6800.0)" in result["Temperature"]["reason"]

    assert result["Red_x"]["status"] == "FAIL"
    assert "Actual min (0.61) < Expected min (0.62)" in result["Red_x"]["reason"]

    assert result["White_x"]["status"] == "N/A"
    assert "is null or missing in JSON" in result["White_x"]["reason"]


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
    mock_yaml_data["main_tests"]["Contrast"] = {"min": 800.0, "typ": 1000.0}

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
    mock_yaml_data["main_tests"][skipped_key_yaml] = expected_values

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
    mock_yaml_data["main_tests"][skipped_key_yaml] = expected_values

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
    mock_yaml_data["main_tests"]["Temperature"] = {"min": 6200.0, "max": 6600.0}

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
        "main_tests": {
            "Temperature": {
                "min": 6200.0,
                "typ": 6500.0,  # avg (6300) < typ, but this should NOT cause FAIL
                "max": 6400.0
            }
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


def test_analyze_json_files_for_min_fail(tmp_path, mock_yaml_data):
    """
    REFACTORED: Tests the min_fail logic by passing a list of dictionaries.
    """
    # 1. Setup expected YAML
    expected_values_path = tmp_path / "expected.yaml"
    # We only care about Brightness and Red_x for this test
    mock_yaml_data["main_tests"] = {
        "Brightness": {"min": 100.0},
        "Red_x": {"min": 0.60}
    }
    with open(expected_values_path, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    # 2. Setup input data (list of dicts)
    device_reports = [
        {
            "SerialNumber": "SN1_PASS",
            "Results": {
                "Brightness": 110.0,
                "Coordinates": {"Red_x": 0.61}
            }
        },
        {
            "SerialNumber": "SN2_FAIL_BRIGHTNESS",
            "Results": {
                "Brightness": 90.0,  # <-- Fails ( < 100.0)
                "Coordinates": {"Red_x": 0.61}
            }
        },
        {
            "SerialNumber": "SN3_FAIL_REDX",
            "Results": {
                "Brightness": 110.0,
                "Coordinates": {"Red_x": 0.59}  # <-- Fails ( < 0.60)
            }
        }
    ]

    output_path = tmp_path / "min_fail.json"

    # 3. Run function
    report.analyze_json_files_for_min_fail(
        device_reports=device_reports,
        expected_result_path=expected_values_path,
        output_path=output_path,
        device_name="TestDevice"
    )

    # 4. Check results
    with open(output_path, "r") as f:
        results = json.load(f)

    assert len(results) == 2  # Two failures

    # Check failure 1
    assert "SN2_FAIL_BRIGHTNESS" in results[0]
    assert results[0]["SN2_FAIL_BRIGHTNESS"]["key"] == "Brightness"
    assert results[0]["SN2_FAIL_BRIGHTNESS"]["min_value"] == 90.0

    # Check failure 2
    assert "SN3_FAIL_REDX" in results[1]
    assert results[1]["SN3_FAIL_REDX"]["key"] == "Red_x"
    assert results[1]["SN3_FAIL_REDX"]["min_value"] == 0.59


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


def test_analyze_json_files_for_min_fail_returns_true_on_success(tmp_path):
    """Tests that analyze_json_files_for_min_fail returns True on success."""
    device_reports = [
        {"SerialNumber": "SN1", "Results": {"Brightness": 80.0}}  # Below min of 100
    ]

    expected_yaml = tmp_path / "expected.yaml"
    expected_yaml.write_text("main_tests:\n  Brightness:\n    min: 100.0")

    output_path = tmp_path / "min_fail.json"

    result = report.analyze_json_files_for_min_fail(
        device_reports=device_reports,
        expected_result_path=expected_yaml,
        output_path=output_path,
        device_name="TestDevice"
    )

    assert result is True
    assert output_path.exists()


def test_analyze_json_files_for_min_fail_returns_false_on_missing_yaml(tmp_path):
    """Tests that analyze_json_files_for_min_fail returns False when YAML is missing."""
    device_reports = [{"SerialNumber": "SN1", "Results": {"Brightness": 80.0}}]

    nonexistent_yaml = tmp_path / "nonexistent.yaml"  # Does not exist
    output_path = tmp_path / "min_fail.json"

    result = report.analyze_json_files_for_min_fail(
        device_reports=device_reports,
        expected_result_path=nonexistent_yaml,
        output_path=output_path,
        device_name="TestDevice"
    )

    assert result is False
    assert not output_path.exists()


def test_analyze_json_files_for_min_fail_returns_false_on_write_error(tmp_path):
    """Tests that analyze_json_files_for_min_fail returns False on write error."""
    device_reports = [{"SerialNumber": "SN1", "Results": {"Brightness": 80.0}}]

    expected_yaml = tmp_path / "expected.yaml"
    expected_yaml.write_text("main_tests:\n  Brightness:\n    min: 100.0")

    # Invalid output path
    invalid_output = tmp_path / "nonexistent_dir" / "min_fail.json"

    result = report.analyze_json_files_for_min_fail(
        device_reports=device_reports,
        expected_result_path=expected_yaml,
        output_path=invalid_output,
        device_name="TestDevice"
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
    expected_file.write_text("main_tests:\n  Brightness:\n    min: 90.0\n    typ: 100.0\n    max: 110.0")

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
    expected_file.write_text("main_tests:\n  Brightness:\n    min: 90.0\n    typ: 100.0")

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