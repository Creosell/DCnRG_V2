# tests/test_parse1.py

import pytest
import yaml

from src import parse


# Параметр tmp_path предоставляет временную папку для создания тестовых файлов.
# Фикстура mocker позволяет нам подменять функции.

def test_parse_yaml_success(tmp_path, mock_yaml_data):
    """Тестирование успешного парсинга значения из YAML-файла."""
    # Создаем фиктивный YAML-файл
    yaml_file = tmp_path / "config.yaml"
    with open(yaml_file, "w") as f:
        yaml.safe_dump(mock_yaml_data, f)

    # Проверяем получение вложенного значения
    value = parse.parse_yaml(str(yaml_file), "main_tests", "Brightness", "min")
    assert value == 80.0

    # Проверяем случай, когда ключ не найден
    value_none = parse.parse_yaml(str(yaml_file), "main_tests", "NonExistentKey", "min")
    assert value_none is None


def test_coordinate_srgb_ntsc(mocker, mock_yaml_data):
    """Тестирование функций coordinate_srgb и coordinate_ntsc с мокированием parse_yaml."""
    # Заглушаем функцию parse_yaml, чтобы она возвращала тестовые координаты по очереди
    mock_results = [0.64, 0.33, 0.30, 0.60, 0.15, 0.06]
    mocker.patch('src.parse.parse_yaml', side_effect=mock_results)

    # sRGB должен вернуть 6 координат
    coords_srgb = parse.coordinate_srgb("dummy_file.yaml")
    assert coords_srgb == mock_results
    assert parse.parse_yaml.call_count == 6

    # Сбрасываем счетчик мока и тестируем NTSC
    parse.parse_yaml.reset_mock()
    mock_results_ntsc = [0.67, 0.33, 0.30, 0.60, 0.15, 0.06]  # 6 значений для NTSC
    mocker.patch('src.parse.parse_yaml', side_effect=mock_results_ntsc)

    # NTSC должен вернуть 6 координат (исходя из логики парсинга)
    coords_ntsc = parse.coordinate_ntsc("dummy_file.yaml")
    assert coords_ntsc == mock_results_ntsc


def test_coordinates_of_triangle_success(mocker, mock_display_data):
    """
    Тестирование извлечения координат треугольника устройства из JSON.
    Используем mock_display_data с реальными координатами.
    """
    # Заглушаем функцию parse_one_file
    mocker.patch('src.helpers.parse_one_file', return_value=mock_display_data)
    mocker.patch('src.parse.h.parse_one_file', return_value=mock_display_data)

    coords = parse.coordinates_of_triangle("dummy_report.json")
    # Координаты из NotTV.json:
    # Red: x=0.648, y=0.336
    # Green: x=0.304, y=0.63
    # Blue: x=0.152, y=0.06
    expected = [0.648, 0.336, 0.304, 0.63, 0.152, 0.06]
    assert coords == pytest.approx(expected)


def test_get_device_info_success(mocker, mock_display_data):
    """Тестирование извлечения информации об устройстве. Используем mock_display_data."""
    # Заглушаем h.parse_one_file
    mocker.patch('src.parse.h.parse_one_file', return_value=mock_display_data)

    device_config, is_tv, sn = parse.get_device_info("dummy_file.json")

    # Ожидаемые значения из NotTV.json
    assert device_config == "15iA"
    assert is_tv is False
    assert sn == "NotTV"


def test_get_device_info_failure(mocker):
    """Тестирование get_device_info при ошибке парсинга файла."""
    # Заглушаем h.parse_one_file на возврат None
    mocker.patch('src.parse.h.parse_one_file', return_value=None)

    device_config, is_tv, sn = parse.get_device_info("bad_file.json")

    assert device_config is None
    assert is_tv is False
    assert sn is None