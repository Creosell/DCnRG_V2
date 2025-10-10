# tests/test_helpers.py

import json

from reportlab.lib.colors import green, red, grey

from src import helpers


# Используем фикстуру mocker и mock_json_data из conftest.py

def test_pass_fail_color():
    """Тестирование функции pass_fail_color."""
    assert helpers.pass_fail_color("PASS") == green
    assert helpers.pass_fail_color("FAIL") == red
    assert helpers.pass_fail_color("N/A") == grey
    assert helpers.pass_fail_color("UNKNOWN") == grey
    assert helpers.pass_fail_color(None) == grey


def test_parse_one_file_success(tmp_path, mock_display_data):
    """Тестирование успешного парсинга одного JSON-файла."""
    # Создаем временный файл
    test_file = tmp_path / "test_report.json"
    with open(test_file, "w") as f:
        json.dump(mock_display_data, f)

    data = helpers.parse_one_file(str(test_file))

    assert data is not None
    assert data["SerialNumber"] == "NotTV"
    assert len(data["Measurements"]) == 14  # 14 - количество измерений в mock_display_data


# Тест мокирует внешние зависимости reportlab и calculate
def test_create_pdf_calls_plot(mocker, tmp_path):
    """Тестирование, что функция create_pdf вызывает plot_color_space."""
    import json  # Добавляем импорт
    from src import helpers  # Добавляем импорт

    # 1. Создание фиктивного входного файла (final_report.json)
    mock_input_data = {
        "Brightness": {"actual_values": {"avg": 100.0}, "status": "PASS"},
        "Temperature": {"actual_values": {"avg": 6700}, "status": "FAIL"},
        "Red_x": {"actual_values": {"avg": 0.64}, "status": "PASS"},
        "Red_y": {"actual_values": {"avg": 0.65}, "status": "PASS"},
        "Green_x": {"actual_values": {"avg": 0.64}, "status": "PASS"},
        "Green_y": {"actual_values": {"avg": 0.65}, "status": "PASS"},
        "Blue_x": {"actual_values": {"avg": 0.64}, "status": "PASS"},
        "Blue_y": {"actual_values": {"avg": 0.65}, "status": "PASS"},
        "White_x": {"actual_values": {"avg": 0.31}, "status": "PASS"},
        "White_y": {"actual_values": {"avg": 0.32}, "status": "PASS"},
    }

    min_fail_file = tmp_path / "min_fail.json"
    min_fail_file.write_text("[]")

    # sRGB (из conftest): R(0.64, 0.33), G(0.30, 0.60), B(0.15, 0.06)
    MOCK_RGB_COORDS = [0.64, 0.33, 0.30, 0.60, 0.15, 0.06]
    # NTSC (из conftest): R(0.67, 0.33), G(0, 0), B(0, 0) - NTSC в фикстуре неполный, но для теста сойдет.
    # Используем корректный треугольник для sRGB и NTSC из другого теста для большей надежности.
    MOCK_NTSC_COORDS = [0.67, 0.33, 0.21, 0.71, 0.14, 0.08]  # Пример корректного NTSC

    input_file = tmp_path / "final_report.json"
    output_file = tmp_path / "output_report.pdf"

    with open(input_file, "w") as f:
        json.dump(mock_input_data, f)

    # 2. Мокирование plot_color_space из calculate (зависимость)
    mock_plot = mocker.patch('src.calculate.plot_color_space')

    # 3. Вызов тестируемой функции
    # ИСПРАВЛЕНО: Списки RGB и NTSC должны содержать по 6 элементов (x, y для 3-х точек)
    # canvas.Canvas уже замокан в conftest.py
    helpers.create_pdf(
        input_file=str(input_file),
        output_file=str(output_file),
        rgb=MOCK_RGB_COORDS,  # <-- Исправлено
        ntsc=MOCK_NTSC_COORDS,  # <-- Исправлено
        plot_picture="plot.png",
        color_space_pic="space.png",
        min_fail=str(min_fail_file),
        test_type="Color"
    )

    # 4. Проверка: функция plot_color_space должна быть вызвана
    # plot_color_space ожидает: RGB, NTSC, x1, y1, x2, y2, x3, y3, output_file, color_space_pic
    # В create_pdf, она вызывается с:
    # plot_color_space(RGB, NTSC, r_x, r_y, g_x, g_y, b_x, b_y, plot_picture, color_space_pic)
    # где r_x, g_x, b_x, r_y, g_y, b_y берутся из JSON.

    # Так как mock_input_data содержит 'Red_x', 'White_x', 'White_y', но не 'Red_y', 'Green_x', 'Green_y', 'Blue_x', 'Blue_y',
    # то в реальной жизни код упадет, но для целей мокирования просто проверяем, что вызов произошел.
    # Если вам нужно проверить аргументы, необходимо добавить все ключи в `mock_input_data`
    # (см. `create_pdf` в `helpers.py` строки 228-233)

    # Например, чтобы убедиться, что plot_color_space получает ожидаемые координаты (x,y для R,G,B):
    mock_plot.assert_called_once_with(
        MOCK_RGB_COORDS,  # Мокированные RGB
        MOCK_NTSC_COORDS,  # Мокированные NTSC
        0.64,  # R_x
        0.65,  # R_y
        0.64,  # G_x
        0.65,  # G_y
        0.64,  # B_x
        0.65,  # B_y
        "plot.png",
        "space.png"
    )

    # 5. Проверка: должен быть вызван метод save() на объекте Canvas
    # Mocking in conftest.py: mocker.patch('src.helpers.canvas.Canvas')
    # Это создает mock-объект для класса Canvas.
    # reportlab.pdfgen.canvas.Canvas - это конструктор.
    # mock_canvas - это результат вызова конструктора.
    mock_canvas = helpers.canvas.Canvas.return_value
    mock_canvas.save.assert_called_once()

def test_parse_one_file_failure(tmp_path):
    """Тестирование parse_one_file на несуществующем и некорректном файле."""
    # Файл не найден
    assert helpers.parse_one_file(tmp_path / "nonexistent.json") is None

    # Некорректный JSON
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{'invalid': 'json'}")
    assert helpers.parse_one_file(bad_file) is None


def test_archive_reports_logic(mocker, tmp_path):
    """Тестирование создания архива."""
    # Мокируем zipfile
    mock_zip_file = mocker.patch('src.helpers.zipfile.ZipFile')
    mock_zip_instance = mock_zip_file.return_value.__enter__.return_value

    # Создаем фиктивные папки и файлы для архивации
    folder1 = tmp_path / "device_reports"
    folder1.mkdir()
    (folder1 / "report1.json").touch()

    folder2 = tmp_path / "pdf_reports"
    folder2.mkdir()
    (folder2 / "report.pdf").touch()

    helpers.archive_reports("TestDevice", "20251010", [folder1, folder2])

    # Проверяем, что метод write был вызван для каждого файла
    assert mock_zip_instance.write.call_count == 2


def test_clear_folders_logic(tmp_path):
    """Тестирование функции очистки папок."""
    # Создаем структуру папок и файлов
    folder_to_clear = tmp_path / "folder1"
    folder_to_clear.mkdir()
    (folder_to_clear / "file1.txt").touch()

    subfolder = folder_to_clear / "sub"
    subfolder.mkdir()
    (subfolder / "file2.txt").touch()

    # Перед очисткой файлы существуют
    assert (folder_to_clear / "file1.txt").exists()
    assert (subfolder / "file2.txt").exists()

    helpers.clear_folders([folder_to_clear])

    # После очистки - не существуют
    assert not (folder_to_clear / "file1.txt").exists()
    assert not (subfolder / "file2.txt").exists()