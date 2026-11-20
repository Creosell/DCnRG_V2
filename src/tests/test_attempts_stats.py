"""Tests of the "Repeated measurements" section: the statistics of the attempts and their place in the HTML report."""
import json
from pathlib import Path

import pytest

import src.attempts_stats as stats
import src.helpers as helpers

SPEC = {
    "Brightness": {"min": 400, "typ": 450, "max": None},
    "Red_x": {"min": 0.655, "typ": 0.670, "max": 0.685},
    "Red_y": {"min": 0.295, "typ": 0.310, "max": 0.325},
}


def attempt(lv, x=0.28, y=0.29, t=9000):
    return {"x": x, "y": y, "Lv": lv, "T": t}


def device(serial, **points):
    """A TV measurement file; every keyword is a location with its attempts."""
    return serial, {"IsTV": True, "Measurements": [{"Location": loc, **attempts[0], "Attempts": attempts} for loc, attempts in points.items()]}


def build(*devices, total=10):
    return stats.build_attempts_stats(list(devices), SPEC, total)


def point(result, serial, location):
    card = next(c for c in result["cards"] if c["serial"] == serial)
    return next(p for p in card["points"] if p["location"] == location)


def test_no_repeated_point_means_no_section():
    assert build(device("SN1", WhiteColor=[attempt(470)])) is None
    assert stats.build_attempts_stats([], SPEC, 5) is None


def test_a_file_without_attempts_is_ignored():
    assert stats.build_attempts_stats([("SN1", {"IsTV": True, "Measurements": [{"Location": "WhiteColor", "x": 0.28, "y": 0.29, "Lv": 470, "T": 9000}]})], SPEC, 5) is None


@pytest.mark.parametrize("attempts, outcome, best", [
    ([attempt(392), attempt(456)], "rescued", 2),            # outside the spec, then within
    ([attempt(378), attempt(385), attempt(392)], "improved", 3),  # better each time, still outside the spec
    ([attempt(388), attempt(387), attempt(389)], "improved", 3),  # barely better
    ([attempt(472), attempt(468), attempt(475)], "improved", 3),  # the first was already good, a brighter one still counts
    ([attempt(458), attempt(441), attempt(449)], "same", 1),      # the first is the best
    ([attempt(398), attempt(462), attempt(441)], "rescued", 2),   # the best is the second of three
])
def test_the_outcome_and_the_best_attempt_of_the_white_point(attempts, outcome, best):
    result = build(device("SN1", WhiteColor=attempts))

    p = point(result, "SN1", "WhiteColor")
    assert (p["outcome"], p["best"], p["attempts"]) == (outcome, best, len(attempts))


def test_the_darker_black_is_the_best_and_a_dark_point_has_no_spec_to_judge_by():
    result = build(device("SN1", BlackColor=[attempt(0.094), attempt(0.058), attempt(0.061)]))

    p = point(result, "SN1", "BlackColor")
    assert (p["best"], p["first"], p["best_value"], p["outcome"]) == (2, "0.094", "0.058", "improved")


def test_color_point_is_plotted_by_the_distance_from_typ_and_judged_by_the_window():
    result = build(device("SN1", RedColor=[attempt(120, 0.690, 0.318), attempt(120, 0.672, 0.311)]))

    p = point(result, "SN1", "RedColor")
    assert p["scale"] == "Δxy"
    assert (p["outcome"], p["best"]) == ("rescued", 2)  # x 0.690 is outside 0.655..0.685, 0.672 inside
    assert p["first"] == "0.022" and p["best_value"] == "0.002"


def test_attempts_without_a_valid_number_skip_the_point():
    broken = [attempt(400), {"x": 0.28, "y": 0.29, "Lv": None, "T": 9000}]

    assert build(device("SN1", WhiteColor=broken)) is None


def test_the_numbers_of_the_section():
    result = build(
        device("SN1", WhiteColor=[attempt(392), attempt(456)]),
        device("SN2", WhiteColor=[attempt(472), attempt(468)], BlackColor=[attempt(0.06), attempt(0.05)]),
        total=10,
    )

    kpis = result["kpis"]
    assert (kpis["devices"], kpis["total_devices"], kpis["devices_percent"]) == (2, 10, 20)
    assert (kpis["points"], kpis["rescued"]) == (3, 1)
    assert kpis["attempts_average"] == 2.0
    assert kpis["gain_average"] == round((64 + 0) / 2)  # white points only, first -> best: 392 -> 456 and 472 -> 472 (the best of two good ones is the brighter)


def test_the_card_summary_counts_the_outcomes_of_its_points():
    result = build(
        device("A", WhiteColor=[attempt(392), attempt(456)]),
        device("B", WhiteColor=[attempt(392), attempt(456)], BlackColor=[attempt(0.06), attempt(0.061)]),
        device("C", WhiteColor=[attempt(472), attempt(470)]),
    )

    summaries = {c["serial"]: c["summary"] for c in result["cards"]}
    assert summaries == {"A": "1 fixed", "B": "1 fixed", "C": "No effect"}  # B: the black did not get darker


def test_the_strip_draws_every_attempt_and_rings_the_best_one():
    result = build(device("SN1", WhiteColor=[attempt(398), attempt(462), attempt(441)]))

    svg = point(result, "SN1", "WhiteColor")["svg"]
    assert svg.count("<circle") == 3
    assert svg.count('stroke="#111"') == 1  # only the best is ringed
    assert svg.startswith("<svg") and svg.endswith("</svg>")


@pytest.mark.parametrize("lvs, words, tone", [
    ([392, 456], "Fixed", "ok"),                              # fail -> ok
    ([431, 462], "Fixed", "ok"),                              # warn -> ok
    ([378, 436], "Improved, now warn", "warning"),            # fail -> warn
    ([378, 392], "Improved, still fail", "fail"),             # fail -> fail, better
    ([430, 441], "Improved, still warn", "warning"),          # warn -> warn, better
    ([455, 470], "Improved", "ok"),                           # ok -> ok, better
    ([395, 380, 372], "No effect, still fail", "fail"),       # the first is the best, fail
    ([441, 430, 436], "No effect, still warn", "warning"),    # the first is the best, warn
    ([470, 458, 462], "No effect", "none"),                   # the first is the best, ok: nothing to fix
])
def test_the_words_and_the_tone_of_every_transition_of_the_white_point(lvs, words, tone):
    p = point(build(device("SN1", WhiteColor=[attempt(v) for v in lvs])), "SN1", "WhiteColor")

    assert (p["outcome_text"], p["tone"]) == (words, tone)


def test_a_point_without_a_spec_is_neutral():
    result = build(device("SN1", BlackColor=[attempt(0.094), attempt(0.058)]))

    assert point(result, "SN1", "BlackColor")["tone"] == "none"


def test_the_serial_number_of_a_card_takes_the_verdict_of_the_device():
    result = stats.build_attempts_stats([device("SN1", WhiteColor=[attempt(392), attempt(456)]), device("SN2", WhiteColor=[attempt(430), attempt(441)])], SPEC, 5, {"SN1": "FAIL", "SN2": "PASS"})

    assert {c["serial"]: c["verdict"] for c in result["cards"]} == {"SN1": "FAIL", "SN2": "PASS"}
    html = render_section(result)
    assert 'verdict-fail" title="Device verdict: FAIL">SN1' in html and 'verdict-pass" title="Device verdict: PASS">SN2' in html


def test_attempts_with_equal_values_sit_in_rows_of_their_own():
    result = build(device("SN1", WhiteColor=[attempt(388), attempt(388), attempt(389)]))

    svg = point(result, "SN1", "WhiteColor")["svg"]
    ys = [float(s.split('cy="')[1].split('"')[0]) for s in svg.split("<circle")[1:]]
    assert len(set(ys)) == 3  # one row per attempt: the dots never overlap
    assert svg.count(">388<") == 2 and svg.count(">389<") == 1  # every dot carries its value


def test_the_strips_of_one_point_share_a_scale():
    result = build(
        device("SN1", WhiteColor=[attempt(398), attempt(462)]),
        device("SN2", WhiteColor=[attempt(430), attempt(440)]),
    )

    x = lambda svg: float(svg.split("<circle cx=\"")[1].split("\"")[0])
    first_of_sn1 = x(point(result, "SN1", "WhiteColor")["svg"])
    first_of_sn2 = x(point(result, "SN2", "WhiteColor")["svg"])
    assert first_of_sn1 < first_of_sn2  # 398 is left of 430 on the same scale


# --- the section in the HTML report -------------------------------------------------------------------------------------------

TEMPLATE_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "report_template.html"


def render_section(attempts_stats):
    """Renders the real markup of the section (the block of the template guarded by attempts_stats) on its own."""
    from jinja2 import Environment, select_autoescape

    text = TEMPLATE_FILE.read_text(encoding="utf-8")
    start = text.index("{% if attempts_stats %}")
    block = text[start:text.index("    <div class=\"report-footer\">")]
    return Environment(autoescape=select_autoescape(["html"])).from_string(block).render(attempts_stats=attempts_stats)


def test_the_section_is_drawn_for_a_point_measured_again():
    html = render_section(build(device("SN1", WhiteColor=[attempt(392), attempt(456)])))

    assert "Repeated measurements" in html and "attempt-card" in html and "SN1" in html
    assert 'class="attempt-badge">1 fixed' in html
    assert "best 2 of 2" not in html and "cd/m²" in html and "<svg" in html  # the ringed dot says which attempt is the best


def test_the_section_is_not_drawn_without_repeated_measurements():
    assert render_section(None).strip() == ""


def test_create_html_report_hands_the_statistics_to_the_template(mocker, tmp_path):
    template = mocker.MagicMock()
    template.render.return_value = "<html></html>"
    environment = mocker.MagicMock()
    environment.get_template.return_value = template
    mocker.patch("src.helpers.Environment", return_value=environment)
    input_file = tmp_path / "final.json"
    input_file.write_text(json.dumps({"Results": {"Brightness": {"avg": 460}}}), encoding="utf-8")
    expected = tmp_path / "expected.yaml"
    expected.write_text("Brightness:\n  min: 400\n  typ: 450\n  max: None\n", encoding="utf-8")
    svg = tmp_path / "bg.svg"
    svg.write_text("<svg></svg>", encoding="utf-8")

    def create(attempts_devices):
        helpers.create_html_report(
            input_file=input_file, output_file=tmp_path / "out.html", cie_background_svg=svg,
            device_reports=[{"SerialNumber": "SN1", "Results": {"Brightness": 460}, "MeasurementDateTime": "20250101_120000"}],
            current_device_name="Demo", app_version="1.0.0", expected_yaml=expected, attempts_devices=attempts_devices)
        return template.render.call_args.args[0]["attempts_stats"]

    assert create([device("SN1", WhiteColor=[attempt(392), attempt(456)])])["kpis"]["devices"] == 1
    assert create([device("SN1", WhiteColor=[attempt(470)])]) is None
    assert create(None) is None
