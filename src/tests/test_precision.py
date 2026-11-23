"""The precision a verdict is made at: every metric of a specification has its own, written in one table."""
from pathlib import Path

import yaml

from src import report

ROOT = Path(__file__).resolve().parents[2]


def test_every_metric_of_the_example_specification_has_an_explicit_precision():
    spec = yaml.safe_load((ROOT / "config" / "configuration_example.yaml").read_text(encoding="utf-8"))
    metrics = [key for key in spec if key != "Coordinates_tolerance"]

    assert [key for key in metrics if key not in report.REPORT_PRECISION] == []  # a missing key would silently get the default of two decimals


def test_a_value_is_judged_as_it_is_shown():
    from src import evaluate

    spec = {"Brightness": {"min": 320, "typ": 350, "max": None}, "Brightness_uniformity": {"min": 65, "typ": 70, "max": None}}

    assert evaluate.get_cell_status("Brightness", 319.6, spec) == evaluate.STATUS_WARNING  # shown as 320: not below the minimum
    assert evaluate.get_cell_status("Brightness", 319.4, spec) == evaluate.STATUS_FAIL  # shown as 319
    assert evaluate.get_cell_status("Brightness_uniformity", 64.96, spec) == evaluate.STATUS_WARNING  # shown as 65.0
    assert evaluate.get_cell_status("Brightness_uniformity", 64.94, spec) == evaluate.STATUS_FAIL  # shown as 64.9
