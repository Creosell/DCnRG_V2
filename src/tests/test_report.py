# tests/test_report.py

import json
from pathlib import Path

import pytest

from src import report


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

def test_json_report_creates_file(tmp_path):
    """Тестирование, что json_report успешно создает файл с корректной структурой."""
    output_folder = tmp_path
    device_name = "TestDevice"
    sn = "SN001"
    t = "Time001"

    report.json_report(
        sn=sn, t=t, brightness=100.5, contrast=1000,
        output_folder=output_folder, device_name=device_name
    )

    expected_file = output_folder / f"{device_name}_{sn}_{t}.json"
    assert expected_file.exists()

    with open(expected_file, "r") as f:
        data = json.load(f)

    assert data["SerialNumber"] == sn
    assert data["Results"]["Brightness"] == 100.5
    assert data["Results"]["Contrast"] == 1000


def test_calculate_full_report_file_errors(mocker, tmp_path):
    """Тестирование calculate_full_report на устойчивость к ошибкам в файлах."""
    # Файл с ошибкой декодирования JSON
    bad_json_path = tmp_path / "Monitor_SN1.json"
    with open(bad_json_path, "w") as f:
        f.write("{'bad': json,}")

    # Файл с корректным JSON, но без ключа 'Results'
    no_results_path = tmp_path / "Monitor_SN2.json"
    with open(no_results_path, "w") as f:
        json.dump({"SerialNumber": "SN2"}, f)

    mocker.patch('src.report.glob.glob', return_value=[str(bad_json_path), str(no_results_path)])

    output_file = tmp_path / "full_report.json"
    # Функция должна отработать без ошибок, пропустив "плохие" файлы
    report.calculate_full_report(tmp_path, str(output_file), "Monitor")

    # Проверяем, что выходной файл создан, но пуст, так как все входные файлы были проблемными
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result["SerialNumber"] == ["SN2"]  # SN1 не добавился из-за ошибки парсинга
    assert result["Results"] == {}  # Данных для агрегации не было


def test_generate_comparison_report_logic(tmp_path, mock_yaml_data):
    """Тестирование основной логики generate_comparison_report (PASS/FAIL/N/A)."""
    # 1. Создаем JSON с результатами
    full_report_data = {
        "Results": {
            "Brightness": {"avg": 110.0, "min": 85.0},
            "Temperature": {"avg": 6900, "max": 7000, "min": 6000},  # <-- Добавлен 'min'
            "Coordinates": {
                "Red_x": {"min": 0.61, "max": 0.65}
            }
        }
    }
    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    # 2. Создаем YAML с ожиданиями
    mock_yaml_data["main_tests"]["Temperature"].update({"typ": 6500.0, "min": 5500.0})
    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        json.dump(mock_yaml_data, f)

    # 3. Выполняем сравнение
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(str(json_file), str(yaml_file), str(output_file), is_tv_flag=False)

    # 4. Проверяем результат
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result["Brightness"]["status"] == "PASS"
    assert "Actual avg (110.0) >= Expected typ (100.0)" in result["Brightness"]["reason"]

    assert result["Temperature"]["status"] == "FAIL"
    assert "Actual max (7000) > Expected max (6800.0)" in result["Temperature"]["reason"]

    assert result["Red_x"]["status"] == "FAIL"
    assert "Actual min (0.61) < Expected min (0.62)" in result["Red_x"]["reason"]

    assert result["White_x"]["status"] == "N/A"
    assert "is null or missing in JSON" in result["White_x"]["reason"]


@pytest.mark.parametrize(
    "actual_avg, expected_status, expected_reason_part",
    [
        # Случай 1: Явный PASS. Среднее значение выше ожидаемого.
        (1100.0, "PASS", "Actual avg (1100.0) >= Expected typ (935.0)"),

        # Случай 2: Граничный PASS. Среднее значение находится точно на границе допуска (1000 - 6.5% = 935).
        (935.0, "PASS", "Actual avg (935.0) >= Expected typ (935.0)"),

        # Случай 3: Граничный FAIL. Среднее значение чуть ниже границы допуска.
        (934.9, "FAIL", "Actual avg (934.9) < Expected typ (935.0)"),

        # Случай 4: Явный FAIL. Среднее значение значительно ниже допуска.
        (900.0, "FAIL", "Actual avg (900.0) < Expected typ (935.0)"),
    ],
)
def test_generate_comparison_report_tv_contrast_tolerance_scenarios(
        tmp_path, mock_yaml_data, actual_avg, expected_status, expected_reason_part
):
    """
    Тестирование различных сценариев (PASS/FAIL) для допуска контраста на ТВ.
    """
    # 1. Настройка данных
    full_report_data = {
        "Results": {"Contrast": {"avg": actual_avg, "min": 850.0}}  # min проходит всегда
    }
    mock_yaml_data["main_tests"]["Contrast"] = {"min": 800.0, "typ": 1000.0}

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        json.dump(mock_yaml_data, f)

    # 2. Выполнение сравнения с флагом is_tv_flag=True
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(str(json_file), str(yaml_file), str(output_file), is_tv_flag=True)

    # 3. Проверка результата
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result["Contrast"]["status"] == expected_status
    assert expected_reason_part in result["Contrast"]["reason"]


# Параметризация по всем ключам, где для ТВ пропускается проверка avg
@pytest.mark.parametrize("skipped_key_yaml", list(report.AVG_FAIL_SKIP_KEYS_FOR_TV))
def test_generate_comparison_report_tv_avg_skip_pass_on_min(
        tmp_path, mock_yaml_data, skipped_key_yaml
):
    """
    Проверяет, что для всех пропускаемых ключей ТВ получает PASS,
    если min значение в норме, даже если avg ниже ожидаемого.
    """
    # 1. Настройка данных
    # avg ниже typ, но min выше порога
    actual_values = {"avg": 90.0, "min": 85.0}
    expected_values = {"min": 80.0, "typ": 100.0}

    # В YAML ключи могут быть с подчеркиванием, а в JSON - CamelCase
    key_in_json = report.YAML_TO_JSON_KEY_MAP.get(skipped_key_yaml, skipped_key_yaml)


    full_report_data = {"Results": {key_in_json: actual_values}}
    mock_yaml_data["main_tests"][skipped_key_yaml] = expected_values

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        json.dump(mock_yaml_data, f)

    # 2. Выполнение сравнения
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(str(json_file), str(yaml_file), str(output_file), is_tv_flag=True)

    # 3. Проверка
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result[skipped_key_yaml]["status"] == "PASS"
    assert "(TV) Actual min (85.0) >= Expected min (80.0)" in result[skipped_key_yaml]["reason"]


@pytest.mark.parametrize("skipped_key_yaml", list(report.AVG_FAIL_SKIP_KEYS_FOR_TV))
def test_generate_comparison_report_tv_avg_skip_fail_on_min(
        tmp_path, mock_yaml_data, skipped_key_yaml
):
    """
    Проверяет, что для всех пропускаемых ключей ТВ получает FAIL,
    если min значение ниже нормы, несмотря на пропуск проверки avg.
    """
    # 1. Настройка данных
    # avg ниже typ, и min тоже ниже порога
    actual_values = {"avg": 90.0, "min": 75.0}
    expected_values = {"min": 80.0, "typ": 100.0}

    key_in_json = report.YAML_TO_JSON_KEY_MAP.get(skipped_key_yaml, skipped_key_yaml)

    full_report_data = {"Results": {key_in_json: actual_values}}
    mock_yaml_data["main_tests"][skipped_key_yaml] = expected_values

    json_file = tmp_path / "full_report.json"
    with open(json_file, "w") as f:
        json.dump(full_report_data, f)

    yaml_file = tmp_path / "expected.yaml"
    with open(yaml_file, "w") as f:
        json.dump(mock_yaml_data, f)

    # 2. Выполнение сравнения
    output_file = tmp_path / "comparison.json"
    report.generate_comparison_report(str(json_file), str(yaml_file), str(output_file), is_tv_flag=True)

    # 3. Проверка
    with open(output_file, "r") as f:
        result = json.load(f)

    assert result[skipped_key_yaml]["status"] == "FAIL"
    assert "Actual min (75.0) < Expected min threshold (80.0)" in result[skipped_key_yaml]["reason"]