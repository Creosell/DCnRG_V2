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

    # --- FIX IS HERE ---
    # Tell the render function to return an actual string
    mock_template.render.return_value = "<html>Mocked HTML</html>"
    # --- END OF FIX ---

    mock_env = mocker.MagicMock(spec=Environment)
    mock_env.get_template.return_value = mock_template
    mocker.patch('src.helpers.Environment', return_value=mock_env)

    # 2. Create REAL input files in tmp_path
    # ... (rest of the file creation is correct) ...
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
    helpers.create_html_report(
        input_file=input_file,
        output_file=output_file,
        min_fail_file=min_fail_file,
        cie_background_svg=svg_file,
        rgb_coords=[0.64, 0.33, 0.30, 0.60, 0.15, 0.06],
        ntsc_coords=[0.67, 0.33, 0.21, 0.71, 0.14, 0.08],
        device_reports=device_reports_list
    )

    # 4. Verify
    mock_env.get_template.assert_called_with(helpers.HTML_TEMPLATE_NAME)

    # Check that render was called
    mock_template.render.assert_called_once()  # Now we check the call

    # Check that the REAL output file was created and has content
    assert output_file.exists()
    assert output_file.stat().st_size > 0  # Will be > 0 because we wrote "<html>...</html>"


# --------------------------------------------------------------------------------
# Unchanged File System Tests
# --------------------------------------------------------------------------------

def test_archive_reports_logic(mocker, tmp_path):
    """Tests archive creation (Fixed)."""
    mock_zip_file = mocker.patch('src.helpers.zipfile.ZipFile')
    mock_zip_instance = mock_zip_file.return_value.__enter__.return_value

    # --- FIX IS HERE ---
    # We must mock Path.cwd() to return our tmp_path.
    # This makes the function believe tmp_path is the project root.
    mocker.patch('src.helpers.Path.cwd', return_value=tmp_path)
    # --- END OF FIX ---

    # Create dummy folders and files inside tmp_path
    folder1 = tmp_path / "device_reports"
    folder1.mkdir()
    file_to_archive = folder1 / "report1.json"
    file_to_archive.touch()

    # Run the function
    helpers.archive_reports("TestDevice", "20251010", [folder1])

    # Now, relative_to(Path.cwd()) will succeed, and write() will be called.
    assert mock_zip_instance.write.call_count == 1

    # We can add a more robust check:
    expected_path_in_zip = Path("device_reports") / "report1.json"
    mock_zip_instance.write.assert_called_with(
        file_to_archive,  # The full, absolute path to the source file
        expected_path_in_zip  # The relative path inside the archive
    )


def test_clear_folders_logic(tmp_path):
    """Tests folder cleanup (unchanged)."""
    folder_to_clear = tmp_path / "folder1"
    folder_to_clear.mkdir()
    (folder_to_clear / "file1.txt").touch()

    assert (folder_to_clear / "file1.txt").exists()
    helpers.clear_folders([folder_to_clear])
    assert not (folder_to_clear / "file1.txt").exists()