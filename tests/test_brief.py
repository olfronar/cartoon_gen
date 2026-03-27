from datetime import date

from agent_researcher.brief import generate_brief
from tests.conftest import make_scored_item


class TestGenerateBrief:
    def test_20_items(self):
        items = [make_scored_item() for _ in range(25)]
        brief = generate_brief(items)
        assert len(brief.items) == 20

    def test_fewer_than_20_items(self):
        items = [make_scored_item() for _ in range(3)]
        brief = generate_brief(items)
        assert len(brief.items) == 3

    def test_date_is_today(self):
        brief = generate_brief([make_scored_item()])
        assert brief.date == date.today()

    def test_empty_items(self):
        brief = generate_brief([])
        assert len(brief.items) == 0
