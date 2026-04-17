from __future__ import annotations

import logging
from pathlib import Path

from script_writer.prompts import CHARACTER_INTERVIEW_SYSTEM, CHARACTER_PROFILE_TEMPLATE

from .interviewer import run_interview

logger = logging.getLogger(__name__)


def list_characters(characters_dir: Path) -> list[str]:
    """List existing character names."""
    if not characters_dir.exists():
        return []
    return sorted(p.stem for p in characters_dir.glob("*.md"))


def create_character(api_key: str, characters_dir: Path, model: str = "claude-opus-4-7") -> Path:
    """Run character interview and write the profile file."""
    existing = list_characters(characters_dir)

    context = ""
    if existing:
        context = "Existing characters: " + ", ".join(existing)
        for name in existing:
            path = characters_dir / f"{name}.md"
            context += f"\n\n--- {name} ---\n{path.read_text(encoding='utf-8')}"

    profile = run_interview(
        api_key=api_key,
        system_prompt=CHARACTER_INTERVIEW_SYSTEM,
        model=model,
        initial_context=context,
    )

    return _write_character_profile(profile, characters_dir)


def _write_character_profile(profile: dict, characters_dir: Path) -> Path:
    """Render and write a character profile to disk."""
    characters_dir.mkdir(parents=True, exist_ok=True)

    name = profile["name"]

    traits_formatted = "\n".join(f"- {t}" for t in profile.get("personality_traits", []))
    quirks_formatted = "\n".join(f"- {q}" for q in profile.get("quirks", []))

    relationships = profile.get("relationships", {})
    if isinstance(relationships, dict):
        relationships_formatted = "\n".join(f"- **{k}**: {v}" for k, v in relationships.items())
    else:
        relationships_formatted = str(relationships)

    content = CHARACTER_PROFILE_TEMPLATE.format(
        name=name,
        role=profile.get("role", ""),
        comedic_function=profile.get("comedic_function", ""),
        traits_formatted=traits_formatted,
        quirks_formatted=quirks_formatted,
        tech_relationship=profile.get("tech_relationship", ""),
        relationships_formatted=relationships_formatted or "None yet",
        appearance=profile.get("appearance", ""),
        visual_description=profile.get("visual_description", ""),
        absurd_reaction=profile.get("absurd_reaction", ""),
    )

    # Sanitize filename
    safe_name = name.lower().replace(" ", "_")
    path = characters_dir / f"{safe_name}.md"
    path.write_text(content, encoding="utf-8")

    print(f"\nCharacter profile written to {path}")
    logger.info("Character profile written: %s", path)
    return path


def delete_character(characters_dir: Path) -> None:
    """Interactive character deletion."""
    existing = list_characters(characters_dir)
    if not existing:
        print("No characters to delete.")
        return

    print("\nExisting characters:")
    for i, name in enumerate(existing, 1):
        print(f"  {i}. {name}")

    choice = input("\nDelete which character? (number or name, or 'cancel'): ").strip()
    if choice.lower() == "cancel":
        return

    try:
        idx = int(choice) - 1
        name = existing[idx]
    except (ValueError, IndexError):
        name = choice

    path = characters_dir / f"{name}.md"
    if path.exists():
        path.unlink()
        print(f"Deleted {path}")
    else:
        print(f"Character file not found: {path}")
