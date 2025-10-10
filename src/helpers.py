import glob
import json
import os
import zipfile
from pathlib import Path

from PyPDF2 import PdfMerger
from reportlab.lib.colors import red, black, green, grey, whitesmoke, beige
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.platypus import Table, TableStyle

import src.calculate as cal


def pass_fail_color(result):
    """
    Возвращает цвет для статуса PASS/FAIL.
    Использует словарное сопоставление вместо if/elif/else.
    """
    color_map = {
        "PASS": green,
        "FAIL": red
    }
    # Возвращаем цвет, или grey для "N/A" и других случаев
    return color_map.get(result, grey)


def parse_one_file(file_path):
    """Загружает и возвращает данные из одного JSON файла."""
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading/parsing file {file_path}: {e}")
        return None


def create_pdf(
        input_file,
        output_file,
        rgb,
        ntsc,
        plot_picture,
        color_space_pic,
        min_fail,
        test_type,
):
    """
    Генерирует PDF отчет из JSON файла с результатами теста.
    Логика упрощена за счет использования циклов и уменьшения дублирования.
    """
    pdf = canvas.Canvas(output_file, pagesize=letter)
    pdf.setFont("Helvetica", 11)

    try:
        with open(input_file, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading/parsing input file {input_file}: {e}")
        return

    # --- Первая страница: Текстовые результаты ---
    pdf.drawString(250, 760, "Display Analysis Report")
    pdf.setFont("Helvetica", 8)

    # Заголовки таблицы и их позиции
    headers = ["Param", "min act", "min exp", "avg act", "avg exp", "max act", "max exp", "STATUS"]
    x_positions = [50, 200, 250, 300, 350, 400, 450, 500]
    y_header = 730

    for x, header in zip(x_positions, headers):
        pdf.drawString(x, y_header, header)

    param_list = [
        ("Brightness", "Brightness"),
        ("Brightness_uniformity", "Brightness uniformity"),
        ("Cg_rgb_area", "Color Gamut RGB by Area"),
        ("Cg_ntsc_area", "Color Gamut NTSC by Area"),
        ("Contrast", "Contrast"),
        ("Temperature", "Temperature"),
    ]

    y_start = 700
    line_height = 20

    # Вывод основных параметров в цикле
    for i, (param_name, text) in enumerate(param_list):
        param_data = data.get(param_name, {})
        actual = param_data.get("actual_values", {})
        expected = param_data.get("expected_values", {})
        status = param_data.get("status", "N/A")

        y_pos = y_start - i * line_height

        # Список значений для вывода
        values = [
            actual.get("min"), expected.get("min"),
            actual.get("avg"), expected.get("typ"),
            actual.get("max"), expected.get("max"),
        ]

        pdf.drawString(50, y_pos, f"{text}:")

        # Вывод значений с форматированием до 6 символов
        for j, value in enumerate(values):
            x_pos = x_positions[1] + j * 50 + 5
            pdf.drawString(x_pos, y_pos, f"{value}"[:6])

            # Статус с цветом
        pdf.setFillColor(green if status == "PASS" else red)
        pdf.drawString(500, y_pos, status)
        pdf.setFillColor(black)

    # --- Координаты цвета и график ---
    if test_type != "Contrast":
        coordinate_names = ["Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y"]
        # Лаконичное извлечение координат
        coordinates = [data.get(name, {}).get("actual_values", {}).get("avg") for name in coordinate_names]
        x1, y1, x2, y2, x3, y3 = coordinates

        cal.plot_color_space(
            rgb, ntsc, x1, y1, x2, y2, x3, y3, plot_picture, color_space_pic
        )

        # Начальная позиция для таблицы
        y_table_start = y_start - len(param_list) * line_height - line_height * 2
        pdf.drawString(50, y_table_start, "Color coordinates")

        colors = ["Red", "Green", "Blue", "White"]
        table_data = [["Color", "min", "typ", "max", "status"]]

        # Создание данных для таблицы координат в цикле
        for color in colors:
            x_data = data.get(f"{color}_x", {})
            y_data = data.get(f"{color}_y", {})

            x_act = x_data.get("actual_values", {})
            y_act = y_data.get("actual_values", {})

            # Для White 'typ' - это 'avg', для RGB - извлеченная координата
            if color == "White":
                x_typ = x_act.get("avg")
                y_typ = y_act.get("avg")
            else:
                x_typ = coordinates[coordinate_names.index(f"{color}_x")]
                y_typ = coordinates[coordinate_names.index(f"{color}_y")]

            table_data.extend([
                [
                    f"{color} X",
                    f"{x_act.get('min')}",
                    f"{x_typ:.4f}",
                    f"{x_act.get('max')}",
                    x_data.get("status", "N/A")
                ],
                [
                    f"{color} Y",
                    f"{y_act.get('min')}",
                    f"{y_typ:.4f}",
                    f"{y_act.get('max')}",
                    y_data.get("status", "N/A")
                ]
            ])

        # Создание и отрисовка таблицы
        table = Table(table_data, colWidths=[100, 100, 100, 100, 100])

        # Добавляем динамический цвет для статуса в таблице
        # noinspection SpellCheckingInspection
        style_list = [
            ("BACKGROUND", (0, 0), (-1, 0), grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), beige),
            ("GRID", (0, 0), (-1, -1), 1, black),
        ]

        # Применяем цвет фона к ячейке "STATUS" с использованием pass_fail_color
        for row in range(1, len(table_data)):
            status_value = table_data[row][4]
            style_list.append(("BACKGROUND", (4, row), (4, row), pass_fail_color(status_value)))

        table.setStyle(TableStyle(style_list))

        table.wrapOn(pdf, 50, 300)
        y_table_draw = y_table_start - len(table_data) * 20
        table.drawOn(pdf, 50, y_table_draw)

    # --- График и Fail on minimum values ---
    y_graph_start = y_table_draw - 320 - 20  # 320 - это высота графика, 20 - отступ

    pdf.drawImage(plot_picture, 100, y_graph_start, width=400, height=320)

    pdf.showPage()
    pdf.drawString(250, 750, "Fail on minimum values")

    try:
        with open(min_fail, "r") as f:
            min_fail_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading/parsing min_fail file {min_fail}: {e}")
        min_fail_data = []

    text_object = pdf.beginText()
    text_object.setTextOrigin(inch, 10 * inch)
    text_object.setFont("Courier", 8)

    # Упрощенный вывод данных min_fail_data
    for entry in min_fail_data:
        for test_id, details in entry.items():
            text_object.textLine(f"Serial Number: {test_id}")
            # Используем генератор для вывода деталей
            for key, value in details.items():
                text_object.textLine(f"{key}: {value}")
            text_object.textLine("")

    pdf.drawText(text_object)
    pdf.save()


def device_reports_to_pdf(folder_path, output_path, device_name):
    """
    Генерирует PDF файл, содержащий форматированный JSON контент
    из отчетов для указанного устройства.
    """
    c = canvas.Canvas(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    style_h = styles["Heading1"]
    style_n = styles["Normal"]
    style_code = styles["Code"]  # Используем стиль Code для JSON

    y_position = 750  # Стартовая Y позиция

    # Используем glob для получения списка файлов
    pattern = Path(folder_path) / f"{device_name}_*.json"
    device_reports = glob.glob(str(pattern))

    for file_path in device_reports:
        file_name = Path(file_path).name

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Форматируем JSON
            json_string = json.dumps(data, indent=4)
            lines = json_string.splitlines()

            line_height = 12  # Приблизительная высота строки

            # --- Заголовок файла ---
            p = Paragraph(f"<b>File: {file_name}</b>", style_h)
            p.wrapOn(c, letter[0] - 2 * inch, letter[1])
            p.drawOn(c, inch, y_position)
            y_position -= 50

            # --- Контент JSON ---
            for line in lines:
                # Используем стиль Code для сохранения моноширинного шрифта JSON
                p = Paragraph(line, style_n)
                p_width, p_height = p.wrapOn(c, letter[0] - 2 * inch, letter[1])

                # Проверка на новую страницу
                if y_position - p_height < 50:
                    c.showPage()
                    y_position = 750

                p.drawOn(c, inch, y_position)
                y_position -= line_height

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")

    c.save()
    print(f"PDF file created successfully at {output_path}")


def merge_pdfs(pdf_paths, output_path):
    """Объединяет несколько PDF файлов в один."""
    merger = PdfMerger()

    # Используем генератор для более лаконичной обработки ошибок
    try:
        for path in pdf_paths:
            merger.append(path)

        with open(output_path, "wb") as output_file:
            merger.write(output_file)
        print(f"Successfully merged PDFs to {output_path}")

    except FileNotFoundError:
        print(f"Error: File not found in path list.")
    except Exception as e:
        print(f"Error during PDF merge: {e}")
    finally:
        merger.close()


def archive_reports(device_name, timestamp, source_folders):
    """
    Архивирует все файлы из папок-источников в один zip файл
    в папке report_archive.
    """
    archive_folder = Path('report_archive')
    archive_folder.mkdir(exist_ok=True)  # Создаем папку, если не существует

    # Формируем имя zip файла с использованием Path
    zip_filename = f"{device_name}_{timestamp}.zip"
    zip_path = archive_folder / zip_filename

    try:
        files_added = 0
        # Создаем zip архив
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

            # Проходим по каждой папке-источнику
            for folder_name in source_folders:
                folder_path = Path(folder_name)
                if folder_path.exists():
                    # Используем os.walk для рекурсивного обхода
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_path = Path(root) / file
                            # name_in_archive - путь внутри архива, относительный к текущей директории
                            name_in_archive = file_path.relative_to(folder_path.parent)
                            zipf.write(file_path, name_in_archive)
                            files_added += 1
                            print(f"Добавлен файл: {file_path}")
                else:
                    print(f"Папка {folder_name} не найдена")

            if files_added == 0:
                print("Не найдено файлов для архивирования")
                zip_path.unlink()  # Удаляем пустой архив
                return None

        print(f"Архив создан: {zip_path}")
        print(f"Всего файлов заархивировано: {files_added}")
        return str(zip_path)

    except Exception as e:
        print(f"Ошибка при создании архива: {e}")
        return None


def clear_folders(folders):
    """
    Удаляет все файлы из указанных папок, используя pathlib. Path.
    """
    removed_count = 0

    for folder_path in map(Path, folders):
        if not folder_path.is_dir():
            print(f"Папка {folder_path} не найдена или не является папкой")
            continue

        # Используем glob() для рекурсивного поиска всех файлов (Path.glob)
        for file_path in folder_path.glob('**/*'):
            if file_path.is_file():
                try:
                    file_path.unlink()  # Метод Path для удаления файла
                    removed_count += 1
                except Exception as e:
                    print(f"Ошибка при удалении файла {file_path}: {e}")

    print(f"Всего удалено файлов: {removed_count}")