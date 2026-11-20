"""
Builds a demo of the "Repeated measurements" section: ten measurement files of one TV configuration with different histories of
repeated measurements, and the report generated from them.

    python tools/make_attempts_demo.py          the ten devices below
    python tools/make_attempts_demo.py --cases  one device per transition of a point (first attempt -> best attempt), see CASES

Writes the files to data_examples/attempts_demo/data and the report to data_examples/attempts_demo/report.html. The configuration
of the demo is a copy of a real one with a tighter color tolerance, so the color points can fail.

The ten devices (the numbers are the attempts of a point in the order they were measured):
    AT10001  no repeats, everything good (only counted in "devices of the report")
    AT10002  everything bad, a little better with every repeat, still outside the spec
    AT10003  white and red were bad and stayed bad
    AT10004  white outside the spec, the 2nd attempt rescued it
    AT10005  everything was good at the first attempt, measured again anyway
    AT10006  the best attempt is the 2nd of three
    AT10007  the best attempt is the first, the repeats were worse
    AT10008  the black point (the darker the better) and points without a spec
    AT10009  color points: rescued, rescued, good from the start
    AT10010  below typ: improved, but not up to the typical value
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data_examples" / "attempts_demo"
CONFIG_NAME = "SDF-75UQM8000MBAC_CH31"
# The measurement app of this project keeps the device configurations next to its executable; the demo needs one with the spec of a TV
CONFIG_SOURCES = [
    Path(r"C:\Users\Pavel\source\repos\Creosell\WPF-LCD-Test\WPF LCD Test\bin\Debug\net8.0-windows\config\device_configs\CH31") / f"{CONFIG_NAME}.yaml",
]

GRID = ["TopLeft", "TopCenter", "TopRight", "MiddleLeft", "Center", "MiddleRight", "BottomLeft", "BottomCenter", "BottomRight"]
GOOD_XY = {"RedColor": (0.670, 0.310), "GreenColor": (0.270, 0.660), "BlueColor": (0.150, 0.060), "WhiteColor": (0.280, 0.290)}
GRID_LV = {"TopLeft": 452, "TopCenter": 468, "TopRight": 455, "MiddleLeft": 460, "Center": 472, "MiddleRight": 463, "BottomLeft": 450, "BottomCenter": 466, "BottomRight": 454}


def attempt(x, y, lv, t=9100):
    return {"x": x, "y": y, "Lv": lv, "T": t}


def base_points() -> dict:
    """The points of a device without any problem; every value is a list of attempts of length one."""
    points = {loc: [attempt(0.280, 0.290, lv)] for loc, lv in GRID_LV.items()}
    points["WhiteColor"] = [attempt(0.280, 0.290, 478)]
    points["BlackColor"] = [attempt(0.280, 0.290, 0.060, t=0)]
    for loc in ("RedColor", "GreenColor", "BlueColor"):
        x, y = GOOD_XY[loc]
        points[loc] = [attempt(x, y, 120)]
    return points


def white(*lvs):
    return [attempt(0.280, 0.290, lv) for lv in lvs]


def black(*lvs):
    return [attempt(0.280, 0.290, lv, t=0) for lv in lvs]


def grid(loc, *lvs):
    return [attempt(0.280, 0.290, lv) for lv in lvs]


def color(loc, *xys):
    return [attempt(x, y, 120) for x, y in xys]


SCENARIOS = {
    "AT10001": {},
    "AT10002": {"WhiteColor": white(378, 385, 392), "TopLeft": grid("TopLeft", 392, 399, 404)},
    "AT10003": {"WhiteColor": white(388, 387, 389), "RedColor": color("RedColor", (0.692, 0.320), (0.694, 0.322), (0.690, 0.318))},
    "AT10004": {"WhiteColor": white(392, 456)},
    "AT10005": {"WhiteColor": white(472, 468, 475), "BlackColor": black(0.058, 0.061)},
    "AT10006": {"WhiteColor": white(398, 462, 441)},
    "AT10007": {"WhiteColor": white(458, 441, 449)},
    "AT10008": {"BlackColor": black(0.094, 0.061, 0.058), "TopLeft": grid("TopLeft", 405, 418), "MiddleLeft": grid("MiddleLeft", 410, 412, 431)},
    "AT10009": {"RedColor": color("RedColor", (0.690, 0.318), (0.680, 0.314), (0.672, 0.311)),
                "GreenColor": color("GreenColor", (0.290, 0.650), (0.280, 0.655)),
                "BlueColor": color("BlueColor", (0.150, 0.060), (0.151, 0.061))},
    "AT10010": {"WhiteColor": white(425, 431, 440), "BottomRight": grid("BottomRight", 430, 436)},
}


# One device per transition of a point between the states of its spec (the white point: fail below 400, warn below 450, ok from 450)
CASES = {
    "CASE01": {"WhiteColor": white(392, 456)},             # fail -> ok            Fixed
    "CASE02": {"WhiteColor": white(431, 462)},             # warn -> ok            Fixed
    "CASE03": {"WhiteColor": white(378, 436)},             # fail -> warn          Improved, now warn
    "CASE04": {"WhiteColor": white(378, 385, 392)},        # fail -> fail, better  Improved, still fail
    "CASE05": {"WhiteColor": white(430, 441)},             # warn -> warn, better  Improved, still warn
    "CASE06": {"WhiteColor": white(455, 470)},             # ok -> ok, better      Improved
    "CASE07": {"TopLeft": grid("TopLeft", 392, 404),       # no spec, better       Improved (neutral)
               "BlackColor": black(0.094, 0.058)},
    "CASE08": {"WhiteColor": white(395, 380, 372)},        # first is the best, fail  No effect, still fail
    "CASE09": {"WhiteColor": white(441, 430, 436)},        # first is the best, warn  No effect, still warn
    "CASE10": {"WhiteColor": white(470, 458, 462),         # first is the best, ok    No effect (neutral)
               "BlackColor": black(0.058, 0.061)},
    "CASE11": {"RedColor": color("RedColor", (0.692, 0.320), (0.690, 0.318), (0.672, 0.311)),    # colors: fail -> ok
               "GreenColor": color("GreenColor", (0.290, 0.650), (0.285, 0.652)),                 # fail -> fail, better
               "BlueColor": color("BlueColor", (0.150, 0.060), (0.152, 0.062))},                  # ok, the first is the best
    "CASE12": {"WhiteColor": white(378, 392), "RedColor": color("RedColor", (0.692, 0.320), (0.690, 0.318)),  # the worst card: everything stays bad
               "BlackColor": black(0.058, 0.094), "TopLeft": grid("TopLeft", 392, 380)},
}


def best_index(location: str, attempts: list) -> int:
    """The index the report generator picks; the demo takes it from the generator itself."""
    sys.path.insert(0, str(ROOT))
    import src.evaluate as ev
    spec = yaml.safe_load(DEMO_CONFIG.read_text(encoding="utf-8"))
    import src.report as r
    return ev.best_attempt_index(location, attempts, r.expand_coordinates_tolerance(spec), True)


def write_files():
    data_dir = DEMO / "data"
    shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True)
    for number, (serial, changes) in enumerate(SCENARIOS.items()):
        points = base_points()
        points.update(changes)
        measurements = []
        for location, attempts in points.items():
            best = best_index(location, attempts) if len(attempts) > 1 else 0
            entry = {"Location": location, **{k: attempts[best][k] for k in ("x", "y", "Lv", "T")}}
            if len(attempts) > 1:
                entry["Attempts"] = [{**a, "Best": i == best} for i, a in enumerate(attempts)]
            measurements.append(entry)
        device = {
            "SerialNumber": serial, "DeviceConfiguration": CONFIG_NAME, "IsTV": True,
            "MeasurementDateTime": f"202611{16 + number // 4:02d}_{9 + number:02d}{number * 5:02d}00",
            "Colorimeter": {"Model": "CA-410", "ProbeSN": "81026182", "Channel": 2},
            "Measurements": measurements,
        }
        (data_dir / f"{serial}.json").write_text(json.dumps(device, indent=2, ensure_ascii=False), encoding="utf-8")
    return data_dir


def prepare_config(workdir: Path) -> Path:
    source = next((p for p in CONFIG_SOURCES if p.exists()), None)
    if source is None:
        raise SystemExit(f"No device configuration to copy the spec from: {CONFIG_SOURCES}")
    text = source.read_text(encoding="utf-8").replace("Coordinates_tolerance: 0.060", "Coordinates_tolerance: 0.015")
    target = workdir / "config" / "device_configs" / f"{CONFIG_NAME}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def main() -> int:
    global DEMO_CONFIG, DEMO, SCENARIOS
    if "--cases" in sys.argv:
        DEMO, SCENARIOS = ROOT / "data_examples" / "attempts_cases", CASES
    with tempfile.TemporaryDirectory(prefix="attempts_demo_") as tmp:
        work = Path(tmp)
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("tests", "__pycache__"))
        shutil.copytree(ROOT / "config", work / "config", dirs_exist_ok=True)
        shutil.copy(ROOT / "main.py", work / "main.py")
        DEMO_CONFIG = prepare_config(work)
        data_dir = write_files()
        shutil.copytree(data_dir, work / "data")
        result = subprocess.run([sys.executable, "main.py", "--noclean", "--no-timestamp"], cwd=work, capture_output=True, text=True)
        sys.stdout.write(result.stdout[-1500:])
        sys.stderr.write(result.stderr[-1500:])
        html = next((work / "results").glob("*.html"), None)
        if result.returncode != 0 or html is None:
            return result.returncode or 1
        shutil.copy(html, DEMO / "report.html")
    print(f"Report: {DEMO / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
