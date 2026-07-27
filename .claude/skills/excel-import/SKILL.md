---
name: excel-import
description: Converts manually filled "9 points" Excel measurement sheets (workbook has sheets "Statistics"/"Gamma"/"9 points"/"5_13 points"; filename often like "<Model> ORDER x SCREEN CHECK vX.X.xlsx" or "<Model>亮度表.xlsx") into DCnRG_V2 data/*.json files, wires up the matching device YAML config, and runs the report pipeline. Use when the user hands over such an Excel file and wants a report generated.
---

# Excel Import ("9 points" sheet → data/*.json → report)

## Когда использовать

Пользователь даёт Excel-файл ручного заполнения замеров с листом **"9 points"**
(обычно в книге также есть листы `Statistics`, `Gamma`, `5_13 points`) и хочет
получить из него файлы `data/*.json` для `main.py` и/или готовый HTML-отчёт.
Имя файла бывает разным (`<Модель> ORDER x SCREEN CHECK vX.X.xlsx`,
`<Модель>亮度表.xlsx` и т.п.) — не полагайся на паттерн имени, проверяй лист
`9 points` напрямую (`openpyxl`, `data_only=True`).

## Сквозной workflow

1. **Конвертировать** через `tools/excel_import.py`:
   ```bash
   python tools/excel_import.py "<путь к .xlsx>" --output-dir data
   ```
   Флаг `--monitor` — если устройство НЕ TV (по умолчанию скрипт всегда
   ставит `IsTV=True`; для мониторов уточнить у пользователя явно, автоматика
   этого определить не может).

2. **Проверить/поправить `DeviceConfiguration`** в сгенерированных JSON.
   Скрипт берёт имя устройства из имени файла (всё до слова `ORDER`, либо весь
   stem, если `ORDER` не найдено) — это часто не совпадает с реальным именем
   заказа/конфига (например файл `SDF-55UQ7000MBAC亮度表.xlsx` даст
   `DeviceConfiguration = "SDF-55UQ7000MBAC亮度表"`, а нужное имя —
   `SDF-55UQ7000MBAC_CH28`). **Всегда уточняй у пользователя точное имя
   заказа/конфига**, если оно не очевидно из контекста разговора. Массовая
   правка всех файлов сразу:
   ```python
   import json, glob
   for f in glob.glob('data/<serial-prefix>*.json'):
       with open(f, 'r', encoding='utf-8') as fh:
           data = json.load(fh)
       data['DeviceConfiguration'] = '<точное имя>'
       with open(f, 'w', encoding='utf-8') as fh:
           json.dump(data, fh, indent=2)
   ```
   (Не `sed` — JSON пишется с `ensure_ascii`-эскейпами для не-ASCII имён,
   текстовая замена не сработает; правь через `json.load`/`json.dump`.)

3. **Найти и подложить YAML-конфиг устройства.** `main.py` ищет
   `config/device_configs/<DeviceConfiguration>.yaml`, при отсутствии тихо
   откатывается на `config/configuration_example.yaml` (общий шаблон без
   точных допусков конкретной модели — отчёт всё равно сгенерируется, но
   сравнение будет не по адресным допускам). Поэтому перед прогоном стоит
   поискать реальный конфиг заказа, например в `D:\TV\Samples\<N> order\
   Optical_configs\<DeviceConfiguration>.yaml`, и скопировать его:
   ```bash
   cp "D:/TV/Samples/28 order/Optical_configs/<DeviceConfiguration>.yaml" \
      "config/device_configs/"
   ```
   `config/device_configs/*` в `.gitignore` (кроме `.gitkeep`) — копировать
   туда конкретные заказные конфиги безопасно, в коммит они не попадут.

4. **Прогнать пайплайн**, ограничившись именно этим устройством (в `data/`
   могут одновременно лежать данные по другим моделям — см. ниже про
   `data/`):
   ```bash
   python main.py --verbose --device "<DeviceConfiguration>"
   ```
   Проверить лог на `Failed '...' calculation` (ожидаемо для `delta_e`, см.
   ограничения ниже) и что в конце `Report generated: results\...html`.

## `data/` — важные нюансы

- Вся папка `data/` в `.gitignore` — файлы там никогда не попадают в
  `git status`/коммиты, это чисто рабочая область.
- В `data/` могут одновременно лежать **чужие, не связанные с текущей
  задачей** JSON-файлы — например настоящие экспорты измерительного прибора
  (с полными x/y/T по каждой точке, не только Lv) для других моделей,
  оставленные с прошлых сессий. Перед запуском `main.py` **без** `--device`
  стоит проверить, что реально лежит в `data/`:
  ```bash
  grep -h '"DeviceConfiguration"' data/*.json | sort | uniq -c
  ```
  Не удалять и не трогать чужие файлы без явного запроса пользователя —
  просто сообщить, что они там есть, и спросить, что с ними делать.
- После **успешной** генерации отчёта `main.py` сам архивирует и удаляет
  обработанные исходные JSON из `data/` (см. `CLAUDE.md` про
  `archive_specific_files`/`clear_specific_files`). Значит после первого
  успешного прогона файлы, созданные конвертером, из `data/` исчезнут —
  это нормально, результат смотреть в `results/*.html` и
  `report_archive/*.zip`. Если нужно перегенерировать — либо конвертировать
  Excel заново, либо распаковать нужный `report_archive/*.zip`.

## Формат листа "9 points" (для доработки/отладки скрипта)

Данные организованы блоками по 9 строк. В каждом блоке — до двух образцов
рядом: левый занимает колонки A–F, правый — те же позиции со сдвигом
+6 колонок (G–L). Внутри блока (row0 = первая строка блока, col0 = A(1) или
G(7)):

| Что | Ячейка (относительно row0/col0) |
|---|---|
| Номер образца | row0, col0 |
| Серийный номер (объединена на 4 колонки) | row0, col0+2 |
| Сетка яркости 3×3 (Top/Middle/Bottom × Left/Center/Right) | row0+2..+4, col0+2..+4 |
| Температура (T), одно значение на образец | row0+5, col0+3 |
| Яркость White (Lv) | row0+6, col0+2 |
| Яркость Black (Lv) | row0+6, col0+3 |
| x координаты White/Red/Green/Blue | row0+7, col0+1..+4 |
| y координаты White/Red/Green/Blue | row0+8, col0+1..+4 |

Колонка `F`/`L` внутри блока — это Excel-формулы (`MAX`/`MIN`/контраст/площадь
гамута через `IFERROR`/`ABS`), не сырые данные, их всегда игнорировать
(проверено через `data_only=False`: `F3='=MAX(C3:E5)'` и т.п.).

Пустые шаблонные строки (заполнен только номер образца, серийный номер и
данные пусты) конвертер сам отфильтровывает — обрабатываются только образцы
с непустым серийным номером (`_extract_sample` возвращает сэмпл, но вызывающий
код в `convert()` пропускает те, где `sample["serial"] is None`).

Проверено на двух реальных файлах (`SDX-...43U5500MBA...`,
`SDF-...55UQ7000MBAC亮度表...`) — раскладка идентична в обоих, включая формулы
в колонке F/L. Если попадётся файл с другой раскладкой — сначала сверить
через `data_only=True`/`data_only=False` дамп первых ~18 строк листа
`9 points`, не гадать по аналогии.

## Известные ограничения данных

В листе "9 points" **нет** x/y координат цветности для 9 точек сетки и для
`Center`/`BlackColor` — только Lv. Из-за этого:
- Delta E (цветовая однородность) не считается — это ожидаемо и штатно
  обрабатывается генератором (метрика уходит в `None`, лог пишет
  `Failed 'delta_e' calculation: ...`).
- Координаты `Center_x/Center_y` в отчёте будут отсутствовать — вместо них
  для TV-метрик используются координаты `WhiteColor` (см. `calculate.py`:
  `brightness_calculation_point`/`numerator_key` = `"WhiteColor"` при
  `is_tv=True`).
- `Lv` для `RedColor`/`GreenColor`/`BlueColor` тоже не заполняется (в Excel
  для гамута есть только x/y) — это не используется расчётами (`cg`/`cg_by_area`
  берут только x/y через `coordinates_of_triangle`), но если кто-то ждёт
  Lv в этих точках в отчёте — их там не будет.

## Связанный фикс в коде (уже в основной ветке, коммит `f561c64`)

`src/parse.py::get_coordinates` был исправлен, чтобы не падать с `KeyError`,
когда у измерения (например `Center`) отсутствуют ключи `x`/`y` — раньше это
приводило к тому, что отбрасывались вообще все координаты (включая валидные
Red/Green/Blue/White), и пайплайн падал в `helpers.process_device_reports`
(`AttributeError: 'NoneType' object has no attribute 'items'`). Если это
исключение снова где-то вылезет — искать похожую причину: прямое
`measurement["x"]` без `.get()`/без обработки `KeyError`/`TypeError` при
неполных ручных данных. Тест на это: воспроизводится, только если у ЛЮБОЙ
из локаций `Red/Green/Blue/White/Center` отсутствует `x` или `y` — при
конвертации из Excel такое происходит для `Center`.

`tools/excel_import.py` и этот фикс уже закоммичены — при следующем запуске
просто пользоваться ими, не пересоздавать.
