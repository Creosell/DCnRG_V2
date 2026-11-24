import sys
from pathlib import Path

from src import paths


def test_sct_root_has_the_highest_priority(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert paths.resolve_root() == tmp_path


def test_frozen_build_uses_the_executable_folder(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.ROOT_ENV_VAR, raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ReportGenerator.exe"))

    assert paths.resolve_root() == tmp_path


def test_script_run_uses_the_current_directory(monkeypatch):
    monkeypatch.delenv(paths.ROOT_ENV_VAR, raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert paths.resolve_root() == Path(".")


def test_empty_sct_root_is_ignored(monkeypatch):
    monkeypatch.setenv(paths.ROOT_ENV_VAR, "")
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert paths.resolve_root() == Path(".")
