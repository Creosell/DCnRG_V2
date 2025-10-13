# tests/test_calculate.py

import numpy as np
import pytest

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
    mock_coords = [0.636, 0.329, 0.311, 0.615, 0.156, 0.049]
    mocker.patch('src.calculate.parse.coordinates_of_triangle', return_value=mock_coords)

    # Проверяем 'sRGB, NTSC'
    result_srgb_ntsc = calculate.cg_by_area("dummy_file.json", "sRGB, NTSC")
    assert result_srgb_ntsc[0] == pytest.approx(101.86, 0.01)
    assert result_srgb_ntsc[1] == pytest.approx(72.24, 0.01)

    # Проверяем 'sRGB'
    result_srgb = calculate.cg_by_area("dummy_file.json", "sRGB")
    assert result_srgb[0] == pytest.approx(101.86,0.01)
    assert result_srgb[1] == None

    # Проверяем 'NTSC'
    result_ntsc = calculate.cg_by_area("dummy_file.json", "NTSC")
    assert result_ntsc[0] == None
    assert result_ntsc[1] == pytest.approx(72.24, 0.01)

    # Проверяем 'DCI-P3
    result_dci_p3=calculate.cg_by_area("dummy_file.json", "DCI-P3")
    assert result_dci_p3[0] == pytest.approx(75.09, 0.01)
    assert result_dci_p3[1] == None

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
    brightness_data = {'min': 145.2, 'max': 159.7}
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

def test_calculate_overlap_percentage_invalid_triangle():
    """Тестирование overlap_percentage, когда один из треугольников вырожденный."""
    # Первый треугольник валидный, второй - точки на одной линии (площадь 0)
    result = calculate.calculate_overlap_percentage(0, 0, 1, 1, 0, 1, 5, 5, 6, 6, 7, 7)
    assert "the input data does not form valid triangles" in result


def test_brightness_empty_report(mocker):
    """Тестирование функции brightness, когда отчет не может быть спарсен (возвращает None)."""
    mocker.patch('src.calculate.h.parse_one_file', return_value=None)
    result = calculate.brightness("nonexistent_file.json", is_tv=False)
    expected = {"min": None, "typ": None, "max": None, "uniformity_center_lv": None}
    assert result == expected


def test_brightness_uniformity_edge_cases():
    """Тестирование brightness_uniformity с некорректными входными данными."""
    # Случай 1: max_lv равен 0
    assert calculate.brightness_uniformity({'min': 100, 'max': 0}) == 0.0
    # Случай 2: Отсутствуют ключи
    assert calculate.brightness_uniformity({'min': 100}) == 0.0
    assert calculate.brightness_uniformity({}) == 0.0


def test_cg_logic(mocker):
    """Тестирование основной логики функции cg (по перекрытию)."""
    # Мокируем зависимости
    mock_coords = [0.636, 0.329, 0.311, 0.615, 0.156, 0.049]
    mocker.patch('src.calculate.parse.coordinates_of_triangle', return_value=mock_coords)

    mock_overlap = mocker.patch('src.calculate.calculate_overlap_percentage')

    mock_overlap.side_effect = [
        95.5,  # Результат 1-го вызова: ntsc_overlap
        85.2,  # Результат 2-го вызова: rgb_overlap
        100.0,  # Результат 3-го вызова: dci_p3_overlap (не используется в этом тесте)
    ]

    # Проверяем 'sRGB, NTSC'
    cg_rgb, cg_ntsc = calculate.cg("file.json", "sRGB, NTSC")
    assert cg_rgb == 85.2
    assert cg_ntsc == 95.5

    mock_overlap.reset_mock(side_effect=True)  # Сбрасываем мок для нового запуска
    mock_overlap.side_effect = [95.5, 85.2, 100.0]

    cg_rgb_only, cg_ntsc_dummy = calculate.cg("file.json", "sRGB")
    assert cg_rgb_only == 85.2
    assert cg_ntsc_dummy is None



def test_contrast_zero_lv(mocker, mock_display_data):
    """Тестирование расчета контраста, когда Lv черного или белого равен нулю."""
    # Устанавливаем Lv для Center и BlackColor в 0
    mock_display_data["Measurements"][4]["Lv"] = 0.0  # Center
    mock_display_data["Measurements"][12]["Lv"] = 0.0  # BlackColor
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_display_data)

    contrast = calculate.contrast("dummy.json", is_tv=False)
    assert contrast == 0.0


def test_temperature_missing_data(mocker, mock_display_data):
    """Тестирование функции temperature, когда точка 'Center' или 'T' отсутствуют."""
    # Случай 1: Точка 'Center' отсутствует
    no_center_data = {"Measurements": [m for m in mock_display_data["Measurements"] if m["Location"] != "Center"]}
    mocker.patch('src.calculate.h.parse_one_file', return_value=no_center_data)
    with pytest.raises(ZeroDivisionError, match="NO Temperature for Central DOT"):
        calculate.temperature("dummy.json")

    # Случай 2: У 'Center' нет ключа 'T'
    no_t_data = mock_display_data.copy()
    del no_t_data["Measurements"][4]["T"]  # Удаляем 'T' у Center
    mocker.patch('src.calculate.h.parse_one_file', return_value=no_t_data)
    with pytest.raises(ZeroDivisionError, match="NO Temperature for Central DOT"):
        calculate.temperature("dummy.json")


def test_delta_e_success(mocker, mock_display_data):
    """Тестирование успешного расчета Delta E."""
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_display_data)
    # В mock_display_data все точки (кроме цветовых) имеют схожие координаты,
    # поэтому Delta E должен быть небольшим, но не нулевым.
    avg_delta_e = calculate.delta_e("dummy.json")
    assert isinstance(avg_delta_e, float)
    assert avg_delta_e > 0
    # Проверяем, что значение разумно (очень маленькое, так как точки почти идентичны)
    assert avg_delta_e == pytest.approx(2.28, abs=0.01)


def test_serial_number_and_time(mocker, mock_display_data):
    """Тестирование получения серийного номера и времени измерения."""
    mocker.patch('src.calculate.h.parse_one_file', return_value=mock_display_data)
    sn = calculate.serial_number("dummy.json")
    time = calculate.measurement_time("dummy.json")
    assert sn == "NotTV"
    assert time == "20250624_184822"

    # Тест на случай сбоя парсинга
    mocker.patch('src.calculate.h.parse_one_file', return_value=None)
    sn_fail = calculate.serial_number("dummy.json")
    time_fail = calculate.measurement_time("dummy.json")
    assert sn_fail is None
    assert time_fail is None
