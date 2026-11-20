"""The device configuration: taken from the folder it names, shown without the folder, used in the page title."""
import pytest

import main
import src.helpers as helpers

TEMPLATE = main.CONFIG_DIR / "report_template.html"


@pytest.fixture
def configs(tmp_path, monkeypatch):
    folder = tmp_path / "device_configs" / "CH32"
    other = tmp_path / "device_configs" / "CH33"
    folder.mkdir(parents=True)
    other.mkdir(parents=True)
    (folder / "TV-50_CH32.yaml").write_text("Brightness: {min: 1}", encoding="utf-8")
    (folder / "Same.yaml").write_text("Brightness: {min: 1}", encoding="utf-8")
    (other / "Same.yaml").write_text("Brightness: {min: 2}", encoding="utf-8")
    (tmp_path / "device_configs" / "Flat.yaml").write_text("Brightness: {min: 1}", encoding="utf-8")
    monkeypatch.setattr(main, "CONFIG_DIR", tmp_path)
    return tmp_path / "device_configs"


def test_a_bare_name_is_a_file_of_the_root_only(configs):
    assert main.resolve_expected_yaml("Flat") == configs / "Flat.yaml"
    assert main.resolve_expected_yaml("TV-50_CH32") is None  # lies in CH32: never guessed from the subfolders


def test_the_same_name_in_two_folders_is_two_configurations(configs):
    assert main.resolve_expected_yaml("CH32\\Same") == configs / "CH32" / "Same.yaml"
    assert main.resolve_expected_yaml("CH33/Same") == configs / "CH33" / "Same.yaml"
    assert main.resolve_expected_yaml("Same") is None


def test_a_name_with_its_subfolder_is_taken_from_that_folder(configs):
    assert main.resolve_expected_yaml("CH32\\TV-50_CH32") == configs / "CH32" / "TV-50_CH32.yaml"
    assert main.resolve_expected_yaml("CH32/TV-50_CH32") == configs / "CH32" / "TV-50_CH32.yaml"


def test_an_unknown_name_or_a_traversal_finds_nothing(configs):
    assert main.resolve_expected_yaml("Unknown") is None
    assert main.resolve_expected_yaml("..\\..\\Flat") == configs / "Flat.yaml"  # ".." segments are dropped: nothing outside device_configs is reachable
    assert main.resolve_expected_yaml("") is None


@pytest.mark.parametrize("name, shown", [("CH32\\TV-50_CH32", "TV-50_CH32"), ("CH32/TV-50_CH32", "TV-50_CH32"), ("TV-50_CH32", "TV-50_CH32")])
def test_the_report_shows_the_configuration_without_its_subfolder(name, shown):
    assert helpers.config_display_name(name) == shown


def test_the_page_title_is_made_of_the_configuration():
    assert "<title>{{ report_title }}</title>" in TEMPLATE.read_text(encoding="utf-8")
