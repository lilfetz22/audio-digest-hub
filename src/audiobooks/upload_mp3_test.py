"""
Test suite for upload_mp3.py

Run with:
    python -m pytest upload_mp3_test.py -v
"""
import json
import math
import os
import sys
from pathlib import Path
from unittest.mock import ANY, MagicMock, call, patch

import pytest
import requests

# Ensure the module under test is importable
sys.path.insert(0, os.path.dirname(__file__))

import upload_mp3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_config_ini(tmp_path):
    """Write a minimal config.ini and return its path."""
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[WebApp]\n"
        "API_URL = https://example.com/api\n"
        "API_KEY = test-api-key-123\n"
    )
    return str(ini)


@pytest.fixture
def fake_mp3(tmp_path):
    """Create a tiny file that pretends to be an MP3."""
    mp3 = tmp_path / "test_audio.mp3"
    mp3.write_bytes(b"\x00" * 1024)  # 1 KB
    return mp3


@pytest.fixture
def sample_text_blocks():
    return [
        {"title": "Introduction", "text": "Hello world " * 50},
        {"title": "Chapter 1", "text": "Some content " * 100},
        {"title": "Conclusion", "text": "Goodbye " * 30},
    ]


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_valid_config(self, fake_config_ini):
        cfg = upload_mp3.load_config(fake_config_ini)
        assert cfg["api_url"] == "https://example.com/api"
        assert cfg["api_key"] == "test-api-key-123"

    def test_exits_when_file_missing(self, tmp_path):
        with pytest.raises(SystemExit):
            upload_mp3.load_config(str(tmp_path / "nonexistent.ini"))

    def test_exits_when_key_missing(self, tmp_path):
        bad_ini = tmp_path / "bad.ini"
        bad_ini.write_text("[WebApp]\nAPI_URL = https://example.com\n")
        with pytest.raises(SystemExit):
            upload_mp3.load_config(str(bad_ini))

    def test_exits_when_section_missing(self, tmp_path):
        bad_ini = tmp_path / "bad.ini"
        bad_ini.write_text("[Other]\nFOO = bar\n")
        with pytest.raises(SystemExit):
            upload_mp3.load_config(str(bad_ini))


# ---------------------------------------------------------------------------
# probe_duration_ms
# ---------------------------------------------------------------------------


class TestProbeDurationMs:
    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="C:/fake/ffmpeg.exe")
    def test_parses_duration_from_stderr(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr=(
                "Input #0, mp3, from 'some.mp3':\n"
                "  Duration: 00:01:30.50, start: 0.000000, bitrate: 128 kb/s\n"
            ),
        )
        ms = upload_mp3.probe_duration_ms("some.mp3")
        assert ms == 90_500

    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="ffmpeg")
    def test_parses_hours_and_minutes(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="  Duration: 01:02:03.00, start: 0.000000, bitrate: 128 kb/s\n",
        )
        ms = upload_mp3.probe_duration_ms("some.mp3")
        assert ms == (1 * 3600 + 2 * 60 + 3) * 1000

    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="ffmpeg")
    def test_raises_when_duration_not_found(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="no duration here")
        with pytest.raises(RuntimeError):
            upload_mp3.probe_duration_ms("some.mp3")

    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="C:/fake/ffmpeg.exe")
    def test_invokes_ffmpeg_with_input_flag(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stderr="  Duration: 00:00:05.00, bitrate: 1 kb/s\n"
        )
        upload_mp3.probe_duration_ms("input.mp3")
        args = mock_run.call_args[0][0]
        assert args[0] == "C:/fake/ffmpeg.exe"
        assert "-i" in args
        assert args[args.index("-i") + 1] == "input.mp3"


# ---------------------------------------------------------------------------
# export_chunk
# ---------------------------------------------------------------------------


class TestExportChunk:
    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="C:/fake/ffmpeg.exe")
    def test_builds_correct_ffmpeg_command(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = upload_mp3.export_chunk("input.mp3", 1000, 5000, "output.mp3")

        assert result == "output.mp3"
        args = mock_run.call_args[0][0]
        assert args[0] == "C:/fake/ffmpeg.exe"
        assert "-ss" in args
        assert args[args.index("-ss") + 1] == "1.0"
        assert "-t" in args
        assert args[args.index("-t") + 1] == "4.0"
        assert "-i" in args
        assert args[args.index("-i") + 1] == "input.mp3"
        assert "-c" in args
        assert args[args.index("-c") + 1] == "copy"
        assert args[-1] == "output.mp3"

    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="ffmpeg")
    def test_raises_on_nonzero_return_code(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="boom")
        with pytest.raises(RuntimeError):
            upload_mp3.export_chunk("input.mp3", 0, 1000, "output.mp3")

    @patch("upload_mp3.subprocess.run")
    @patch("upload_mp3._ffmpeg_exe", return_value="ffmpeg")
    def test_does_not_raise_on_success(self, mock_exe, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        # Should not raise.
        upload_mp3.export_chunk("input.mp3", 0, 1000, "output.mp3")


# ---------------------------------------------------------------------------
# create_metadata
# ---------------------------------------------------------------------------


class TestCreateMetadata:
    def test_basic_metadata(self):
        md = upload_mp3.create_metadata("My Title", 60_000)
        assert md["title"] == "My Title"
        assert md["duration_seconds"] == 60
        chapters = json.loads(md["chapters_json"])
        assert "Part Start" in chapters
        assert chapters["Part Start"] == 0

    def test_duration_rounding(self):
        md = upload_mp3.create_metadata("Title", 90_500)  # 90.5 s
        assert md["duration_seconds"] == 90


# ---------------------------------------------------------------------------
# _create_chapter_list
# ---------------------------------------------------------------------------


class TestCreateChapterList:
    def test_proportional_chapters(self, sample_text_blocks):
        total_duration_ms = 120_000
        chapters = upload_mp3._create_chapter_list(total_duration_ms, sample_text_blocks)
        assert len(chapters) == 3
        # First chapter always starts at 0
        assert chapters[0]["start_time_ms"] == 0
        assert chapters[0]["title"] == "Introduction"
        # Subsequent chapters start later
        assert chapters[1]["start_time_ms"] > 0
        assert chapters[2]["start_time_ms"] > chapters[1]["start_time_ms"]

    def test_single_block(self):
        blocks = [{"title": "Only", "text": "content"}]
        chapters = upload_mp3._create_chapter_list(60_000, blocks)
        assert len(chapters) == 1
        assert chapters[0]["start_time_ms"] == 0

    def test_empty_text_blocks(self):
        blocks = [
            {"title": "A", "text": ""},
            {"title": "B", "text": ""},
        ]
        chapters = upload_mp3._create_chapter_list(60_000, blocks)
        assert len(chapters) == 2
        # All start at 0 because total_chars is 0
        assert chapters[0]["start_time_ms"] == 0
        assert chapters[1]["start_time_ms"] == 0


# ---------------------------------------------------------------------------
# _create_metadata  (chapter-aware)
# ---------------------------------------------------------------------------


class TestCreateMetadataWithChapters:
    def test_includes_chapters(self, sample_text_blocks):
        md = upload_mp3._create_metadata("Chaptered", 60_000, sample_text_blocks)
        assert md["title"] == "Chaptered"
        assert md["duration_seconds"] == 60
        chapters = json.loads(md["chapters_json"])
        assert "Introduction" in chapters
        assert "Chapter 1" in chapters
        assert "Conclusion" in chapters


# ---------------------------------------------------------------------------
# upload_single_file
# ---------------------------------------------------------------------------


class TestUploadSingleFile:
    @patch("upload_mp3.requests.post")
    def test_success_on_first_attempt(self, mock_post, fake_mp3):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "abc123"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            {"title": "t"},
        )
        assert result is True
        mock_post.assert_called_once()

    @patch("upload_mp3.requests.post")
    def test_non_retriable_http_error(self, mock_post, fake_mp3):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "Bad Request"
        error = requests.exceptions.HTTPError(response=resp)
        resp.raise_for_status.side_effect = error
        mock_post.return_value = resp

        result = upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            {"title": "t"},
        )
        assert result is False

    @patch("upload_mp3.time.sleep")
    @patch("upload_mp3.requests.post")
    def test_retries_on_server_error_then_succeeds(self, mock_post, mock_sleep, fake_mp3):
        # First call: 500 error, second call: success
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        fail_resp.text = "Internal Server Error"
        fail_error = requests.exceptions.HTTPError(response=fail_resp)
        fail_resp.raise_for_status.side_effect = fail_error

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"id": "ok"}
        ok_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [fail_resp, ok_resp]

        result = upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            {"title": "t"},
        )
        assert result is True
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(10)  # base_delay * 2^0

    @patch("upload_mp3.time.sleep")
    @patch("upload_mp3.requests.post")
    def test_retries_on_network_error_then_succeeds(self, mock_post, mock_sleep, fake_mp3):
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"id": "ok"}
        ok_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [
            requests.exceptions.ConnectionError("network down"),
            ok_resp,
        ]

        result = upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            {"title": "t"},
        )
        assert result is True
        assert mock_post.call_count == 2

    @patch("upload_mp3.time.sleep")
    @patch("upload_mp3.requests.post")
    def test_fails_after_max_retries(self, mock_post, mock_sleep, fake_mp3):
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        fail_resp.text = "Service Unavailable"
        error = requests.exceptions.HTTPError(response=fail_resp)
        fail_resp.raise_for_status.side_effect = error
        mock_post.return_value = fail_resp

        result = upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            {"title": "t"},
        )
        assert result is False
        assert mock_post.call_count == 5  # max_retries

    def test_file_not_found(self):
        result = upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            "/nonexistent/file.mp3",
            {"title": "t"},
        )
        assert result is False

    @patch("upload_mp3.requests.post")
    def test_authorization_header(self, mock_post, fake_mp3):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        upload_mp3.upload_single_file(
            "https://example.com/api",
            "my-secret-key",
            str(fake_mp3),
            {"title": "t"},
        )
        called_headers = mock_post.call_args[1]["headers"]
        assert called_headers["Authorization"] == "Bearer my-secret-key"

    @patch("upload_mp3.requests.post")
    def test_posts_to_correct_url(self, mock_post, fake_mp3):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        upload_mp3.upload_single_file(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            {"title": "t"},
        )
        assert mock_post.call_args[0][0] == "https://example.com/api/audiobooks"

    @patch("upload_mp3.time.sleep")
    @patch("upload_mp3.requests.post")
    def test_exponential_backoff_delays(self, mock_post, mock_sleep, fake_mp3):
        """Verify sleep durations grow exponentially on repeated server errors."""
        fail_resp = MagicMock()
        fail_resp.status_code = 502
        fail_resp.text = "Bad Gateway"
        error = requests.exceptions.HTTPError(response=fail_resp)
        fail_resp.raise_for_status.side_effect = error
        mock_post.return_value = fail_resp

        upload_mp3.upload_single_file(
            "https://example.com/api", "key", str(fake_mp3), {"title": "t"}
        )
        # base_delay=10; delays: 10, 20, 40, 80  (4 sleeps before giving up on 5th)
        expected_delays = [call(10), call(20), call(40), call(80)]
        assert mock_sleep.call_args_list == expected_delays


# ---------------------------------------------------------------------------
# upload_audiobook
# ---------------------------------------------------------------------------


class TestUploadAudiobook:
    @patch("upload_mp3.upload_single_file", return_value=True)
    @patch("upload_mp3.probe_duration_ms", return_value=60_000)
    def test_small_file_uploads_directly(self, mock_probe, mock_upload, fake_mp3):
        result = upload_mp3.upload_audiobook(
            "https://example.com/api", "key", str(fake_mp3), base_title="Test"
        )
        assert result is True
        mock_upload.assert_called_once()

    @patch("upload_mp3.split_and_upload_chunks", return_value=True)
    @patch("upload_mp3.probe_duration_ms", return_value=300_000)
    def test_large_file_triggers_chunking(self, mock_probe, mock_split, tmp_path):
        # Create a file > MAX_UPLOAD_SIZE_MB
        big_mp3 = tmp_path / "big.mp3"
        big_mp3.write_bytes(b"\x00" * int(40 * 1024 * 1024))  # 40 MB

        result = upload_mp3.upload_audiobook(
            "https://example.com/api", "key", str(big_mp3), base_title="Big"
        )
        assert result is True
        mock_split.assert_called_once()
        # duration_ms should have been threaded through as the 4th positional arg
        assert mock_split.call_args[0][3] == 300_000

    def test_missing_file_returns_false(self):
        result = upload_mp3.upload_audiobook(
            "https://example.com/api", "key", "/no/such/file.mp3"
        )
        assert result is False

    @patch("upload_mp3.upload_single_file", return_value=True)
    @patch("upload_mp3.probe_duration_ms", return_value=60_000)
    def test_default_title_from_filename(self, mock_probe, mock_upload, fake_mp3):
        upload_mp3.upload_audiobook("https://example.com/api", "key", str(fake_mp3))
        title = mock_upload.call_args[0][3]["title"]
        assert fake_mp3.name in title

    @patch("upload_mp3.upload_single_file", return_value=False)
    @patch("upload_mp3.probe_duration_ms", return_value=60_000)
    def test_upload_failure_returns_false(self, mock_probe, mock_upload, fake_mp3):
        result = upload_mp3.upload_audiobook(
            "https://example.com/api", "key", str(fake_mp3), base_title="Fail"
        )
        assert result is False

    @patch("upload_mp3.upload_single_file", return_value=True)
    @patch("upload_mp3.probe_duration_ms", return_value=60_000)
    def test_uses_chapter_metadata_when_text_blocks_provided(
        self, mock_probe, mock_upload, fake_mp3, sample_text_blocks
    ):
        upload_mp3.upload_audiobook(
            "https://example.com/api",
            "key",
            str(fake_mp3),
            base_title="Chaptered",
            text_blocks=sample_text_blocks,
        )
        metadata = mock_upload.call_args[0][3]
        chapters = json.loads(metadata["chapters_json"])
        assert "Introduction" in chapters
        assert "Chapter 1" in chapters
        assert "Conclusion" in chapters

    @patch("upload_mp3.probe_duration_ms", side_effect=RuntimeError("corrupt file"))
    def test_handles_audio_processing_error(self, mock_probe, fake_mp3):
        result = upload_mp3.upload_audiobook(
            "https://example.com/api", "key", str(fake_mp3)
        )
        assert result is False


# ---------------------------------------------------------------------------
# split_and_upload_chunks
# ---------------------------------------------------------------------------


class TestSplitAndUploadChunks:
    @patch("upload_mp3.probe_duration_ms", return_value=30_000)
    @patch("upload_mp3.export_chunk")
    @patch("upload_mp3.upload_single_file", return_value=True)
    def test_splits_into_correct_number_of_chunks(
        self, mock_upload, mock_export, mock_probe
    ):
        file_size_mb = 80.0  # should create ceil(80/35) = 3 chunks
        mp3_path = Path("fake_audio.mp3")
        duration_ms = 300_000

        result = upload_mp3.split_and_upload_chunks(
            "https://example.com/api",
            "key",
            mp3_path,
            duration_ms,
            "Title",
            file_size_mb,
        )
        assert result is True
        num_chunks = math.ceil(file_size_mb / upload_mp3.MAX_UPLOAD_SIZE_MB)
        assert mock_upload.call_count == num_chunks
        assert mock_export.call_count == num_chunks

    @patch("upload_mp3.probe_duration_ms", return_value=30_000)
    @patch("upload_mp3.export_chunk")
    @patch("upload_mp3.upload_single_file")
    def test_stops_on_first_chunk_failure(self, mock_upload, mock_export, mock_probe):
        mock_upload.side_effect = [True, False, True]  # second chunk fails
        file_size_mb = 105.0  # ceil(105/35) = 3 chunks
        mp3_path = Path("fake_audio.mp3")
        duration_ms = 300_000

        result = upload_mp3.split_and_upload_chunks(
            "https://example.com/api",
            "key",
            mp3_path,
            duration_ms,
            "Title",
            file_size_mb,
        )
        assert result is False
        assert mock_upload.call_count == 2  # stopped after failure
        assert mock_export.call_count == 2  # never exported the 3rd chunk

    @patch("upload_mp3.probe_duration_ms", return_value=30_000)
    @patch("upload_mp3.export_chunk")
    @patch("upload_mp3.upload_single_file", return_value=True)
    def test_chunk_titles_include_part_numbers(self, mock_upload, mock_export, mock_probe):
        file_size_mb = 70.0  # 2 chunks
        mp3_path = Path("my_audio.mp3")
        duration_ms = 100_000

        upload_mp3.split_and_upload_chunks(
            "https://example.com/api",
            "key",
            mp3_path,
            duration_ms,
            "My Audio",
            file_size_mb,
        )
        titles = [c[0][3]["title"] for c in mock_upload.call_args_list]
        assert titles[0] == "My Audio (Part 1 of 2)"
        assert titles[1] == "My Audio (Part 2 of 2)"

    @patch("upload_mp3.probe_duration_ms", return_value=30_000)
    @patch("upload_mp3.export_chunk")
    @patch("upload_mp3.upload_single_file", return_value=True)
    def test_chunk_filenames_follow_part_n_of_m_scheme(
        self, mock_upload, mock_export, mock_probe
    ):
        """The `_part_N_of_M.mp3` naming scheme is a public contract the
        backend/frontend rely on -- must not change."""
        file_size_mb = 70.0
        mp3_path = Path("my_audio.mp3")
        duration_ms = 100_000

        upload_mp3.split_and_upload_chunks(
            "https://example.com/api",
            "key",
            mp3_path,
            duration_ms,
            "Title",
            file_size_mb,
        )
        filenames = [c.args[3] for c in mock_export.call_args_list]
        assert filenames[0].replace("\\", "/").endswith("my_audio_part_1_of_2.mp3")
        assert filenames[1].replace("\\", "/").endswith("my_audio_part_2_of_2.mp3")

    @patch("upload_mp3.probe_duration_ms", return_value=30_000)
    @patch("upload_mp3.export_chunk")
    @patch("upload_mp3.upload_single_file", return_value=True)
    def test_export_chunk_called_with_correct_time_ranges(
        self, mock_upload, mock_export, mock_probe
    ):
        file_size_mb = 70.0  # 2 chunks
        mp3_path = Path("audio.mp3")
        duration_ms = 100_000

        upload_mp3.split_and_upload_chunks(
            "https://example.com/api",
            "key",
            mp3_path,
            duration_ms,
            "Title",
            file_size_mb,
        )
        chunk_duration_ms = math.ceil(duration_ms / 2)
        expected_calls = [
            call(mp3_path, 0, chunk_duration_ms, ANY),
            call(mp3_path, chunk_duration_ms, duration_ms, ANY),
        ]
        assert mock_export.call_args_list == expected_calls

    @patch("upload_mp3.probe_duration_ms", return_value=30_000)
    @patch("upload_mp3.export_chunk")
    @patch("upload_mp3.upload_single_file", return_value=True)
    def test_uses_chapter_metadata_when_text_blocks_provided(
        self, mock_upload, mock_export, mock_probe, sample_text_blocks
    ):
        file_size_mb = 70.0
        mp3_path = Path("audio.mp3")
        duration_ms = 100_000

        upload_mp3.split_and_upload_chunks(
            "https://example.com/api",
            "key",
            mp3_path,
            duration_ms,
            "Title",
            file_size_mb,
            text_blocks=sample_text_blocks,
        )
        metadata = mock_upload.call_args_list[0][0][3]
        chapters = json.loads(metadata["chapters_json"])
        assert "Introduction" in chapters


# ---------------------------------------------------------------------------
# main (CLI entry-point)
# ---------------------------------------------------------------------------


class TestMain:
    @patch("upload_mp3.upload_audiobook", return_value=True)
    @patch("upload_mp3.load_config", return_value={"api_url": "https://x.com", "api_key": "k"})
    def test_successful_run(self, mock_config, mock_upload, fake_mp3):
        with patch("sys.argv", ["upload_mp3.py", str(fake_mp3)]):
            upload_mp3.main()
        mock_upload.assert_called_once()

    @patch("upload_mp3.upload_audiobook", return_value=False)
    @patch("upload_mp3.load_config", return_value={"api_url": "https://x.com", "api_key": "k"})
    def test_exits_1_on_failure(self, mock_config, mock_upload, fake_mp3):
        with patch("sys.argv", ["upload_mp3.py", str(fake_mp3)]):
            with pytest.raises(SystemExit) as exc_info:
                upload_mp3.main()
            assert exc_info.value.code == 1

    def test_exits_1_when_file_missing(self):
        with patch("sys.argv", ["upload_mp3.py", "/no/such/file.mp3"]):
            with pytest.raises(SystemExit) as exc_info:
                upload_mp3.main()
            assert exc_info.value.code == 1

    def test_no_args_shows_help(self):
        with patch("sys.argv", ["upload_mp3.py"]):
            with pytest.raises(SystemExit) as exc_info:
                upload_mp3.main()
            assert exc_info.value.code == 2  # argparse exits with 2
