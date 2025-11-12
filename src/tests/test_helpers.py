# tests/test_helpers.py

import json
import zipfile
from pathlib import Path

import pytest
from jinja2 import Environment

from src import helpers
from src import report  # Import for precision constants


# --------------------------------------------------------------------------------
# NEW TESTS for HTML Reporting
# --------------------------------------------------------------------------------

def test_process_device_reports(mocker):  # Removed mock_display_data
    """
    Tests the 'process_device_reports' helper function.
    It should flatten, format, and apply User-Friendly Names (UFN).
    """

    # 1. Input data: Create a mock that mimics r.json_report's output
    mock_report_data = {
        "SerialNumber": "NotTV",
        "MeasurementDateTime": "2025_01",
        "IsTV": False,
        "Results": {
            "Brightness": 159.7,
            "Contrast": 258.26,
            "Coordinates": {
                "Red_x": 0.648,
                "Red_y": 0.336
            }
        }
    }
    device_reports_list = [mock_report_data]  # Pass the correctly structured mock

    # 2. Define UFN mapping and precision
    ufn_mapping = {
        "Brightness": "Peak Brightness (nits)",
        "Red_x": "Red (x)"
    }

    # Mock precision from report.py
    # We must mock the attribute on the *imported module*
    mocker.patch.object(report, 'REPORT_PRECISION', {
        "Brightness": 0,  # No decimals
        "Red_x": 3  # 3 decimals
    })

    # 3. Process the data
    processed_data = helpers.process_device_reports(device_reports_list, ufn_mapping)

    # 4. Check the output
    sn = "NotTV"
    assert sn in processed_data  # <-- This will now pass

    results = processed_data[sn]["results"]

    # Check UFN mapping
    assert "Peak Brightness (nits)" in results
    assert "Red (x)" in results

    # Check formatting
    # Brightness (159.7) should be rounded to 0 decimals -> "160"
    assert results["Peak Brightness (nits)"] == "160"
    # Red_x (0.648) should be 3 decimals -> "0.648"
    assert results["Red (x)"] == "0.648"


def test_create_html_report(mocker, tmp_path):
    """
    Tests the 'create_html_report' function.
    Mocks Jinja2 and uses the real file system via tmp_path.
    """

    # 1. Mock Jinja2 environment and template
    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "<html>Mocked HTML</html>"

    mock_env = mocker.MagicMock(spec=Environment)
    mock_env.get_template.return_value = mock_template
    mocker.patch('src.helpers.Environment', return_value=mock_env)

    # 2. Create REAL input files in tmp_path
    input_file = tmp_path / "report.json"
    input_file.write_text(json.dumps({
        "Brightness": {"status": "PASS"},
        "Red_x": {"actual_values": {"avg": 0.64}}
    }))

    min_fail_file = tmp_path / "min_fail.json"
    min_fail_file.write_text("[]")

    svg_file = tmp_path / "bg.svg"
    svg_file.write_text("<svg></svg>")

    output_file = tmp_path / "output.html"

    device_reports_list = [
        {"SerialNumber": "SN1", "Results": {"Brightness": 100}, "MeasurementDateTime": "2025_01"}
    ]

    # 3. Call the function
    # REFACTORED: Removed rgb_coords and ntsc_coords
    helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        min_fail_file=min_fail_file,
        cie_background_svg=svg_file,
        device_reports=device_reports_list
    )

    # 4. Verify
    mock_env.get_template.assert_called_with(helpers.HTML_TEMPLATE_NAME)
    mock_template.render.assert_called_once()
    assert output_file.exists()
    assert output_file.stat().st_size > 0


# --------------------------------------------------------------------------------
# NEW TESTS for Refactored File System Helpers
# --------------------------------------------------------------------------------

def test_archive_specific_files(mocker, tmp_path):
    """
    Tests the new 'archive_specific_files' helper.
    """
    mock_zip_file = mocker.patch('src.helpers.zipfile.ZipFile')
    mock_zip_instance = mock_zip_file.return_value.__enter__.return_value

    # We mock 'base_folder' to be tmp_path
    base_folder = tmp_path

    # Create dummy files
    file1 = tmp_path / "data" / "report1.json"
    file2 = tmp_path / "results" / "report.html"
    (tmp_path / "data").mkdir()
    (tmp_path / "results").mkdir()
    file1.touch()
    file2.touch()

    files_to_archive = [file1, file2]
    zip_path = tmp_path / "archive.zip"

    # Run the function
    helpers.archive_specific_files(zip_path, files_to_archive, base_folder)

    # Check that write was called twice
    assert mock_zip_instance.write.call_count == 2

    # Check that paths in zip are correct
    mock_zip_instance.write.assert_any_call(file1, Path("data") / "report1.json")
    mock_zip_instance.write.assert_any_call(file2, Path("results") / "report.html")


def test_clear_specific_files(tmp_path):
    """
    Tests the new 'clear_specific_files' helper.
    """
    # Create dummy files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.json"
    file1.touch()
    file2.touch()

    assert file1.exists()
    assert file2.exists()

    # Run cleanup
    helpers.clear_specific_files([file1, file2])

    # Check that files are gone
    assert not file1.exists()
    assert not file2.exists()