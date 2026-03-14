from datetime import datetime, timezone

from shared.utils import parse_iso_utc, strip_code_fences, strip_html


class TestStripCodeFences:
    def test_json_fences(self):
        text = '```json\n[{"a": 1}]\n```'
        assert strip_code_fences(text) == '[{"a": 1}]'

    def test_plain_fences(self):
        text = "```\nhello\n```"
        assert strip_code_fences(text) == "hello"

    def test_no_fences(self):
        assert strip_code_fences('{"a": 1}') == '{"a": 1}'

    def test_whitespace_around_fences(self):
        text = "  ```json\n[1,2]\n```  "
        assert strip_code_fences(text) == "[1,2]"

    def test_empty_string(self):
        assert strip_code_fences("") == ""

    def test_fences_no_newline(self):
        text = "```content```"
        assert strip_code_fences(text) == "content"


class TestParseIsoUtc:
    def test_z_suffix(self):
        result = parse_iso_utc("2026-03-14T12:00:00Z")
        assert result == datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc)

    def test_offset_suffix(self):
        result = parse_iso_utc("2026-03-14T12:00:00+00:00")
        assert result == datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc)

    def test_invalid_returns_now(self):
        result = parse_iso_utc("not-a-date")
        assert result.tzinfo == timezone.utc

    def test_empty_returns_now(self):
        result = parse_iso_utc("")
        assert result.tzinfo == timezone.utc


class TestStripHtml:
    def test_basic_tags(self):
        assert strip_html("<p>hello</p>") == "hello"

    def test_nested_tags(self):
        assert strip_html("<div><b>bold</b> text</div>") == "bold text"

    def test_no_tags(self):
        assert strip_html("plain text") == "plain text"

    def test_empty(self):
        assert strip_html("") == ""
