from agent_researcher.delivery.notion import _build_notion_blocks
from tests.conftest import make_brief, make_scored_item


class TestBuildNotionBlocks:
    def test_item_heading(self):
        brief = make_brief(items=[make_scored_item()])
        blocks = _build_notion_blocks(brief)
        headings = [b for b in blocks if b["type"] == "heading_3"]
        assert any("1." in str(h) for h in headings)

    def test_item_details(self):
        item = make_scored_item(comedy_angle="Very funny")
        brief = make_brief(items=[item])
        blocks = _build_notion_blocks(brief)
        bullets = [b for b in blocks if b["type"] == "bulleted_list_item"]
        texts = [b["bulleted_list_item"]["rich_text"][0]["text"]["content"] for b in bullets]
        assert any("Source:" in t for t in texts)
        assert any("Very funny" in t for t in texts)

    def test_empty_brief(self):
        brief = make_brief()
        blocks = _build_notion_blocks(brief)
        assert len(blocks) == 0
