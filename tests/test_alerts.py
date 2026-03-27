from unittest.mock import MagicMock, patch

from agent_researcher.alerts import alert_failure, alert_success
from shared.config import Settings
from tests.conftest import make_brief, make_scored_item


class TestAlertSuccess:
    def test_skips_when_no_webhook(self):
        settings = Settings()
        brief = make_brief(items=[make_scored_item()])
        # Should not raise
        alert_success(brief, ["Local: output/briefs/test.md"], settings)

    def test_sends_when_webhook_set(self):
        settings = Settings(slack_webhook_url="https://hooks.slack.com/test")
        brief = make_brief(items=[make_scored_item()])

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            alert_success(brief, ["Local: test.md"], settings)

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert b"Comedy Brief" in req.data


class TestAlertFailure:
    def test_skips_when_no_webhook(self):
        settings = Settings()
        alert_failure(RuntimeError("boom"), settings)

    def test_sends_when_webhook_set(self):
        settings = Settings(slack_webhook_url="https://hooks.slack.com/test")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            alert_failure(RuntimeError("something broke"), settings)

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert b"RuntimeError" in req.data
        assert b"something broke" in req.data
