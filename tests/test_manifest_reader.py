from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from shared.models import ShotResult, ShotsManifest
from tests.conftest import write_script_json
from video_designer.pipeline.manifest_reader import read_manifests


def _write_manifest(shots_dir: Path, date_str: str, index: int, success: bool = True) -> None:
    """Write a shots manifest with one successful scene + end card."""
    scene_path = shots_dir / f"{date_str}_{index}" / "scene_1.png"
    end_card_path = shots_dir / f"{date_str}_{index}" / "end_card.png"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_bytes(b"fake png")
    end_card_path.write_bytes(b"fake png")

    manifest = ShotsManifest(
        script_title="Test",
        script_index=index,
        date=date.fromisoformat(date_str),
        shots=[
            ShotResult(
                script_index=index,
                scene_number=1,
                success=success,
                output_path=scene_path if success else None,
                error=None if success else "failed",
            ),
            ShotResult(
                script_index=index,
                scene_number=0,
                success=success,
                output_path=end_card_path if success else None,
                error=None if success else "failed",
            ),
        ],
    )
    manifest_path = shots_dir / f"{date_str}_{index}" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")


class TestManifestReader:
    def test_reads_paired_data(self, tmp_path):
        shots_dir = tmp_path / "static_shots"
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        write_script_json(scripts_dir, "2026-03-15", 1, title="Ep 1")
        _write_manifest(shots_dir, "2026-03-15", 1)

        results = read_manifests(
            target_date=date(2026, 3, 15),
            shots_dir=shots_dir,
            scripts_dir=scripts_dir,
        )
        assert len(results) == 1
        assert results[0].index == 1
        assert results[0].script.title == "Ep 1"
        assert len(results[0].manifest.shots) == 2

    def test_auto_detect_latest(self, tmp_path):
        shots_dir = tmp_path / "static_shots"
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        write_script_json(scripts_dir, "2026-03-14", 1)
        _write_manifest(shots_dir, "2026-03-14", 1)
        write_script_json(scripts_dir, "2026-03-15", 1)
        _write_manifest(shots_dir, "2026-03-15", 1)

        results = read_manifests(shots_dir=shots_dir, scripts_dir=scripts_dir)
        assert results[0].script.date == date(2026, 3, 15)

    def test_skips_no_successful_shots(self, tmp_path):
        shots_dir = tmp_path / "static_shots"
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        write_script_json(scripts_dir, "2026-03-15", 1)
        _write_manifest(shots_dir, "2026-03-15", 1, success=False)

        results = read_manifests(
            target_date=date(2026, 3, 15),
            shots_dir=shots_dir,
            scripts_dir=scripts_dir,
        )
        assert len(results) == 0

    def test_missing_shots_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_manifests(
                shots_dir=tmp_path / "nonexistent",
                scripts_dir=tmp_path,
            )
