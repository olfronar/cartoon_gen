from __future__ import annotations

from datetime import date

import pytest

from shared.utils import find_script_videos


class TestFindScriptVideos:
    def test_finds_videos_for_date(self, tmp_path):
        for idx in (1, 2, 3):
            d = tmp_path / f"2026-03-21_{idx}"
            d.mkdir()
            (d / "script_video.mp4").write_bytes(b"fake")

        result = find_script_videos(date(2026, 3, 21), tmp_path)
        assert len(result) == 3
        assert [idx for idx, _ in result] == [1, 2, 3]
        assert all(p.name == "script_video.mp4" for _, p in result)

    def test_auto_detects_latest_date(self, tmp_path):
        for dt in ("2026-03-20", "2026-03-21"):
            d = tmp_path / f"{dt}_1"
            d.mkdir()
            (d / "script_video.mp4").write_bytes(b"fake")

        result = find_script_videos(None, tmp_path)
        assert len(result) == 1
        assert "2026-03-21" in str(result[0][1])

    def test_raises_on_no_videos(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_script_videos(date(2026, 3, 21), tmp_path)
