"""Converts manually filled "9 points" Excel sheets into DCnRG_V2 data/*.json files.

Sheet layout (per 9-row block, two samples side by side, columns offset by +6):
    row+0, col A/G       -> sample index
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
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import openpyxl

SHEET_NAME = "9 points"
STATS_SHEET_NAME = "Statistics"
SPEC_COLS = {"min": 7, "typ": 8, "max": 9}  # Spec MIN/TYP/MAX in columns G:I of the Statistics sheet
TOLERANCE_LABEL = "Coordinates tolerance"
BLOCK_ROWS = 9
SAMPLE_COL_OFFSETS = (0, 6)  # left sample starts at column A, right sample at column G
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _device_name_from_filename(xlsx_path: Path) -> str:
    match = re.match(r"(.+?)\s+ORDER\b", xlsx_path.stem, flags=re.IGNORECASE)
    return match.group(1) if match else xlsx_path.stem


PLAIN_SPEC_KEYS = {
    "brightness": ("Brightness", 1),
    "brightness uniformity": ("Brightness_uniformity", 100),
    "contrast": ("Contrast", 1),
    "color temperature": ("Temperature", 1),
}
COORDINATE_SPEC_RE = re.compile(r"(red|green|blue|white) ([xy])", re.IGNORECASE)
GAMUT_SPEC_RE = re.compile(r"color gamut,\s*(ntsc|srgb|dci-p3|rec\.?2020)\s+(1931 xy|1976 u'v')", re.IGNORECASE)
GAMUT_SPACE_SUFFIX = {"ntsc": "ntsc", "srgb": "rgb", "dci-p3": "dcip3", "rec2020": "rec2020", "rec.2020": "rec2020"}
YAML_METRIC_ORDER = (
    ["Brightness", "Brightness_uniformity", "Contrast"]
    + [f"Cg_{cs}{suffix}" for cs in ("rgb", "ntsc", "dcip3", "rec2020")
       for suffix in ("_area", "", "_uv_area", "_uv")]
    + ["Temperature", "Delta_e"]
)
COORDINATE_KEYS = [f"{c}_{a}" for c in ("Red", "Green", "Blue", "White") for a in ("x", "y")]


def _spec_key(label: str) -> tuple[str, float] | None:
    """Maps a Statistics row label to (YAML metric key, scale factor from sheet units to YAML units)."""
    label = label.strip()
    if label.lower() in PLAIN_SPEC_KEYS:
        return PLAIN_SPEC_KEYS[label.lower()]
    if match := COORDINATE_SPEC_RE.fullmatch(label):
        return f"{match[1].capitalize()}_{match[2].lower()}", 1
    if match := GAMUT_SPEC_RE.fullmatch(label):
        space = GAMUT_SPACE_SUFFIX[match[1].lower()]
        return f"Cg_{space}{'_uv' if 'u' in match[2] else ''}_area", 100
    return None


def extract_expected(xlsx_path: Path) -> dict:
    """Reads the Spec MIN/TYP/MAX table (and the coordinates tolerance) from the Statistics sheet.

    Returns {"metrics": {yaml_key: {"min", "typ", "max"}}, "tolerance": float | None}.
    Gamut and uniformity values are converted from fractions to percent; empty cells become None.
    """
    ws = openpyxl.load_workbook(xlsx_path, data_only=True)[STATS_SHEET_NAME]
    metrics = {}
    for row in range(2, ws.max_row + 1):
        label = ws.cell(row=row, column=1).value
        mapped = _spec_key(label) if isinstance(label, str) else None
        if mapped is None:
            continue
        key, scale = mapped
        metrics[key] = {
            name: None if (v := ws.cell(row=row, column=col).value) is None else round(v * scale, 6)
            for name, col in SPEC_COLS.items()
        }

    tolerance = next(
        (ws.cell(row=row, column=15).value for row in range(1, ws.max_row + 1)
         if ws.cell(row=row, column=13).value == TOLERANCE_LABEL),
        None,
    )
    return {"metrics": metrics, "tolerance": tolerance}


def _fmt(value) -> str:
    return "None" if value is None else f"{value:g}"


def build_expected_yaml(expected: dict) -> str:
    """Renders an expected-values device config in the same layout as configuration_example.yaml."""
    metrics = expected["metrics"]
    empty = {"min": None, "typ": None, "max": None}
    lines = []
    for key in YAML_METRIC_ORDER:
        spec = metrics.get(key, empty)
        lines.append(f"{key}:")
        lines += [f"  {name}: {_fmt(spec[name])}" for name in ("min", "typ", "max")]

    lines.append(f"Coordinates_tolerance: {_fmt(expected['tolerance'])}")
    for key in COORDINATE_KEYS:
        lines += [f"{key}:", f"  typ: {_fmt(metrics.get(key, empty)['typ'])}"]
    return "\n".join(lines) + "\n"


def _extract_sample(ws, row0: int, col0: int):
    """Extracts one sample's raw cells starting at row0/col0 (1-indexed, base=A or G)."""
    idx = ws.cell(row=row0, column=col0).value
    if idx is None:
        return None

    serial = ws.cell(row=row0, column=col0 + 2).value

    top = [ws.cell(row=row0 + 2, column=col0 + c).value for c in (2, 3, 4)]
    mid = [ws.cell(row=row0 + 3, column=col0 + c).value for c in (2, 3, 4)]
    bot = [ws.cell(row=row0 + 4, column=col0 + c).value for c in (2, 3, 4)]

    temperature = ws.cell(row=row0 + 5, column=col0 + 3).value
    white_lv = ws.cell(row=row0 + 6, column=col0 + 2).value
    black_lv = ws.cell(row=row0 + 6, column=col0 + 3).value

    gamut_x = [ws.cell(row=row0 + 7, column=col0 + c).value for c in (1, 2, 3, 4)]
    gamut_y = [ws.cell(row=row0 + 8, column=col0 + c).value for c in (1, 2, 3, 4)]

    return {
        "idx": idx,
        "serial": serial,
        "top": top,
        "mid": mid,
        "bot": bot,
        "temperature": temperature,
        "white_lv": white_lv,
        "black_lv": black_lv,
        "white_xy": (gamut_x[0], gamut_y[0]),
        "red_xy": (gamut_x[1], gamut_y[1]),
        "green_xy": (gamut_x[2], gamut_y[2]),
        "blue_xy": (gamut_x[3], gamut_y[3]),
    }


def _build_report(sample: dict, device_config: str, is_tv: bool, measurement_dt: str) -> dict:
    top_left, top_center, top_right = sample["top"]
    mid_left, center, mid_right = sample["mid"]
    bot_left, bot_center, bot_right = sample["bot"]

    def point(location, lv, xy=(None, None), t=None):
        x, y = xy
        return {"Location": location, "x": x, "y": y, "Lv": lv, "T": t}

    measurements = [
        point("TopLeft", top_left),
        point("TopCenter", top_center),
        point("TopRight", top_right),
        point("MiddleLeft", mid_left),
        point("Center", center, t=sample["temperature"]),
        point("MiddleRight", mid_right),
        point("BottomLeft", bot_left),
        point("BottomCenter", bot_center),
        point("BottomRight", bot_right),
        point("WhiteColor", sample["white_lv"], xy=sample["white_xy"]),
        point("RedColor", None, xy=sample["red_xy"]),
        point("GreenColor", None, xy=sample["green_xy"]),
        point("BlueColor", None, xy=sample["blue_xy"]),
        point("BlackColor", sample["black_lv"]),
    ]

    return {
        "SerialNumber": str(sample["serial"]) if sample["serial"] is not None else str(sample["idx"]),
        "DeviceConfiguration": device_config,
        "IsTV": is_tv,
        "MeasurementDateTime": measurement_dt,
        "Measurements": measurements,
    }


def convert(xlsx_path: Path, output_dir: Path, is_tv: bool = True, device_config: str | None = None) -> list[Path]:
    """Converts the "9 points" sheet into per-sample JSON files.

    `device_config` overrides the DeviceConfiguration derived from the file name.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[SHEET_NAME]
    device_config = device_config or _device_name_from_filename(xlsx_path)
    measurement_dt = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for row0 in range(1, ws.max_row + 1, BLOCK_ROWS):
        for col_offset in SAMPLE_COL_OFFSETS:
            sample = _extract_sample(ws, row0, 1 + col_offset)
            if sample is None or sample["serial"] is None:
                continue

            report = _build_report(sample, device_config, is_tv, measurement_dt)
            safe_serial = re.sub(r"[^A-Za-z0-9_.-]", "_", report["SerialNumber"])
            out_path = output_dir / f"{safe_serial}.json"
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            written.append(out_path)

    return written


def _resolve_config(device_config: str) -> tuple[str, Path]:
    """Resolves `--device-config` (YAML path or config name) to (name, yaml path)."""
    candidate = Path(device_config)
    if candidate.suffix.lower() in (".yaml", ".yml"):
        if not candidate.is_file():
            sys.exit(f"Config file not found: {candidate}")
        return candidate.stem, candidate

    yaml_path = PROJECT_ROOT / "config" / "device_configs" / f"{device_config}.yaml"
    if not yaml_path.is_file():
        sys.exit(f"Config '{device_config}' not found in {yaml_path.parent}. Pass a path to the .yaml instead.")
    return device_config, yaml_path


def generate_report(json_files: list[Path], name: str, yaml_path: Path, output_dir: Path) -> Path:
    """Runs main.py in an isolated temp workspace and copies the resulting HTML into `output_dir`."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copytree(PROJECT_ROOT / "config", work / "config", dirs_exist_ok=True)
        (work / "config" / "device_configs").mkdir(parents=True, exist_ok=True)
        shutil.copy2(yaml_path, work / "config" / "device_configs" / f"{name}.yaml")
        (work / "data").mkdir()
        for f in json_files:
            shutil.copy2(f, work / "data" / f.name)

        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), "--no-timestamp", "--noclean"],
            cwd=work, check=True, env={**os.environ, "PYTHONUTF8": "1"},
        )
        html = work / "results" / f"{name}.html"
        if not html.is_file():
            sys.exit("Report was not generated.")
        target = output_dir / html.name
        shutil.copy2(html, target)
        return target


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx_file", type=Path, help="Path to the manually filled Excel file")
    config_help = (
        "Config name (from config/device_configs) or path to a .yaml. "
        "Sets DeviceConfiguration in the JSON files and also generates the HTML report next to them."
    )
    parser.add_argument("device_config_pos", nargs="?", metavar="device_config", help=config_help)
    parser.add_argument("--output-dir", type=Path, default=Path("data"), help="Directory for generated JSON files")
    parser.add_argument("--device-config", help=config_help)
    parser.add_argument(
        "--spec-from-xlsx", action="store_true",
        help="Build the device YAML from the Spec table on the Statistics sheet "
             "(saved as <device_config>.yaml in --output-dir) instead of reading an existing config. "
             "Enabled automatically when no device config is given (name is taken from the file name).",
    )
    parser.add_argument("--monitor", action="store_true", help="Mark device as monitor instead of TV")
    args = parser.parse_args()

    device_config = args.device_config or args.device_config_pos
    if args.spec_from_xlsx or not device_config:
        device_config = device_config or _device_name_from_filename(args.xlsx_file)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        name, yaml_path = device_config, args.output_dir / f"{device_config}.yaml"
        yaml_path.write_text(build_expected_yaml(extract_expected(args.xlsx_file)), encoding="utf-8")
        print(f"Expected values config: {yaml_path}")
    else:
        name, yaml_path = _resolve_config(device_config)

    written = convert(args.xlsx_file, args.output_dir, is_tv=not args.monitor, device_config=name)
    print(f"Written {len(written)} file(s) to {args.output_dir}")
    for path in written:
        print(f"  {path}")

    if yaml_path:
        print(f"Report: {generate_report(written, name, yaml_path, args.output_dir)}")


if __name__ == "__main__":
    main()
