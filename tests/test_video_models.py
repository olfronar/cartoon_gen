from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from shared.models import ClipResult, VideoManifest


class TestClipResult:
    def test_creation(self):
        clip = ClipResult(
            script_index=1,
            scene_number=1,
            success=True,
            output_path=Path("output/videos/2026-03-15_1/scene_1.mp4"),
            duration_seconds=15.0,
            error=None,
        )
        assert clip.success is True
        assert clip.duration_seconds == 15.0

    def test_failed_clip(self):
        clip = ClipResult(
            script_index=1,
            scene_number=2,
            success=False,
            output_path=None,
            duration_seconds=None,
            error="xAI timeout",
        )
        assert clip.success is False
        assert clip.error == "xAI timeout"


class TestVideoManifest:
    def test_to_dict(self):
        manifest = VideoManifest(
            script_title="Test Episode",
            script_index=1,
            date=date(2026, 3, 15),
            clips=[
                ClipResult(
                    script_index=1,
                    scene_number=1,
                    success=True,
                    output_path=Path("scene_1.mp4"),
                    duration_seconds=15.0,
                    error=None,
                ),
            ],
            script_video_path=Path("script_video.mp4"),
        )
        data = manifest.to_dict()
        assert data["date"] == "2026-03-15"
        assert data["clips"][0]["output_path"] == "scene_1.mp4"
        assert data["script_video_path"] == "script_video.mp4"

    def test_to_dict_json_serializable(self):
        manifest = VideoManifest(
            script_title="Test",
            script_index=1,
            date=date(2026, 3, 15),
            clips=[],
            script_video_path=None,
        )
        json_str = json.dumps(manifest.to_dict())
        assert isinstance(json_str, str)

    def test_to_dict_none_paths(self):
        manifest = VideoManifest(
            script_title="Test",
            script_index=1,
            date=date(2026, 3, 15),
            clips=[
                ClipResult(
                    script_index=1,
                    scene_number=1,
                    success=False,
                    output_path=None,
                    duration_seconds=None,
                    error="failed",
                ),
            ],
            script_video_path=None,
        )
        data = manifest.to_dict()
        assert data["clips"][0]["output_path"] is None
        assert data["script_video_path"] is None
