from __future__ import annotations

import logging
from pathlib import Path

from shared.models import ComedyBrief

logger = logging.getLogger(__name__)


def render_brief(brief: ComedyBrief) -> str:
    lines = [f"## Today's Comedy Brief — {brief.date.isoformat()}", ""]

    if brief.top_picks:
        lines.append("### TOP PICKS")
        lines.append("")
        for i, scored in enumerate(brief.top_picks, 1):
            item = scored.item
            sources_str = " / ".join(item.sources)
            lines.append(f"{i}. {item.title}")
            lines.append(f"   - Source: {sources_str}")
            if scored.comedy_angle:
                lines.append(f"   - Why it's funny: {scored.comedy_angle}")
            lines.append(
                f"   - Score: {scored.total_score:.1f} "
                f"(comedy={scored.comedy_potential:.0f}, "
                f"resonance={scored.cultural_resonance:.0f}, "
                f"fresh={scored.freshness:.0f}"
                f"{', multi-source +1' if scored.multi_source_bonus else ''})"
            )
            lines.append(f"   - Raw URL: {item.url}")
            lines.append("")

    if brief.also_notable:
        lines.append("### ALSO NOTABLE (didn't make cut)")
        lines.append("")
        for scored in brief.also_notable:
            item = scored.item
            sources_str = " / ".join(item.sources)
            lines.append(f"- **{item.title}** ({sources_str})")
            if scored.comedy_angle:
                lines.append(f"  - Why it's funny: {scored.comedy_angle}")
            if item.url:
                lines.append(f"  - URL: {item.url}")
        lines.append("")

    return "\n".join(lines)


def write_brief_local(brief: ComedyBrief, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{brief.date.isoformat()}.md"
    path = output_dir / filename

    content = render_brief(brief)
    path.write_text(content, encoding="utf-8")

    logger.info("Brief written to %s", path)
    return path
