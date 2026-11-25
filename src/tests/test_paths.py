from pathlib import Path

from src import paths


def test_sct_root_has_the_highest_priority(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.ROOT_ENV_VAR, str(tmp_path))

    assert paths.resolve_root() == tmp_path


def test_without_sct_root_the_current_directory_is_used(monkeypatch):
    monkeypatch.delenv(paths.ROOT_ENV_VAR, raising=False)

    assert paths.resolve_root() == Path(".")


def test_empty_sct_root_is_ignored(monkeypatch):
    monkeypatch.setenv(paths.ROOT_ENV_VAR, "")

    assert paths.resolve_root() == Path(".")
