from __future__ import annotations

import json
from datetime import date

import pytest

from script_writer.pipeline.brief_reader import read_brief
from tests.conftest import make_brief, make_scored_item


class TestBriefReader:
    def test_read_brief_by_date(self, tmp_path):
        """Read a brief JSON sidecar by explicit date."""
        brief = make_brief(items=[make_scored_item()])
        json_path = tmp_path / "2026-03-14.json"
        json_path.write_text(json.dumps(brief.to_dict()), encoding="utf-8")

        result = read_brief(brief_date=date(2026, 3, 14), briefs_dir=tmp_path)
        assert result.date == date(2026, 3, 14)
        assert len(result.items) == 1

    def test_read_brief_latest(self, tmp_path):
        """Auto-detect latest brief when no date given."""
        for d in ["2026-03-12", "2026-03-14", "2026-03-13"]:
            brief = make_brief()
            brief_data = brief.to_dict()
            brief_data["date"] = d
            (tmp_path / f"{d}.json").write_text(json.dumps(brief_data), encoding="utf-8")

        result = read_brief(briefs_dir=tmp_path)
        assert result.date == date(2026, 3, 14)

    def test_read_brief_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing brief."""
        with pytest.raises(FileNotFoundError):
            read_brief(brief_date=date(2026, 1, 1), briefs_dir=tmp_path)

    def test_read_brief_no_json_files(self, tmp_path):
        """Raise FileNotFoundError when no JSON files exist."""
        with pytest.raises(FileNotFoundError):
            read_brief(briefs_dir=tmp_path)

    def test_read_brief_no_directory(self, tmp_path):
        """Raise FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError):
            read_brief(briefs_dir=tmp_path / "nonexistent")
