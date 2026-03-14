from __future__ import annotations

import asyncio
import logging
from datetime import date

import anthropic

from shared.config import Settings, load_settings
from shared.models import CartoonScript, Logline, ScoredItem

from .brief_reader import read_brief
from .context_loader import build_context_block, load_art_style, load_characters
from .logline_generator import generate_loglines
from .logline_selector import select_logline
from .renderer import write_script
from .script_expander import expand_script, generate_synopsis

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
) -> list[CartoonScript]:
    """Run the full script writer pipeline."""
    settings = settings or load_settings()

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY required for script generation")

    # Single client for all LLM calls
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Load brief
    brief = read_brief(brief_date=target_date, briefs_dir=settings.output_dir)
    logger.info("Processing brief for %s with %d top picks", brief.date, len(brief.top_picks))

    if not brief.top_picks:
        logger.warning("No top picks in brief — nothing to write")
        return []

    # Load context
    characters = load_characters(settings.characters_dir)
    art_style = load_art_style(settings.art_style_path)
    context_block = build_context_block(characters, art_style)

    if not characters:
        logger.warning("No character profiles found — run 'python -m script_writer.setup' first")
    if not art_style:
        logger.warning("No art style found — run 'python -m script_writer.setup art-style' first")

    model = settings.script_writer_model
    max_tokens = settings.script_writer_max_tokens

    # Stages 1+2: Generate loglines and select best, per item in parallel
    print("Generating and selecting loglines...")
    selected = await _generate_and_select_parallel(
        items=brief.top_picks,
        context_block=context_block,
        client=client,
        model=model,
        max_tokens=max_tokens,
    )

    # Stage 3: Expand to full scripts (parallel)
    print("Expanding scripts (parallel)...")
    scripts = await _expand_all_parallel(
        selected=selected,
        items=brief.top_picks,
        script_date=brief.date,
        context_block=context_block,
        client=client,
        model=model,
        max_tokens=max_tokens,
    )

    # Stage 4: Write output
    print("Writing scripts...")
    for i, script in enumerate(scripts, 1):
        md_path, _ = write_script(script, i, settings.scripts_output_dir)
        print(f"  Script {i}: {md_path}")

    print(f"\nDone! {len(scripts)} scripts written to {settings.scripts_output_dir}")
    return scripts


async def _generate_and_select_parallel(
    items: list[ScoredItem],
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> dict[int, Logline]:
    """Generate 3 loglines per item and select the best, all items in parallel."""

    async def _gen_and_select(i: int, item: ScoredItem) -> tuple[int, Logline] | None:
        loglines = await asyncio.to_thread(
            generate_loglines, item, context_block, client, model, max_tokens
        )
        if not loglines:
            logger.warning("No loglines for item %d, skipping", i)
            return None
        best = await asyncio.to_thread(
            select_logline, loglines, item, context_block, client, model, max_tokens
        )
        print(f"  Item {i + 1}/{len(items)}: selected '{best.approach}' approach")
        return i, best

    results = await asyncio.gather(*[_gen_and_select(i, item) for i, item in enumerate(items)])

    return {i: logline for result in results if result is not None for i, logline in [result]}


async def _expand_all_parallel(
    selected: dict[int, Logline],
    items: list[ScoredItem],
    script_date: date,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> list[CartoonScript]:
    """Expand all selected loglines to full scripts in parallel."""

    async def _expand_one(idx: int, logline: Logline) -> CartoonScript | None:
        item = items[idx]
        try:
            synopsis = await asyncio.to_thread(
                generate_synopsis, logline, item, context_block, client, model, max_tokens
            )
            script = await asyncio.to_thread(
                expand_script,
                logline,
                synopsis,
                item,
                script_date,
                context_block,
                client,
                model,
                max_tokens,
            )
            return script
        except Exception:
            logger.exception("Script expansion failed for item %d", idx)
            return None

    tasks = [_expand_one(idx, logline) for idx, logline in selected.items()]
    results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]
