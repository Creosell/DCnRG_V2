"""Converts DCnRG_V2 data/*.json optical measurement reports back into a "9 points"
Excel template (reverse of excel_to_report.py).

Sheet layout (per 9-row block, two samples side by side, columns offset by +6):
    row+0, col A/G       -> sample index (idx, already pre-filled in template)
    row+0, col C/I        -> serial number (merged C1:F1 / I1:L1)
    row+2..+4, col C:E/I:K -> 3x3 brightness (Lv) grid: Top/Middle/Bottom x Left/Center/Right
    row+5, col D/J        -> color temperature (T)
    row+6, col C/I        -> White Lv
    row+6, col D/J        -> Black Lv
    row+7, col B:E/H:K    -> White/Red/Green/Blue x
    row+8, col B:E/H:K    -> White/Red/Green/Blue y
"""

import argparse
import json
from pathlib import Path

import openpyxl

SHEET_NAME = "9 points"
BLOCK_ROWS = 9
SAMPLE_COL_OFFSETS = (0, 6)  # left sample starts at column A, right sample at column G


def _slot_position(slot: int):
    """Maps a 1-based slot number to (row0, col0) using the template's idx layout
    (left column of each block = idx 1..10, right column = idx 11..20)."""
    if slot <= 10:
        block, col_offset = slot - 1, 0
    else:
        block, col_offset = slot - 11, 6
    row0 = 1 + block * BLOCK_ROWS
    return row0, 1 + col_offset


def _measurement_map(report: dict) -> dict:
    return {m["Location"]: m for m in report["Measurements"]}


def _write_sample(ws, row0: int, col0: int, report: dict) -> None:
    m = _measurement_map(report)

    ws.cell(row=row0, column=col0 + 2).value = report["SerialNumber"]

    for c, loc in zip((2, 3, 4), ("TopLeft", "TopCenter", "TopRight")):
        ws.cell(row=row0 + 2, column=col0 + c).value = m[loc]["Lv"]
    for c, loc in zip((2, 3, 4), ("MiddleLeft", "Center", "MiddleRight")):
        ws.cell(row=row0 + 3, column=col0 + c).value = m[loc]["Lv"]
    for c, loc in zip((2, 3, 4), ("BottomLeft", "BottomCenter", "BottomRight")):
        ws.cell(row=row0 + 4, column=col0 + c).value = m[loc]["Lv"]

    ws.cell(row=row0 + 5, column=col0 + 3).value = m["Center"]["T"]
    ws.cell(row=row0 + 6, column=col0 + 2).value = m["WhiteColor"]["Lv"]
    ws.cell(row=row0 + 6, column=col0 + 3).value = m["BlackColor"]["Lv"]

    for c, loc in zip((1, 2, 3, 4), ("WhiteColor", "RedColor", "GreenColor", "BlueColor")):
        ws.cell(row=row0 + 7, column=col0 + c).value = m[loc]["x"]
        ws.cell(row=row0 + 8, column=col0 + c).value = m[loc]["y"]


def export(json_dir: Path, template_xlsx: Path, output_xlsx: Path) -> int:
    reports = []
    for path in sorted(json_dir.glob("*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        reports.append(report)
    reports.sort(key=lambda r: r["SerialNumber"])

    wb = openpyxl.load_workbook(template_xlsx)
    ws = wb[SHEET_NAME]

    for slot, report in enumerate(reports, start=1):
        row0, col0 = _slot_position(slot)
        _write_sample(ws, row0, col0, report)

    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_xlsx)
    return len(reports)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_dir", type=Path, help="Directory with data/*.json reports")
    parser.add_argument("template_xlsx", type=Path, help="Path to the blank '9 points' Excel template")
    parser.add_argument("output_xlsx", type=Path, help="Path to write the filled Excel file")
    args = parser.parse_args()

    count = export(args.json_dir, args.template_xlsx, args.output_xlsx)
    print(f"Written {count} sample(s) into {args.output_xlsx}")


if __name__ == "__main__":
    main()
