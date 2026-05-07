# tests/test_helpers.py

import json
import zipfile
from pathlib import Path
import yaml

import pytest
from jinja2 import Environment

from src import helpers
from src import report  # Import for precision constants


# --------------------------------------------------------------------------------
# NEW TESTS for HTML Reporting Logic
# --------------------------------------------------------------------------------

def test_process_device_reports(mocker):
    """
    Tests 'process_device_reports'.
    Returns a tuple: (main_reports, gamut_xy_reports, gamut_uv_reports, coord_reports).
    Checks flattening, formatting, UFN mapping, and separation into four groups.
    """

    # 1. Input data
    mock_report_data = {
        "SerialNumber": "Device123",
        "MeasurementDateTime": "20250101_120000",
        "IsTV": False,
        "Results": {
            "Brightness": 159.7,
            "Contrast": 1000,
            "CgByAreaRGB": 95.5,
            "CgRGB": 88.2,
            "Coordinates": {
                "Red_x": 0.648123,
                "Red_y": 0.336
            }
        }
    }
    device_reports_list = [mock_report_data]

    # 2. Define UFN mapping
    ufn_mapping = {
        "Brightness": "Peak Brightness",
        "CgByAreaRGB": "sRGB Area (%)",
        "CgRGB": "sRGB Coverage (%)",
        "Red_x": "Red (x)"
    }

    # Mock precision constants
    mocker.patch.object(report, 'REPORT_PRECISION', {
        "Brightness": 0,
        "CgByAreaRGB": 1,
        "CgRGB": 1,
        "Red_x": 3
    })

    # 2.5. Mock expected values (empty for this basic test)
    expected_values = {}

    # 3. Execute
    main_data, gamut_xy_data, gamut_uv_data, coord_data = helpers.process_device_reports(device_reports_list, ufn_mapping, expected_values)

    # 4. Verify Structure
    sn = "Device123"
    assert sn in main_data
    assert sn in gamut_xy_data
    assert sn in gamut_uv_data
    assert sn in coord_data

    # 5. Verify Main Data content
    assert "Peak Brightness" in main_data[sn]["results"]
    assert main_data[sn]["results"]["Peak Brightness"] == "160"
    assert "sRGB Area (%)" not in main_data[sn]["results"]
    assert "Red (x)" not in main_data[sn]["results"]

    # 6. Verify Gamut XY Data content (CIE 1931)
    assert "sRGB Area (%)" in gamut_xy_data[sn]["results"]
    assert gamut_xy_data[sn]["results"]["sRGB Area (%)"] == "95.5"
    assert "sRGB Coverage (%)" in gamut_xy_data[sn]["results"]
    assert gamut_xy_data[sn]["results"]["sRGB Coverage (%)"] == "88.2"
    assert "Peak Brightness" not in gamut_xy_data[sn]["results"]
    assert "Red (x)" not in gamut_xy_data[sn]["results"]

    # 7. Verify Coordinate Data content
    assert "Red (x)" in coord_data[sn]["results"]
    assert coord_data[sn]["results"]["Red (x)"] == "0.648"
    assert "Peak Brightness" not in coord_data[sn]["results"]
    assert "sRGB Area (%)" not in coord_data[sn]["results"]

    # 8. Verify Metadata
    assert main_data[sn]["measurement_date"] == "20250101120000"  # Underscore removed
    assert gamut_xy_data[sn]["is_tv"] is False
    assert coord_data[sn]["is_tv"] is False


def test_process_main_report(tmp_path):
    """
    Tests 'process_main_report'.
    Checks UFN renaming and main/coord separation.
    """
    raw_data = {
        "Brightness": {"actual_values": {"avg": 100}},
        "Contrast": {"actual_values": {"avg": 200}},
        "Red_x": {"actual_values": {"avg": 0.65}},
        "Blue_x": {"actual_values": {"avg": 0.15}},
    }

    ufn_mapping = {
        "Brightness": "Brightness (nits)",
        "Red_x": "Red (x)",
        "Blue_x": "Blue (x)",
    }

    expected_values = {}

    main_rows, coord_rows = helpers.process_main_report(raw_data, ufn_mapping, expected_values)

    assert isinstance(main_rows, dict)
    assert isinstance(coord_rows, dict)

    # Brightness and Contrast → Main (not in COORD_KEYS_INTERNAL)
    assert "Brightness (nits)" in main_rows
    assert main_rows["Brightness (nits)"] == raw_data["Brightness"]
    assert "Contrast" in main_rows  # no UFN mapping, key used as-is

    # Red_x, Blue_x → Coordinates
    assert "Red (x)" in coord_rows
    assert coord_rows["Red (x)"] == raw_data["Red_x"]
    assert "Blue (x)" in coord_rows


def test_create_html_report(mocker, tmp_path):
    """
    Tests 'create_html_report' integration.
    """
    # 1. Mocks
    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "<html>Report</html>"
    mock_env = mocker.MagicMock(spec=Environment)
    mock_env.get_template.return_value = mock_template
    mocker.patch('src.helpers.Environment', return_value=mock_env)

    # 2. File Setup
    input_file = tmp_path / "final_report.json"
    input_file.write_text(json.dumps({"Results": {"Brightness": {"avg": 100}}}))

    expected_file = tmp_path / "expected_report.yaml"
    expected_file.write_text("Brightness:\n  min: 80\n  typ: 100\n  max: 120")


    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")

    view_config = tmp_path / "view.yaml"
    view_config.write_text("columns:\n  Brightness: true")

    output_file = tmp_path / "output.html"

    device_reports = [
        {"SerialNumber": "SN1", "Results": {"Brightness": 100}, "MeasurementDateTime": "20250101_120000"}
    ]

    # 3. Execute
    helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=device_reports,
        current_device_name="TestDevice",
        app_version="1.0.0",
        expected_yaml=expected_file,
    )

    # 4. Verify
    mock_env.get_template.assert_called_with(helpers.HTML_TEMPLATE_NAME)
    mock_template.render.assert_called_once()
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "<html>Report</html>"


# --------------------------------------------------------------------------------
# EXISTING File System Tests (Unchanged)
# --------------------------------------------------------------------------------

def test_archive_specific_files(mocker, tmp_path):
    """Tests 'archive_specific_files'."""
    mock_zip_file = mocker.patch('src.helpers.zipfile.ZipFile')
    mock_zip_instance = mock_zip_file.return_value.__enter__.return_value
    base_folder = tmp_path

    file1 = tmp_path / "data" / "report1.json"
    (tmp_path / "data").mkdir()
    file1.touch()

    files_to_archive = [file1]
    zip_path = tmp_path / "archive.zip"

    helpers.archive_specific_files(zip_path, files_to_archive, base_folder)

    assert mock_zip_instance.write.call_count == 1
    mock_zip_instance.write.assert_any_call(file1, Path("data") / "report1.json")


def test_clear_specific_files(tmp_path):
    """Tests 'clear_specific_files'."""
    file1 = tmp_path / "file1.txt"
    file1.touch()
    assert file1.exists()

    helpers.clear_specific_files([file1])
    assert not file1.exists()


# --------------------------------------------------------------------------------
# NEW TESTS for Return Values (bool validation)
# --------------------------------------------------------------------------------

def test_create_html_report_returns_true_on_success(mocker, tmp_path):
    """Tests that create_html_report returns True on successful execution."""
    # Setup mocks
    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "<html>Report</html>"
    mock_env = mocker.MagicMock(spec=Environment)
    mock_env.get_template.return_value = mock_template
    mocker.patch('src.helpers.Environment', return_value=mock_env)

    # Setup files
    input_file = tmp_path / "final_report.json"
    input_file.write_text(json.dumps({"Results": {"Brightness": {"avg": 100}}}))

    expected_file = tmp_path / "expected_report.yaml"
    expected_file.write_text("Brightness:\n  min: 80\n  typ: 100\n  max: 120")


    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")

    view_config = tmp_path / "view.yaml"
    view_config.write_text("columns:\n  Brightness: true")

    output_file = tmp_path / "output.html"

    device_reports = [
        {"SerialNumber": "SN1", "Results": {"Brightness": 100}, "MeasurementDateTime": "20250101_120000"}
    ]

    # Execute
    result = helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=device_reports,
        current_device_name="TestDevice",
        app_version="1.0.0",
        expected_yaml=expected_file,
    )

    # Verify return value
    assert result is True
    assert output_file.exists()


def test_create_html_report_returns_false_on_missing_input_file(mocker, tmp_path):
    """Tests that create_html_report returns False when input file is missing."""
    input_file = tmp_path / "nonexistent.json"  # Does not exist
    output_file = tmp_path / "output.html"
    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")
    view_config = tmp_path / "view.yaml"
    view_config.write_text("columns: {}")
    expected_file = tmp_path / "expected.yaml"
    expected_file.write_text("{}")

    result = helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=[],
        current_device_name="TestDevice",
        app_version="1.0.0",
        expected_yaml=expected_file,
    )

    assert result is False
    assert not output_file.exists()


def test_create_html_report_returns_false_on_missing_expected_yaml(mocker, tmp_path):
    """Tests that create_html_report returns False when expected YAML is missing."""
    input_file = tmp_path / "final_report.json"
    input_file.write_text(json.dumps({"Results": {}}))

    output_file = tmp_path / "output.html"
    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")
    view_config = tmp_path / "view.yaml"
    view_config.write_text("columns: {}")
    expected_file = tmp_path / "nonexistent.yaml"  # Does not exist

    result = helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=[],
        current_device_name="TestDevice",
        app_version="1.0.0",
        expected_yaml=expected_file,
    )

    assert result is False
    assert not output_file.exists()


def test_create_html_report_returns_false_on_template_load_error(mocker, tmp_path):
    """Tests that create_html_report returns False when template loading fails."""
    # Setup files
    input_file = tmp_path / "final_report.json"
    input_file.write_text(json.dumps({"Results": {}}))

    expected_file = tmp_path / "expected.yaml"
    expected_file.write_text("{}")


    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")

    view_config = tmp_path / "view.yaml"
    view_config.write_text("columns: {}")

    output_file = tmp_path / "output.html"

    # Mock Environment to raise exception on get_template
    mock_env = mocker.MagicMock(spec=Environment)
    mock_env.get_template.side_effect = Exception("Template not found")
    mocker.patch('src.helpers.Environment', return_value=mock_env)

    result = helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=[],
        current_device_name="TestDevice",
        app_version="1.0.0",
        expected_yaml=expected_file,
    )

    assert result is False
    assert not output_file.exists()


def test_process_main_report_dynamic_cg_filter(tmp_path):
    """
    Tests dynamic Color Gamut filtering based on expected values presence.
    """
    # Mock data with all 4 CG metrics
    raw_data = {
        "Brightness": {"actual_values": {"avg": 100}},
        "CgByAreaRGB": {"actual_values": {"avg": 72}},
        "CgByAreaNTSC": {"actual_values": {"avg": 68}},
        "CgRGB": {"actual_values": {"avg": 71}},
        "CgNTSC": {"actual_values": {"avg": 69}},
    }

    ufn_mapping = {
        "Brightness": "Brightness (cd/m²)",
        "CgByAreaRGB": "sRGB Gamut Area (%)",
        "CgByAreaNTSC": "NTSC Gamut Area (%)",
        "CgRGB": "sRGB Gamut Coverage (%)",
        "CgNTSC": "NTSC Gamut Coverage (%)",
    }

    # Expected values: only Cg_rgb_area and Cg_rgb have values
    # Using string 'None' to simulate YAML parsing behavior
    expected_values = {
        "Cg_rgb_area": {"min": 67, "typ": 72, "max": 'None'},
        "Cg_ntsc_area": {"min": 'None', "typ": 'None', "max": 'None'},  # All 'None' - should be hidden
        "Cg_rgb": {"min": 'None', "typ": 72, "max": 'None'},  # Has typ - should be visible
        "Cg_ntsc": {"min": 'None', "typ": 'None', "max": 'None'},  # All 'None' - should be hidden
    }

    # Execute
    main_rows, coord_rows = helpers.process_main_report(raw_data, ufn_mapping, expected_values)

    # Verify filtering
    assert "Brightness (cd/m²)" in main_rows  # Always visible
    assert "sRGB Gamut Area (%)" in main_rows  # Has expected values
    assert "sRGB Gamut Coverage (%)" in main_rows  # Has typ expected value
    assert "NTSC Gamut Area (%)" not in main_rows  # All expected values are None
    assert "NTSC Gamut Coverage (%)" not in main_rows  # All expected values are None


def test_should_display_metric():
    """
    Tests _should_display_metric helper function.
    """
    # Non-CG metric - always display
    assert helpers._should_display_metric("Brightness", {}) is True
    assert helpers._should_display_metric("Contrast", {"Contrast": {"min": None, "typ": None, "max": None}}) is True

    # CG metric with at least one expected value
    expected_with_min = {"Cg_rgb_area": {"min": 67, "typ": None, "max": None}}
    assert helpers._should_display_metric("CgByAreaRGB", expected_with_min) is True

    expected_with_typ = {"Cg_ntsc": {"min": None, "typ": 72, "max": None}}
    assert helpers._should_display_metric("CgNTSC", expected_with_typ) is True

    expected_with_max = {"Cg_rgb": {"min": None, "typ": None, "max": 100}}
    assert helpers._should_display_metric("CgRGB", expected_with_max) is True

    # CG metric with all None expected values - hide
    expected_all_none = {"Cg_ntsc_area": {"min": None, "typ": None, "max": None}}
    assert helpers._should_display_metric("CgByAreaNTSC", expected_all_none) is False

    # CG metric with string 'None' values (YAML parsing edge case) - hide
    expected_string_none = {"Cg_ntsc_area": {"min": 'None', "typ": 'None', "max": 'None'}}
    assert helpers._should_display_metric("CgByAreaNTSC", expected_string_none) is False

    # CG metric with mixed None types and valid value - display
    expected_mixed = {"Cg_rgb": {"min": 'None', "typ": 72, "max": None}}
    assert helpers._should_display_metric("CgRGB", expected_mixed) is True

    # CG metric not in expected_values dict - hide
    assert helpers._should_display_metric("CgByAreaRGB", {}) is False


def test_get_cell_status():
    """
    Tests _get_cell_status helper function for cell highlighting logic.
    """
    expected_values = {
        "Brightness": {"min": 100, "typ": 120, "max": 140},
        "Red_x": {"min": 0.60, "typ": 0.64, "max": 0.68},
    }

    # Normal value - no status
    assert helpers._get_cell_status("Brightness", 120, expected_values, False) is None

    # Below typ but above min - warning (yellow)
    assert helpers._get_cell_status("Brightness", 110, expected_values, False) == "warning"

    # Below min - fail (red)
    assert helpers._get_cell_status("Brightness", 95, expected_values, False) == "fail"

    # Above max - fail (red)
    assert helpers._get_cell_status("Brightness", 150, expected_values, False) == "fail"

    # Coordinate below typ - no warning (coordinates only check min/max)
    assert helpers._get_cell_status("Red_x", 0.62, expected_values, True) is None

    # Coordinate below min - fail (red)
    assert helpers._get_cell_status("Red_x", 0.59, expected_values, True) == "fail"

    # Coordinate above max - fail (red)
    assert helpers._get_cell_status("Red_x", 0.69, expected_values, True) == "fail"

    # String 'None' values should be treated as None
    expected_with_string_none = {
        "Brightness": {"min": 'None', "typ": 120, "max": 'None'}
    }
    assert helpers._get_cell_status("Brightness", 110, expected_with_string_none, False) == "warning"
    assert helpers._get_cell_status("Brightness", 50, expected_with_string_none, False) == "warning"  # Below typ, no min check

    # None value - no status
    assert helpers._get_cell_status("Brightness", None, expected_values, False) is None


def test_process_device_reports_with_cell_status(mocker):
    """
    Tests process_device_reports with cell status highlighting across all three groups.
    """
    mock_report_data = {
        "SerialNumber": "Device456",
        "MeasurementDateTime": "20250101_120000",
        "IsTV": False,
        "Results": {
            "Brightness": 110,      # Below typ (120), above min (100) - warning
            "Contrast": 90,         # Below min (100) - fail
            "Temperature": 9500,    # Normal
            "CgByAreaRGB": 65,      # Below typ (70), above min (60) - warning
            "CgRGB": 55,            # Below min (60) - fail
            "Coordinates": {
                "Red_x": 0.59,      # Below min (0.60) - fail
                "Red_y": 0.335      # Normal
            }
        }
    }

    ufn_mapping = {
        "Brightness": "Brightness (cd/m²)",
        "Contrast": "Contrast Ratio",
        "Temperature": "Color Temperature (K)",
        "CgByAreaRGB": "sRGB Area (%)",
        "CgRGB": "sRGB Coverage (%)",
        "Red_x": "Red (x)",
        "Red_y": "Red (y)"
    }

    expected_values = {
        "Brightness": {"min": 100, "typ": 120, "max": 'None'},
        "Contrast": {"min": 100, "typ": 150, "max": 'None'},
        "Temperature": {"min": 9000, "typ": 9500, "max": 10000},
        "Cg_rgb_area": {"min": 60, "typ": 70, "max": None},
        "Cg_rgb": {"min": 60, "typ": 75, "max": None},
        "Red_x": {"min": 0.60, "typ": 0.64, "max": 0.68},
        "Red_y": {"min": 0.30, "typ": 0.34, "max": 0.38}
    }

    mocker.patch.object(report, 'REPORT_PRECISION', {
        "Brightness": 0,
        "Contrast": 0,
        "Temperature": 0,
        "CgByAreaRGB": 1,
        "CgRGB": 1,
        "Red_x": 3,
        "Red_y": 3
    })

    main_data, gamut_xy_data, gamut_uv_data, coord_data = helpers.process_device_reports([mock_report_data], ufn_mapping, expected_values)

    sn = "Device456"

    # Check cell status for main data
    assert main_data[sn]["cell_status"]["Brightness (cd/m²)"] == "warning"
    assert main_data[sn]["cell_status"]["Contrast Ratio"] == "fail"
    assert "Color Temperature (K)" not in main_data[sn]["cell_status"]  # Normal, no status

    # Check cell status for gamut_xy data (CIE 1931)
    assert gamut_xy_data[sn]["cell_status"]["sRGB Area (%)"] == "warning"
    assert gamut_xy_data[sn]["cell_status"]["sRGB Coverage (%)"] == "fail"

    # Check cell status for coordinates
    assert coord_data[sn]["cell_status"]["Red (x)"] == "fail"
    assert "Red (y)" not in coord_data[sn]["cell_status"]  # Normal, no status


def test_should_display_metric_uv():
    """Tests _should_display_metric for CIE 1976 u'v' keys."""
    # Valid expected values — display
    assert helpers._should_display_metric("CgByAreaUVDCI-P3", {"Cg_dcip3_uv_area": {"min": 90, "typ": 95, "max": None}}) is True
    assert helpers._should_display_metric("CgUVDCI-P3", {"Cg_dcip3_uv": {"min": None, "typ": 93, "max": None}}) is True

    # All None — hide
    assert helpers._should_display_metric("CgByAreaUVRGB", {"Cg_rgb_uv_area": {"min": None, "typ": None, "max": None}}) is False
    assert helpers._should_display_metric("CgUVNTSC", {"Cg_ntsc_uv": {"min": "None", "typ": "None", "max": "None"}}) is False

    # Key missing entirely — hide
    assert helpers._should_display_metric("CgByAreaUVDCI-P3", {}) is False


def test_should_display_metric_delta_e():
    """Tests that DeltaE is now dynamically gated by expected values."""
    # Has expected value — display
    assert helpers._should_display_metric("DeltaE", {"Delta_e": {"min": None, "typ": 5, "max": 7}}) is True

    # All None — hide
    assert helpers._should_display_metric("DeltaE", {"Delta_e": {"min": None, "typ": None, "max": None}}) is False

    # Key absent — hide
    assert helpers._should_display_metric("DeltaE", {}) is False


def test_should_display_metric_dcip3():
    """
    Tests _should_display_metric for DCI-P3 specific keys.
    """
    # Valid expected values — display
    assert helpers._should_display_metric("CgByAreaDCI-P3", {"Cg_dcip3_area": {"min": 60, "typ": 70, "max": None}}) is True
    assert helpers._should_display_metric("CgDCI-P3", {"Cg_dcip3": {"min": None, "typ": 72, "max": None}}) is True

    # All None — hide
    assert helpers._should_display_metric("CgByAreaDCI-P3", {"Cg_dcip3_area": {"min": None, "typ": None, "max": None}}) is False
    assert helpers._should_display_metric("CgDCI-P3", {"Cg_dcip3": {"min": "None", "typ": "None", "max": "None"}}) is False

    # Key missing from expected_values entirely — hide
    assert helpers._should_display_metric("CgByAreaDCI-P3", {}) is False
    assert helpers._should_display_metric("CgDCI-P3", {}) is False


def test_get_cell_status_dcip3():
    """
    Tests _get_cell_status for DCI-P3 metrics mapped via JSON_TO_YAML_KEY_MAP.
    """
    expected_values = {
        "Cg_dcip3_area": {"min": 60, "typ": 70, "max": None},
        "Cg_dcip3": {"min": 55, "typ": 65, "max": None},
    }

    # CgByAreaDCI-P3: above typ — normal
    assert helpers._get_cell_status("CgByAreaDCI-P3", 75, expected_values) is None
    # CgByAreaDCI-P3: below typ, above min — warning
    assert helpers._get_cell_status("CgByAreaDCI-P3", 65, expected_values) == "warning"
    # CgByAreaDCI-P3: below min — fail
    assert helpers._get_cell_status("CgByAreaDCI-P3", 55, expected_values) == "fail"

    # CgDCI-P3: above typ — normal
    assert helpers._get_cell_status("CgDCI-P3", 70, expected_values) is None
    # CgDCI-P3: below typ, above min — warning
    assert helpers._get_cell_status("CgDCI-P3", 60, expected_values) == "warning"
    # CgDCI-P3: below min — fail
    assert helpers._get_cell_status("CgDCI-P3", 50, expected_values) == "fail"


def test_process_main_report_dynamic_dcip3_filter(tmp_path):
    """
    Tests dynamic DCI-P3 column filtering: columns appear only when expected values are present.
    """
    raw_data = {
        "Brightness": {"actual_values": {"avg": 100}},
        "CgByAreaRGB": {"actual_values": {"avg": 72}},
        "CgByAreaDCI-P3": {"actual_values": {"avg": 75}},
        "CgDCI-P3": {"actual_values": {"avg": 68}},
    }

    ufn_mapping = {
        "Brightness": "Brightness (cd/m²)",
        "CgByAreaRGB": "sRGB Gamut Area (%)",
        "CgByAreaDCI-P3": "DCI-P3 Gamut Area (%)",
        "CgDCI-P3": "DCI-P3 Gamut Coverage (%)",
    }

    # Scenario 1: DCI-P3 expected values present — columns visible
    expected_with_dcip3 = {
        "Cg_rgb_area": {"min": 67, "typ": 72, "max": None},
        "Cg_dcip3_area": {"min": 60, "typ": 70, "max": None},
        "Cg_dcip3": {"min": 55, "typ": 65, "max": None},
    }
    main_rows, _ = helpers.process_main_report(raw_data, ufn_mapping, expected_with_dcip3)

    assert "sRGB Gamut Area (%)" in main_rows
    assert "DCI-P3 Gamut Area (%)" in main_rows
    assert "DCI-P3 Gamut Coverage (%)" in main_rows

    # Scenario 2: DCI-P3 expected values all None — columns hidden
    expected_without_dcip3 = {
        "Cg_rgb_area": {"min": 67, "typ": 72, "max": None},
        "Cg_dcip3_area": {"min": None, "typ": None, "max": None},
        "Cg_dcip3": {"min": None, "typ": None, "max": None},
    }
    main_rows, _ = helpers.process_main_report(raw_data, ufn_mapping, expected_without_dcip3)

    assert "sRGB Gamut Area (%)" in main_rows
    assert "DCI-P3 Gamut Area (%)" not in main_rows
    assert "DCI-P3 Gamut Coverage (%)" not in main_rows


def test_create_html_report_plot_triangles_checked(mocker, tmp_path):
    """
    Tests that plot_triangles_checked is correctly derived from expected_values
    and passed to the template context.
    """
    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "<html></html>"
    mock_env = mocker.MagicMock(spec=Environment)
    mock_env.get_template.return_value = mock_template
    mocker.patch('src.helpers.Environment', return_value=mock_env)

    # Common files
    input_file = tmp_path / "report.json"
    input_file.write_text(json.dumps({"Results": {}}))
    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")
    view_config = tmp_path / "view.yaml"
    view_config.write_text("columns: {}")
    output_file = tmp_path / "output.html"
    device_reports = [
        {"SerialNumber": "SN1", "Results": {}, "MeasurementDateTime": "20250101_120000"}
    ]

    # Scenario 1: sRGB + DCI-P3 have expected values, NTSC — all None
    expected_file = tmp_path / "expected.yaml"
    expected_file.write_text(
        "Cg_rgb_area:\n  min: 67\n  typ: 72\n  max: None\n"
        "Cg_ntsc_area:\n  min: None\n  typ: None\n  max: None\n"
        "Cg_dcip3_area:\n  min: 60\n  typ: 70\n  max: None\n"
    )

    helpers.create_html_report(
        input_file=input_file, output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=device_reports, current_device_name="TestDevice",
        app_version="1.0.0", expected_yaml=expected_file,
    )

    context = mock_template.render.call_args[0][0]
    assert context["plot_triangles_checked"]["srgb"] is True
    assert context["plot_triangles_checked"]["ntsc"] is False
    assert context["plot_triangles_checked"]["dcip3"] is True

    # Scenario 2: no CG keys in expected — все три False
    mock_template.render.reset_mock()
    expected_file.write_text(
        "Brightness:\n  min: 100\n  typ: 120\n  max: None\n"
    )

    helpers.create_html_report(
        input_file=input_file, output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=device_reports, current_device_name="TestDevice",
        app_version="1.0.0", expected_yaml=expected_file,
    )

    context = mock_template.render.call_args[0][0]
    assert context["plot_triangles_checked"]["srgb"] is False
    assert context["plot_triangles_checked"]["ntsc"] is False
    assert context["plot_triangles_checked"]["dcip3"] is False

    # Scenario 3: DCI-P3 only in UV variant — dcip3 must still be True
    mock_template.render.reset_mock()
    expected_file.write_text(
        "Cg_dcip3_area:\n  min: None\n  typ: None\n  max: None\n"
        "Cg_dcip3_uv_area:\n  min: 88\n  typ: 93\n  max: None\n"
    )

    helpers.create_html_report(
        input_file=input_file, output_file=output_file,
        cie_background_svg=svg_file,
        device_reports=device_reports, current_device_name="TestDevice",
        app_version="1.0.0", expected_yaml=expected_file,
    )

    context = mock_template.render.call_args[0][0]
    assert context["plot_triangles_checked"]["srgb"] is False
    assert context["plot_triangles_checked"]["ntsc"] is False
    assert context["plot_triangles_checked"]["dcip3"] is True


def test_collect_tolerance_legend():
    """
    Tests collect_tolerance_legend function to ensure it correctly groups metrics by tolerance percent.
    """
    ufn_mapping = {
        "Brightness": "Brightness (cd/m²)",
        "Contrast": "Contrast Ratio",
        "CgByAreaRGB": "sRGB Gamut Area (%)",
        "Temperature": "Color Temperature (K)"
    }

    main_report_data = {
        "Brightness": {
            "status": "PASS",
            "tolerance_applied": {"percent": 5, "original_typ": 100, "adjusted_typ": 95}
        },
        "Contrast": {
            "status": "PASS",
            "tolerance_applied": {"percent": 5, "original_typ": 1000, "adjusted_typ": 950}
        },
        "CgByAreaRGB": {
            "status": "PASS",
            "tolerance_applied": {"percent": 2, "original_typ": 100, "adjusted_typ": 98}
        },
        "Temperature": {
            "status": "PASS",
            "tolerance_applied": None  # No tolerance for Temperature
        }
    }

    legend = helpers.collect_tolerance_legend(main_report_data, ufn_mapping)

    # Check grouping by percent
    assert 5 in legend
    assert 2 in legend
    assert len(legend) == 2

    # Check metric names in groups (sorted descending by percent)
    assert "Brightness (cd/m²)" in legend[5]
    assert "Contrast Ratio" in legend[5]
    assert len(legend[5]) == 2

    assert "sRGB Gamut Area (%)" in legend[2]
    assert len(legend[2]) == 1

    # Temperature should not appear (no tolerance)
    assert "Color Temperature (K)" not in str(legend)


def test_collect_tolerance_legend_empty():
    """
    Tests collect_tolerance_legend with no tolerance applied.
    """
    ufn_mapping = {"Brightness": "Brightness (cd/m²)"}

    main_report_data = {
        "Brightness": {
            "status": "PASS",
            "tolerance_applied": None
        }
    }

    legend = helpers.collect_tolerance_legend(main_report_data, ufn_mapping)

    assert len(legend) == 0