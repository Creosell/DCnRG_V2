"""
Builds a demo of the "Repeated measurements" section from real measurements: ten devices of a batch of 32 are the base, and the
repeated attempts of their points are the values the other 22 devices measured at the same point.

    python tools/make_attempts_real_demo.py

Writes the files to data_examples/attempts_real/data and the report to data_examples/attempts_real/report.html.
"""
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import src.evaluate as ev  # noqa: E402
import src.report as report  # noqa: E402
import yaml  # noqa: E402

DEMO = ROOT / "data_examples" / "attempts_real"
BATCH = Path(r"C:\Users\Pavel\Desktop\Excel_update\Tests\32pcs")
CONFIG_SOURCE = Path(r"C:\Users\Pavel\source\repos\Creosell\WPF-LCD-Test\WPF LCD Test\bin\Debug\net8.0-windows\config\device_configs\CH32\SDF-50UQ7000MBA_CH32.yaml")
BASE_COUNT = 10
REPEATABLE = ["WhiteColor", "BlackColor", "RedColor", "GreenColor", "BlueColor", "TopLeft", "TopRight", "Center", "BottomLeft", "BottomRight"]
KEYS = ("x", "y", "Lv", "T")


def number(value):
    """A float, or None for a missing or damaged number of the file."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def usable(measurement: dict) -> bool:
    """A point can be repeated when it has the number it is judged by: the coordinates of a color, the luminance of the rest."""
    if measurement is None:
        return False
    needed = ("x", "y") if measurement["Location"] in ("RedColor", "GreenColor", "BlueColor") else ("Lv",)
    return all(number(measurement.get(k)) is not None for k in needed)


def load_batch() -> list:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(BATCH.glob("*.json"))]


def by_location(device: dict) -> dict:
    return {m["Location"]: m for m in device["Measurements"]}


def build_devices(batch: list, expected_values: dict) -> list:
    """The base devices with the attempts taken from the donors (a donor gives a point to a device only once)."""
    base, donors = batch[:BASE_COUNT], batch[BASE_COUNT:]
    rng = random.Random(32)
    result = []
    for device in base:
        measurements = by_location(device)
        repeated = rng.sample(candidates := [loc for loc in REPEATABLE if usable(measurements.get(loc))], min(len(candidates), rng.choice([0, 1, 2, 3, 3, 4, 5])))
        for location in repeated:
            pool = [by_location(d)[location] for d in donors if usable(by_location(d).get(location))]
            attempts = [{k: number(measurements[location].get(k)) for k in KEYS}]
            attempts += [{k: number(m.get(k)) for k in KEYS} for m in rng.sample(pool, rng.choice([1, 2, 2, 3, 4]))]
            best = ev.best_attempt_index(location, attempts, expected_values, True)
            measurements[location].update(attempts[best])
            measurements[location]["Attempts"] = [{**a, "Best": i == best} for i, a in enumerate(attempts)]
        device["Measurements"] = list(measurements.values())
        device["DeviceConfiguration"] = f"{CONFIG_SOURCE.parent.name}\{CONFIG_SOURCE.stem}"  # the folder the configuration is chosen from, as the application writes it
        result.append(device)
    return result


def main() -> int:
    batch = load_batch()
    config_text = CONFIG_SOURCE.read_text(encoding="utf-8")
    expected = report.expand_coordinates_tolerance(yaml.safe_load(config_text))
    devices = build_devices(batch, expected)

    data_dir = DEMO / "data"
    shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True)
    for device in devices:
        (data_dir / f"{device['SerialNumber']}.json").write_text(json.dumps(device, indent=2, ensure_ascii=False), encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="attempts_real_") as tmp:
        work = Path(tmp)
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("tests", "__pycache__"))
        shutil.copytree(ROOT / "config", work / "config", dirs_exist_ok=True)
        shutil.copy(ROOT / "main.py", work / "main.py")
        target = work / "config" / "device_configs" / "CH32" / CONFIG_SOURCE.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(config_text, encoding="utf-8")
        shutil.copytree(data_dir, work / "data")
        result = subprocess.run([sys.executable, "main.py", "--noclean", "--no-timestamp"], cwd=work, capture_output=True, text=True)
        sys.stdout.write(result.stdout[-1200:])
        sys.stderr.write(result.stderr[-1200:])
        html = next((work / "results").glob("*.html"), None)
        if result.returncode != 0 or html is None:
            return result.returncode or 1
        shutil.copy(html, DEMO / "report.html")
    print(f"Report: {DEMO / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
