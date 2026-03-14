from datetime import date

from agent_researcher.delivery.local import render_brief, write_brief_local
from shared.models import ComedyBrief
from tests.conftest import make_raw_item, make_scored_item


class TestRenderBrief:
    def test_contains_date(self):
        brief = ComedyBrief(date=date(2026, 3, 14), top_picks=[], also_notable=[])
        result = render_brief(brief)
        assert "2026-03-14" in result

    def test_top_picks_section(self):
        item = make_scored_item(comedy_angle="Funny angle")
        brief = ComedyBrief(date=date(2026, 3, 14), top_picks=[item])
        result = render_brief(brief)
        assert "### TOP PICKS" in result
        assert "Test Item" in result
        assert "Funny angle" in result

    def test_also_notable_section(self):
        item = make_scored_item()
        brief = ComedyBrief(date=date(2026, 3, 14), also_notable=[item])
        result = render_brief(brief)
        assert "### ALSO NOTABLE" in result

    def test_multi_source_indicator(self):
        raw = make_raw_item(sources=["hackernews", "reddit"])
        item = make_scored_item(raw_item=raw)
        brief = ComedyBrief(date=date(2026, 3, 14), top_picks=[item])
        result = render_brief(brief)
        assert "multi-source +1" in result

    def test_empty_brief(self):
        brief = ComedyBrief(date=date(2026, 3, 14))
        result = render_brief(brief)
        assert "2026-03-14" in result
        assert "TOP PICKS" not in result


class TestWriteBriefLocal:
    def test_writes_file(self, tmp_path):
        item = make_scored_item()
        brief = ComedyBrief(date=date(2026, 3, 14), top_picks=[item])
        path = write_brief_local(brief, tmp_path)
        assert path.exists()
        assert path.name == "2026-03-14.md"
        content = path.read_text()
        assert "Test Item" in content

    def test_creates_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        brief = ComedyBrief(date=date(2026, 3, 14))
        path = write_brief_local(brief, nested)
        assert path.exists()
