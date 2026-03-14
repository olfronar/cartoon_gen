from unittest.mock import MagicMock, patch

import pytest

from agent_researcher.runner import run
from shared.config import Settings
from tests.conftest import make_raw_item


@pytest.mark.asyncio
async def test_run_with_no_keys(tmp_path):
    """Pipeline runs end-to-end with no API keys, using fallback scoring."""
    settings = Settings(output_dir=tmp_path)

    items = [
        make_raw_item(title=f"Item {i}", url=f"https://example.com/{i}", score=100 - i)
        for i in range(10)
    ]

    mock_source = MagicMock()
    mock_source.name = "test"
    mock_source.fetch.return_value = items

    with patch("agent_researcher.runner.get_active_sources", return_value=[mock_source]):
        brief = await run(settings=settings)

    assert len(brief.top_picks) == 5
    assert len(brief.also_notable) == 5
    assert brief.top_picks[0].item.score >= brief.top_picks[1].item.score
    # Verify file was written to tmp_path
    assert list(tmp_path.glob("*.md"))


@pytest.mark.asyncio
async def test_run_handles_source_failure(tmp_path):
    """Pipeline continues when a source throws an exception."""
    settings = Settings(output_dir=tmp_path)

    good_source = MagicMock()
    good_source.name = "good"
    good_source.fetch.return_value = [
        make_raw_item(title=f"Item {i}", url=f"https://example.com/{i}") for i in range(3)
    ]

    bad_source = MagicMock()
    bad_source.name = "bad"
    bad_source.fetch.side_effect = Exception("source crashed")

    with patch(
        "agent_researcher.runner.get_active_sources",
        return_value=[good_source, bad_source],
    ):
        brief = await run(settings=settings)

    assert len(brief.top_picks) == 3


@pytest.mark.asyncio
async def test_run_calls_alert_failure_on_pipeline_error(tmp_path):
    """alert_failure is called when the pipeline raises."""
    settings = Settings(output_dir=tmp_path, slack_webhook_url="https://hooks.slack.com/test")

    with (
        patch(
            "agent_researcher.runner.get_active_sources",
            side_effect=RuntimeError("broken"),
        ),
        patch("agent_researcher.runner.alert_failure") as mock_alert,
        pytest.raises(RuntimeError, match="broken"),
    ):
        await run(settings=settings)

    mock_alert.assert_called_once()
    assert isinstance(mock_alert.call_args[0][0], RuntimeError)
