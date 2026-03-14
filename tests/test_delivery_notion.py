from agent_researcher.delivery.notion import _build_notion_blocks
from tests.conftest import make_brief, make_scored_item


class TestBuildNotionBlocks:
    def test_top_picks_heading(self):
        brief = make_brief(top_picks=[make_scored_item()])
        blocks = _build_notion_blocks(brief)
        headings = [b for b in blocks if b["type"] == "heading_2"]
        assert any("TOP PICKS" in str(h) for h in headings)

    def test_top_pick_item_details(self):
        item = make_scored_item(comedy_angle="Very funny")
        brief = make_brief(top_picks=[item])
        blocks = _build_notion_blocks(brief)
        bullets = [b for b in blocks if b["type"] == "bulleted_list_item"]
        texts = [b["bulleted_list_item"]["rich_text"][0]["text"]["content"] for b in bullets]
        assert any("Source:" in t for t in texts)
        assert any("Very funny" in t for t in texts)

    def test_also_notable_section(self):
        brief = make_brief(also_notable=[make_scored_item()])
        blocks = _build_notion_blocks(brief)
        headings = [b for b in blocks if b["type"] == "heading_2"]
        assert any("ALSO NOTABLE" in str(h) for h in headings)

    def test_empty_brief(self):
        brief = make_brief()
        blocks = _build_notion_blocks(brief)
        # Should still have the TOP PICKS heading
        assert len(blocks) == 1
        assert "TOP PICKS" in str(blocks[0])
