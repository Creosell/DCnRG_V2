"""Validates config/device_configs/*.yaml files against the reference schema
defined by config/configuration_example.yaml.

Checks performed per file:
    - Filename contains only ASCII characters (parse.py opens files without
      encoding="utf-8", so a non-ASCII DeviceConfiguration name silently
      fails to match on Windows - see mojibake bug with Cyrillic look-alikes).
    - YAML parses without errors and has a mapping at the root.
    - Top-level keys match the reference exactly (catches typos, missing
      metrics, and keys copy-pasted from an older schema).
    - Each metric is a {min, typ, max} mapping with numeric or "None" values.
    - Coordinate entries (Red_x, Red_y, ...) require a numeric "typ" and
      allow optional numeric/"None" min/max.
    - Coordinates_tolerance is a plain number.

Run after dropping new/edited device config files into config/device_configs/:
    uv run python tools/validate_device_configs.py
"""

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
DEVICE_CONFIGS_DIR = CONFIG_DIR / "device_configs"
REFERENCE_YAML = CONFIG_DIR / "configuration_example.yaml"

COORDINATE_TEST_KEYS = {
    "Red_x", "Red_y", "Green_x", "Green_y", "Blue_x", "Blue_y", "White_x", "White_y",
}
COORDINATES_TOLERANCE_KEY = "Coordinates_tolerance"


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_none_marker(value) -> bool:
    return value == "None"


def check_filename(path: Path, errors: list, warnings: list) -> None:
    stem = path.stem
    for ch in stem:
        if ord(ch) > 127:
            errors.append(
                f"non-ASCII character {ch!r} (U+{ord(ch):04X}) in filename - "
                f"parse.py reads files without encoding='utf-8', so this can "
                f"mismatch the DeviceConfiguration field on Windows"
            )
    if stem != stem.strip():
        errors.append("filename has leading/trailing whitespace")
    if " " in stem:
        warnings.append("filename contains spaces - DeviceConfiguration values rarely do")


def check_metric_dict(key: str, value, errors: list) -> None:
    if not isinstance(value, dict):
        errors.append(f"'{key}': expected a mapping with min/typ/max, got {type(value).__name__}")
        return
    missing = {"min", "typ", "max"} - value.keys()
    if missing:
        errors.append(f"'{key}': missing field(s) {sorted(missing)}")
    extra = value.keys() - {"min", "typ", "max"}
    if extra:
        errors.append(f"'{key}': unexpected field(s) {sorted(extra)}")
    for field in ("min", "typ", "max"):
        if field not in value:
            continue
        v = value[field]
        if not is_number(v) and not is_none_marker(v):
            errors.append(f"'{key}.{field}': value {v!r} is neither a number nor 'None'")


def check_coordinate_entry(key: str, value, errors: list) -> None:
    if not isinstance(value, dict):
        errors.append(f"'{key}': expected a mapping, got {type(value).__name__}")
        return
    if "typ" not in value:
        errors.append(f"'{key}': missing required 'typ' field")
    elif not is_number(value["typ"]):
        errors.append(f"'{key}.typ': value {value['typ']!r} is not a number")
    extra = value.keys() - {"min", "typ", "max"}
    if extra:
        errors.append(f"'{key}': unexpected field(s) {sorted(extra)}")
    for field in ("min", "max"):
        if field in value and not is_number(value[field]) and not is_none_marker(value[field]):
            errors.append(f"'{key}.{field}': value {value[field]!r} is neither a number nor 'None'")


def validate_config(path: Path, reference_keys: set) -> tuple[list, list]:
    errors: list = []
    warnings: list = []

    check_filename(path, errors, warnings)

    try:
        data = load_yaml(path)
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return errors, warnings

    if not isinstance(data, dict) or not data:
        errors.append("file is empty or does not contain a YAML mapping at the root")
        return errors, warnings

    actual_keys = set(data.keys())
    missing_keys = reference_keys - actual_keys
    unknown_keys = actual_keys - reference_keys

    if missing_keys:
        errors.append(f"missing key(s): {sorted(missing_keys)}")
    if unknown_keys:
        errors.append(f"unknown/unexpected key(s), check for typos: {sorted(unknown_keys)}")

    for key in actual_keys & reference_keys:
        value = data[key]
        if key == COORDINATES_TOLERANCE_KEY:
            if not is_number(value):
                errors.append(f"'{key}': expected a number, got {value!r}")
        elif key in COORDINATE_TEST_KEYS:
            check_coordinate_entry(key, value, errors)
        else:
            check_metric_dict(key, value, errors)

    return errors, warnings


def main() -> int:
    # Console codepages (e.g. cp1252 on Windows) can't render arbitrary
    # filename characters; fall back to escaping instead of crashing on print.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dir", type=Path, default=DEVICE_CONFIGS_DIR,
        help=f"directory with device config YAML files (default: {DEVICE_CONFIGS_DIR})",
    )
    parser.add_argument(
        "--reference", type=Path, default=REFERENCE_YAML,
        help=f"reference YAML defining the expected schema (default: {REFERENCE_YAML})",
    )
    args = parser.parse_args()

    if not args.reference.exists():
        print(f"Reference YAML not found: {args.reference}")
        return 1

    reference_data = load_yaml(args.reference)
    reference_keys = set(reference_data.keys())

    config_files = sorted(args.dir.glob("*.yaml"))
    if not config_files:
        print(f"No .yaml files found in {args.dir}")
        return 1

    had_errors = False
    for path in config_files:
        errors, warnings = validate_config(path, reference_keys)
        status = "OK" if not errors else "FAIL"
        print(f"[{status}] {path.name}")
        for w in warnings:
            print(f"    WARN: {w}")
        for e in errors:
            print(f"    ERROR: {e}")
        if errors:
            had_errors = True

    print()
    print(f"Checked {len(config_files)} file(s).")
    return 1 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
