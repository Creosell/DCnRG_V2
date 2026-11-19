# tests/test_evaluate.py

import copy
import io
import json
import sys
from pathlib import Path

import pytest

from src import calculate as cal
from src import evaluate as ev
from src import helpers
from src import report

ROOT_DIR = Path(__file__).resolve().parents[2]

SPEC = {
    "Brightness": {"min": 150, "typ": 250, "max": None},
    "Brightness_uniformity": {"min": 65, "typ": 70, "max": None},
    "Contrast": {"min": 100, "typ": 200, "max": None},
    "Temperature": {"min": 6000, "typ": None, "max": 7000},
    "Red_x": {"min": 0.62, "typ": 0.65, "max": 0.68},
    "White_x": {"min": 0.30, "typ": 0.33, "max": 0.34},
    "Cg_rgb_area": {"min": 90, "typ": 95, "max": None},
    "Cg_ntsc": {"min": "None", "typ": "None", "max": "None"},
}


def checks_by_key(result):
    return {check["key"]: check for check in result["checks"]}


def test_required_locations():
    assert ev.required_locations("Brightness", True) == ("WhiteColor",)
    assert ev.required_locations("Brightness", False) == ("Center",)
    assert ev.required_locations("Contrast", True) == ("WhiteColor", "BlackColor")
    assert ev.required_locations("Cg_rec2020_uv_area", True) == ("RedColor", "GreenColor", "BlueColor")
    assert ev.required_locations("Brightness_uniformity", True) == ev.UNIFORMITY_LOCATIONS
    assert ev.required_locations("Red_x", True) == ("RedColor",)
    assert ev.required_locations("White_y", True) == ("WhiteColor",)
    assert ev.required_locations("Center_x", True) == ("Center",)
    assert ev.required_locations("Temperature", True) == ("Center",)
    assert ev.required_locations("Coordinates_tolerance", True) == ()


def test_evaluate_full_tv_device(mock_tv_data):
    result = ev.evaluate(mock_tv_data, SPEC)
    checks = checks_by_key(result)

    assert result["schema"] == ev.EVALUATE_SCHEMA_VERSION
    assert result["complete"] is True
    assert "Cg_ntsc" not in checks  # a spec of 'None' markers is not a requirement
    assert checks["Brightness"]["value"] == 200
    assert checks["Brightness"]["status"] == ev.STATUS_WARNING  # 200 is below typ 250 but above min 150
    assert checks["Contrast"]["status"] == ev.STATUS_PASS  # 200 / 0.618 = 323
    assert checks["Temperature"]["status"] == ev.STATUS_PASS
    assert checks["Red_x"]["status"] == ev.STATUS_PASS  # 0.648 inside [0.62; 0.68]
    assert checks["White_x"]["status"] == ev.STATUS_PASS  # 0.339 inside [0.30; 0.34]
    assert checks["Cg_rgb_area"]["status"] == ev.STATUS_PASS
    assert result["device"] == ev.VERDICT_WARN


def test_evaluate_marks_failing_coordinate_and_reports_the_bounds(mock_tv_data):
    spec = {"White_x": {"min": 0.30, "typ": 0.32, "max": 0.335}}

    check = checks_by_key(ev.evaluate(mock_tv_data, spec))["White_x"]

    assert check["status"] == ev.STATUS_FAIL
    assert check["value"] == 0.339
    assert (check["min"], check["typ"], check["max"]) == (0.30, 0.32, 0.335)
    assert check["locations"] == ["WhiteColor"]


def test_evaluate_partial_device_keeps_missing_metrics_pending(mock_tv_data):
    partial = copy.deepcopy(mock_tv_data)
    partial["Measurements"] = [m for m in partial["Measurements"] if m["Location"] == "WhiteColor"]

    result = ev.evaluate(partial, SPEC)
    checks = checks_by_key(result)

    assert checks["Brightness"]["status"] == ev.STATUS_WARNING
    assert checks["White_x"]["status"] != ev.STATUS_PENDING
    assert checks["Contrast"]["status"] == ev.STATUS_PENDING
    assert checks["Contrast"]["missing"] == ["BlackColor"]
    assert checks["Brightness_uniformity"]["status"] == ev.STATUS_PENDING
    assert "TopLeft" in checks["Brightness_uniformity"]["missing"]
    assert checks["Cg_rgb_area"]["missing"] == ["RedColor", "GreenColor", "BlueColor"]
    assert checks["Red_x"]["missing"] == ["RedColor"]
    assert result["complete"] is False


def test_evaluate_without_measurements_is_all_pending_and_does_not_fail(mock_tv_data):
    empty = {"SerialNumber": "SN", "IsTV": True, "Measurements": []}

    result = ev.evaluate(empty, SPEC)

    assert {check["status"] for check in result["checks"]} == {ev.STATUS_PENDING}
    assert result["device"] == ev.VERDICT_PASS
    assert result["complete"] is False


def test_evaluate_uniformity_waits_for_all_points_and_points_to_the_darkest_one(mock_tv_data):
    partial = copy.deepcopy(mock_tv_data)
    partial["Measurements"] = [m for m in partial["Measurements"] if m["Location"] != "BottomRight"]
    assert checks_by_key(ev.evaluate(partial, SPEC))["Brightness_uniformity"]["status"] == ev.STATUS_PENDING

    check = checks_by_key(ev.evaluate(mock_tv_data, SPEC))["Brightness_uniformity"]

    assert check["status"] == ev.STATUS_PASS  # 145.2 / 166.0 = 87.5 %
    assert check["locations"] == ["TopCenter"]  # the lowest luminance among the nine points


def test_evaluate_uniformity_below_spec_fails(mock_tv_data):
    data = copy.deepcopy(mock_tv_data)
    next(m for m in data["Measurements"] if m["Location"] == "TopLeft")["Lv"] = 90.0

    check = checks_by_key(ev.evaluate(data, SPEC))["Brightness_uniformity"]

    assert check["status"] == ev.STATUS_FAIL
    assert check["locations"] == ["TopLeft"]


def test_evaluate_temperature_without_a_valid_value_is_unavailable(mock_tv_data):
    data = copy.deepcopy(mock_tv_data)
    next(m for m in data["Measurements"] if m["Location"] == "Center")["T"] = None

    check = checks_by_key(ev.evaluate(data, SPEC))["Temperature"]

    assert check["status"] == ev.STATUS_UNAVAILABLE
    assert check["value"] is None


def test_evaluate_skips_measurements_with_non_numeric_values(mock_tv_data):
    data = copy.deepcopy(mock_tv_data)
    next(m for m in data["Measurements"] if m["Location"] == "RedColor")["x"] = "0..2760"

    check = checks_by_key(ev.evaluate(data, SPEC))["Red_x"]

    assert check["status"] == ev.STATUS_PENDING


def test_evaluate_warns_below_typ_and_passes_without_remarks(mock_tv_data):
    spec = {"Brightness": {"min": 150, "typ": 190, "max": None}}
    result = ev.evaluate(mock_tv_data, spec)
    assert result["device"] == ev.VERDICT_PASS and result["checks"][0]["status"] == ev.STATUS_PASS

    spec = {"Brightness": {"min": 150, "typ": 210, "max": None}}
    result = ev.evaluate(mock_tv_data, spec)
    assert result["device"] == ev.VERDICT_WARN and result["checks"][0]["status"] == ev.STATUS_WARNING


def test_evaluate_lower_is_better_metric(mock_display_data):
    spec = {"Delta_e": {"min": None, "typ": 0.01, "max": 100}}

    check = checks_by_key(ev.evaluate(mock_display_data, spec))["Delta_e"]

    assert check["status"] == ev.STATUS_WARNING  # above typ, below max


def test_evaluate_matches_the_cell_statuses_of_the_report(mock_tv_data):
    """The statuses of the online evaluation must be the ones the HTML report highlights."""
    spec = {
        **SPEC,
        "Brightness": {"min": 250, "typ": 300, "max": None},
        "Green_y": {"min": 0.6, "typ": 0.62, "max": 0.64},
        "Blue_x": {"min": 0.14, "typ": 0.15, "max": 0.151},
        "Cg_rgb": {"min": 50, "typ": 99, "max": None},
    }
    calc_res = cal.run_calculations(mock_tv_data, True)
    device_report = report.json_report(sn="SN", t="20250101_120000", is_tv=True, device_name="X", **calc_res)

    reports = helpers.process_device_reports([device_report], helpers.UFN_MAPPING, spec)
    cell_status = {}
    for group in reports:
        cell_status.update(group["SN"]["cell_status"])

    checks = ev.evaluate(mock_tv_data, spec)["checks"]
    assert checks
    for check in checks:
        if check["status"] in (ev.STATUS_WARNING, ev.STATUS_FAIL):
            assert cell_status[helpers.UFN_MAPPING[check["key"]]] == check["status"], check["key"]
        else:
            assert helpers.UFN_MAPPING[check["key"]] not in cell_status, check["key"]


# --------------------------------------------------------------------------------
# --evaluate command line mode
# --------------------------------------------------------------------------------

@pytest.fixture
def app_main(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT_DIR))
    import main
    return main


@pytest.fixture
def spec_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / "config" / "device_configs"
    config_dir.mkdir(parents=True)
    (config_dir / "50UQ6031_REV1.yaml").write_text(
        "Brightness:\n  min: 150\n  typ: 250\n  max: None\n"
        "White_x:\n  typ: 0.33\nCoordinates_tolerance: 0.005\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run_evaluate(app_main, monkeypatch, capsys, payload: str, source="-"):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload.encode("utf-8"))))
    code = app_main.run_evaluate(source)
    return code, json.loads(capsys.readouterr().out)


def test_run_evaluate_prints_the_checks_and_writes_nothing(app_main, spec_dir, mock_tv_data, monkeypatch, capsys):
    code, result = run_evaluate(app_main, monkeypatch, capsys, json.dumps(mock_tv_data))

    assert code == app_main.ExitCode.SUCCESS
    checks = checks_by_key(result)
    assert checks["Brightness"]["status"] == ev.STATUS_WARNING
    assert checks["White_x"]["min"] == 0.325 and checks["White_x"]["max"] == 0.335  # tolerance expanded
    assert checks["White_x"]["status"] == ev.STATUS_FAIL
    assert sorted(p.name for p in spec_dir.iterdir()) == ["config"]  # no data/logs/results directories


def test_run_evaluate_accepts_utf8_with_bom_and_a_file_path(app_main, spec_dir, mock_tv_data, monkeypatch, capsys):
    path = spec_dir / "device.json"
    path.write_text(json.dumps(mock_tv_data), encoding="utf-8-sig")

    code = app_main.run_evaluate(str(path))

    assert code == app_main.ExitCode.SUCCESS
    assert json.loads(capsys.readouterr().out)["schema"] == ev.EVALUATE_SCHEMA_VERSION


def test_run_evaluate_reports_a_missing_spec(app_main, spec_dir, mock_tv_data, monkeypatch, capsys):
    mock_tv_data["DeviceConfiguration"] = "Unknown_device"

    code, result = run_evaluate(app_main, monkeypatch, capsys, json.dumps(mock_tv_data))

    assert code == app_main.ExitCode.CONFIG_ERROR
    assert "spec not found" in result["error"]


def test_run_evaluate_reports_invalid_input(app_main, spec_dir, monkeypatch, capsys):
    code, result = run_evaluate(app_main, monkeypatch, capsys, "{not json")

    assert code == app_main.ExitCode.GENERAL_ERROR
    assert result["error"].startswith("invalid input")


def test_evaluate_flag_is_parsed(app_main, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ReportGenerator.exe", "--evaluate", "-"])

    assert app_main.parse_args().evaluate == "-"


def test_verdict_of():
    assert ev.verdict_of([]) == ev.VERDICT_PASS
    assert ev.verdict_of(["warning", "pass"]) == ev.VERDICT_WARN
    assert ev.verdict_of(["warning", "fail"]) == ev.VERDICT_FAIL


def test_report_marks_the_device_verdict(mock_tv_data):
    spec = {"Brightness": {"min": 150, "typ": 250, "max": None}, "Red_x": {"min": 0.62, "typ": 0.65, "max": 0.68}}
    calc_res = cal.run_calculations(mock_tv_data, True)
    device_report = report.json_report(sn="SN", t="20250101_120000", is_tv=True, device_name="X", **calc_res)

    main_data, _, _, coord_data = helpers.process_device_reports([device_report], helpers.UFN_MAPPING, spec)

    assert main_data["SN"]["verdict"] == ev.VERDICT_WARN  # brightness 200 is below typ 250
    assert coord_data["SN"]["verdict"] == ev.VERDICT_WARN  # the verdict is the same in every table


def test_temperature_is_checked_against_min_and_max_only():
    spec = {"Temperature": {"min": 7300, "typ": 9300, "max": 11300}}

    assert ev.get_cell_status("Temperature", 8833, spec) is None  # below typ, inside the window
    assert ev.get_cell_status("Temperature", 7000, spec) == ev.STATUS_FAIL
    assert ev.get_cell_status("Temperature", 11500, spec) == ev.STATUS_FAIL


# --------------------------------------------------------------------------------
# attempts of a point
# --------------------------------------------------------------------------------

def attempt(lv, x=0.339, y=0.348, t=6752):
    return {"x": x, "y": y, "Lv": lv, "T": t}


def test_best_attempt_prefers_the_better_status_over_a_higher_luminance():
    spec = {"Brightness": {"min": 160, "typ": 190, "max": None}}
    attempts = [attempt(150), attempt(180), attempt(195)]  # fail, warning, pass

    assert ev.best_attempt_index("WhiteColor", attempts, spec, True) == 2
    assert ev.best_attempt_index("WhiteColor", [attempt(150), attempt(180)], spec, True) == 1


def test_best_attempt_with_equal_status_takes_the_higher_luminance():
    spec = {"Brightness": {"min": 160, "typ": 190, "max": None}}

    assert ev.best_attempt_index("WhiteColor", [attempt(150), attempt(120), attempt(140)], spec, True) == 0
    assert ev.best_attempt_index("WhiteColor", [attempt(170), attempt(180), attempt(175)], spec, True) == 1


def test_best_attempt_of_a_color_point_is_the_closest_to_typ_coordinates():
    spec = {"Red_x": {"min": 0.62, "typ": 0.65, "max": 0.68}, "Red_y": {"min": 0.30, "typ": 0.33, "max": 0.36}}
    near_but_dark = attempt(10, x=0.651, y=0.331)
    far_but_bright = attempt(90, x=0.629, y=0.309)  # inside min/max, farther from typ

    assert ev.best_attempt_index("RedColor", [far_but_bright, near_but_dark], spec, False) == 1


def test_best_attempt_of_the_black_point_is_the_darkest():
    assert ev.best_attempt_index("BlackColor", [attempt(0.05), attempt(0.02), attempt(0.04)], {}, False) == 1
    assert ev.best_attempt_index("BlackColor", [attempt(0.02), attempt(0.02)], {}, False) == 1  # the later one wins a tie
    assert ev.best_attempt_index("BlackColor", [attempt(0.05), attempt(0.5)], {}, True) == 0


def test_best_attempt_of_the_black_point_ignores_an_attempt_without_luminance():
    assert ev.best_attempt_index("BlackColor", [{"x": 0.3, "y": 0.3}, attempt(0.2)], {}, False) == 1


def test_best_attempt_of_a_single_attempt_or_a_point_without_spec_is_the_highest_luminance():
    assert ev.best_attempt_index("BottomLeft", [attempt(100)], {}, False) == 0
    assert ev.best_attempt_index("BottomLeft", [attempt(100), attempt(120), attempt(110)], {}, False) == 1


def test_best_attempt_does_not_fail_on_an_attempt_without_a_color_temperature_value():
    spec = {"Temperature": {"min": 6000, "typ": None, "max": 7000}}

    assert ev.best_attempt_index("Center", [attempt(100, t=None), attempt(90, t=5000)], spec, False) == 0  # 5000 K fails


def test_evaluate_uses_the_best_attempt_and_reports_the_attempts(mock_tv_data):
    data = copy.deepcopy(mock_tv_data)
    white = next(m for m in data["Measurements"] if m["Location"] == "WhiteColor")
    white["Attempts"] = [attempt(150), attempt(180), attempt(170)]
    spec = {"Brightness": {"min": 160, "typ": 190, "max": None}}

    result = ev.evaluate(data, spec)

    check = checks_by_key(result)["Brightness"]
    assert check["value"] == 180 and check["status"] == ev.STATUS_WARNING
    assert result["attempts"]["WhiteColor"] == {"count": 3, "best": 1, "deviated": True}
    assert result["attempts"]["Center"] == {"count": 1, "best": 0, "deviated": False}


def test_resolve_attempts_gives_the_black_point_its_darkest_attempt_and_the_white_point_its_brightest(mock_tv_data):
    data = copy.deepcopy(mock_tv_data)
    black = next((m for m in data["Measurements"] if m["Location"] == "BlackColor"), None)
    if black is None:
        black = {"Location": "BlackColor", "x": 0.3, "y": 0.3, "Lv": 0.1, "T": 6500}
        data["Measurements"].append(black)
    black["Attempts"] = [attempt(0.05), attempt(0.02), attempt(0.04)]
    white = next(m for m in data["Measurements"] if m["Location"] == "WhiteColor")
    white["Attempts"] = [attempt(150), attempt(180), attempt(170)]

    resolved, summary = ev.resolve_attempts(data, {})

    by_location = {m["Location"]: m for m in resolved["Measurements"]}
    assert (summary["BlackColor"]["best"], by_location["BlackColor"]["Lv"]) == (1, 0.02)
    assert (summary["WhiteColor"]["best"], by_location["WhiteColor"]["Lv"]) == (1, 180)


def test_evaluate_marks_a_point_as_deviated_even_when_the_best_attempt_is_fine(mock_tv_data):
    data = copy.deepcopy(mock_tv_data)
    white = next(m for m in data["Measurements"] if m["Location"] == "WhiteColor")
    white["Attempts"] = [attempt(150), attempt(200)]
    spec = {"Brightness": {"min": 160, "typ": 190, "max": None}}

    result = ev.evaluate(data, spec)

    assert checks_by_key(result)["Brightness"]["status"] == ev.STATUS_PASS
    assert result["attempts"]["WhiteColor"]["deviated"] is True
    assert result["attempts"]["WhiteColor"]["best"] == 1


def test_evaluate_without_attempts_keeps_the_measurement_values(mock_tv_data):
    result = ev.evaluate(mock_tv_data, SPEC)

    assert checks_by_key(result)["Brightness"]["value"] == 200
    assert all(info["count"] == 1 and info["best"] == 0 for info in result["attempts"].values())
