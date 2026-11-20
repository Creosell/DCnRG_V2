"""The name of a device configuration: found by the bare name in any subfolder, shown without the subfolder, used in the page title."""
import pytest

import main
import src.helpers as helpers

TEMPLATE = main.CONFIG_DIR / "report_template.html"


@pytest.fixture
def configs(tmp_path, monkeypatch):
    folder = tmp_path / "device_configs" / "CH32"
    folder.mkdir(parents=True)
    (folder / "TV-50_CH32.yaml").write_text("Brightness: {min: 1}", encoding="utf-8")
    (tmp_path / "device_configs" / "Flat.yaml").write_text("Brightness: {min: 1}", encoding="utf-8")
    monkeypatch.setattr(main, "CONFIG_DIR", tmp_path)
    return tmp_path / "device_configs"


def test_a_bare_name_is_found_in_a_subfolder(configs):
    assert main.resolve_expected_yaml("TV-50_CH32") == configs / "CH32" / "TV-50_CH32.yaml"
    assert main.resolve_expected_yaml("Flat") == configs / "Flat.yaml"


def test_a_name_with_its_subfolder_still_works(configs):
    assert main.resolve_expected_yaml("CH32\\TV-50_CH32") == configs / "CH32" / "TV-50_CH32.yaml"
    assert main.resolve_expected_yaml("CH32/TV-50_CH32") == configs / "CH32" / "TV-50_CH32.yaml"


def test_an_unknown_name_or_a_traversal_finds_nothing(configs):
    assert main.resolve_expected_yaml("Unknown") is None
    assert main.resolve_expected_yaml("..\\..\\Flat") == configs / "Flat.yaml"  # ".." segments are dropped, the name is searched inside device_configs only
    assert main.resolve_expected_yaml("") is None


@pytest.mark.parametrize("name, shown", [("CH32\\TV-50_CH32", "TV-50_CH32"), ("CH32/TV-50_CH32", "TV-50_CH32"), ("TV-50_CH32", "TV-50_CH32")])
def test_the_report_shows_the_configuration_without_its_subfolder(name, shown):
    assert helpers.config_display_name(name) == shown


def test_the_page_title_is_made_of_the_configuration():
    assert "<title>{{ report_title }}</title>" in TEMPLATE.read_text(encoding="utf-8")
