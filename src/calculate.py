import numpy as np
from shapely.geometry import Polygon
from colormath2.color_objects import xyYColor, LabColor
from colormath2.color_conversions import convert_color
from colormath2.color_diff import delta_e_cie2000
import src.parse as parse
import src.helpers as h
import matplotlib.pyplot as plt


def area(p):
    """Calculates the area of a triangle defined by three points."""
    return 0.5 * abs(np.cross(p[1] - p[0], p[2] - p[0]))


def calculate_overlap_percentage(x1, y1, x2, y2, x3, y3, x4, y4, x5, y5, x6, y6):
    """Calculates the percentage for area of the first triangle covered by the second triangle."""
    triangle1 = np.array([[x1, y1], [x2, y2], [x3, y3]])
    triangle2 = np.array([[x4, y4], [x5, y5], [x6, y6]])

    # Check if the input data forms valid triangles
    if area(triangle1) == 0 or area(triangle2) == 0:
        return "Error: the input data does not form valid triangles."

    # Convert the triangles into Polygon objects using the Shapely library
    polygon1 = Polygon(triangle1)
    polygon2 = Polygon(triangle2)

    # Calculate the intersection area of the polygons
    intersection = polygon1.intersection(polygon2)

    # If the intersection is not an empty polygon, calculate its area
    if intersection.is_empty:
        intersection_area = 0.0
    else:
        intersection_area = intersection.area

    # Calculate the percentage for area of the first triangle covered by the second triangle
    overlap_percentage = (intersection_area / polygon1.area) * 100

    return overlap_percentage


def brightness(file, is_tv):
    """
    Рассчитывает min/max яркость, типовую яркость (typ) для отчета
    (WhiteColor или Center) и яркость Center для расчета равномерности.
    """
    report = h.parse_one_file(file)
    if report is None:
        return {"min": None, "typ": None, "max": None, "uniformity_center_lv": None}

    measurements = report.get("Measurements", [])

    typical_lv_for_report = None
    center_lv_for_uniformity = None

    # 1. Точка для типового значения (typ): WhiteColor для ТВ, Center для остальных
    report_typ_key = "WhiteColor" if is_tv else "Center"

    # Исключенные точки для расчета min/max (т.е. для оценки равномерности)
    excluded_locations = {"RedColor", "GreenColor", "BlueColor", "BlackColor","WhiteColor"}
    all_lv_values = []

    for measurement in measurements:
        location = measurement.get("Location")
        lv_str = measurement.get("Lv")

        try:
            lv = float(lv_str)
        except (ValueError, TypeError):
            continue

            # a) Находим типовое значение для отчета (typ)
        if location == report_typ_key:
            typical_lv_for_report = lv

        # b) Находим значение Center (всегда для равномерности)
        if location == "Center":
            center_lv_for_uniformity = lv

        # c) Собираем значения для расчета min/max
        if location not in excluded_locations:
            all_lv_values.append(lv)

    # 2. Расчет min, max
    min_lv = min(all_lv_values) if all_lv_values else None
    max_lv = max(all_lv_values) if all_lv_values else None

    # 3. Возвращаем результат
    return {
        "min": min_lv,
        "typ": typical_lv_for_report,
        "max": max_lv,
        "uniformity_center_lv": center_lv_for_uniformity
    }


def brightness_uniformity(brightness_value):
    """
    Рассчитывает равномерность яркости, используя минимальную яркость
    и яркость Center (uniformity_center_lv).
    """
    min_lv = brightness_value.get("min")
    center_lv = brightness_value.get("uniformity_center_lv")

    if min_lv is None or center_lv is None or center_lv == 0.0:
        return 0.0

    brightness_uniformity_percent = (min_lv / center_lv) * 100
    return brightness_uniformity_percent


def cg_by_area(file, color_space):
    coordinate = parse.coordinates_of_triangle(file)
    if len(coordinate) != 6:
        return None
    x1, y1, x2, y2, x3, y3 = coordinate
    triangle = np.array([[x1, y1], [x2, y2], [x3, y3]])
    color_gamut_srgb = (area(triangle) / 0.112) * 100
    color_gamut_ntcs = (area(triangle) / 0.158) * 100
    if color_space == "sRGB, NTSC":
        return float(color_gamut_srgb), float(color_gamut_ntcs)
    elif color_space == "sRGB":
        return float(color_gamut_srgb), None
    elif color_space == "NTSC":
        return None, float(color_gamut_ntcs)
    else:
        pass


def cg(file, color_space, RGB, NTSC):
    coordinate = parse.coordinates_of_triangle(file)
    if len(coordinate) != 6:
        return None
    x1, y1, x2, y2, x3, y3 = coordinate
    if color_space == "sRGB, NTSC":
        ntsc = calculate_overlap_percentage(*NTSC, x1, y1, x2, y2, x3, y3)
        rgb = calculate_overlap_percentage(*RGB, x1, y1, x2, y2, x3, y3)
        return rgb, ntsc
    elif color_space == "sRGB":
        rgb = calculate_overlap_percentage(*RGB, x1, y1, x2, y2, x3, y3)
        ntsc = "null"
        return rgb, None
    elif color_space == "NTSC":
        rgb = "null"
        ntsc = calculate_overlap_percentage(*NTSC, x1, y1, x2, y2, x3, y3)
        return None, ntsc
    else:
        pass


def contrast(file_path, is_tv):
    """
    Рассчитывает контрастность.
    Использует WhiteColor/BlackColor для ТВ (is_tv=True) и Center/BlackColor иначе.
    """
    report = h.parse_one_file(file_path)
    if report is None:
        return None

    measurements = report.get("Measurements", [])

    # Собираем Lv для нужных точек (Center, WhiteColor, BlackColor)
    lv_values = {}

    for m in measurements:
        location = m.get("Location")

        if location in ["Center", "WhiteColor", "BlackColor"]:
            try:
                # Безопасное извлечение и конвертация в float, по умолчанию 0.0
                lv_values[location] = float(m.get("Lv", 0.0))
            except (ValueError, TypeError):
                lv_values[location] = 0.0  # В случае ошибки преобразования

    # Определяем числитель на основе флага is_tv
    numerator_key = "WhiteColor" if is_tv else "Center"

    numerator_lv = lv_values.get(numerator_key, 0.0)
    black_lv = lv_values.get("BlackColor", 0.0)

    # Расчет контрастности
    if black_lv == 0.0 or numerator_lv == 0.0:
        return 0.0

    return round(numerator_lv / black_lv, 2)


def temperature(file):
    report = h.parse_one_file(file)
    measurements = report.get("Measurements", [])

    temperature = None

    for measurement in measurements:
        if measurement["Location"] == "Center":
            temperature = float(measurement["T"])
    if temperature is None:
        raise ZeroDivisionError("NO Temperature for Central DOT")

    return temperature


def delat_e(file):
    locations = [
        "BottomLeft",
        "BottomCenter",
        "BottomRight",
        "MiddleLeft",
        "Center",
        "MiddleRight",
        "TopLeft",
        "TopCenter",
        "TopRight",
    ]
    report = h.parse_one_file(file)
    expected_x = float(next(
        (m.get('x') for m in report.get('Measurements', []) if m.get('Location') == 'Center'),
        '0.0'
    ))
    expected_y = float(next(
        (m.get('y') for m in report.get('Measurements', []) if m.get('Location') == 'Center'),
        '0.0'
    ))
    measurements = report.get("Measurements", [])
    ref = parse.find_closest_to_target(report, expected_x, expected_y)
    reference_location = ref["Location"]
    ref_x = ref["x"]
    ref_y = ref["y"]
    ref_lv = ref["Lv"]

    """Calculates Delta E Color Uniformity for given locations."""
    delta_e_values = []

    if ref_x is None or ref_y is None or ref_lv is None:
        return "Error: Missing reference color data for Center."

    ref_color = xyYColor(ref_x, ref_y, ref_lv)

    # Calculate Delta E for each location

    for measurement in measurements:

        if (measurement["Location"] not in locations) or measurement[
            "Location"
        ] == reference_location:
            continue
        x = float(measurement["x"])
        y = float(measurement["y"])
        lv = float(measurement["Lv"])
        if x is None or y is None or lv is None:
            continue

        color = xyYColor(x, y, lv)
        ref_lab = convert_color(ref_color, LabColor)
        color_lab = convert_color(color, LabColor)

        delta_e = delta_e_cie2000(ref_lab, color_lab)
        delta_e_values.append(delta_e)

    # Calculate average Delta E
    if delta_e_values:
        avg_delta_e = sum(delta_e_values) / len(delta_e_values)
        return avg_delta_e
    else:
        return "Error: No valid Delta E values calculated."


def serial_number(file):
    # Parse the JSON data if it's a string
    report = h.parse_one_file(file)
    # Extract the serial number and measurement time
    serial_number = report.get("SerialNumber", None)
    return serial_number


def measurement_time(file):
    # Parse the JSON data if it's a string
    report = h.parse_one_file(file)

    # measurement time
    measurement_time = report.get("MeasurementDateTime", None)
    return measurement_time


def plot_color_space(RGB, NTSC, x1, y1, x2, y2, x3, y3, output_file, color_space_pic):
    """Plots the color space with sRGB and device triangles and a background image."""
    # Создаем фигуру
    plt.figure(figsize=(8, 8))
    plt.title("Color Space with sRGB, NTSC and Device Triangles")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.xlim(0, 0.8)
    plt.ylim(0, 0.9)

    # Добавляем изображение на фон
    img = plt.imread(color_space_pic)  # Загружаем изображение
    plt.imshow(
        img, extent=[0, 0.77, 0, 0.82], aspect="auto"
    )  # Устанавливаем изображение как фон

    # Рисуем треугольник sRGB
    sRGB_triangle = np.array(
        [[RGB[0], RGB[1]], [RGB[2], RGB[3]], [RGB[4], RGB[5]], [RGB[0], RGB[1]]]
    )
    plt.plot(sRGB_triangle[:, 0], sRGB_triangle[:, 1], label="sRGB", color="blue")

    # Рисуем треугольник устройства
    device_triangle = np.array([[x1, y1], [x2, y2], [x3, y3], [x1, y1]])
    plt.plot(
        device_triangle[:, 0], device_triangle[:, 1], label="Device", color="green"
    )

    ntsc_triangle = np.array(
        [[NTSC[0], NTSC[1]], [NTSC[2], NTSC[3]], [NTSC[4], NTSC[5]], [NTSC[0], NTSC[1]]]
    )
    plt.plot(ntsc_triangle[:, 0], sRGB_triangle[:, 1], label="NTSC", color="black")

    # Добавляем легенду
    plt.legend()

    # Сохраняем график в файл
    plt.savefig(output_file)
    plt.close()
