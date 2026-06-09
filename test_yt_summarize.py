import pytest
import sys
import importlib.util
from pathlib import Path

# Import module with dash in name
spec = importlib.util.spec_from_file_location("yt_summarize", Path(__file__).parent / "yt-summarize.py")
yt_summarize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yt_summarize)

parse_queue_text = yt_summarize.parse_queue_text
extract_video_id = yt_summarize.extract_video_id


# --- parse_queue_text ---

def test_parse_queue_returns_urls_under_heading():
    text = "# Video Queue\n\n## Guitar Rigs\nhttps://youtu.be/abc\nhttps://youtu.be/def\n\n## Max for Live\nhttps://youtu.be/ghi\n"
    assert parse_queue_text(text, "Guitar Rigs") == ["https://youtu.be/abc", "https://youtu.be/def"]


def test_parse_queue_case_insensitive():
    text = "# Video Queue\n\n## Guitar Rigs\nhttps://youtu.be/abc\n"
    assert parse_queue_text(text, "guitar rigs") == ["https://youtu.be/abc"]


def test_parse_queue_missing_topic_returns_empty():
    text = "# Video Queue\n\n## Guitar Rigs\nhttps://youtu.be/abc\n"
    assert parse_queue_text(text, "Nonexistent Topic") == []


def test_parse_queue_skips_non_url_lines():
    text = "# Video Queue\n\n## Guitar Rigs\nhttps://youtu.be/abc\nsome notes here\nhttps://youtu.be/def\n"
    assert parse_queue_text(text, "Guitar Rigs") == ["https://youtu.be/abc", "https://youtu.be/def"]


def test_parse_queue_stops_at_next_heading():
    text = "# Video Queue\n\n## Topic A\nhttps://youtu.be/aaa\n\n## Topic B\nhttps://youtu.be/bbb\n"
    assert parse_queue_text(text, "Topic A") == ["https://youtu.be/aaa"]


def test_parse_queue_empty_section_returns_empty():
    text = "# Video Queue\n\n## Guitar Rigs\n\n## Max for Live\nhttps://youtu.be/abc\n"
    assert parse_queue_text(text, "Guitar Rigs") == []


# --- extract_video_id ---

def test_extract_video_id_standard_url():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_with_extra_params():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_raises():
    with pytest.raises(ValueError, match="Could not extract video ID"):
        extract_video_id("https://example.com/notayoutube")


# --- get_video_title ---

def test_get_video_title_parses_page_title():
    from unittest.mock import patch, MagicMock
    fake_html = b"<html><head><title>Never Gonna Give You Up - YouTube</title></head></html>"
    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_html
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = yt_summarize.get_video_title("dQw4w9WgXcQ")
    assert result == "Never Gonna Give You Up"


def test_get_video_title_falls_back_to_id_on_error():
    from unittest.mock import patch
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        result = yt_summarize.get_video_title("dQw4w9WgXcQ")
    assert result == "dQw4w9WgXcQ"


# --- fetch_transcript_text ---

def test_fetch_transcript_text_joins_snippets():
    from unittest.mock import patch, MagicMock
    fake_transcript = [
        {"text": "Hello world", "start": 0.0, "duration": 2.0},
        {"text": "How are you", "start": 2.0, "duration": 2.0},
    ]
    mock_api = MagicMock()
    mock_api.get_transcript.return_value = fake_transcript
    with patch.object(yt_summarize, "YouTubeTranscriptApi", mock_api):
        result = yt_summarize.fetch_transcript_text("dQw4w9WgXcQ")
    assert "Hello world" in result
    assert "How are you" in result


# --- write_transcript_md ---

def test_write_transcript_md_creates_file():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        topic_dir = Path(tmp)
        path = yt_summarize.write_transcript_md("My Video Title", "transcript content here", topic_dir)
        assert path.exists()
        assert path.name == "my-video-title.md"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("# My Video Title")
        assert "transcript content here" in content


def test_write_transcript_md_skips_if_exists():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        topic_dir = Path(tmp)
        resources = topic_dir / "topic-resources"
        resources.mkdir()
        existing = resources / "my-video-title.md"
        existing.write_text("original content", encoding="utf-8")
        path = yt_summarize.write_transcript_md("My Video Title", "new content", topic_dir)
        assert path.read_text(encoding="utf-8") == "original content"


def test_action_prompt_library_covers_all_types():
    ACTION_PROMPT_LIBRARY = yt_summarize.ACTION_PROMPT_LIBRARY
    VALID_TYPES = yt_summarize.VALID_TYPES
    for t in VALID_TYPES:
        assert t in ACTION_PROMPT_LIBRARY, f"Missing action prompt for type: {t}"
        assert isinstance(ACTION_PROMPT_LIBRARY[t], str)
        assert len(ACTION_PROMPT_LIBRARY[t]) > 20
