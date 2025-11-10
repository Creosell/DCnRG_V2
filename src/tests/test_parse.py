# tests/test_parse.py

import pytest
import yaml
import json

from src import parse


# --------------------------------------------------------------------------------
# NEW / MOVED TESTS for parse_one_file (formerly in test_helpers.py)
# --------------------------------------------------------------------------------

def test_parse_one_file_success(tmp_path, mock_display_data):
    """Tests successful parsing of a single JSON file."""
    test_file = tmp_path / "test_report.json"
    with open(test_file, "w") as f:
        json.dump(mock_display_data, f)

    # We test the function now located in 'parse'
    data = parse.parse_one_file(str(test_file))

    assert data is not None
    assert data["SerialNumber"] == "NotTV"
    assert len(data["Measurements"]) == 13


def test_parse_one_file_failure(tmp_path):
    """Tests parse_one_file on non-existent and corrupt files."""
    # File not found
    assert parse.parse_one_file(tmp_path / "nonexistent.json") is None

    # Corrupt JSON
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{'invalid': 'json'}")
    assert parse.parse_one_file(bad_file) is None


# --------------------------------------------------------------------------------
# Unchanged YAML Tests
# --------------------------------------------------------------------------------

def test_parse_yaml_success(tmp_path, mock_yaml_data):
    """Tests successful parsing of a value from a YAML file."""
    yaml_file = tmp_path / "config.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    value = parse.parse_yaml(str(yaml_file), "main_tests", "Brightness", "min")
    assert value == 80.0


# ... (other YAML tests like test_coordinate_srgb_ntsc are fine) ...

# --------------------------------------------------------------------------------
# Refactored Tests (Passing Dicts)
# --------------------------------------------------------------------------------

def test_coordinates_of_triangle_success(mock_display_data):
    """
    Tests triangle coordinate extraction from a data dictionary.
    """
    # REFACTORED: Pass the mock data dictionary directly. No mocks needed.
    coords = parse.coordinates_of_triangle(mock_display_data)

    # Coordinates from NotTV.json:
    # Red: x=0.648, y=0.336
    # Green: x=0.304, y=0.63
    # Blue: x=0.152, y=0.06
    expected = [0.648, 0.336, 0.304, 0.63, 0.152, 0.06]
    assert coords == pytest.approx(expected)


def test_coordinates_of_triangle_missing_color(mock_display_data):
    """Tests coordinates_of_triangle when a color is missing."""
    # Remove GreenColor from data
    filtered_measurements = [m for m in mock_display_data["Measurements"] if m["Location"] != "GreenColor"]
    mock_display_data["Measurements"] = filtered_measurements

    # REFACTORED: Pass the modified dict
    coords = parse.coordinates_of_triangle(mock_display_data)

    # Expect only 4 coordinates (Red and Blue)
    expected = [0.648, 0.336, 0.152, 0.06]
    assert coords == pytest.approx(expected)


def test_get_coordinates_logic(mock_display_data):
    """Tests get_coordinates for a non-TV device."""
    # REFACTORED: Pass dict
    coords = parse.get_coordinates(mock_display_data, is_tv_flag=False)

    assert coords["Red_x"] == 0.648

    # --- FIX IS HERE ---
    # Check 'Center' keys, which come from the 'Center' location
    assert coords["Center_y"] == 0.328  # From 'Center'
    assert coords["Center_x"] == 0.309  # From 'Center'
    # The key "White_x" is never created, so this assertion is removed
    # assert coords["White_x"] is None
    # --- END OF FIX ---


def test_get_coordinates_tv_logic(mock_tv_data):
    """Tests get_coordinates for a TV device."""
    # REFACTORED: Pass dict
    coords = parse.get_coordinates(mock_tv_data, is_tv_flag=True)

    assert coords["Red_x"] == 0.648

    # --- FIX IS HERE ---
    # Check 'Center' keys, which come from the 'WhiteColor' location
    assert coords["Center_y"] == 0.348  # From 'WhiteColor'
    assert coords["Center_x"] == 0.339  # From 'WhiteColor'
    # The key "White_x" is never created, so this assertion is removed
    # assert coords["White_x"] is None
    # --- END OF FIX ---


def test_find_closest_to_target(mock_display_data):
    """Tests finding the closest point to a target (Unchanged)."""
    target_x, target_y = 0.3, 0.3
    # This test was already correct, passing a dict.
    closest = parse.find_closest_to_target(mock_display_data, target_x, target_y)

    assert closest["Location"] != "RedColor"
    assert "Center" in closest["Location"]


def test_get_device_info_success(mocker, mock_display_data, tmp_path):
    """Tests extracting device info. This function still reads files."""
    # REFACTORED: Mock the new location of parse_one_file
    mocker.patch('src.parse.parse_one_file', return_value=mock_display_data)

    # We still need a dummy file path to pass to the function
    dummy_file_path = tmp_path / "dummy.json"

    device_config, is_tv, sn = parse.get_device_info(dummy_file_path)

    assert device_config == "SDNB-15iA"
    assert is_tv is False
    assert sn == "NotTV"


def test_get_device_info_failure(mocker, tmp_path):
    """Tests get_device_info when file parsing fails."""
    # REFACTORED: Mock the new location
    mocker.patch('src.parse.parse_one_file', return_value=None)

    dummy_file_path = tmp_path / "bad_file.json"
    device_config, is_tv, sn = parse.get_device_info(dummy_file_path)

    # The function explicitly returns (None, False, None) on parse failure
    assert device_config is None
    assert is_tv is False
    assert sn is None