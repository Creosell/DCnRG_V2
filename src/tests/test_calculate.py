# tests/test_calculate.py

import pytest
import numpy as np
from src import calculate


# Используем фикстуры mocker, mock_tv_data, mock_display_data, mock_black_lv из conftest.py

# --------------------------------------------------------------------------------
# Исходные тесты (area, overlap, cg_by_area)
# --------------------------------------------------------------------------------

def test_area_valid_triangle():
    """Тестирование расчета площади правильного треугольника (3 точки)."""
    # Прямоугольный треугольник с катетами 3 и 4. Площадь = 0.5 * 3 * 4 = 6.0
    p = np.array([[0, 0], [3, 0], [0, 4]])
    assert calculate.area(p) == pytest.approx(6.0)


def test_area_degenerate_triangle():
    """Тестирование расчета площади для вырожденного треугольника (точки на одной линии)."""
    # Точки на линии Y=1
    p = np.array([[1, 1], [5, 1], [10, 1]])
    assert calculate.area(p) == pytest.approx(0.0)


def test_calculate_overlap_percentage_no_overlap(mocker):
    """Тестирование расчета перекрытия, когда его нет (мокируем Shapely)."""
    # Мокируем создание Polygon и Intersection, чтобы не зависеть от Shapely/Numpy
    mock_poly1 = mocker.MagicMock(area=10.0)
    mock_poly2 = mocker.MagicMock()
    mock_intersection = mocker.MagicMock(is_empty=True, area=0.0)
    mock_poly1.intersection.return_value = mock_intersection

    # Мокируем Shapely.Polygon в src.calculate
    mocker.patch('src.calculate.Polygon', side_effect=[mock_poly1, mock_poly2])

    # ИСПРАВЛЕНИЕ: Используем координаты, которые образуют валидные треугольники
    # Например, два простых треугольника, чтобы избежать раннего выхода с ошибкой.
    valid_coords = [0, 0, 1, 0, 0, 1, 10, 10, 11, 10, 10, 11]

    result = calculate.calculate_overlap_percentage(*valid_coords)  # Передаем валидные координаты

    # intersection.area / polygon1.area * 100 = 0.0 / 10.0 * 100 = 0.0
    assert result == pytest.approx(0.0)

    # intersection.area / polygon1.area * 100 = 0.0 / 10.0 * 100 = 0.0
    assert result == pytest.approx(0.0)


def test_calculate_overlap_percentage_full_overlap(mocker):
    """Тестирование расчета перекрытия, когда второе полностью внутри первого (мокируем Shapely)."""
    # Мокируем создание Polygon и Intersection
    mock_poly1 = mocker.MagicMock(area=10.0)
    mock_poly2 = mocker.MagicMock(area=5.0)
    # Пересечение равно площади второго полигона (5.0)
    mock_intersection = mocker.MagicMock(is_empty=False, area=5.0)
    mock_poly1.intersection.return_value = mock_intersection

    mocker.patch('src.calculate.Polygon', side_effect=[mock_poly1, mock_poly2])

    valid_coords = [0, 0, 1, 0, 0, 1, 10, 10, 11, 10, 10, 11]

    result = calculate.calculate_overlap_percentage(*valid_coords)  # Передаем валидные координаты

    # intersection.area / polygon1.area * 100 = 5.0 / 10.0 * 100 = 50.0
    assert result == pytest.approx(50.0)


def test_cg_by_area_logic(mocker):
    """Тестирование расчета цветового охвата по площади."""
    # Мокируем parse.coordinates_of_triangle, чтобы вернуть R, G, B координаты
    # (эти координаты формируют треугольник с площадью ~0.14)
    mock_coords = [0.640, 0.330, 0.300, 0.600, 0.150, 0.060]
    mocker.patch('src.calculate.parse.coordinates_of_triangle', return_value=mock_coords)

    # Мокируем функцию area, чтобы она возвращала фиксированную площадь для треугольника устройства
    mocker.patch('src.calculate.area', return_value=0.140)

    # sRGB = 0.112 (из mock_yaml_data)
    # NTSC = 0.158 (из mock_yaml_data)

    # 0.140 / 0.112 * 100 = 125.0
    # 0.140 / 0.158 * 100 = ~88.6

    # Проверяем 'sRGB, NTSC'
    result_srgb_ntsc = calculate.cg_by_area("dummy_file.json", "sRGB, NTSC")
    assert result_srgb_ntsc[0] == pytest.approx(125.0)
    assert result_srgb_ntsc[1] == pytest.approx(88.60759493670887)

    # Проверяем 'sRGB'
    result_srgb = calculate.cg_by_area("dummy_file.json", "sRGB")
    assert result_srgb[0] == pytest.approx(125.0)
    assert result_srgb[1] == None

    # Проверяем 'NTSC'
    result_ntsc = calculate.cg_by_area("dummy_file.json", "NTSC")
    assert result_ntsc[0] == None
    assert result_ntsc[1] == pytest.approx(88.60759493670887)


# --------------------------------------------------------------------------------
# Конвертированные тесты (brightness, uniformity, contrast, temperature) из test_calculate1.py
# --------------------------------------------------------------------------------

def test_brightness_logic_tv(mocker, mock_tv_data):
    """Проверяет расчет яркости для TV (typ = WhiteColor Lv, min/max = uniformity points)."""
    # Мокируем зависимость h.parse_one_file
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_tv_data)
    brightness_tv = calculate.brightness("dummy_tv.json", is_tv=True)
    # TV: typ=WhiteColor(200.0), min=145.2, max=200.0 (так как WhiteColor - самая яркая)
    assert brightness_tv['typ'] == pytest.approx(200.0, abs=0.1)
    assert brightness_tv['min'] == pytest.approx(145.2, abs=0.1)
    assert brightness_tv['max'] == pytest.approx(166.0, abs=0.1)


def test_brightness_logic_display(mocker, mock_display_data):
    """Проверяет расчет яркости для Display (не-TV) (typ=Center Lv)."""
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_display_data)
    brightness_disp = calculate.brightness("dummy_nottv.json", is_tv=False)
    # Display: typ=Center(159.7), min=145.2, max=166.0
    assert brightness_disp['typ'] == pytest.approx(159.7, abs=0.1)
    assert brightness_disp['min'] == pytest.approx(145.2, abs=0.1)
    assert brightness_disp['max'] == pytest.approx(166.0, abs=0.1)


def test_brightness_uniformity():
    """Проверяет расчет равномерности яркости."""
    # Случай 1: Стандартные данные
    brightness_data = {'min': 145.2, 'uniformity_center_lv': 159.7}
    uniformity = calculate.brightness_uniformity(brightness_data)
    # (1 - (min / typ)) * 100 = 9.0795...
    assert uniformity == pytest.approx(90.92, abs=0.01)

    # Случай 2: typ = 0 (Uniformity = 0.0)
    brightness_data_zero = {'min': 150, 'typ': 0}
    assert calculate.brightness_uniformity(brightness_data_zero) == 0.0


def test_contrast_logic(mocker, mock_tv_data, mock_display_data, mock_black_lv):
    """Проверяет расчет контрастности для TV и не-TV."""

    # # Мокируем функцию извлечения Lv для BlackColor (добавлена в calculate.py)
    # # NOTE: В реальной жизни нужно убедиться, что get_black_lv определена в calculate.py или импортирована.
    # mocker.patch('src.calculate.get_black_lv', return_value=mock_black_lv)  # 0.6183643

    # Случай 1: TV (is_tv = True). Контраст = WhiteColor (200.0) / BlackColor (0.6183643)
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_tv_data)
    contrast_tv = calculate.contrast("dummy_tv.json", is_tv=True)
    expected_tv = 200.0 / mock_black_lv
    assert contrast_tv == pytest.approx(expected_tv, abs=0.01)

    # Случай 2: Не-TV (is_tv = False). Контраст = Center Lv (159.7) / BlackColor (0.6183643)
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_display_data)
    contrast_nottv = calculate.contrast("dummy_nottv.json", is_tv=False)
    expected_nottv = 159.7 / mock_black_lv
    assert contrast_nottv == pytest.approx(expected_nottv, abs=0.01)


def test_temperature_extraction(mocker, mock_tv_data):
    """Проверяет извлечение цветовой температуры (T) из центральной точки."""
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_tv_data)
    temp = calculate.temperature("dummy_tv.json")
    # T для Center в mock_tv_data = 6752
    assert temp == 6752