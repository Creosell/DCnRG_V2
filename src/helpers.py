import src.calculate as cal
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.colors import red, black, green, grey, whitesmoke, beige
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import json
from PyPDF2 import PdfMerger
import os
import zipfile
import shutil
from datetime import datetime
from pathlib import Path


def pass_fail_color(result):
    if result == "PASS":
        data = green
    elif result == "FAIL":
        data = red
    else:
        data = "N/A"
    return data


def parse_one_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def create_pdf(
    input_file,
    output_file,
    RGB,
    NTSC,
    plot_picture,
    color_space_pic,
    min_fail,
    test_type,
):
    indent1 = 0
    indent2 = 0
    i = 0
    pdf = canvas.Canvas(output_file, pagesize=letter)
    pdf.setFont("Helvetica", 11)
    with open(input_file, "r") as f:
        data = json.load(f)

    param_list = [
        ("Brightness", "Brightness"),
        ("Brightness_uniformity", "Brightness uniformity"),
        ("Cg_rgb_area", "Color Gamut RGB by Area"),
        ("Cg_ntsc_area", "Color Gamut NTSC by Area"),
        # ("Cg_rgb", "Color Gamut RGB"),
        # ("Cg_ntsc", "Clor Gamut NTSC"),
        ("Contrast", "Contrast"),
        ("Temperature", "Temperature"),
        # ("Delta_e", "Color Uniformity"),
    ]
    pdf.drawString(250, 760, "Display Analysis Report")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(50, 730, "Param")
    pdf.drawString(200, 730, "min act")
    pdf.drawString(250, 730, "min exp")
    pdf.drawString(300, 730, "avg act")
    pdf.drawString(350, 730, "avg exp")
    pdf.drawString(400, 730, "max act")
    pdf.drawString(450, 730, "max exp")
    pdf.drawString(500, 730, "STATUS")

    # First page: Text results
    for param_name, text in param_list:
        avg_param = data.get(param_name).get("actual_values").get("avg")
        min_param = data.get(param_name).get("actual_values").get("min")
        max_param = data.get(param_name).get("actual_values").get("max")
        avg_exp = data.get(param_name).get("expected_values").get("typ")
        min_exp = data.get(param_name).get("expected_values").get("min")
        max_exp = data.get(param_name).get("expected_values").get("max")
        status = data.get(param_name).get("status")
        pdf.drawString(50, 700 - indent2, f"{text}:")
        pdf.drawString(205, 700 - indent2, f"{min_param}"[:6])
        pdf.drawString(255, 700 - indent2, f"{min_exp}"[:6])
        pdf.drawString(305, 700 - indent2, f"{avg_param}"[:6])
        pdf.drawString(355, 700 - indent2, f"{avg_exp}"[:6])
        pdf.drawString(405, 700 - indent2, f"{max_param}"[:6])
        pdf.drawString(455, 700 - indent2, f"{max_exp}"[:6])
        if status == "PASS":
            pdf.setFillColor(green)
        else:
            pdf.setFillColor(red)
        pdf.drawString(500, 700 - indent1, status)
        pdf.setFillColor(black)
        indent1 += 20
        indent2 += 20

    if test_type == "Contrast":
        pass
    else:
        coordinate_list = ["Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y"]
        coordinates = []
        for coordinate_name in coordinate_list:
            coordinate = data.get(coordinate_name).get("actual_values").get("avg")
            coordinates.append(coordinate)
        x1, y1, x2, y2, x3, y3 = coordinates
        cal.plot_color_space(
            RGB, NTSC, x1, y1, x2, y2, x3, y3, plot_picture, color_space_pic
        )

        pdf.drawString(50, 500, "Color cordinates")

        # Extract min/max/avg values in a compact way
        colors = ["Red", "Green", "Blue", "White"]
        metrics = {}

        for color in colors:
            metrics[color] = {
                "x_min": data.get(f"{color}_x").get("actual_values").get("min"),
                "x_max": data.get(f"{color}_x").get("actual_values").get("max"),
                "y_min": data.get(f"{color}_y").get("actual_values").get("min"),
                "y_max": data.get(f"{color}_y").get("actual_values").get("max"),
                "x_status": data.get(f"{color}_x").get("status"),
                "y_status": data.get(f"{color}_y").get("status"),
            }
            if color == "White":
                metrics[color].update(
                    {
                        "x_avg": data.get(f"{color}_x").get("actual_values").get("avg"),
                        "y_avg": data.get(f"{color}_y").get("actual_values").get("avg"),
                        "x_status": data.get(f"{color}_x").get("status"),
                        "y_status": data.get(f"{color}_y").get("status"),
                    }
                )

        # Define the table data
        table_data = [
            ["Color", "min", "typ", "max", "status"],
            [
                "Red X",
                f"{metrics['Red']['x_min']}",
                f"{x1:.4f}",
                f"{metrics['Red']['x_max']}",
                f"{metrics['Red']['x_status']}",
            ],
            [
                "Red Y",
                f"{metrics['Red']['y_min']}",
                f"{y1:.4f}",
                f"{metrics['Red']['y_max']}",
                f"{metrics['Red']['y_status']}",
            ],
            [
                "Green X",
                f"{metrics['Green']['x_min']}",
                f"{x2:.4f}",
                f"{metrics['Green']['x_max']}",
                f"{metrics['Green']['x_status']}",
            ],
            [
                "Green Y",
                f"{metrics['Green']['y_min']}",
                f"{y2:.4f}",
                f"{metrics['Green']['y_max']}",
                f"{metrics['Green']['y_status']}",
            ],
            [
                "Blue X",
                f"{metrics['Blue']['x_min']}",
                f"{x3:.4f}",
                f"{metrics['Blue']['x_max']}",
                f"{metrics['Blue']['x_status']}",
            ],
            [
                "Blue Y",
                f"{metrics['Blue']['y_min']}",
                f"{y3:.4f}",
                f"{metrics['Blue']['y_max']}",
                f"{metrics['Blue']['y_status']}",
            ],
            [
                "White X",
                f"{metrics['White']['x_min']}",
                f"{metrics['White']['x_avg']}",
                f"{metrics['White']['x_max']}",
                f"{metrics['White']['x_status']}",
            ],
            [
                "White Y",
                f"{metrics['White']['y_min']}",
                f"{metrics['White']['y_avg']}",
                f"{metrics['White']['y_max']}",
                f"{metrics['White']['y_status']}",
            ],
        ]

        # Create the table
        table = Table(table_data, colWidths=[100, 100, 100])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), grey),  # Header background
                    ("TEXTCOLOR", (0, 0), (-1, 0), whitesmoke),  # Header text color
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # Center align all cells
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Header font
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Header padding
                    ("BACKGROUND", (0, 1), (-1, -1), beige),  # Cell background
                    ("GRID", (0, 0), (-1, -1), 1, black),  # Grid lines
                ]
            )
        )

        # Draw the table on the PDF
        table.wrapOn(pdf, 50, 300)
        table.drawOn(
            pdf, 50, 500 - len(table_data) * 20
        )  # Adjust position based on table size

    # Add a new page for the color space graph
    pdf.drawImage(plot_picture, 100, 0, width=400, height=320)
    # Add a new page for the color space graph
    # pdf.drawImage(plot_picture, 50, 150, width=225, height=180)

    pdf.showPage()  # Start a new page for the table
    pdf.drawString(250, 750, "Fail on minimum values")

    try:
        with open(min_fail, "r") as f:
            min_fail_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {min_fail}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {min_fail}")
        return

    textobject = pdf.beginText()
    textobject.setTextOrigin(inch, 10 * inch)
    textobject.setFont("Courier", 8)
    for entry in min_fail_data:
        for test_id, details in entry.items():
            textobject.textLine(f"Serial Number: {test_id}")
            for key, value in details.items():
                textobject.textLine(f"{key}: {value}")
            textobject.textLine("")  # Add a blank line for separation
    pdf.drawText(textobject)

    pdf.showPage()

    # Save the PDF
    pdf.save()


def device_reports_to_pdf(folder_path, output_path):
    """
    Generates a PDF file containing the formatted content of JSON files
    from a specified folder.

    Args:
        folder_path (str): The path to the folder containing the JSON files.
        output_path (str): The path to save the generated PDF file.
    """

    c = canvas.Canvas(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]

    page_number = 1
    y_position = 750  # Starting Y position for content

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                # Format the JSON data for PDF
                json_string = json.dumps(
                    data, indent=4
                )  # Use json.dumps for pretty formatting

                # Split the JSON string into lines
                lines = json_string.splitlines()

                # Calculate the height required for the JSON content
                line_height = 12  # Approximate line height
                required_height = len(lines) * line_height + 50  # Add some padding

                # Check if there's enough space on the current page
                if y_position - required_height < 50:  # 50 is bottom margin
                    c.showPage()  # Create a new page
                    page_number += 1
                    y_position = 750  # Reset Y position for the new page

                # Add a title for each JSON file
                p = Paragraph(f"<b>File: {filename}</b>", styleH)
                p.wrapOn(c, letter[0] - 2 * inch, letter[1])
                p.drawOn(c, inch, y_position)
                y_position -= 50

                # Write the JSON content to the PDF
                for line in lines:
                    p = Paragraph(line, styleN)
                    p.wrapOn(c, letter[0] - 2 * inch, letter[1])
                    p_height = p.wrapOn(c, letter[0] - 2 * inch, letter[1])[1]
                    if y_position - p_height < 50:
                        c.showPage()
                        page_number += 1
                        y_position = 750
                    p.drawOn(c, inch, y_position)
                    y_position -= line_height

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    c.save()
    print(f"PDF file created successfully at {output_path}")


def merge_pdfs(pdf_paths, output_path):
    """Merges multiple PDF files into a single PDF.

    Args:
        pdf_paths (list): A list of paths to the PDF files to merge.
        output_path (str): The path to save the merged PDF file.
    """
    merger = PdfMerger()

    for path in pdf_paths:
        try:
            merger.append(path)
        except FileNotFoundError:
            print(f"Error: File not found: {path}")
            return  # Or raise the exception, depending on desired behavior
        except Exception as e:
            print(f"Error processing {path}: {e}")
            return

    try:
        with open(output_path, "wb") as output_file:
            merger.write(output_file)
        print(f"Successfully merged PDFs to {output_path}")
    except Exception as e:
        print(f"Error writing merged PDF: {e}")
    finally:
        merger.close()


def archive_reports(device_name, timestamp, source_folders):
    """
    Архивирует все файлы из папок device_reports, pdf_reports, test_reports
    в один zip файл в папке report_archive

    Args:
        device_name (str): Имя устройства для формирования имени архива

    Returns:
        str: Путь к созданному архиву или None в случае ошибки
    """

    # Папки-источники
    # source_folders = ['device_reports', 'pdf_reports', 'test_reports']

    # Папка назначения
    archive_folder = 'report_archive'

    # Создаем папку архива, если она не существует
    Path(archive_folder).mkdir(exist_ok=True)

    # Формируем имя zip файла
    zip_filename = f"{device_name}_{timestamp}.zip"
    zip_path = os.path.join(archive_folder, zip_filename)

    try:
        # Создаем zip архив
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_added = 0

            # Проходим по каждой папке-источнику
            for folder in source_folders:
                if os.path.exists(folder):
                    # Получаем все файлы из папки
                    for root, dirs, files in os.walk(folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Добавляем файл в архив с сохранением структуры папок
                            arcname = os.path.relpath(file_path, '.')
                            zipf.write(file_path, arcname)
                            files_added += 1
                            print(f"Добавлен файл: {file_path}")
                else:
                    print(f"Папка {folder} не найдена")

            if files_added == 0:
                print("Не найдено файлов для архивирования")
                os.remove(zip_path)  # Удаляем пустой архив
                return None

        print(f"Архив создан: {zip_path}")
        print(f"Всего файлов заархивировано: {files_added}")

        return zip_path

    except Exception as e:
        print(f"Ошибка при создании архива: {e}")
        return None


def clear_folders(folders):
    """
    Удаляет все файлы из указанных папок, оставляя сами папки

    Args:
        folders (list): Список папок для очистки
    """
    removed_count = 0

    for folder in folders:
        if os.path.exists(folder):
            # Проходим по всем файлам в папке и подпапках
            for root, dirs, files in os.walk(folder, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)[[1]]
                        print(f"Удален файл: {file_path}")
                        removed_count += 1
                    except Exception as e:
                        print(f"Ошибка при удалении файла {file_path}: {e}")
        else:
            print(f"Папка {folder} не найдена")

    print(f"Всего удалено файлов: {removed_count}")

