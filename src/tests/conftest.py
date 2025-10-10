# tests/conftest.py

import pytest


# --- ФИКСТУРЫ ДЛЯ ИЗОЛИРОВАННОГО ТЕСТИРОВАНИЯ ---

@pytest.fixture
def mock_display_data():
    """
    Фиктивные данные для ДИСПЛЕЯ (IsTV=False) на основе NotTV.json.
    Center Lv: 159.7 (typ)
    Min Lv (uniformity points): 145.2
    Max Lv (uniformity points): 166.0
    WhiteColor Lv: N/A
    BlackColor Lv: N/A
    """
    return {
        "SerialNumber": "NotTV",
        "DeviceConfiguration": "15iA",
        "IsTV": False,
        "MeasurementDateTime": "20250624_184822",
        "Measurements": [
            {"Location": "TopLeft", "x": 0.308, "y": 0.328, "Lv": 152.6, "T": 6771},
            {"Location": "TopCenter", "x": 0.309, "y": 0.328, "Lv": 145.2, "T": 6744},
            {"Location": "TopRight", "x": 0.308, "y": 0.328, "Lv": 155.1, "T": 6816},
            {"Location": "MiddleLeft", "x": 0.308, "y": 0.329, "Lv": 152.1, "T": 6750},
            {"Location": "Center", "x": 0.309, "y": 0.328, "Lv": 159.7, "T": 6752},
            {"Location": "MiddleRight", "x": 0.308, "y": 0.329, "Lv": 153.2, "T": 6772},
            {"Location": "BottomLeft", "x": 0.309, "y": 0.328, "Lv": 161.1, "T": 6742},
            {"Location": "BottomCenter", "x": 0.308, "y": 0.327, "Lv": 166.0, "T": 6828},
            {"Location": "BottomRight", "x": 0.309, "y": 0.328, "Lv": 156.9, "T": 6790},
            # Цветовые точки
            {"Location": "RedColor", "x": 0.648, "y": 0.336, "Lv": 12.0, "T": 1500},
            {"Location": "GreenColor", "x": 0.304, "y": 0.630, "Lv": 80.0, "T": 10000},
            {"Location": "BlueColor", "x": 0.152, "y": 0.060, "Lv": 4.0, "T": 12000},
            {"Location": "BlackColor", "x": 0.152, "y": 0.060, "Lv": 0.6183643, "T": 12000},
            {"Location": "WhiteColor", "x": 0.309, "y": 0.328, "Lv": 159.7, "T": 6752}, # Для Display WhiteColor = Center
        ]
    }


@pytest.fixture
def mock_tv_data():
    """
    Фиктивные данные для ТВ (IsTV=True) на основе TV.json.
    WhiteColor Lv: 200.0
    BlackColor Lv: N/A
    """
    data = {
        "SerialNumber": "TV",
        "DeviceConfiguration": "50UQ6031_REV1",
        "IsTV": True,
        "MeasurementDateTime": "20250624_164822",
        "Measurements": [
            {"Location": "TopLeft", "x": 0.308, "y": 0.328, "Lv": 152.6, "T": 6771},
            {"Location": "TopCenter", "x": 0.309, "y": 0.328, "Lv": 145.2, "T": 6744},
            {"Location": "TopRight", "x": 0.308, "y": 0.328, "Lv": 155.1, "T": 6816},
            {"Location": "MiddleLeft", "x": 0.308, "y": 0.329, "Lv": 152.1, "T": 6750},
            {"Location": "Center", "x": 0.309, "y": 0.328, "Lv": 159.7, "T": 6752},
            {"Location": "MiddleRight", "x": 0.308, "y": 0.329, "Lv": 153.2, "T": 6772},
            {"Location": "BottomLeft", "x": 0.309, "y": 0.328, "Lv": 161.1, "T": 6742},
            {"Location": "BottomCenter", "x": 0.308, "y": 0.327, "Lv": 166.0, "T": 6828},
            {"Location": "BottomRight", "x": 0.309, "y": 0.328, "Lv": 156.9, "T": 6790},
            # Цветовые точки
            {"Location": "RedColor", "x": 0.648, "y": 0.336, "Lv": 12.0, "T": 1500},
            {"Location": "GreenColor", "x": 0.304, "y": 0.630, "Lv": 80.0, "T": 10000},
            {"Location": "BlueColor", "x": 0.152, "y": 0.060, "Lv": 4.0, "T": 12000},
            {"Location": "BlackColor", "x": 0.152, "y": 0.060, "Lv": 0.6183643, "T": 12000},
            {"Location": "WhiteColor", "x": 0.309, "y": 0.328, "Lv": 200.0, "T": 6752}, # Для TV WhiteColor != Center
        ]
    }
    return data


@pytest.fixture
def mock_yaml_data():
    """
    Фиктивные данные для конфигурационного YAML-файла.
    """
    return {
        "sRGB": {
            "Red": {"x": 0.64, "y": 0.33},
            "Green": {"x": 0.30, "y": 0.60},
            "Blue": {"x": 0.15, "y": 0.06},
        },
        "NTSC": {
            "Red": {"x": 0.67, "y": 0.33},
            "Green": {"x": 0.21, "y": 0.71},
            "Blue": {"x": 0.14, "y": 0.08},
        },
        "main_tests": {
            "Brightness": {"min": 80.0, "typ": 100.0, "max": 150.0},
            "Temperature": {"max": 6800.0},
            "Red_x": {"min": 0.62, "max": 0.66},
            "White_x": {"max": 0.34},
        }
    }

@pytest.fixture
def mock_black_lv():
    """Фиктивное значение Lv для BlackColor (используется в расчете контраста)."""
    return 0.6183643

# --- ФИКСТУРЫ ДЛЯ МОКИНГА ВНЕШНИХ ЗАВИСИМОСТЕЙ ---

@pytest.fixture(autouse=True)
def mock_external_libs(mocker):
    """
    Автоматическое мокирование внешних тяжелых библиотек, чтобы ускорить тесты.
    """
    # Мокинг reportlab (используется в helpers.py)
    mocker.patch('src.helpers.canvas.Canvas', create=True)
    mocker.patch('src.helpers.SimpleDocTemplate', create=True)
    mocker.patch('src.helpers.getSampleStyleSheet')
    mocker.patch('src.helpers.Paragraph', create=True)
    mocker.patch('src.helpers.Table')
    # Мокинг PyPDF2 (используется в helpers.py)
    mocker.patch('src.helpers.PdfMerger')
    # Мокинг matplotlib.pyplot (используется в calculate.py)
    mocker.patch('src.calculate.plt')
    # Мокинг os.remove, чтобы не удалять реальные файлы
    mocker.patch('src.helpers.os.remove')
    # Мокинг shapely.geometry.Polygon, если его не мокают напрямую в тестах
    try:
        mocker.patch('src.calculate.Polygon')
    except AttributeError:
        # Если Polygon не импортируется в calculate.py или уже замокан
        pass