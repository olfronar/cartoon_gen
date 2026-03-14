from datetime import date

from agent_researcher.brief import generate_brief
from tests.conftest import make_scored_item


class TestGenerateBrief:
    def test_top_5_picks(self):
        items = [make_scored_item() for _ in range(20)]
        brief = generate_brief(items)
        assert len(brief.top_picks) == 5

    def test_also_notable_up_to_10(self):
        items = [make_scored_item() for _ in range(20)]
        brief = generate_brief(items)
        assert len(brief.also_notable) == 10

    def test_fewer_than_5_items(self):
        items = [make_scored_item() for _ in range(3)]
        brief = generate_brief(items)
        assert len(brief.top_picks) == 3
        assert len(brief.also_notable) == 0

    def test_date_is_today(self):
        brief = generate_brief([make_scored_item()])
        assert brief.date == date.today()

    def test_empty_items(self):
        brief = generate_brief([])
        assert len(brief.top_picks) == 0
        assert len(brief.also_notable) == 0
