# tests/test_report.py

import pytest
import json
from src import report
from collections import defaultdict
import glob
import os
from pathlib import Path


# Используем фикстуру mocker и tmp_path из conftest.py

def test_set_nested_value_new_path():
    """Тестирование создания нового пути вложенного словаря."""
    d = {}
    report.set_nested_value(d, "Results.Brightness.min", 80.0)
    assert d["Results"]["Brightness"]["min"] == 80.0


def test_set_nested_value_merge_dict():
    """Тестирование объединения (update) словарей на конечном уровне."""
    d = {"Results": {"Brightness": {"min": 90.0}}}
    new_data = {"avg": 100.0, "max": 110.0}
    report.set_nested_value(d, "Results.Brightness", new_data)
    # min должен остаться, а avg и max добавиться
    assert d["Results"]["Brightness"] == {"min": 90.0, "avg": 100.0, "max": 110.0}


def test_is_effectively_all_null_stat_package():
    """Тестирование проверки на "пустой" пакет статистики."""
    # Все None (должно быть True)
    assert report.is_effectively_all_null_stat_package({"avg": None, "min": None, "max": None}) is True
    # Список с None (должно быть True)
    assert report.is_effectively_all_null_stat_package({"avg": [None, None], "min": None, "max": None}) is True
    # Скаляр (должно быть False)
    assert report.is_effectively_all_null_stat_package({"avg": 100.0, "min": None, "max": None}) is False
    # Список с числом (должно быть False)
    assert report.is_effectively_all_null_stat_package({"avg": [None, 100.0], "min": None, "max": None}) is False


def create_mock_device_report(tmp_path, device, sn, value):
    """
    Вспомогательная функция для создания фиктивного отчета устройства.
    Имитирует формат вывода report.json_report, подходящий для агрегации.
    """
    report_data = {
        "SerialNumber": sn,
        "MeasurementDateTime": "20250101",
        "Results": {
            "Brightness": value,
            "ArrayData": [value, value + 5]
        }
    }
    filename = Path(tmp_path) / f"{device}_{sn}.json"
    with open(filename, "w") as f:
        json.dump(report_data, f)
    return str(filename)


def test_calculate_full_report_aggregator_logic(mocker, tmp_path):
    """
    Тестирование функции calculate_full_report, которая агрегирует данные
    из отчетов отдельных устройств.
    """
    # 1. Создание фиктивных входных файлов
    reports = [
        create_mock_device_report(tmp_path, "Monitor", "SN1", 100.0),
        create_mock_device_report(tmp_path, "Monitor", "SN2", 120.0),
        create_mock_device_report(tmp_path, "Monitor", "SN3", 110.0),
    ]

    # 2. Мокирование glob.glob для возврата списка файлов
    report_paths = [str(r) for r in reports]
    mocker.patch('src.report.glob.glob', return_value=report_paths)

    output_file = tmp_path / "full_report.json"

    # 3. Вызов тестируемой функции
    report.calculate_full_report(
        input_folder=tmp_path,
        output_file=str(output_file),
        device_name="Monitor"
    )

    # 4. Проверка результатов в выходном файле
    with open(output_file, "r") as f:
        result_data = json.load(f)

    # --- ЛОГИЧНЫЕ ОЖИДАНИЯ (Агрегация всех 3-х отчетов: 100.0, 120.0, 110.0) ---
    # Min: 100.0, Max: 120.0, Avg: (100 + 120 + 110) / 3 = 110.0

    # Проверка агрегированной статистики для скаляра (Brightness)
    brightness_stats = result_data["Results"]["Brightness"]
    assert brightness_stats["min"] == pytest.approx(100.0)
    assert brightness_stats["max"] == pytest.approx(120.0)
    assert brightness_stats["avg"] == pytest.approx(110.0)

    # Проверка агрегированной статистики для списка (ArrayData)
    # Массив: [100.0, 105.0], [120.0, 125.0], [110.0, 115.0]
    # Min: [100.0, 105.0]
    # Max: [120.0, 125.0]
    # Avg: [(100+120+110)/3, (105+125+115)/3] = [110.0, 115.0]
    array_stats = result_data["Results"]["ArrayData"]
    assert array_stats["min"] == pytest.approx([100.0, 105.0])
    assert array_stats["max"] == pytest.approx([120.0, 125.0])
    assert array_stats["avg"] == pytest.approx([110.0, 115.0])