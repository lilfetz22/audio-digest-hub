import pytest
import os
import configparser
import json
import base64
import logging
import datetime
import subprocess
from unittest.mock import MagicMock, patch, mock_open, ANY, call
from pathlib import Path
import requests

# Import the script to be tested
import generate_audiobook as ga

# --- Fixtures for Setup and Mocking ---


@pytest.fixture
def mock_config_file(tmp_path):
    """Creates a temporary, valid config.ini file for tests."""
    config = configparser.ConfigParser()
    config["WebApp"] = {
        "API_URL": "https://fake-api.com",
        "API_KEY": "fake_api_key",
    }
    config["Gmail"] = {
        "CREDENTIALS_FILE": "fake_credentials.json",
        "TOKEN_FILE": "fake_token.json",
    }
    config["TTS"] = {"REFERENCE_VOICE_FILE": "path/to/fake_voice.wav"}
    config_path = tmp_path / "config.ini"
    with open(config_path, "w") as f:
        config.write(f)
    return str(config_path)


@pytest.fixture(autouse=True)
def prevent_sys_exit(monkeypatch):
    """Prevents sys.exit() from stopping the test suite."""
    monkeypatch.setattr(ga.sys, "exit", lambda x: (_ for _ in ()).throw(SystemExit(x)))


@pytest.fixture
def mock_tts_client(mocker):
    """Mocks the global TTS_CLIENT for chunking and its methods."""
    mock_client = MagicMock()
    mock_synthesizer = MagicMock()
    mock_synthesizer.split_into_sentences.return_value = ["sentence 1.", "sentence 2."]
    mock_client.synthesizer = mock_synthesizer
    mock_client.tts.return_value = [0.1, 0.2]  # Mock a numpy array chunk
    mocker.patch.object(ga, "TTS_CLIENT", mock_client)
    mocker.patch(
        "generate_audiobook.np.concatenate", return_value=b"concatenated_audio"
    )
    mocker.patch("generate_audiobook.TTS_CLIENT.synthesizer.save_wav")
    return mock_client


@pytest.fixture
def mock_audio_segment(mocker):
    """Mocks pydub.AudioSegment and its chained calls."""
    mock_segment_instance = MagicMock()
    # Mock the export method so it doesn't actually write files
    mock_export = mock_segment_instance.export
    mock_export.return_value.read.return_value = b"mp3_data_bytes"

    mock_from_wav = mocker.patch("generate_audiobook.AudioSegment.from_wav")
    mock_from_wav.return_value = mock_segment_instance
    return mock_segment_instance


@pytest.fixture
def mock_email_data():
    """Provides mock email data for parsing tests, including UNREAD status."""
    text_content = "This is a plain text newsletter."
    html_content = "<h1>Hello</h1><p>This is an HTML newsletter.</p>"

    # Message 1 is UNREAD
    mock_msg_1 = {
        "id": "msg1",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Test Sender 1 <sender1@example.com>"},
                {"name": "Subject", "value": "Unread Email"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            text_content.encode("utf-8")
                        ).decode("ascii")
                    },
                }
            ],
        },
    }

    # Message 2 is already read (no UNREAD label)
    mock_msg_2 = {
        "id": "msg2",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Test Sender 2 <sender2@example.com>"},
                {"name": "Subject", "value": "Read Email"},
            ],
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            html_content.encode("utf-8")
                        ).decode("ascii")
                    },
                }
            ],
        },
    }

    # Malformed message to test error handling
    malformed_msg = {
        "id": "msg3",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [{"name": "From", "value": "Bad Sender <sender3@example.com>"}],
            "parts": [{"mimeType": "text/plain", "body": {"data": "not-base64"}}],
        },
    }

    return [mock_msg_1, mock_msg_2, malformed_msg]


# --- Test Classes ---


class TestConfigAndSetup:
    def test_load_config_success(self, mock_config_file):
        config = ga.load_config(mock_config_file)
        assert config["api_url"] == "https://fake-api.com"
        assert config["api_key"] == "fake_api_key"
        assert config["reference_voice_file"] == "path/to/fake_voice.wav"

    def test_load_config_missing_file(self, caplog):
        with pytest.raises(SystemExit):
            ga.load_config("nonexistent_file.ini")
        assert "Configuration file 'nonexistent_file.ini' not found." in caplog.text

    def test_load_config_missing_key(self, tmp_path, caplog):
        config_path = tmp_path / "invalid_config.ini"
        config_path.write_text("[WebApp]\nAPI_URL = https://fake-api.com\n")
        with pytest.raises(SystemExit):
            ga.load_config(str(config_path))
        assert "Missing key in config.ini: 'API_KEY'" in caplog.text

    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    @patch("logging.Formatter")
    @patch("logging.getLogger")
    def test_setup_logging(self, m_get_logger, m_formatter, m_stream, m_file):
        mock_logger = MagicMock()
        m_get_logger.return_value = mock_logger
        ga.setup_logging()
        m_get_logger.assert_called_once()
        mock_logger.setLevel.assert_called_with(logging.INFO)
        assert mock_logger.addHandler.call_count == 2
        m_file.assert_called_with("audiobook_generator.log", mode="a", encoding="utf-8")
        m_stream.assert_called_with(ga.sys.stdout)


class TestApiInteractions:
    def test_fetch_sources_success(self, requests_mock):
        requests_mock.get(
            "https://fake-api.com/sources", json=[{"sender_email": "test@example.com"}]
        )
        sources = ga.fetch_sources("https://fake-api.com", "fake_key")
        assert sources == [{"sender_email": "test@example.com"}]

    def test_fetch_sources_http_error(self, requests_mock, caplog):
        requests_mock.get(
            "https://fake-api.com/sources", status_code=500, text="Server Error"
        )
        with pytest.raises(SystemExit):
            ga.fetch_sources("https://fake-api.com", "fake_key")
        assert "A network error occurred" in caplog.text

    def test_check_existing_audiobook_found(self, requests_mock, caplog):
        """Test that check_existing_audiobook returns True when a duplicate title is found."""
        mock_audiobooks = [
            {"id": "1", "title": "Daily Digest for 2025-07-04", "created_at": "2025-07-04T10:00:00Z"},
            {"id": "2", "title": "Daily Digest for 2025-07-03", "created_at": "2025-07-03T10:00:00Z"},
        ]
        requests_mock.get(
            "https://fake-api.com/audiobooks", 
            status_code=200, 
            json=mock_audiobooks
        )
        
        with caplog.at_level(logging.INFO):
            result = ga.check_existing_audiobook("https://fake-api.com", "fake_key", "Daily Digest for 2025-07-04")
        
        assert result is True
        assert "Checking if audiobook 'Daily Digest for 2025-07-04' already exists..." in caplog.text
        assert "Audiobook 'Daily Digest for 2025-07-04' already exists. Skipping generation." in caplog.text

    def test_check_existing_audiobook_not_found(self, requests_mock, caplog):
        """Test that check_existing_audiobook returns False when no duplicate title is found."""
        mock_audiobooks = [
            {"id": "1", "title": "Daily Digest for 2025-07-03", "created_at": "2025-07-03T10:00:00Z"},
            {"id": "2", "title": "Daily Digest for 2025-07-02", "created_at": "2025-07-02T10:00:00Z"},
        ]
        requests_mock.get(
            "https://fake-api.com/audiobooks", 
            status_code=200, 
            json=mock_audiobooks
        )
        
        with caplog.at_level(logging.INFO):
            result = ga.check_existing_audiobook("https://fake-api.com", "fake_key", "Daily Digest for 2025-07-04")
        
        assert result is False
        assert "Checking if audiobook 'Daily Digest for 2025-07-04' already exists..." in caplog.text
        assert "No existing audiobook found with title 'Daily Digest for 2025-07-04'. Proceeding with generation." in caplog.text

    def test_check_existing_audiobook_api_error(self, requests_mock, caplog):
        """Test that check_existing_audiobook handles API errors gracefully."""
        requests_mock.get(
            "https://fake-api.com/audiobooks", 
            status_code=500, 
            text="Internal Server Error"
        )
        
        with caplog.at_level(logging.WARNING):
            result = ga.check_existing_audiobook("https://fake-api.com", "fake_key", "Daily Digest for 2025-07-04")
        
        assert result is False
        assert "API returned status 500. Proceeding with generation to avoid blocking." in caplog.text

    def test_check_existing_audiobook_network_error(self, requests_mock, caplog):
        """Test that check_existing_audiobook handles network errors gracefully."""
        requests_mock.get(
            "https://fake-api.com/audiobooks", 
            exc=requests.exceptions.ConnectionError("Connection failed")
        )
        
        with caplog.at_level(logging.INFO):
            result = ga.check_existing_audiobook("https://fake-api.com", "fake_key", "Daily Digest for 2025-07-04")
        
        assert result is False
        assert "Error checking for existing audiobook:" in caplog.text
        assert "Proceeding with generation due to API error." in caplog.text

    def test_upload_audiobook_success(self, requests_mock, tmp_path, caplog):
        filepath = tmp_path / "test.mp3"
        filepath.write_text("mp3_data")
        metadata = {"title": "test"}
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=200, json={"status": "ok"}
        )
        with caplog.at_level(logging.INFO):
            result = ga.upload_audiobook(
                "https://fake-api.com", "fake_key", str(filepath), metadata
            )

        assert result is True
        assert f"Preparing to upload '{filepath}'" in caplog.text
        assert "Upload successful. Server response:" in caplog.text

    def test_upload_audiobook_http_error(self, requests_mock, tmp_path, caplog):
        filepath = tmp_path / "test.mp3"
        filepath.write_text("mp3_data")
        metadata = {"title": "test"}
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=400, text="Bad Request"
        )
        with caplog.at_level(logging.ERROR):
            result = ga.upload_audiobook(
                "https://fake-api.com", "fake_key", str(filepath), metadata
            )

        assert result is False
        assert (
            f"A non-retriable HTTP error occurred:"
            in caplog.text
        )


class TestGmailInteraction:
    @pytest.fixture
    def mock_gmail_service(self):
        """A basic mock for the gmail service."""
        return MagicMock()

    @patch("generate_audiobook.os.path.exists", side_effect=[False, False])
    @patch("generate_audiobook.Credentials.from_authorized_user_file")
    @patch("generate_audiobook.InstalledAppFlow.from_client_secrets_file")
    def test_authenticate_gmail_credentials_not_found(
        self, m_flow, m_creds, m_exists, caplog
    ):
        with pytest.raises(SystemExit):
            ga.authenticate_gmail("token.json", "creds.json")
        assert "Credentials file 'creds.json' not found." in caplog.text
        # Assert that we exit *before* attempting to use the missing credentials file.
        m_flow.assert_not_called()

    def test_process_emails_success_and_marks_as_read(
        self, mock_gmail_service, mock_email_data
    ):
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }
        # The code reverses the list, so mock side_effect in reverse order
        # Message 2 (already read) is processed first, then Message 1 (unread)
        mock_gmail_service.users().messages().get().execute.side_effect = [
            mock_email_data[1],
            mock_email_data[0],
        ]

        sources = [
            {"sender_email": "sender1@example.com", "custom_name": "Newsletter One"},
            {"sender_email": "sender2@example.com", "custom_name": "Newsletter Two"},
        ]

        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-27"
        )

        # Test text processing
        assert "HelloThis is an HTML newsletter." in full_text
        assert "This is a plain text newsletter." in full_text
        assert full_text.startswith("\n\nNewsletter from: Newsletter Two.")
        assert len(text_blocks) == 2

        # Test that modify() was called to mark the email as read
        mock_modify_call = mock_gmail_service.users().messages().modify

        # It should be called exactly once, for msg1 which was UNREAD.
        mock_modify_call.assert_called_once_with(
            userId="me", id="msg1", body={"removeLabelIds": ["UNREAD"]}
        )

    def test_process_emails_with_parsing_error(
        self, mock_gmail_service, mock_email_data, caplog
    ):
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg3"}]
        }
        mock_gmail_service.users().messages().get().execute.return_value = (
            mock_email_data[2]
        )
        sources = [
            {"sender_email": "sender3@example.com", "custom_name": "Bad Newsletter"}
        ]
        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-27"
        )
        assert "Bad Newsletter could not be processed" in full_text
        assert text_blocks[0]["title"] == "Bad Newsletter (Error)"
        assert "Failed to parse email from Bad Newsletter" in caplog.text

    def test_process_emails_no_matching_emails(self, mock_gmail_service):
        mock_gmail_service.users().messages().list().execute.return_value = {}
        sources = [
            {"sender_email": "sender1@example.com", "custom_name": "Newsletter One"}
        ]
        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-27"
        )
        assert full_text == ""
        assert text_blocks == []


class TestHelperFunctions:
    def test_remove_markdown_links(self):
        text = "Check [this link](http://a.com) and [another one](http://b.com)."
        expected = "Check this link and another one."
        assert ga.remove_markdown_links(text) == expected
        assert ga.remove_markdown_links("No links here.") == "No links here."

    @pytest.mark.parametrize(
        "chunk, max_len, expected_count",
        [
            ("Short clean sentence.", 250, 1),
            ("Sentence with a url https://example.com to remove.", 250, 1),
            ("", 250, 0),
            ("https://just-a-url.com", 250, 0),
            ("a " * 100, 50, 4),
            ("longword" * 10, 50, 2),
        ],
    )
    def test_validate_and_process_chunk(self, chunk, max_len, expected_count):
        result = ga.validate_and_process_chunk(chunk, max_len=max_len)
        assert len(result) == expected_count
        for sub_chunk in result:
            assert len(sub_chunk) <= max_len


class TestAudioAndMetadata:
    def test__create_chapter_list(self):
        text_blocks = [
            {"title": "Intro", "text": "a" * 25},
            {"title": "Middle", "text": "b" * 50},
            {"title": "End", "text": "c" * 25},
        ]
        total_duration_ms = 100000  # 100 seconds
        chapters = ga._create_chapter_list(total_duration_ms, text_blocks)
        assert len(chapters) == 3
        assert chapters[0] == {"title": "Intro", "start_time_ms": 0.0}
        assert chapters[1] == {"title": "Middle", "start_time_ms": 25000.0}
        assert chapters[2] == {"title": "End", "start_time_ms": 75000.0}

    def test__create_metadata(self):
        """
        Tests that metadata is created with the correct format,
        especially the chapters_json dictionary.
        """
        mock_segment = MagicMock()
        mock_segment.__len__.return_value = 123000  # 123 seconds
        text_blocks = [
            {"title": "Chapter 1", "text": "text..."},
            {"title": "Chapter 2", "text": "more text..."},
        ]

        # This predefined list is what we WANT _create_chapter_list to return.
        mock_chapter_list = [
            {"title": "Chapter 1", "start_time_ms": 0},
            {
                "title": "Chapter 2",
                "start_time_ms": 61500,
            },  # We want to test with 61.5s
        ]

        # --- FIX: Use `patch` to correctly mock the function ---
        # The target string should be 'module_alias._function_name'
        with patch(
            "generate_audiobook._create_chapter_list", return_value=mock_chapter_list
        ):
            # Inside this block, any call to ga._create_chapter_list will return our predefined list.
            metadata = ga._create_metadata("My Title", mock_segment, text_blocks)

        # The rest of the test remains the same, but will now pass.
        assert metadata["title"] == "My Title"
        assert metadata["duration_seconds"] == 123

        chapters_dict = json.loads(metadata["chapters_json"])
        expected_chapters = {
            "Chapter 1": 0,
            "Chapter 2": 61,  # 61500ms / 1000 = 61.5, cast to int is 61
        }
        assert chapters_dict == expected_chapters

    def test__create_metadata_for_chunk(self):
        """
        Tests that metadata for a chunk correctly calculates relative
        chapter times and formats them as a dictionary.
        """
        mock_chunk_segment = MagicMock()
        mock_chunk_segment.__len__.return_value = 50000  # 50s
        original_chapters = [
            {"title": "Chap 1", "start_time_ms": 0},
            {"title": "Chap 2", "start_time_ms": 30000},
            {"title": "Chap 3", "start_time_ms": 60000},
            {"title": "Chap 4", "start_time_ms": 90000},
        ]
        chunk_start_ms = 40000

        metadata = ga._create_metadata_for_chunk(
            "My Title (Part 2)", mock_chunk_segment, original_chapters, chunk_start_ms
        )

        assert metadata["title"] == "My Title (Part 2)"
        assert metadata["duration_seconds"] == 50

        chapters_dict = json.loads(metadata["chapters_json"])

        expected_chapters = {"Chap 3": 20}

        assert chapters_dict == expected_chapters

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    @patch("generate_audiobook.os.makedirs")
    def test_generate_audio_creates_archive_folder(
        self, m_makedirs, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment
    ):
        """Test that the archive folder is created when it doesn't exist."""
        mock_audio_segment.export.return_value.read.return_value = b"A" * (1024 * 1024)
        config = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "path/to/voice.wav",
        }
        
        ga.generate_and_upload_audio("text", [{"title": "t", "text": "t"}], config, "d")
        
        # Should create the archive folder with exist_ok=True
        m_makedirs.assert_called_once_with(ga.ARCHIVE_FOLDER, exist_ok=True)

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    @patch("generate_audiobook.os.makedirs")
    def test_generate_audio_logs_archive_folder_ready(
        self, m_makedirs, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment, caplog
    ):
        """Test that the function logs when the archive folder is ready."""
        mock_audio_segment.export.return_value.read.return_value = b"A" * (1024 * 1024)
        config = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "path/to/voice.wav",
        }
        
        with caplog.at_level(logging.INFO):
            ga.generate_and_upload_audio("text", [{"title": "t", "text": "t"}], config, "d")
        
        # Should log that the archive folder is ready
        assert f"Archive folder ready: {ga.ARCHIVE_FOLDER}" in caplog.text

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    def test_generate_audio_uses_archive_folder_for_single_file(
        self, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment
    ):
        """Test that single MP3 files are saved to the archive folder."""
        mock_audio_segment.export.return_value.read.return_value = b"A" * (1024 * 1024)
        config = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "path/to/voice.wav",
        }
        
        files_created = ga.generate_and_upload_audio("text", [{"title": "t", "text": "t"}], config, "d")
        
        # Check that the file path includes the archive folder
        expected_filepath = os.path.join(ga.ARCHIVE_FOLDER, "digest_d.mp3")
        assert expected_filepath in files_created
        
        # Check that upload was called with the correct filepath
        m_upload.assert_called_once()
        call_args = m_upload.call_args
        assert call_args[0][2] == expected_filepath  # filepath is the third argument

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    def test_generate_audio_uses_archive_folder_for_chunked_files(
        self, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment
    ):
        """Test that chunked MP3 files are saved to the archive folder."""
        mock_audio_segment.__len__.return_value = 300000
        mock_audio_segment.export.return_value.read.return_value = b"A" * int(
            ga.MAX_UPLOAD_SIZE_MB * 1.5 * 1024 * 1024
        )
        mock_audio_segment.__getitem__.return_value = mock_audio_segment
        config = {"api_url": "url", "api_key": "key", "reference_voice_file": "v.wav"}
        date_str = "2023-01-01"

        files_created = ga.generate_and_upload_audio(
            "text", [{"title": "t", "text": "t"}], config, date_str
        )
        
        # Check that chunk files are in the archive folder
        expected_part1 = os.path.join(ga.ARCHIVE_FOLDER, "digest_2023-01-01_part_1_of_2.mp3")
        expected_part2 = os.path.join(ga.ARCHIVE_FOLDER, "digest_2023-01-01_part_2_of_2.mp3")
        
        assert expected_part1 in files_created
        assert expected_part2 in files_created
        
        # Check that uploads were called with correct filepaths
        assert m_upload.call_count == 2
        upload_calls = m_upload.call_args_list
        assert upload_calls[0][0][2] == expected_part1  # filepath is the third argument
        assert upload_calls[1][0][2] == expected_part2

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    def test_generate_audio_uses_reference_voice(
        self, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment
    ):
        mock_audio_segment.export.return_value.read.return_value = b"A" * (1024 * 1024)
        config = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "path/to/voice.wav",
        }
        ga.generate_and_upload_audio("text", [{"title": "t", "text": "t"}], config, "d")
        mock_tts_client.tts.assert_any_call(
            text=ANY, language="en", speaker_wav="path/to/voice.wav"
        )
        m_upload.assert_called_once()

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=False)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    def test_generate_audio_uses_default_speaker(
        self, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment
    ):
        mock_audio_segment.export.return_value.read.return_value = b"A" * (1024 * 1024)
        config = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "path/that/does/not/exist.wav",
        }
        ga.generate_and_upload_audio("text", [{"title": "t", "text": "t"}], config, "d")
        mock_tts_client.tts.assert_any_call(
            text=ANY, language="en", speaker=ga.DEFAULT_SPEAKER
        )
        m_upload.assert_called_once()

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    def test_generate_and_upload_chunked_files(
        self, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment
    ):
        mock_audio_segment.__len__.return_value = 300000
        mock_audio_segment.export.return_value.read.return_value = b"A" * int(
            ga.MAX_UPLOAD_SIZE_MB * 1.5 * 1024 * 1024
        )
        mock_audio_segment.__getitem__.return_value = mock_audio_segment
        config = {"api_url": "url", "api_key": "key", "reference_voice_file": "v.wav"}
        date_str = "2023-01-01"

        files_created = ga.generate_and_upload_audio(
            "text", [{"title": "t", "text": "t"}], config, date_str
        )
        base_name = f"digest_{date_str}"
        part1_name = os.path.join(ga.ARCHIVE_FOLDER, f"{base_name}_part_1_of_2.mp3")
        part2_name = os.path.join(ga.ARCHIVE_FOLDER, f"{base_name}_part_2_of_2.mp3")

        assert m_upload.call_count == 2
        # Check call arguments for both chunk uploads
        m_upload.assert_has_calls(
            [call(ANY, ANY, part1_name, ANY), call(ANY, ANY, part2_name, ANY)],
            any_order=False,
        )
        # Check returned list of files for cleanup
        assert len(files_created) == 3
        assert ga.TEMP_WAV_FILE in files_created
        assert part1_name in files_created
        assert part2_name in files_created

    def test_generate_audio_empty_text(self, caplog):
        with caplog.at_level(logging.INFO):
            files = ga.generate_and_upload_audio("   ", [], {}, "d")
        assert "No text content to synthesize" in caplog.text
        assert files == []

    @patch("generate_audiobook.upload_audiobook", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy_wav_data")
    def test_generate_audio_skips_chunks_exceeding_token_limit(
        self, m_open, m_exists, m_upload, mock_tts_client, mock_audio_segment, caplog
    ):
        """
        Tests that chunks exceeding the XTTS token limit are skipped and a warning is logged.
        """
        # This chunk is valid and should be processed
        valid_chunk = "This is a perfectly fine sentence."
        # This chunk is deliberately long and will exceed the token limit
        long_chunk = "s=88570519&lid=7618&elqTrackId=a761f708238e42158dbf78a26dc7fb52&elq=9fbf84b5718945219f0937c3adab8d8d&elqaid=4566&elqat=1" * 10

        # Mock the sentence splitter to return our specific chunks
        mock_tts_client.synthesizer.split_into_sentences.return_value = [valid_chunk, long_chunk]

        # Mock the tokenizer's encode method to return token lists of different lengths
        # The first call (for valid_chunk) returns a short list.
        # The second call (for long_chunk) returns a list longer than the limit.
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = [
            [1, 2, 3],          # Represents tokens for valid_chunk
            [0] * 500,          # Represents tokens for long_chunk (over the limit)
        ]
        mock_tts_client.synthesizer.tts_model.tokenizer = mock_tokenizer

        config = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "v.wav",
        }

        with caplog.at_level(logging.WARNING):
            ga.generate_and_upload_audio(
                f"{valid_chunk}\n{long_chunk}", [{"title": "t", "text": "t"}], config, "d"
            )

        # 1. Assert that the TTS synthesis function was only called ONCE (for the valid chunk)
        mock_tts_client.tts.assert_called_once()

        # 2. Assert that the call was made with the correct, valid text
        mock_tts_client.tts.assert_called_with(
            text=valid_chunk, language="en", speaker_wav="v.wav"
        )

        # 3. Assert that the warning for skipping the long chunk was logged
        assert "SKIPPING CHUNK: Text is too long for TTS model" in caplog.text
        assert f"({500} tokens > {390})" in caplog.text


class TestMainExecution:
    @pytest.fixture(autouse=True)
    def mock_main_dependencies(self, mocker):
        """Mock all external dependencies for main function."""
        mocker.patch("generate_audiobook.setup_logging")
        mocker.patch(
            "generate_audiobook.load_config",
            return_value={
                "api_url": "url",
                "api_key": "key",
                "token_file": "t",
                "credentials_file": "c",
                "reference_voice_file": "v.wav",
            },
        )
        mocker.patch("generate_audiobook.verify_authentication", return_value=True)
        mocker.patch("generate_audiobook.initialize_tts_model")
        mocker.patch("generate_audiobook.fetch_sources", return_value=[{"id": 1}])
        mocker.patch("generate_audiobook.authenticate_gmail")
        mocker.patch("googleapiclient.discovery.build")
        self.mock_process_emails = mocker.patch(
            "generate_audiobook.process_emails",
            return_value=("text", [{"text": "block"}]),
        )
        self.mock_gen_upload = mocker.patch(
            "generate_audiobook.generate_and_upload_audio", return_value=["file1.mp3"]
        )
        self.mock_cleanup = mocker.patch("generate_audiobook.cleanup")
        self.mock_remove_links = mocker.patch(
            "generate_audiobook.remove_markdown_links", side_effect=lambda x: x
        )
        self.mock_check_existing = mocker.patch(
            "generate_audiobook.check_existing_audiobook", return_value=False
        )

    @pytest.mark.parametrize(
        "argv, expected_dates",
        [
            (["script", "--date", "2023-05-10"], ["2023-05-10"]),
            (
                ["script", "--start-date", "2023-05-10", "--end-date", "2023-05-11"],
                ["2023-05-10", "2023-05-11"],
            ),
        ],
    )
    def test_main_date_args_success(self, monkeypatch, argv, expected_dates):
        monkeypatch.setattr(ga.sys, "argv", argv)
        ga.main()

        assert self.mock_check_existing.call_count == len(expected_dates)
        assert self.mock_process_emails.call_count == len(expected_dates)
        assert self.mock_gen_upload.call_count == len(expected_dates)
        assert self.mock_cleanup.call_count == len(expected_dates)

        for i, expected_date in enumerate(expected_dates):
            expected_title = f"Daily Digest for {expected_date}"
            assert self.mock_check_existing.call_args_list[i].args[2] == expected_title
            assert self.mock_process_emails.call_args_list[i].args[2] == expected_date
            assert self.mock_gen_upload.call_args_list[i].args[3] == expected_date
            assert self.mock_cleanup.call_args_list[i].args[0] == ["file1.mp3"]

    def test_main_skips_existing_audiobook(self, monkeypatch, caplog):
        """Test that main skips processing when an audiobook already exists."""
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_check_existing.return_value = True  # Simulate existing audiobook
        
        with caplog.at_level(logging.INFO):
            ga.main()
        
        # Should check for existing audiobook
        self.mock_check_existing.assert_called_once_with("url", "key", "Daily Digest for 2023-05-10")
        
        # Should skip processing and generation
        self.mock_process_emails.assert_not_called()
        self.mock_gen_upload.assert_not_called()
        self.mock_cleanup.assert_called_once_with([])
        
        assert "Skipping 2023-05-10 - audiobook already exists." in caplog.text

    def test_main_no_content_for_date(self, monkeypatch):
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_process_emails.return_value = ("  ", [])  # No content
        ga.main()
        self.mock_process_emails.assert_called_once_with(ANY, ANY, "2023-05-10")
        self.mock_gen_upload.assert_not_called()
        self.mock_cleanup.assert_called_once_with([])

    def test_main_invalid_date_format(self, monkeypatch, caplog):
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023/05/10"])
        with pytest.raises(SystemExit):
            ga.main()
        assert "Invalid date format" in caplog.text

    def test_main_start_after_end_date(self, monkeypatch, caplog):
        monkeypatch.setattr(
            ga.sys,
            "argv",
            ["script", "--start-date", "2023-05-11", "--end-date", "2023-05-10"],
        )
        with pytest.raises(SystemExit):
            ga.main()
        assert (
            "Start date (2023-05-11) cannot be after end date (2023-05-10)"
            in caplog.text
        )

    def test_main_mixed_existing_and_new_audiobooks(self, monkeypatch, caplog):
        """Test that main handles a mix of existing and new audiobooks correctly."""
        monkeypatch.setattr(ga.sys, "argv", ["script", "--start-date", "2023-05-10", "--end-date", "2023-05-11"])
        
        # First date exists, second date doesn't
        self.mock_check_existing.side_effect = [True, False]
        
        with caplog.at_level(logging.INFO):
            ga.main()
        
        # Should check for both dates
        assert self.mock_check_existing.call_count == 2
        assert self.mock_check_existing.call_args_list[0].args[2] == "Daily Digest for 2023-05-10"
        assert self.mock_check_existing.call_args_list[1].args[2] == "Daily Digest for 2023-05-11"
        
        # Should only process the second date (first was skipped)
        self.mock_process_emails.assert_called_once_with(ANY, ANY, "2023-05-11")
        self.mock_gen_upload.assert_called_once_with(ANY, ANY, ANY, "2023-05-11")
        assert self.mock_cleanup.call_count == 2  # Called for both dates (even if empty)
        
        assert "Skipping 2023-05-10 - audiobook already exists." in caplog.text


class TestCleanup:
    @patch("generate_audiobook.unpin_file_from_onedrive")
    @patch("generate_audiobook.os.remove")
    @patch("generate_audiobook.os.path.exists", return_value=True)
    def test_cleanup_handles_file_types_correctly(self, m_exists, m_remove, m_unpin):
        files_to_clean = ["audio.mp3", "temp.wav", "unknown.txt"]
        ga.cleanup(files_to_clean)

        m_exists.assert_has_calls(
            [call("audio.mp3"), call("temp.wav"), call("unknown.txt")]
        )
        m_remove.assert_called_once_with("temp.wav")
        m_unpin.assert_called_once_with(Path("audio.mp3"))

    @patch("generate_audiobook.unpin_file_from_onedrive")
    @patch("generate_audiobook.os.remove")
    @patch("generate_audiobook.os.path.exists", return_value=True)
    def test_cleanup_handles_archive_folder_files(self, m_exists, m_remove, m_unpin):
        """Test that cleanup handles MP3 files in the archive folder correctly."""
        archive_mp3_file = os.path.join(ga.ARCHIVE_FOLDER, "digest_2023-01-01.mp3")
        files_to_clean = [archive_mp3_file, "temp.wav"]
        ga.cleanup(files_to_clean)

        m_exists.assert_has_calls(
            [call(archive_mp3_file), call("temp.wav")]
        )
        m_remove.assert_called_once_with("temp.wav")
        m_unpin.assert_called_once_with(Path(archive_mp3_file))

    @patch("generate_audiobook.os.remove", side_effect=OSError("Permission denied"))
    @patch("generate_audiobook.os.path.exists", return_value=True)
    def test_cleanup_handles_remove_error(self, m_exists, m_remove, caplog):
        files = ["bad_file.wav"]
        with caplog.at_level(logging.ERROR):
            ga.cleanup(files)
        assert (
            "Could not process temporary file bad_file.wav: Permission denied"
            in caplog.text
        )

    @patch("generate_audiobook.subprocess.run")
    def test_unpin_success(self, mock_run, caplog):
        test_path = Path("my_file.mp3")
        with caplog.at_level(logging.INFO):
            ga.unpin_file_from_onedrive(test_path)

        mock_run.assert_called_once_with(
            ["attrib", "+U", "-P", str(test_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert f"Successfully unpinned '{test_path}'" in caplog.text

    @patch("generate_audiobook.subprocess.run", side_effect=FileNotFoundError)
    def test_unpin_attrib_not_found(self, mock_run, caplog):
        test_path = Path("my_file.mp3")
        with caplog.at_level(logging.ERROR):
            ga.unpin_file_from_onedrive(test_path)
        assert "The 'attrib' command was not found." in caplog.text

    @patch("generate_audiobook.subprocess.run")
    def test_unpin_subprocess_error(self, mock_run, caplog):
        test_path = Path("my_file.mp3")
        error = subprocess.CalledProcessError(
            returncode=1, cmd="attrib", stderr="Access denied."
        )
        mock_run.side_effect = error

        with caplog.at_level(logging.ERROR):
            ga.unpin_file_from_onedrive(test_path)

        assert f"Failed to execute 'attrib' command for '{test_path}'" in caplog.text
        assert "Access denied." in caplog.text
