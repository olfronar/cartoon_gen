from __future__ import annotations

from unittest.mock import patch

import pytest

from script_writer.pipeline.logline_tournament import compare_pair, run_tournament
from shared.models import Logline
from tests.conftest import make_scored_item


def _make_logline(text: str, approach: str = "test", format_type: str = "exchange") -> Logline:
    return Logline(
        text=text,
        approach=approach,
        featured_characters=["Billy"],
        visual_hook="test hook",
        news_essence="test news",
        format_type=format_type,
    )


class TestComparePair:
    @patch("script_writer.pipeline.logline_tournament.call_llm_json")
    def test_returns_winner(self, mock_llm):
        mock_llm.return_value = {
            "winner": "b",
            "reasoning": "funnier",
            "loser_feedback": "try harder",
        }
        a = _make_logline("logline A")
        b = _make_logline("logline B")
        item = make_scored_item()
        winner, loser, feedback = compare_pair(a, b, item, "ctx", None, "model", 100)
        assert winner is b
        assert loser is a
        assert feedback == "try harder"

    @patch("script_writer.pipeline.logline_tournament.call_llm_json")
    def test_defaults_to_a(self, mock_llm):
        mock_llm.return_value = {"winner": "a", "reasoning": "ok"}
        a = _make_logline("logline A")
        b = _make_logline("logline B")
        winner, loser, _ = compare_pair(a, b, make_scored_item(), "ctx", None, "model", 100)
        assert winner is a
        assert loser is b


class TestRunTournament:
    def test_single_candidate(self):
        logline = _make_logline("only one")
        result = run_tournament([logline], make_scored_item(), "ctx", None, "model", 100)
        assert result is logline

    @patch("script_writer.pipeline.logline_tournament.call_llm_json")
    def test_two_candidates(self, mock_llm):
        mock_llm.return_value = {
            "winner": "b",
            "reasoning": "better",
            "loser_feedback": "needs work",
        }
        a = _make_logline("A")
        b = _make_logline("B")
        result = run_tournament([a, b], make_scored_item(), "ctx", None, "model", 100)
        # Round 1: 1 compare + 1 revision attempt + final round: 1 compare = 3
        assert result is not None
        assert mock_llm.call_count >= 1

    @patch("script_writer.pipeline.logline_tournament.call_llm_json")
    def test_five_candidates(self, mock_llm):
        mock_llm.return_value = {
            "winner": "a",
            "reasoning": "first wins",
            "loser_feedback": "improve",
        }
        loglines = [_make_logline(f"L{i}") for i in range(5)]
        result = run_tournament(loglines, make_scored_item(), "ctx", None, "model", 100)
        # Round 1: 2 comparisons + up to 2 revisions, then subsequent rounds
        assert mock_llm.call_count >= 4
        assert result is not None

    @patch("script_writer.pipeline.logline_tournament.call_llm_json")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = Exception("API error")
        loglines = [_make_logline("A"), _make_logline("B")]
        result = run_tournament(loglines, make_scored_item(), "ctx", None, "model", 100)
        assert result is loglines[0]  # falls back to first

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            run_tournament([], make_scored_item(), "ctx", None, "model", 100)
