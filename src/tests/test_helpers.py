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
    Now returns a tuple: (main_reports, coord_reports).
    Checks flattening, formatting, UFN mapping, and separation of coordinates.
    """

    # 1. Input data
    mock_report_data = {
        "SerialNumber": "Device123",
        "MeasurementDateTime": "20250101_120000",
        "IsTV": False,
        "Results": {
            "Brightness": 159.7,
            "Contrast": 1000,
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
        "Red_x": "Red (x)"
    }

    # Mock precision constants
    mocker.patch.object(report, 'REPORT_PRECISION', {
        "Brightness": 0,
        "Red_x": 3
    })

    # 3. Execute
    main_data, coord_data = helpers.process_device_reports(device_reports_list, ufn_mapping)

    # 4. Verify Structure
    sn = "Device123"
    assert sn in main_data
    assert sn in coord_data

    # 5. Verify Main Data content
    # Brightness should be here, rounded to 0 decimals
    assert "Peak Brightness" in main_data[sn]["results"]
    assert main_data[sn]["results"]["Peak Brightness"] == "160"
    # Coordinates should NOT be here
    assert "Red (x)" not in main_data[sn]["results"]

    # 6. Verify Coordinate Data content
    # Coordinates should be here, rounded to 3 decimals
    assert "Red (x)" in coord_data[sn]["results"]
    assert coord_data[sn]["results"]["Red (x)"] == "0.648"
    # Main data should NOT be here
    assert "Peak Brightness" not in coord_data[sn]["results"]

    # 7. Verify Metadata
    assert main_data[sn]["measurement_date"] == "20250101120000"  # Underscore removed
    assert coord_data[sn]["is_tv"] is False


def test_process_main_report(tmp_path):
    """
    Tests 'process_main_report'.
    Checks filtering based on config, sorting, renaming, and separation.
    """
    # 1. Mock Data
    raw_data = {
        "Brightness": {"actual_values": {"avg": 100}},
        "Contrast": {"actual_values": {"avg": 200}}, # Should be filtered out by config
        "Red_x": {"actual_values": {"avg": 0.65}},
        "Blue_x": {"actual_values": {"avg": 0.15}}
    }

    # ИСПРАВЛЕНИЕ: Используем имена, совпадающие с helpers.COORD_HEADERS_UFN
    ufn_mapping = {
        "Brightness": "Brightness (nits)",
        "Red_x": "Red (x)",   # Было "Red X"
        "Blue_x": "Blue (x)"  # Было "Blue X"
    }

    # 2. Create Mock Config File
    config_path = tmp_path / "view_config.yaml"
    config_data = {
        "columns": {
            "Brightness": True,
            "Contrast": False,  # Explicitly disabled
            "Red_x": True,
            # Blue_x is missing from config, should be ignored if dict is used
        }
    }
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # 3. Execute
    main_rows, coord_rows = helpers.process_main_report(raw_data, ufn_mapping, config_path)

    # 4. Verify Output Types
    assert isinstance(main_rows, dict)
    assert isinstance(coord_rows, dict)

    # 5. Verify Filtering & Separation
    # Brightness -> Main, Enabled
    assert "Brightness (nits)" in main_rows
    assert main_rows["Brightness (nits)"] == raw_data["Brightness"]

    # Contrast -> Disabled in config
    assert "Contrast" not in main_rows
    assert "Contrast Ratio" not in main_rows

    # Red_x -> Coords, Enabled
    assert "Red (x)" in coord_rows
    assert coord_rows["Red (x)"] == raw_data["Red_x"]

    # Blue_x -> Not in config (if config is dict, usually implies strict filter)
    # Based on logic: [k for k, enabled in columns_config.items() if enabled]
    assert "Blue (x)" not in coord_rows


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

    min_fail_file = tmp_path / "min_fail.json"
    min_fail_file.write_text("[]")

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
        min_fail_file=min_fail_file,
        cie_background_svg=svg_file,
        report_view_config=view_config,
        device_reports=device_reports,
        current_device_name="TestDevice",
        app_version="1.0.0"
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