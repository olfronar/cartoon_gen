from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tiktok_publisher.auth import _read_tokens, _save_tokens, load_tokens, refresh_tokens


def _make_settings(tmp_path: Path) -> MagicMock:
    settings = MagicMock()
    settings.tiktok_client_key = "test-key"
    settings.tiktok_client_secret = "test-secret"
    settings.tiktok_tokens_path = tmp_path / "tokens.json"
    settings.tiktok_redirect_port = 8585
    return settings


class TestSaveAndReadTokens:
    def test_round_trip(self, tmp_path):
        settings = _make_settings(tmp_path)
        token_data = {
            "access_token": "act.abc123",
            "refresh_token": "rft.xyz789",
            "open_id": "user-123",
            "expires_in": 86400,
        }

        _save_tokens(settings, token_data)
        tokens = _read_tokens(settings)

        assert tokens["access_token"] == "act.abc123"
        assert tokens["refresh_token"] == "rft.xyz789"
        assert tokens["open_id"] == "user-123"
        assert tokens["expires_at"] > time.time()

    def test_read_missing_file(self, tmp_path):
        settings = _make_settings(tmp_path)
        assert _read_tokens(settings) == {}

    def test_creates_parent_dirs(self, tmp_path):
        settings = _make_settings(tmp_path)
        settings.tiktok_tokens_path = tmp_path / "nested" / "dir" / "tokens.json"

        _save_tokens(
            settings,
            {
                "access_token": "act.test",
                "refresh_token": "rft.test",
                "expires_in": 3600,
            },
        )

        assert settings.tiktok_tokens_path.is_file()


class TestLoadTokens:
    def test_returns_valid_tokens(self, tmp_path):
        settings = _make_settings(tmp_path)
        _save_tokens(
            settings,
            {
                "access_token": "act.valid",
                "refresh_token": "rft.valid",
                "expires_in": 86400,
            },
        )

        tokens = load_tokens(settings)
        assert tokens["access_token"] == "act.valid"

    def test_raises_when_no_tokens(self, tmp_path):
        settings = _make_settings(tmp_path)
        with pytest.raises(RuntimeError, match="No tokens found"):
            load_tokens(settings)

    @patch("tiktok_publisher.auth.refresh_tokens")
    def test_auto_refreshes_expired(self, mock_refresh, tmp_path):
        settings = _make_settings(tmp_path)

        # Write expired tokens
        tokens = {
            "access_token": "act.old",
            "refresh_token": "rft.old",
            "open_id": "user-1",
            "expires_at": time.time() - 3600,
        }
        settings.tiktok_tokens_path.write_text(json.dumps(tokens))

        # Mock refresh to write new tokens
        def do_refresh(s):
            _save_tokens(
                s,
                {
                    "access_token": "act.new",
                    "refresh_token": "rft.new",
                    "open_id": "user-1",
                    "expires_in": 86400,
                },
            )

        mock_refresh.side_effect = do_refresh

        result = load_tokens(settings)
        mock_refresh.assert_called_once_with(settings)
        assert result["access_token"] == "act.new"


class TestRefreshTokens:
    @patch("tiktok_publisher.auth.urllib.request.urlopen")
    def test_refreshes_and_saves(self, mock_urlopen, tmp_path):
        settings = _make_settings(tmp_path)

        # Write initial tokens
        _save_tokens(
            settings,
            {
                "access_token": "act.old",
                "refresh_token": "rft.old",
                "expires_in": 0,
            },
        )

        # Mock API response
        response_data = json.dumps(
            {
                "access_token": "act.refreshed",
                "refresh_token": "rft.rotated",
                "open_id": "user-1",
                "expires_in": 86400,
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = refresh_tokens(settings)
        assert result["access_token"] == "act.refreshed"

        # Verify saved to file
        saved = _read_tokens(settings)
        assert saved["access_token"] == "act.refreshed"
        assert saved["refresh_token"] == "rft.rotated"

    def test_raises_without_refresh_token(self, tmp_path):
        settings = _make_settings(tmp_path)
        with pytest.raises(RuntimeError, match="No refresh token"):
            refresh_tokens(settings)
