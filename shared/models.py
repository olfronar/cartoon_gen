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


def _deserialize_scored_item(entry: dict) -> ScoredItem:
    """Deserialize a single ScoredItem dict from JSON."""
    from shared.utils import parse_iso_utc

    raw = entry["item"]
    raw["timestamp"] = parse_iso_utc(raw["timestamp"])
    return ScoredItem(
        item=RawItem(**raw),
        **{k: v for k, v in entry.items() if k != "item"},
    )


def _deserialize_scored_items(entries: list[dict]) -> list[ScoredItem]:
    """Deserialize a list of ScoredItem dicts from JSON."""
    return [_deserialize_scored_item(e) for e in entries]


# --- Script Writer models ---


@dataclass(slots=True)
class Logline:
    text: str
    approach: str  # "observational" | "satirical" | "metaphorical"
    featured_characters: list[str]
    visual_hook: str
    news_essence: str = ""
    format_type: str = ""  # "visual_punchline" | "exchange" | "cold_reveal" | "demonstration"


@dataclass(slots=True)
class Synopsis:
    setup: str
    development: str
    punchline: str
    estimated_scenes: int
    key_visual_gags: list[str]
    news_explanation: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Synopsis:
        """Deserialize from a JSON-compatible dict (accepts 'escalation' for backward compat)."""
        return cls(
            setup=data["setup"],
            development=data.get("development", data.get("escalation", "")),
            punchline=data["punchline"],
            estimated_scenes=int(data.get("estimated_scenes", 1)),
            key_visual_gags=data.get("key_visual_gags", []),
            news_explanation=data.get("news_explanation", ""),
        )


@dataclass(slots=True)
class SceneScript:
    scene_number: int
    scene_title: str
    setting: str
    scene_prompt: str  # 60-100 words, single 15s scene
    dialogue: list[dict]  # [{"character": ..., "line": ...}]
    visual_gag: str | None
    audio_direction: str
    duration_seconds: int
    camera_movement: str
    transformation: str = ""
    billy_emotion: str = ""  # e.g. "deadpan", "frustrated", "amused", "alarmed"

    @classmethod
    def from_dict(cls, data: dict) -> SceneScript:
        """Deserialize from a JSON-compatible dict, handling missing optional fields."""
        return cls(
            scene_number=data["scene_number"],
            scene_title=data["scene_title"],
            setting=data["setting"],
            scene_prompt=data["scene_prompt"],
            dialogue=data.get("dialogue", []),
            visual_gag=data.get("visual_gag"),
            audio_direction=data.get("audio_direction", ""),
            duration_seconds=int(data.get("duration_seconds", 15)),
            camera_movement=data.get("camera_movement", ""),
            transformation=data.get("transformation", ""),
            billy_emotion=data.get("billy_emotion", ""),
        )


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
    format_type: str = ""  # "visual_punchline" | "exchange" | "cold_reveal" | "demonstration"

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        data["source_item"]["item"]["timestamp"] = self.source_item.item.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> CartoonScript:
        """Deserialize from a JSON-compatible dict."""
        return cls(
            title=data["title"],
            date=date.fromisoformat(data["date"]),
            source_item=_deserialize_scored_item(data["source_item"]),
            logline=data["logline"],
            synopsis=Synopsis.from_dict(data["synopsis"]),
            scenes=[SceneScript.from_dict(s) for s in data["scenes"]],
            end_card_prompt=data["end_card_prompt"],
            characters_used=data["characters_used"],
            format_type=data.get("format_type", ""),
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
        data = asdict(self)
        data["date"] = self.date.isoformat()
        for shot in data["shots"]:
            path = shot["output_path"]
            shot["output_path"] = str(path) if path else None
        return data

    @classmethod
    def from_dict(cls, data: dict) -> ShotsManifest:
        """Deserialize from a JSON-compatible dict."""
        return cls(
            script_title=data["script_title"],
            script_index=data["script_index"],
            date=date.fromisoformat(data["date"]),
            shots=[
                ShotResult(
                    script_index=s["script_index"],
                    scene_number=s["scene_number"],
                    success=s["success"],
                    output_path=Path(s["output_path"]) if s["output_path"] else None,
                    error=s["error"],
                )
                for s in data["shots"]
            ],
        )


# --- Video Designer models ---


@dataclass(slots=True)
class ClipResult:
    script_index: int
    scene_number: int  # 0 = end_card
    success: bool
    output_path: Path | None
    duration_seconds: float | None
    error: str | None


@dataclass(slots=True)
class VideoManifest:
    script_title: str
    script_index: int
    date: date
    clips: list[ClipResult]
    script_video_path: Path | None

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        for clip in data["clips"]:
            path = clip["output_path"]
            clip["output_path"] = str(path) if path else None
        svp = data["script_video_path"]
        data["script_video_path"] = str(svp) if svp else None
        return data
