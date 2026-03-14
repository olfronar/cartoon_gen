from pathlib import Path

from shared.config import Settings, load_settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.anthropic_api_key == ""
        assert s.reddit_client_id == ""
        assert s.output_dir == Path("output/briefs")

    def test_load_missing_env_file(self):
        s = load_settings(env_path="/nonexistent/.env")
        assert s.anthropic_api_key == ""

    def test_load_from_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=test-key-123\nXAI_API_KEY=xai-456\n")
        s = load_settings(env_path=str(env_file))
        assert s.anthropic_api_key == "test-key-123"
        assert s.xai_api_key == "xai-456"
