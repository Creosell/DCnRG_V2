# tests/test_calculate.py

import numpy as np
import pytest

from src import calculate
from src import parse  # Import parse to use its functions if needed
# We need to import the Enum to check the new dictionary keys
from src.calculate import ColorSpace


# We use fixtures from conftest.py (mock_tv_data, mock_display_data, etc.)

# --------------------------------------------------------------------------------
# Math tests (Unchanged)
# --------------------------------------------------------------------------------

def test_area_valid_triangle():
    """Tests area calculation for a valid triangle."""
    p = np.array([[0, 0], [3, 0], [0, 4]])
    assert calculate.area(p) == pytest.approx(6.0)


def test_calculate_overlap_percentage_invalid_triangle():
    """Tests overlap_percentage when one triangle has zero area."""
    # Valid triangle 1, degenerate triangle 2
    result = calculate.calculate_overlap_percentage(0, 0, 1, 1, 0, 1, 5, 5, 6, 6, 7, 7)
    assert "the input data does not form valid triangles" in result


# ... (other pure math tests like overlap are fine) ...

# --------------------------------------------------------------------------------
# Refactored Calculation Tests (No Mocks Needed)
# --------------------------------------------------------------------------------

def test_brightness_logic_tv(mock_tv_data):
    """Checks brightness logic for TV (typ = WhiteColor Lv)."""
    # REFACTORED: Pass the mock data dictionary directly
    brightness_tv = calculate.brightness(mock_tv_data, is_tv=True)

    # TV: typ=WhiteColor(200.0), min=145.2, max=166.0 (from uniformity points)
    assert brightness_tv['typ'] == pytest.approx(200.0, abs=0.1)
    assert brightness_tv['min'] == pytest.approx(145.2, abs=0.1)
    assert brightness_tv['max'] == pytest.approx(166.0, abs=0.1)


def test_brightness_logic_display(mock_display_data):
    """Checks brightness logic for Display (typ=Center Lv)."""
    # REFACTORED: Pass the mock data dictionary directly
    brightness_disp = calculate.brightness(mock_display_data, is_tv=False)

    # Display: typ=Center(159.7), min=145.2, max=166.0
    assert brightness_disp['typ'] == pytest.approx(159.7, abs=0.1)
    assert brightness_disp['min'] == pytest.approx(145.2, abs=0.1)
    assert brightness_disp['max'] == pytest.approx(166.0, abs=0.1)


def test_brightness_empty_report():
    """Tests brightness function when passed None."""
    # REFACTORED: Pass None directly
    result = calculate.brightness(None, is_tv=False)
    expected = {"min": None, "typ": None, "max": None, 'uniformity_center_lv': None}
    assert result == expected


def test_brightness_uniformity():
    """Checks brightness uniformity calculation."""
    brightness_data = {'min': 145.2, 'max': 166.0}  # Using max, not typ
    uniformity = calculate.brightness_uniformity(brightness_data)
    # (145.2 / 166.0) * 100
    assert uniformity == pytest.approx(87.47, abs=0.01)

    # Handle division by zero
    brightness_data_zero = {'min': 150, 'max': 0}
    assert calculate.brightness_uniformity(brightness_data_zero) == 0.0


def test_contrast_logic(mock_tv_data, mock_display_data):
    """Checks contrast logic for TV and non-TV."""
    black_lv = 0.6183643  # From mock data

    # Case 1: TV (is_tv = True). Contrast = WhiteColor (200.0) / BlackColor
    # REFACTORED: Pass dict
    contrast_tv = calculate.contrast(mock_tv_data, is_tv=True)
    # The function now rounds to 2 decimal places
    expected_tv = round(200.0 / black_lv, 2) # 323.44
    assert contrast_tv == pytest.approx(expected_tv)

    # Case 2: Not-TV (is_tv = False). Contrast = Center Lv (159.7) / BlackColor
    # REFACTORED: Pass dict
    contrast_nottv = calculate.contrast(mock_display_data, is_tv=False)
    # The function now rounds to 2 decimal places
    expected_nottv = round(159.7 / black_lv, 2) # 258.26
    assert contrast_nottv == pytest.approx(expected_nottv)


def test_contrast_zero_lv(mock_display_data):
    """Tests contrast calculation when Lv is zero."""
    mock_display_data["Measurements"][4]["Lv"] = 0.0  # Center
    mock_display_data["Measurements"][12]["Lv"] = 0.0  # BlackColor

    contrast = calculate.contrast(mock_display_data, is_tv=False)
    assert contrast == 0.0


def test_temperature_extraction(mock_tv_data):
    """Checks color temperature (T) extraction from the center point."""
    # REFACTORED: Pass dict
    temp = calculate.temperature(mock_tv_data)
    # T for Center in mock_tv_data = 6752
    assert temp == 6752


def test_temperature_missing_data(mock_display_data):
    """Tests temperature function when 'Center' point or 'T' key is missing."""
    # Case 1: 'Center' point is missing
    no_center_data = {"Measurements": [m for m in mock_display_data["Measurements"] if m["Location"] != "Center"]}
    with pytest.raises(ZeroDivisionError, match="NO Temperature for Central DOT"):
        calculate.temperature(no_center_data)

    # Case 2: 'Center' has no 'T' key
    no_t_data = mock_display_data.copy()
    del no_t_data["Measurements"][4]["T"]  # Remove 'T' from Center
    with pytest.raises(ZeroDivisionError, match="NO Temperature for Central DOT"):
        calculate.temperature(no_t_data)


def test_cg_by_area_logic(mocker, mock_display_data):
    """Tests color gamut calculation by area."""
    # REFACTORED: Function signature changed.
    mock_coords = [0.636, 0.329, 0.311, 0.615, 0.156, 0.049]
    mocker.patch('src.parse.coordinates_of_triangle', return_value=mock_coords)

    # Call the new function (no 'color_space' argument)
    result_map = calculate.cg_by_area(mock_display_data)

    # Check the dictionary result using the Enum
    assert result_map[ColorSpace.SRGB] == pytest.approx(101.86, 0.01)
    assert result_map[ColorSpace.NTSC] == pytest.approx(72.24, 0.01)
    assert result_map[ColorSpace.DCI_P3] is not None # Check that it was calculated


def test_delta_e_success(mock_display_data):
    """Tests successful Delta E calculation."""
    # REFACTORED: Pass dict
    avg_delta_e = calculate.delta_e(mock_display_data)
    assert isinstance(avg_delta_e, float)
    assert avg_delta_e > 0
    assert avg_delta_e == pytest.approx(2.28, abs=0.01)


# --------------------------------------------------------------------------------
# NEW TESTS for Refactored Logic
# --------------------------------------------------------------------------------

def test_run_calculations_fulltest(mock_display_data):
    """
    Tests the main 'run_calculations' function.
    Ensures all keys are calculated and returned.
    """
    # REFACTORED: Call the new function signature (no test_type or color_space)
    results = calculate.run_calculations(
        mock_display_data,
        is_tv=False
    )

    # Check that all keys are present
    expected_keys = [
        "brightness", "brightness_uniformity", "contrast",
        "cg_by_area_rgb", "cg_by_area_ntsc", "cg_rgb", "cg_ntsc",
        "temperature", "delta_e", "coordinates"
    ]
    assert all(key in results for key in expected_keys)

    # Check a few values
    assert results["brightness"] == pytest.approx(159.7)
    assert results["contrast"] == pytest.approx(round(159.7 / 0.6183643, 2))
    assert results["temperature"] == 6752


def test_run_calculations_handles_error(mock_display_data):
    """
    Tests that 'run_calculations' handles an internal error gracefully
    and returns None for the failed key.
    """
    # Remove 'Center' to force 'temperature' to fail
    no_center_data = {"Measurements": [m for m in mock_display_data["Measurements"] if m["Location"] != "Center"]}

    # REFACTORED: Call the new function signature
    results = calculate.run_calculations(
        no_center_data,
        is_tv=False
    )

    # Check that the failing key exists and is None
    assert "temperature" in results
    assert results["temperature"] is None

    # Check that other keys were still calculated successfully
    assert "contrast" in results
    assert results["contrast"] == 0.0  # Fails because 'Center' is missing
    assert "brightness" in results
    assert results["brightness"] is None  # Fails because 'Center' is missing