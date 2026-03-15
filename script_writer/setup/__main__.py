import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import load_settings  # noqa: E402

from .art_materials_builder import create_art_materials  # noqa: E402
from .art_style_builder import create_art_style  # noqa: E402
from .character_builder import create_character, delete_character, list_characters  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Script Writer — Character & Art Style Setup")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["all", "characters", "art-style", "art-materials"],
        help="What to set up (default: all)",
    )
    args = parser.parse_args()

    settings = load_settings()

    if args.mode == "art-materials":
        if not settings.google_api_key:
            print("Error: GOOGLE_API_KEY required for art materials generation.")
            sys.exit(1)
        create_art_materials(
            google_api_key=settings.google_api_key,
            characters_dir=settings.characters_dir,
            art_style_path=settings.art_style_path,
            art_materials_dir=settings.art_materials_dir,
            model=settings.shots_model,
        )
        return

    if not settings.anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY required for setup interviews.")
        sys.exit(1)

    if args.mode in ("all", "characters"):
        _characters_menu(settings)

    if args.mode in ("all", "art-style"):
        create_art_style(
            api_key=settings.anthropic_api_key,
            art_style_path=settings.art_style_path,
            model=settings.script_writer_model,
        )


def _characters_menu(settings) -> None:
    """Interactive menu for character management."""
    existing = list_characters(settings.characters_dir)

    if existing:
        print(f"\nExisting characters: {', '.join(existing)}")
        print("\nOptions:")
        print("  1. Add new character")
        print("  2. Delete a character")
        print("  3. Skip")
        choice = input("\nChoice (1/2/3): ").strip()

        if choice == "1":
            create_character(
                api_key=settings.anthropic_api_key,
                characters_dir=settings.characters_dir,
                model=settings.script_writer_model,
            )
        elif choice == "2":
            delete_character(settings.characters_dir)
        else:
            print("Skipping characters.")
    else:
        print("\nNo characters defined yet. Let's create one!")
        create_character(
            api_key=settings.anthropic_api_key,
            characters_dir=settings.characters_dir,
            model=settings.script_writer_model,
        )

    # Offer to add more
    while True:
        more = input("\nAdd another character? (y/n): ").strip().lower()
        if more != "y":
            break
        create_character(
            api_key=settings.anthropic_api_key,
            characters_dir=settings.characters_dir,
            model=settings.script_writer_model,
        )


if __name__ == "__main__":
    main()
