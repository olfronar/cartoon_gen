from __future__ import annotations

from datetime import date

import pytest

from static_shots_maker.pipeline.script_reader import read_scripts
from tests.conftest import write_script_json


class TestScriptReader:
    def test_read_by_date(self, tmp_path):
        write_script_json(tmp_path, "2026-03-15", 1, title="Episode 1")
        write_script_json(tmp_path, "2026-03-15", 2, title="Episode 2")

        results = read_scripts(target_date=date(2026, 3, 15), scripts_dir=tmp_path)
        assert len(results) == 2
        assert results[0][0] == 1
        assert results[1][0] == 2
        assert results[0][1].title == "Episode 1"

    def test_auto_detect_latest(self, tmp_path):
        write_script_json(tmp_path, "2026-03-13", 1)
        write_script_json(tmp_path, "2026-03-15", 1)
        write_script_json(tmp_path, "2026-03-14", 1)

        results = read_scripts(scripts_dir=tmp_path)
        assert results[0][1].date == date(2026, 3, 15)

    def test_missing_directory(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_scripts(scripts_dir=tmp_path / "nonexistent")

    def test_no_scripts(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_scripts(scripts_dir=tmp_path)

    def test_corrupt_json_skipped(self, tmp_path):
        write_script_json(tmp_path, "2026-03-15", 1, title="Good")
        (tmp_path / "2026-03-15_2.json").write_text("{bad json", encoding="utf-8")

        results = read_scripts(target_date=date(2026, 3, 15), scripts_dir=tmp_path)
        assert len(results) == 1
        assert results[0][1].title == "Good"
