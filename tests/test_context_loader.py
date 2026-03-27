from __future__ import annotations

from shared.context_loader import (
    apply_style_enforcement,
    build_context_block,
    build_reference_image_list,
    build_style_directive,
    load_art_materials,
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


class TestLoadArtMaterials:
    def test_loads_existing_pngs(self, tmp_path):
        (tmp_path / "canonical_characters.png").write_bytes(b"fake")

        materials = load_art_materials(tmp_path)
        assert len(materials) == 1
        assert "canonical_characters" in materials

    def test_missing_directory(self, tmp_path):
        materials = load_art_materials(tmp_path / "nonexistent")
        assert materials == {}


class TestBuildReferenceImageList:
    def test_ordered_list(self, tmp_path):
        chars_path = tmp_path / "canonical_characters.png"
        chars_path.write_bytes(b"fake")

        materials = {"canonical_characters": chars_path}
        result = build_reference_image_list(materials)
        assert result == [chars_path]

    def test_empty_materials(self):
        result = build_reference_image_list({})
        assert result == []


class TestBuildStyleDirective:
    def test_empty_input(self):
        assert build_style_directive("") == ""

    def test_short_input_returns_all(self):
        style = "# Title\n\n## Section A\nContent A\n\n## Section B\nContent B"
        result = build_style_directive(style, max_chars=5000)
        assert "Section A" in result
        assert "Section B" in result

    def test_truncates_at_section_boundary(self):
        style = "# Title\n\n## A\n" + "x" * 100 + "\n\n## B\n" + "y" * 100
        result = build_style_directive(style, max_chars=130)
        assert "## A" in result
        assert "## B" not in result

    def test_first_section_exceeds_budget(self):
        style = "x" * 5000
        result = build_style_directive(style, max_chars=100)
        assert result == "x" * 5000

    def test_no_headers(self):
        style = "Just plain text without headers"
        result = build_style_directive(style, max_chars=5000)
        assert result == style


class TestApplyStyleEnforcement:
    def test_with_art_style(self):
        result = apply_style_enforcement("scene prompt", "2D cartoon")
        assert result.startswith("2D cartoon")
        assert result.endswith("scene prompt")
        assert "Match the art style" in result

    def test_empty_art_style(self):
        result = apply_style_enforcement("scene prompt", "")
        assert result == "scene prompt"
