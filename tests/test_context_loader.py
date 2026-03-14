from __future__ import annotations

from script_writer.pipeline.context_loader import (
    build_context_block,
    load_art_style,
    load_characters,
)


class TestLoadCharacters:
    def test_loads_md_files(self, tmp_path):
        (tmp_path / "alice.md").write_text("# Alice\nShe's great", encoding="utf-8")
        (tmp_path / "bob.md").write_text("# Bob\nHe's fine", encoding="utf-8")

        chars = load_characters(tmp_path)
        assert len(chars) == 2
        assert "alice" in chars
        assert "bob" in chars
        assert "She's great" in chars["alice"]

    def test_empty_directory(self, tmp_path):
        chars = load_characters(tmp_path)
        assert chars == {}

    def test_missing_directory(self, tmp_path):
        chars = load_characters(tmp_path / "nonexistent")
        assert chars == {}


class TestLoadArtStyle:
    def test_loads_file(self, tmp_path):
        path = tmp_path / "art_style.md"
        path.write_text("# Style\nCartoon", encoding="utf-8")

        style = load_art_style(path)
        assert "Cartoon" in style

    def test_missing_file(self, tmp_path):
        style = load_art_style(tmp_path / "missing.md")
        assert style == ""


class TestBuildContextBlock:
    def test_with_both(self):
        block = build_context_block(
            characters={"alice": "# Alice\nDesigner"},
            art_style="Bright colors",
        )
        assert "Art Style" in block
        assert "alice" in block
        assert "Bright colors" in block

    def test_empty(self):
        block = build_context_block({}, "")
        assert block == ""
