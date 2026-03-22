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
from googleapiclient.errors import HttpError

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
        m_file.assert_called_with("audiobook_generator.log", mode="w", encoding="utf-8")
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
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=200, json={"status": "ok"}
        )
        with patch("upload_mp3.AudioSegment.from_mp3") as mock_from_mp3:
            mock_audio = MagicMock()
            mock_audio.__len__.return_value = 1000
            mock_from_mp3.return_value = mock_audio

            with caplog.at_level(logging.INFO):
                result = ga.upload_audiobook(
                    "https://fake-api.com", "fake_key", str(filepath), "Test Title", []
                )

        assert result is True
        assert f"Preparing to upload '{filepath}'" in caplog.text
        assert "Upload successful. Server response:" in caplog.text

    def test_upload_audiobook_http_error(self, requests_mock, tmp_path, caplog):
        filepath = tmp_path / "test.mp3"
        filepath.write_text("mp3_data")
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=400, text="Bad Request"
        )
        with patch("upload_mp3.AudioSegment.from_mp3") as mock_from_mp3:
            mock_audio = MagicMock()
            mock_audio.__len__.return_value = 1000
            mock_from_mp3.return_value = mock_audio

            with caplog.at_level(logging.ERROR):
                result = ga.upload_audiobook(
                    "https://fake-api.com", "fake_key", str(filepath), "Test Title", []
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
            "upload_mp3._create_chapter_list", return_value=mock_chapter_list
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

    def test_generate_and_upload_audio_hybrid_empty_text(self, caplog):
        """Test that hybrid workflow returns empty list for blank text."""
        with caplog.at_level(logging.WARNING):
            files = ga.generate_and_upload_audio_hybrid("   ", [], {}, "d")
        assert "No text content to process." in caplog.text
        assert files == []

    @patch("generate_audiobook.upload_audio")
    @patch("generate_audiobook.request_user_feedback")
    @patch("generate_audiobook.notify_user_of_full_text_readiness")
    def test_generate_and_upload_audio_hybrid_success(
        self, mock_notify, mock_feedback, mock_upload, caplog
    ):
        mock_notify.return_value = "/path/to/text.txt"
        mock_feedback.return_value = "/path/to/audio.mp3"
        mock_upload.return_value = True
        config = {"api_url": "url", "api_key": "key"}
        text_blocks = [{"title": "t", "text": "t"}]

        with caplog.at_level(logging.INFO):
            files = ga.generate_and_upload_audio_hybrid(
                "some text", text_blocks, config, "2023-01-01"
            )

        mock_notify.assert_called_once_with("some text", "2023-01-01")
        mock_feedback.assert_called_once_with("2023-01-01")
        mock_upload.assert_called_once_with(
            "/path/to/audio.mp3", config, "2023-01-01", text_blocks
        )
        assert files == ["/path/to/audio.mp3"]
        assert "Hybrid workflow completed successfully" in caplog.text

    @patch("generate_audiobook.upload_audio")
    @patch("generate_audiobook.request_user_feedback")
    @patch("generate_audiobook.notify_user_of_full_text_readiness")
    def test_generate_and_upload_audio_hybrid_no_mp3(
        self, mock_notify, mock_feedback, mock_upload, caplog
    ):
        mock_notify.return_value = "/path/to/text.txt"
        mock_feedback.return_value = None
        config = {"api_url": "url", "api_key": "key"}

        with caplog.at_level(logging.ERROR):
            files = ga.generate_and_upload_audio_hybrid(
                "some text", [{"title": "t", "text": "t"}], config, "2023-01-01"
            )

        assert files == []
        mock_upload.assert_not_called()
        assert "No MP3 file found" in caplog.text

    @patch("generate_audiobook.upload_audio")
    @patch("generate_audiobook.request_user_feedback")
    @patch("generate_audiobook.notify_user_of_full_text_readiness")
    def test_generate_and_upload_audio_hybrid_upload_failure(
        self, mock_notify, mock_feedback, mock_upload, caplog
    ):
        mock_notify.return_value = "/path/to/text.txt"
        mock_feedback.return_value = "/path/to/audio.mp3"
        mock_upload.return_value = False
        config = {"api_url": "url", "api_key": "key"}

        with caplog.at_level(logging.ERROR):
            files = ga.generate_and_upload_audio_hybrid(
                "some text", [{"title": "t", "text": "t"}], config, "2023-01-01"
            )

        assert files == []
        assert "Hybrid workflow failed during upload" in caplog.text


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
        mocker.patch("generate_audiobook.fetch_sources", return_value=[{"id": 1}])
        mocker.patch("generate_audiobook.authenticate_gmail")
        mocker.patch("googleapiclient.discovery.build")
        self.mock_process_content = mocker.patch(
            "generate_audiobook.process_emails_and_raw_content",
            return_value=("text", [{"text": "block"}]),
        )
        self.mock_gen_upload = mocker.patch(
            "generate_audiobook.generate_and_upload_audio_hybrid",
            return_value=["file1.mp3"],
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
        assert self.mock_process_content.call_count == len(expected_dates)
        assert self.mock_gen_upload.call_count == len(expected_dates)
        assert self.mock_cleanup.call_count == len(expected_dates)

        for i, expected_date in enumerate(expected_dates):
            expected_title = f"Daily Digest for {expected_date}"
            assert self.mock_check_existing.call_args_list[i].args[2] == expected_title
            assert self.mock_process_content.call_args_list[i].args[2] == expected_date
            assert self.mock_gen_upload.call_args_list[i].args[3] == expected_date
            assert self.mock_cleanup.call_args_list[i].args[0] == ["file1.mp3"]

    def test_main_skips_existing_audiobook(self, monkeypatch, caplog):
        """Test that main skips processing when an audiobook already exists."""
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_check_existing.return_value = True

        with caplog.at_level(logging.INFO):
            ga.main()

        self.mock_check_existing.assert_called_once_with(
            "url", "key", "Daily Digest for 2023-05-10"
        )
        self.mock_process_content.assert_not_called()
        self.mock_gen_upload.assert_not_called()

        assert "Skipping 2023-05-10 - audiobook already exists." in caplog.text

    def test_main_no_content_for_date(self, monkeypatch):
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_process_content.return_value = ("  ", [])
        ga.main()
        self.mock_process_content.assert_called_once_with(ANY, ANY, "2023-05-10")
        self.mock_gen_upload.assert_not_called()

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
        monkeypatch.setattr(
            ga.sys,
            "argv",
            ["script", "--start-date", "2023-05-10", "--end-date", "2023-05-11"],
        )
        self.mock_check_existing.side_effect = [True, False]

        with caplog.at_level(logging.INFO):
            ga.main()

        assert self.mock_check_existing.call_count == 2
        assert (
            self.mock_check_existing.call_args_list[0].args[2]
            == "Daily Digest for 2023-05-10"
        )
        assert (
            self.mock_check_existing.call_args_list[1].args[2]
            == "Daily Digest for 2023-05-11"
        )
        self.mock_process_content.assert_called_once_with(ANY, ANY, "2023-05-11")
        self.mock_gen_upload.assert_called_once_with(ANY, ANY, ANY, "2023-05-11")

        assert "Skipping 2023-05-10 - audiobook already exists." in caplog.text

    def test_main_exception_in_processing(self, monkeypatch, caplog):
        """Test that exceptions in processing are caught and loop continues."""
        monkeypatch.setattr(
            ga.sys,
            "argv",
            ["script", "--start-date", "2023-05-10", "--end-date", "2023-05-11"],
        )
        self.mock_process_content.side_effect = [
            Exception("processing failed"),
            ("text", [{"text": "block"}]),
        ]

        with caplog.at_level(logging.ERROR):
            ga.main()

        assert self.mock_process_content.call_count == 2
        assert "An error occurred while processing 2023-05-10" in caplog.text


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


class TestVerifyAuthentication:
    def test_success(self, requests_mock, caplog):
        requests_mock.get("https://fake-api.com/sources", status_code=200)
        with caplog.at_level(logging.INFO):
            result = ga.verify_authentication("https://fake-api.com", "fake_key")
        assert result is True
        assert "Authentication successful" in caplog.text

    def test_401_unauthorized(self, requests_mock, caplog):
        requests_mock.get("https://fake-api.com/sources", status_code=401)
        with caplog.at_level(logging.CRITICAL):
            result = ga.verify_authentication("https://fake-api.com", "fake_key")
        assert result is False
        assert "AUTHENTICATION FAILED" in caplog.text

    def test_other_status_code(self, requests_mock, caplog):
        requests_mock.get(
            "https://fake-api.com/sources", status_code=500, text="Error"
        )
        with caplog.at_level(logging.ERROR):
            result = ga.verify_authentication("https://fake-api.com", "fake_key")
        assert result is False
        assert "Pre-flight check failed with unexpected status code: 500" in caplog.text

    def test_network_error(self, requests_mock, caplog):
        requests_mock.get(
            "https://fake-api.com/sources",
            exc=requests.exceptions.ConnectionError("Connection failed"),
        )
        with caplog.at_level(logging.ERROR):
            result = ga.verify_authentication("https://fake-api.com", "fake_key")
        assert result is False
        assert "A network error occurred during the pre-flight check." in caplog.text


class TestFindLastUploadDate:
    def test_success(self, requests_mock, caplog):
        mock_audiobooks = [
            {"title": "Daily Digest for 2023-05-10"},
            {"title": "Daily Digest for 2023-05-08"},
        ]
        requests_mock.get("https://fake-api.com/audiobooks", json=mock_audiobooks)

        with caplog.at_level(logging.INFO):
            result = ga.find_last_upload_date("https://fake-api.com", "fake_key")

        assert result == datetime.date(2023, 5, 10)
        assert "Found last upload date: 2023-05-10" in caplog.text

    def test_non_200_status(self, requests_mock, caplog):
        requests_mock.get("https://fake-api.com/audiobooks", status_code=500)

        with caplog.at_level(logging.WARNING):
            result = ga.find_last_upload_date("https://fake-api.com", "fake_key")

        assert result is None
        assert "Using yesterday as default start date." in caplog.text

    def test_empty_audiobooks(self, requests_mock, caplog):
        requests_mock.get("https://fake-api.com/audiobooks", json=[])

        with caplog.at_level(logging.INFO):
            result = ga.find_last_upload_date("https://fake-api.com", "fake_key")

        assert result is None
        assert "No existing audiobooks found." in caplog.text

    def test_no_valid_dates_in_titles(self, requests_mock, caplog):
        mock_audiobooks = [
            {"title": "Some audiobook without date"},
            {"title": "Another one"},
        ]
        requests_mock.get("https://fake-api.com/audiobooks", json=mock_audiobooks)

        with caplog.at_level(logging.INFO):
            result = ga.find_last_upload_date("https://fake-api.com", "fake_key")

        assert result is None
        assert "No valid dates found" in caplog.text

    def test_invalid_date_value_in_title(self, requests_mock, caplog):
        """Test graceful handling of regex-matching but invalid dates."""
        mock_audiobooks = [{"title": "Daily Digest for 2023-13-45"}]
        requests_mock.get("https://fake-api.com/audiobooks", json=mock_audiobooks)

        with caplog.at_level(logging.WARNING):
            result = ga.find_last_upload_date("https://fake-api.com", "fake_key")

        assert result is None

    def test_network_error(self, requests_mock, caplog):
        requests_mock.get(
            "https://fake-api.com/audiobooks",
            exc=requests.exceptions.ConnectionError("fail"),
        )

        with caplog.at_level(logging.ERROR):
            result = ga.find_last_upload_date("https://fake-api.com", "fake_key")

        assert result is None
        assert "Error fetching audiobooks to find last upload date" in caplog.text


class TestProcessRawContentFiles:
    def test_folder_not_exists(self, tmp_path, monkeypatch, caplog):
        nonexistent = str(tmp_path / "nonexistent")
        monkeypatch.setattr(ga, "RAW_CONTENT_FOLDER", nonexistent)
        target = datetime.date(2023, 5, 10)

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_raw_content_files(target)

        assert text == ""
        assert blocks == []
        assert os.path.exists(nonexistent)
        assert "does not exist. Creating it." in caplog.text

    def test_no_txt_files(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(ga, "RAW_CONTENT_FOLDER", str(tmp_path))
        target = datetime.date(2023, 5, 10)

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_raw_content_files(target)

        assert text == ""
        assert blocks == []
        assert "No .txt files found" in caplog.text

    def test_matching_date_files(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(ga, "RAW_CONTENT_FOLDER", str(tmp_path))
        test_file = tmp_path / "test_content.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        ctime = os.path.getctime(str(test_file))
        target = datetime.datetime.fromtimestamp(ctime).date()

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_raw_content_files(target)

        assert len(blocks) == 1
        assert "test_content" in blocks[0]["title"]
        assert "Hello world" in text
        assert "Successfully processed raw content file" in caplog.text

    def test_no_matching_date(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(ga, "RAW_CONTENT_FOLDER", str(tmp_path))
        test_file = tmp_path / "test_content.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        target = datetime.date(2000, 1, 1)

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_raw_content_files(target)

        assert text == ""
        assert blocks == []
        assert "No raw content files found for 2000-01-01" in caplog.text

    def test_empty_file(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(ga, "RAW_CONTENT_FOLDER", str(tmp_path))
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        ctime = os.path.getctime(str(test_file))
        target = datetime.datetime.fromtimestamp(ctime).date()

        with caplog.at_level(logging.WARNING):
            text, blocks = ga.process_raw_content_files(target)

        assert blocks == []
        assert "Raw content file is empty" in caplog.text

    @patch("os.path.getctime", side_effect=OSError("access denied"))
    def test_os_error_on_getctime(self, mock_getctime, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(ga, "RAW_CONTENT_FOLDER", str(tmp_path))
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        target = datetime.date(2023, 5, 10)

        with caplog.at_level(logging.ERROR):
            text, blocks = ga.process_raw_content_files(target)

        assert blocks == []
        assert "Could not get creation time" in caplog.text


class TestProcessEmailsAndRawContent:
    @patch("generate_audiobook.process_raw_content_files")
    @patch("generate_audiobook.process_emails")
    def test_both_sources(self, mock_emails, mock_raw, caplog):
        mock_emails.return_value = ("email text", [{"text": "email", "title": "E"}])
        mock_raw.return_value = ("raw text", [{"text": "raw", "title": "R"}])

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_emails_and_raw_content(
                MagicMock(), [{"sender_email": "t@e.com", "custom_name": "T"}], "2023-05-10"
            )

        assert text == "email textraw text"
        assert len(blocks) == 2
        assert "Combined" in caplog.text

    @patch("generate_audiobook.process_raw_content_files")
    @patch("generate_audiobook.process_emails")
    def test_only_emails(self, mock_emails, mock_raw, caplog):
        mock_emails.return_value = ("email text", [{"text": "email", "title": "E"}])
        mock_raw.return_value = ("", [])

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_emails_and_raw_content(
                MagicMock(), [{"sender_email": "t@e.com", "custom_name": "T"}], "2023-05-10"
            )

        assert text == "email text"
        assert len(blocks) == 1
        assert "email source(s), no raw content files" in caplog.text

    @patch("generate_audiobook.process_raw_content_files")
    @patch("generate_audiobook.process_emails")
    def test_only_raw(self, mock_emails, mock_raw, caplog):
        mock_emails.return_value = ("", [])
        mock_raw.return_value = ("raw text", [{"text": "raw", "title": "R"}])

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_emails_and_raw_content(
                MagicMock(), [{"sender_email": "t@e.com", "custom_name": "T"}], "2023-05-10"
            )

        assert text == "raw text"
        assert len(blocks) == 1
        assert "raw content file(s), no email sources" in caplog.text

    @patch("generate_audiobook.process_raw_content_files")
    @patch("generate_audiobook.process_emails")
    def test_neither_found(self, mock_emails, mock_raw, caplog):
        mock_emails.return_value = ("", [])
        mock_raw.return_value = ("", [])

        with caplog.at_level(logging.INFO):
            text, blocks = ga.process_emails_and_raw_content(
                MagicMock(), [{"sender_email": "t@e.com", "custom_name": "T"}], "2023-05-10"
            )

        assert text == ""
        assert blocks == []
        assert "No email sources or raw content files found" in caplog.text


class TestNotifyAndUpload:
    def test_notify_user_of_full_text_readiness(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(ga, "CLEANED_TEXT_FOLDER", str(tmp_path))

        with caplog.at_level(logging.INFO):
            result = ga.notify_user_of_full_text_readiness("test content", "2023-01-01")

        assert os.path.exists(result)
        with open(result, "r", encoding="utf-8") as f:
            assert f.read() == "test content"
        assert "Cleaned text saved to" in caplog.text
        assert "digest_2023-01-01_cleaned.txt" in result

    @patch("generate_audiobook.upload_audiobook")
    def test_upload_audio_success(self, mock_upload, caplog):
        mock_upload.return_value = True
        config = {"api_url": "url", "api_key": "key"}
        text_blocks = [{"title": "t", "text": "t"}]

        with caplog.at_level(logging.INFO):
            result = ga.upload_audio("/path/to/file.mp3", config, "2023-01-01", text_blocks)

        assert result is True
        mock_upload.assert_called_once_with(
            "url", "key", "/path/to/file.mp3", "Daily Digest for 2023-01-01", text_blocks
        )
        assert "Upload completed successfully" in caplog.text

    @patch("generate_audiobook.upload_audiobook")
    def test_upload_audio_failure(self, mock_upload, caplog):
        mock_upload.return_value = False
        config = {"api_url": "url", "api_key": "key"}

        with caplog.at_level(logging.ERROR):
            result = ga.upload_audio("/path/to/file.mp3", config, "2023-01-01", [])

        assert result is False
        assert "Upload failed" in caplog.text

    @patch("generate_audiobook.upload_audiobook", side_effect=Exception("boom"))
    def test_upload_audio_exception(self, mock_upload, caplog):
        config = {"api_url": "url", "api_key": "key"}

        with caplog.at_level(logging.ERROR):
            result = ga.upload_audio("/path/to/file.mp3", config, "2023-01-01", [])

        assert result is False
        assert "Upload error" in caplog.text

    @patch("shutil.move")
    @patch("generate_audiobook.time.sleep")
    def test_request_user_feedback_found_immediately(
        self, mock_sleep, mock_move, tmp_path, monkeypatch
    ):
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        expected = downloads / "digest_2023-01-01_cleaned_generated_audio.mp3"
        expected.write_text("mp3")

        archive_dir = tmp_path / "archive"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ga, "ARCHIVE_FOLDER", str(archive_dir))

        result = ga.request_user_feedback("2023-01-01")

        mock_sleep.assert_not_called()
        assert result is not None

    @patch("shutil.move", side_effect=Exception("move failed"))
    @patch("generate_audiobook.time.sleep")
    def test_request_user_feedback_move_failure(
        self, mock_sleep, mock_move, tmp_path, monkeypatch, caplog
    ):
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        expected = downloads / "digest_2023-01-01_cleaned_generated_audio.mp3"
        expected.write_text("mp3")

        archive_dir = tmp_path / "archive"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(ga, "ARCHIVE_FOLDER", str(archive_dir))

        with caplog.at_level(logging.ERROR):
            result = ga.request_user_feedback("2023-01-01")

        assert result is None
        assert "Failed to move MP3 file" in caplog.text


class TestAdditionalGmailCoverage:
    @patch("generate_audiobook.Credentials.from_authorized_user_file")
    @patch("generate_audiobook.os.path.exists", return_value=True)
    def test_authenticate_gmail_token_valid(self, m_exists, m_creds):
        mock_creds = MagicMock()
        mock_creds.valid = True
        m_creds.return_value = mock_creds

        result = ga.authenticate_gmail("token.json", "creds.json")

        assert result == mock_creds
        m_creds.assert_called_once_with("token.json", ga.SCOPES)

    @patch("builtins.open", new_callable=mock_open)
    @patch("generate_audiobook.Credentials.from_authorized_user_file")
    @patch("generate_audiobook.os.path.exists", return_value=True)
    def test_authenticate_gmail_token_expired_refresh(self, m_exists, m_creds, m_open):
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token_value"
        m_creds.return_value = mock_creds

        result = ga.authenticate_gmail("token.json", "creds.json")

        mock_creds.refresh.assert_called_once()
        assert result == mock_creds

    @patch("builtins.open", new_callable=mock_open)
    @patch("generate_audiobook.InstalledAppFlow.from_client_secrets_file")
    @patch("generate_audiobook.Credentials.from_authorized_user_file")
    @patch("generate_audiobook.os.path.exists")
    def test_authenticate_gmail_no_token_new_flow(self, m_exists, m_creds, m_flow, m_open):
        m_exists.side_effect = [False, True]
        mock_new_creds = MagicMock()
        m_flow.return_value.run_local_server.return_value = mock_new_creds

        result = ga.authenticate_gmail("token.json", "creds.json")

        m_creds.assert_not_called()
        m_flow.assert_called_once_with("creds.json", ga.SCOPES)
        assert result == mock_new_creds

    def test_process_emails_empty_sources(self):
        """Empty sources list should return early."""
        full_text, text_blocks = ga.process_emails(MagicMock(), [], "2023-10-27")
        assert full_text == ""
        assert text_blocks == []

    def test_process_emails_http_error_on_list(self, caplog):
        """HttpError on listing emails should return empty."""
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Server Error"
        )
        sources = [{"sender_email": "s@e.com", "custom_name": "Test"}]

        with caplog.at_level(logging.ERROR):
            full_text, text_blocks = ga.process_emails(mock_service, sources, "2023-10-27")

        assert full_text == ""
        assert text_blocks == []
        assert "An error occurred fetching emails" in caplog.text

    def test_process_emails_mark_as_read_http_error(self, caplog):
        """HttpError when marking email as read should log warning and continue."""
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        text_content = "Newsletter content"
        mock_msg = {
            "id": "msg1",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sender <sender@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
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
        mock_service.users().messages().get().execute.return_value = mock_msg
        mock_service.users().messages().modify().execute.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Error"
        )
        sources = [{"sender_email": "sender@example.com", "custom_name": "Test"}]

        with caplog.at_level(logging.WARNING):
            full_text, text_blocks = ga.process_emails(mock_service, sources, "2023-10-27")

        assert "Newsletter content" in full_text
        assert "Could not mark email msg1 as read" in caplog.text


class TestAdditionalCleanupCoverage:
    def test_cleanup_empty_list(self):
        """Cleanup with empty list returns immediately."""
        ga.cleanup([])  # Should not raise

    def test_cleanup_none(self):
        """Cleanup with None returns immediately."""
        ga.cleanup(None)  # Should not raise

    @patch("generate_audiobook.os.path.exists", return_value=False)
    def test_cleanup_file_not_found(self, m_exists, caplog):
        with caplog.at_level(logging.WARNING):
            ga.cleanup(["nonexistent.wav"])
        assert "File not found for cleanup" in caplog.text

    @patch("generate_audiobook.os.remove")
    @patch("generate_audiobook.sys")
    def test_unpin_non_windows(self, mock_sys, mock_remove, caplog):
        mock_sys.platform = "linux"
        test_path = Path("my_file.mp3")
        with caplog.at_level(logging.INFO):
            ga.unpin_file_from_onedrive(test_path)
        mock_remove.assert_called_once_with(test_path)


class TestMainDefaultDateLogic:
    """Tests for the main function's default date handling."""

    @pytest.fixture(autouse=True)
    def mock_main_deps(self, mocker):
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
        mocker.patch("generate_audiobook.fetch_sources", return_value=[{"id": 1}])
        mocker.patch("generate_audiobook.authenticate_gmail")
        mocker.patch("googleapiclient.discovery.build")
        self.mock_process_content = mocker.patch(
            "generate_audiobook.process_emails_and_raw_content",
            return_value=("text", [{"text": "block"}]),
        )
        self.mock_gen_upload = mocker.patch(
            "generate_audiobook.generate_and_upload_audio_hybrid",
            return_value=["file1.mp3"],
        )
        mocker.patch("generate_audiobook.cleanup")
        mocker.patch(
            "generate_audiobook.remove_markdown_links", side_effect=lambda x: x
        )
        mocker.patch("generate_audiobook.check_existing_audiobook", return_value=False)
        self.mock_find_last_upload = mocker.patch(
            "generate_audiobook.find_last_upload_date"
        )

    def test_default_with_last_upload(self, monkeypatch):
        """When no dates specified, use day after last upload as start."""
        monkeypatch.setattr(ga.sys, "argv", ["script"])
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.mock_find_last_upload.return_value = yesterday - datetime.timedelta(days=2)

        ga.main()

        self.mock_find_last_upload.assert_called_once()
        assert self.mock_process_content.call_count == 2

    def test_default_no_previous_uploads(self, monkeypatch):
        """When no previous uploads found, process just yesterday."""
        monkeypatch.setattr(ga.sys, "argv", ["script"])
        self.mock_find_last_upload.return_value = None

        ga.main()

        assert self.mock_process_content.call_count == 1

    def test_default_recent_upload(self, monkeypatch, caplog):
        """When last upload is today, nothing new to process."""
        monkeypatch.setattr(ga.sys, "argv", ["script"])
        self.mock_find_last_upload.return_value = datetime.date.today()

        with caplog.at_level(logging.INFO):
            ga.main()

        self.mock_process_content.assert_not_called()
        assert "No new dates to process" in caplog.text


class TestMainEdgeCases:
    @pytest.fixture(autouse=True)
    def mock_main_deps(self, mocker):
        mocker.patch("generate_audiobook.setup_logging")
        self.mock_load_config = mocker.patch(
            "generate_audiobook.load_config",
            return_value={
                "api_url": "url",
                "api_key": "key",
                "token_file": "t",
                "credentials_file": "c",
                "reference_voice_file": "v.wav",
            },
        )
        self.mock_verify_auth = mocker.patch(
            "generate_audiobook.verify_authentication"
        )
        self.mock_fetch_sources = mocker.patch("generate_audiobook.fetch_sources")
        mocker.patch("generate_audiobook.authenticate_gmail")
        mocker.patch("googleapiclient.discovery.build")
        mocker.patch(
            "generate_audiobook.process_emails_and_raw_content",
            return_value=("text", [{"text": "block"}]),
        )
        mocker.patch(
            "generate_audiobook.generate_and_upload_audio_hybrid", return_value=[]
        )
        mocker.patch("generate_audiobook.cleanup")
        mocker.patch(
            "generate_audiobook.remove_markdown_links", side_effect=lambda x: x
        )
        mocker.patch("generate_audiobook.check_existing_audiobook", return_value=False)

    def test_auth_fails(self, monkeypatch):
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_verify_auth.return_value = False

        with pytest.raises(SystemExit):
            ga.main()

    def test_no_sources(self, monkeypatch, caplog):
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_verify_auth.return_value = True
        self.mock_fetch_sources.return_value = []

        with caplog.at_level(logging.INFO):
            ga.main()

        assert "No sources returned from API. Exiting." in caplog.text

    def test_fatal_error_in_main(self, monkeypatch, caplog):
        monkeypatch.setattr(ga.sys, "argv", ["script", "--date", "2023-05-10"])
        self.mock_verify_auth.return_value = True
        self.mock_fetch_sources.side_effect = RuntimeError("fatal crash")

        with caplog.at_level(logging.CRITICAL):
            with pytest.raises(SystemExit):
                ga.main()

        assert "A fatal, non-recoverable error occurred" in caplog.text
