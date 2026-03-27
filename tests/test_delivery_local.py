from datetime import date

from agent_researcher.delivery.local import render_brief, write_brief_local
from shared.models import ComedyBrief
from tests.conftest import make_raw_item, make_scored_item


class TestRenderBrief:
    def test_contains_date(self):
        brief = ComedyBrief(date=date(2026, 3, 14), items=[])
        result = render_brief(brief)
        assert "2026-03-14" in result

    def test_items_rendered(self):
        item = make_scored_item(comedy_angle="Funny angle")
        brief = ComedyBrief(date=date(2026, 3, 14), items=[item])
        result = render_brief(brief)
        assert "1." in result
        assert "Test Item" in result
        assert "Funny angle" in result

    def test_multi_source_indicator(self):
        raw = make_raw_item(sources=["hackernews", "reddit"])
        item = make_scored_item(raw_item=raw)
        brief = ComedyBrief(date=date(2026, 3, 14), items=[item])
        result = render_brief(brief)
        assert "multi-source +1" in result

    def test_empty_brief(self):
        brief = ComedyBrief(date=date(2026, 3, 14))
        result = render_brief(brief)
        assert "2026-03-14" in result


class TestWriteBriefLocal:
    def test_writes_file(self, tmp_path):
        item = make_scored_item()
        brief = ComedyBrief(date=date(2026, 3, 14), items=[item])
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

    def test_writes_json_sidecar(self, tmp_path):
        import json

        item = make_scored_item()
        brief = ComedyBrief(date=date(2026, 3, 14), items=[item])
        write_brief_local(brief, tmp_path)
        json_path = tmp_path / "2026-03-14.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["date"] == "2026-03-14"
        assert len(data["items"]) == 1
