from __future__ import annotations

from unittest.mock import MagicMock, patch

from script_writer.setup.art_materials_builder import create_art_materials


class TestCreateArtMaterials:
    @patch("script_writer.setup.art_materials_builder.generate_image")
    @patch("script_writer.setup.art_materials_builder.genai")
    def test_generates_character_sheet(self, mock_genai, mock_gen_img, tmp_path):
        """Generates canonical_characters.png."""
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        (chars_dir / "bot.md").write_text("# Bot\nA robot", encoding="utf-8")

        art_style_path = tmp_path / "art_style.md"
        art_style_path.write_text("# Cartoon Style\nBright colors", encoding="utf-8")

        art_materials_dir = tmp_path / "art_materials"
        mock_genai.Client.return_value = MagicMock()

        def fake_generate_image(prompt, output_path, client, model):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake png")
            return output_path

        mock_gen_img.side_effect = fake_generate_image

        result = create_art_materials(
            google_api_key="test-key",
            characters_dir=chars_dir,
            art_style_path=art_style_path,
            art_materials_dir=art_materials_dir,
        )

        assert len(result) == 1
        assert (art_materials_dir / "canonical_characters.png").exists()
        assert mock_gen_img.call_count == 1

    def test_no_characters_returns_empty(self, tmp_path):
        """Returns empty list when no character profiles exist."""
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        art_style_path = tmp_path / "art_style.md"
        art_style_path.write_text("# Style", encoding="utf-8")

        result = create_art_materials(
            google_api_key="test-key",
            characters_dir=chars_dir,
            art_style_path=art_style_path,
            art_materials_dir=tmp_path / "art_materials",
        )
        assert result == []

    def test_no_art_style_returns_empty(self, tmp_path):
        """Returns empty list when art style doesn't exist."""
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        (chars_dir / "bot.md").write_text("# Bot", encoding="utf-8")

        result = create_art_materials(
            google_api_key="test-key",
            characters_dir=chars_dir,
            art_style_path=tmp_path / "missing.md",
            art_materials_dir=tmp_path / "art_materials",
        )
        assert result == []
