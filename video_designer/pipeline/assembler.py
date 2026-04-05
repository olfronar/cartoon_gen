"""Thin re-export of shared assembler functions for backward compatibility."""

from __future__ import annotations

from shared.assembler import (
    _concat_clips,
    _concat_with_glitch,
    _generate_glitch_clip,
    assemble_final_video,
    assemble_script_video,
)

__all__ = [
    "_concat_clips",
    "_concat_with_glitch",
    "_generate_glitch_clip",
    "assemble_final_video",
    "assemble_script_video",
]
