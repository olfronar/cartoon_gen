from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(slots=True)
class RawItem:
    title: str
    url: str
    sources: list[str]
    tier: str  # "discovery" | "validation" | "context"
    score: int  # upvotes / points / 0 for RSS
    timestamp: datetime  # UTC
    snippet: str
    comment_count: int = 0


@dataclass(slots=True)
class ScoredItem:
    item: RawItem
    comedy_potential: float  # 0-10
    cultural_resonance: float  # 0-10
    freshness: float  # 0-10
    multi_source_bonus: float  # 0 or 1
    total_score: float
    comedy_angle: str


@dataclass(slots=True)
class ComedyBrief:
    date: date
    top_picks: list[ScoredItem] = field(default_factory=list)
    also_notable: list[ScoredItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        for section in ("top_picks", "also_notable"):
            for entry in data[section]:
                entry["item"]["timestamp"] = entry["item"]["timestamp"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> ComedyBrief:
        """Deserialize from a JSON-compatible dict."""
        return cls(
            date=date.fromisoformat(data["date"]),
            top_picks=_deserialize_scored_items(data.get("top_picks", [])),
            also_notable=_deserialize_scored_items(data.get("also_notable", [])),
        )


def _deserialize_scored_items(entries: list[dict]) -> list[ScoredItem]:
    """Deserialize a list of ScoredItem dicts from JSON."""
    from shared.utils import parse_iso_utc

    result = []
    for entry in entries:
        raw = entry["item"]
        raw["timestamp"] = parse_iso_utc(raw["timestamp"])
        scored_fields = {k: v for k, v in entry.items() if k != "item"}
        result.append(ScoredItem(item=RawItem(**raw), **scored_fields))
    return result


# --- Script Writer models ---


@dataclass(slots=True)
class Logline:
    text: str
    approach: str  # "absurdist" | "satirical" | "surreal"
    featured_characters: list[str]
    visual_hook: str


@dataclass(slots=True)
class Synopsis:
    setup: str
    escalation: str
    punchline: str
    estimated_scenes: int
    key_visual_gags: list[str]


@dataclass(slots=True)
class SceneScript:
    scene_number: int
    scene_title: str
    setting: str
    scene_prompt: str  # 50-150 words, xAI golden formula
    dialogue: list[dict]  # [{"character": ..., "line": ...}]
    visual_gag: str | None
    audio_direction: str
    duration_seconds: int
    camera_movement: str


@dataclass(slots=True)
class CartoonScript:
    title: str
    date: date
    source_item: ScoredItem
    logline: str
    synopsis: Synopsis
    scenes: list[SceneScript]
    end_card_prompt: str
    characters_used: list[str]

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        data["source_item"]["item"]["timestamp"] = self.source_item.item.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> CartoonScript:
        """Deserialize from a JSON-compatible dict."""
        from shared.utils import parse_iso_utc

        raw = data["source_item"]["item"]
        raw["timestamp"] = parse_iso_utc(raw["timestamp"])
        source_item = ScoredItem(
            item=RawItem(**raw),
            **{k: v for k, v in data["source_item"].items() if k != "item"},
        )
        return cls(
            title=data["title"],
            date=date.fromisoformat(data["date"]),
            source_item=source_item,
            logline=data["logline"],
            synopsis=Synopsis(**data["synopsis"]),
            scenes=[SceneScript(**s) for s in data["scenes"]],
            end_card_prompt=data["end_card_prompt"],
            characters_used=data["characters_used"],
        )


@dataclass(slots=True)
class ShotResult:
    script_index: int
    scene_number: int  # 0 = end_card
    success: bool
    output_path: Path | None
    error: str | None


@dataclass(slots=True)
class ShotsManifest:
    script_title: str
    script_index: int
    date: date
    shots: list[ShotResult]

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "script_title": self.script_title,
            "script_index": self.script_index,
            "date": self.date.isoformat(),
            "shots": [
                {
                    "script_index": s.script_index,
                    "scene_number": s.scene_number,
                    "success": s.success,
                    "output_path": str(s.output_path) if s.output_path else None,
                    "error": s.error,
                }
                for s in self.shots
            ],
        }
