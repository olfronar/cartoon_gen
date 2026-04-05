from __future__ import annotations

from datetime import date

import pytest

from tiktok_publisher.pipeline.video_finder import find_publishable_videos


class TestFindPublishableVideos:
    def test_prefers_captioned(self, tmp_path):
        d = tmp_path / "2026-04-01_1"
        d.mkdir()
        (d / "script_video.mp4").write_bytes(b"raw")
        (d / "script_video_captioned.mp4").write_bytes(b"captioned")

        results = find_publishable_videos(date(2026, 4, 1), tmp_path)
        assert len(results) == 1
        assert results[0][1].name == "script_video_captioned.mp4"

    def test_falls_back_to_raw(self, tmp_path):
        d = tmp_path / "2026-04-01_1"
        d.mkdir()
        (d / "script_video.mp4").write_bytes(b"raw")

        results = find_publishable_videos(date(2026, 4, 1), tmp_path)
        assert len(results) == 1
        assert results[0][1].name == "script_video.mp4"

    def test_skips_empty_dirs(self, tmp_path):
        d = tmp_path / "2026-04-01_1"
        d.mkdir()
        # No video files

        with pytest.raises(FileNotFoundError, match="No publishable videos"):
            find_publishable_videos(date(2026, 4, 1), tmp_path)

    def test_multiple_scripts_sorted(self, tmp_path):
        for i in (3, 1, 2):
            d = tmp_path / f"2026-04-01_{i}"
            d.mkdir()
            (d / "script_video.mp4").write_bytes(b"v")

        results = find_publishable_videos(date(2026, 4, 1), tmp_path)
        assert [idx for idx, _ in results] == [1, 2, 3]

    def test_auto_detects_latest_date(self, tmp_path):
        for date_str in ("2026-04-01", "2026-04-03"):
            d = tmp_path / f"{date_str}_1"
            d.mkdir()
            (d / "script_video.mp4").write_bytes(b"v")

        results = find_publishable_videos(None, tmp_path)
        assert "2026-04-03" in str(results[0][1])

    def test_raises_no_dirs(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No video directories"):
            find_publishable_videos(None, tmp_path)
