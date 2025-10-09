import src.parse as parse
import os
import src.calculate as cal
import src.report as r
import datetime
import src.helpers as h
from pathlib import Path
from collections import defaultdict  # Добавляем для удобной группировки

# --- Шаг 0: Инициализация и настройки ---

# Настройка путей
CURRENT_TIME = datetime.datetime.now()
TIMESTAMP = CURRENT_TIME.strftime("%Y%m%d%H%M")

DATA_FOLDER = Path("data")
DEVICE_REPORTS = Path("device_reports")
PDF_REPORTS_FOLDER = Path("pdf_reports")
TEST_REPORTS_FOLDER = Path("test_reports")
ARCHIVE_REPORTS = Path("report_archive")
PICTURES_FOLDER = Path("pics")

MAIN_CONFIG = Path("config") / "main.yaml"
COLOR_SPACE_CONFIG = Path("config") / "color_space.yaml"
COLOR_SPACE_PICTURE = Path("config") / "space.png"

# Парсинг общих настроек
RGB = parse.coordinate_sRGB(COLOR_SPACE_CONFIG)
NTSC = parse.coordinate_NTSC(COLOR_SPACE_CONFIG)
COLOR_SPACE = parse.parse_yaml(MAIN_CONFIG, "Task", "color_space", "type")
test = parse.parse_yaml(MAIN_CONFIG, "Task", "test", "type")

# Создание рабочих папок при их отсутствии
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
DEVICE_REPORTS.mkdir(parents=True, exist_ok=True)
PDF_REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
TEST_REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
ARCHIVE_REPORTS.mkdir(parents=True, exist_ok=True)
PICTURES_FOLDER.mkdir(parents=True, exist_ok=True)

# Общий файл ожидаемых результатов (используется как запасной)
EXPECTED_RESULT = Path("config") / "expected_result.yaml"

# --- Шаг 1: Сбор файлов и группировка по конфигурации устройства ---
# Группируем файлы по DeviceConfiguration
device_groups = defaultdict(list)
files = os.listdir(DATA_FOLDER)
if not files:
    print(f"В папке {DATA_FOLDER} нет файлов для обработки.")
    exit()

print(f"Найдено {len(files)} файлов для обработки. Начинается группировка...")

for file_name in files:
    if file_name.endswith(".json"):
        file_path = DATA_FOLDER / file_name
        try:
            data = h.parse_one_file(file_path)

            # Получаем ключевые параметры
            device_config = data.get("DeviceConfiguration", "UnknownDevice")
            is_tv = data.get("IsTV", False)
            sn = data.get("SerialNumber", "UnknownSN")

            # Добавляем в группу: путь, флаг TV, серийный номер
            device_groups[device_config].append((file_path, is_tv, sn))

        except Exception as e:
            print(f"Ошибка при парсинге файла {file_name}: {e}")

if not device_groups:
    print("Не удалось сформировать группы устройств. Проверьте файлы.")
    exit()

# --- Шаг 2: Обработка каждой группы устройств ---

for current_device_name, file_list in device_groups.items():
    print(f"\n--- Обработка конфигурации устройства: {current_device_name} ({len(file_list)} файлов) ---")

    # 2.1 Динамическое определение путей для ТЕКУЩЕГО устройства

    # Поиск специфичного файла требований config/device_configs/{name}.yaml
    current_expected_result = Path("config") / "device_configs" / f"{current_device_name}.yaml"
    if not current_expected_result.exists():
        print(
            f"Внимание: Конфигурация требований {current_expected_result} не найдена. Используется общий файл: {EXPECTED_RESULT}")
        current_expected_result = EXPECTED_RESULT  # Запасной вариант

    # Динамические имена файлов отчетов
    current_min_fail = Path("test_reports") / f"min_fail_{current_device_name}.json"
    current_report_from_all = Path("test_reports") / f"full_report_{current_device_name}.json"
    current_final_report = Path("test_reports") / f"final_report_{current_device_name}_{TIMESTAMP}.json"
    current_plot_picture = Path("pics") / f"plot_{current_device_name}.png"
    current_pdf_report = Path("pdf_reports") / f"report_{current_device_name}.pdf"
    current_pdf_report_all = Path("pdf_reports") / f"all_reports_{current_device_name}.pdf"
    current_result = Path("results") / f"{current_device_name}_{TIMESTAMP}.pdf"

    # 2.2 Обрабатываем каждый файл в текущей группе
    for file, is_tv_flag, sn in file_list:
        t = cal.measurement_time(file)

        if test == "FullTest":
            print("FULL TEST")

            # --- ОБНОВЛЕННЫЙ РАСЧЕТ ЯРКОСТИ/РАВНОМЕРНОСТИ ---
            brightness_values = cal.brightness(file, is_tv_flag)  # Передаем флаг is_tv_flag
            brightness = brightness_values["typ"]  # Типовая (WhiteColor/Center)
            brightness_uniformity = cal.brightness_uniformity(brightness_values)  # Использует Center

            # --- ОБНОВЛЕННЫЙ РАСЧЕТ КОНТРАСТНОСТИ ---
            contrast = cal.contrast(file, is_tv_flag)  # Передаем флаг is_tv_flag

            cg_by_area = cal.cg_by_area(file, COLOR_SPACE)
            cg = cal.cg(file, COLOR_SPACE, RGB, NTSC)
            temperature = cal.temperature(file)
            delta_e = cal.delat_e(file)
            coordinates = parse.get_coordinates(file)

            r.json_report(
                sn=sn,
                t=t,
                brightness=brightness,
                brightness_uniformity=brightness_uniformity,
                cg_by_area_rgb=cg_by_area[0],
                cg_by_area_ntsc=cg_by_area[1],
                cg_rgb=cg[0],
                cg_ntsc=cg[1],
                contrast=contrast,
                temperature=temperature,
                delta_e=delta_e,
                coordinates=coordinates,
                output_folder=DEVICE_REPORTS,
                device_name=current_device_name
            )

        if test == "Contrast":
            contrast = cal.contrast(file, is_tv_flag)
            r.json_report(sn=sn, t=t, contrast=contrast, output_folder=DEVICE_REPORTS, device_name=current_device_name)

        if test == "BrightnessUniformity":
            brightness_values = cal.brightness(file, is_tv_flag)
            brightness = brightness_values["typ"]
            brightness_uniformity = cal.brightness_uniformity(brightness_values)
            coordinates = parse.get_coordinates(file)
            r.json_report(
                sn=sn,
                t=t,
                brightness=brightness,
                brightness_uniformity=brightness_uniformity,
                coordinates=coordinates,
                output_folder=DEVICE_REPORTS,
                device_name=current_device_name
            )

        if test == "ColorGamut":
            cg_by_area = cal.cg_by_area(file, COLOR_SPACE)
            cg = cal.cg(file, COLOR_SPACE, RGB, NTSC)
            coordinates = parse.get_coordinates(file)
            r.json_report(
                sn=sn,
                t=t,
                cg_by_area_rgb=cg_by_area[0],
                cg_by_area_ntsc=cg_by_area[1],
                cg_rgb=cg[0],
                cg_ntsc=cg[1],
                coordinates=coordinates,
                output_folder=DEVICE_REPORTS,
                device_name=current_device_name
            )

    # 2.3 --- Агрегация и Отчетность для ТЕКУЩЕЙ конфигурации ---
    print(f"Создание финальных отчетов для {current_device_name}...")

    # ВНИМАНИЕ: Для корректной работы calculate_full_report и analyze_json_files_for_min_fail
    # эти функции должны уметь фильтровать файлы по current_device_name внутри себя.
    r.calculate_full_report(DEVICE_REPORTS, current_report_from_all, current_device_name)
    r.analyze_json_files_for_min_fail(DEVICE_REPORTS, current_expected_result, current_min_fail, current_device_name)
    r.generate_comparison_report(current_report_from_all, current_expected_result, current_final_report)

    # Генерация PDF-отчетов
    h.device_reports_to_pdf(str(DEVICE_REPORTS), str(current_pdf_report_all))  # Добавляем фильтр

    h.create_pdf(
        str(current_final_report),
        str(current_pdf_report),
        RGB,
        NTSC,
        current_plot_picture,
        COLOR_SPACE_PICTURE,
        current_min_fail,
        test,
    )

    h.merge_pdfs((current_pdf_report,current_pdf_report_all),current_result)

    print(f"Отчеты для {current_device_name} сохранены в {current_result}")

# --- Шаг 3: Финальные шаги (Архивация и Очистка) ---
print("\n--- Финализация и очистка ---")

FOLDERS_TO_PROCESS = [DEVICE_REPORTS, PDF_REPORTS_FOLDER, TEST_REPORTS_FOLDER, DATA_FOLDER, PICTURES_FOLDER]
ARCHIVE_SUMMARY_NAME = "Full_Report_Summary"

h.archive_reports(
    ARCHIVE_SUMMARY_NAME,
    TIMESTAMP,
    FOLDERS_TO_PROCESS
)

h.clear_folders(FOLDERS_TO_PROCESS)