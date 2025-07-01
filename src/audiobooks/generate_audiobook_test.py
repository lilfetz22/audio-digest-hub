import pytest
import os
import configparser
import json
import base64
import logging
from unittest.mock import MagicMock, patch, mock_open

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
        "SUPABASE_ANON_KEY": "fake_supabase_key",  # Added new key
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
    # Also mock the setup_logging to avoid creating log files during tests
    monkeypatch.setattr(ga, "setup_logging", lambda: None)


@pytest.fixture
def mock_tts_client(mocker):
    """Mocks the global TTS_CLIENT and its methods."""
    mock_client = MagicMock()
    mocker.patch.object(ga, "TTS_CLIENT", mock_client)
    return mock_client


@pytest.fixture
def mock_email_data():
    """Provides mock email data for parsing tests."""
    text_content = "This is a plain text newsletter."
    html_content = "<h1>Hello</h1><p>This is an HTML newsletter.</p>"

    mock_msg_1 = {
        "id": "msg1",
        "payload": {
            "headers": [
                {"name": "From", "value": "Test Sender 1 <sender1@example.com>"}
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
    mock_msg_2 = {
        "id": "msg2",
        "payload": {
            "headers": [
                {"name": "From", "value": "Test Sender 2 <sender2@example.com>"}
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
    return [mock_msg_1, mock_msg_2]


@pytest.fixture
def mock_simple_email_data():
    """Provides mock email data for a non-multipart email."""
    text_content = "This is a simple body email."
    return [
        {
            "id": "msg_simple",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Simple Sender <simple@example.com>"}
                ],
                "body": {
                    "data": base64.urlsafe_b64encode(
                        text_content.encode("utf-8")
                    ).decode("ascii")
                },
            },
        }
    ]


# --- Test Classes ---


class TestConfig:
    def test_load_config_success(self, mock_config_file):
        config = ga.load_config(mock_config_file)
        assert config["api_url"] == "https://fake-api.com"
        assert config["api_key"] == "fake_api_key"
        assert config["supabase_anon_key"] == "fake_supabase_key"  # Check new key
        assert config["credentials_file"] == "fake_credentials.json"
        assert config["reference_voice_file"] == "path/to/fake_voice.wav"

    def test_load_config_file_not_found(self, caplog):
        with pytest.raises(SystemExit):
            ga.load_config("non_existent_file.ini")
        assert "Configuration file 'non_existent_file.ini' not found" in caplog.text

    def test_load_config_missing_key(self, tmp_path, caplog):
        config_path = tmp_path / "invalid_config.ini"
        config_path.write_text(
            "[WebApp]\nAPI_URL = https://fake-api.com\nAPI_KEY=key\n"
        )  # Missing supabase key
        with pytest.raises(SystemExit):
            ga.load_config(str(config_path))
        # Check for the new, more detailed error message
        assert "Missing key in config.ini: 'SUPABASE_ANON_KEY'" in caplog.text
        assert "Ensure API_URL, API_KEY, and SUPABASE_ANON_KEY" in caplog.text


class TestTTSInitialization:
    # No changes needed in this class, it remains the same.
    @patch("generate_audiobook.torch.cuda.is_available", return_value=True)
    @patch("generate_audiobook.TTS")
    def test_initialize_tts_model_with_cuda(self, mock_tts, mock_cuda, caplog):
        ga.TTS_CLIENT = None
        with caplog.at_level(logging.INFO):
            ga.initialize_tts_model()
        mock_cuda.assert_called_once()
        mock_tts.assert_called_with(ga.TTS_MODEL)
        mock_tts.return_value.to.assert_called_with("cuda")
        assert "Using device: cuda" in caplog.text
        assert ga.TTS_CLIENT is not None


class TestGmailAuth:
    # No changes needed in this class, it remains the same.
    @patch("generate_audiobook.Credentials")
    def test_authenticate_gmail_token_valid(self, mock_creds, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        mock_creds.from_authorized_user_file.return_value.valid = True
        creds = ga.authenticate_gmail("token.json", "creds.json")
        assert creds.valid


class TestApiInteractions:
    def test_fetch_sources_success(self, requests_mock):
        mock_sources = [
            {"sender_email": "test@example.com", "custom_name": "Test News"}
        ]
        # Check that both authorization headers are sent
        headers_to_match = {
            "Authorization": "Bearer fake_key",
            "apikey": "fake_supabase_key",
        }
        requests_mock.get(
            "https://fake-api.com/api/v1/sources",
            request_headers=headers_to_match,
            json=mock_sources,
        )
        sources = ga.fetch_sources(
            "https://fake-api.com", "fake_key", "fake_supabase_key"
        )
        assert sources == mock_sources

    def test_fetch_sources_http_error(self, requests_mock, caplog):
        requests_mock.get(
            "https://fake-api.com/api/v1/sources", status_code=500, text="Server Error"
        )
        with pytest.raises(SystemExit):
            ga.fetch_sources("https://fake-api.com", "fake_key", "fake_supabase_key")
        assert "HTTP Error occurred." in caplog.text
        assert "Status Code: 500" in caplog.text
        assert "Response Body: Server Error" in caplog.text

    def test_fetch_sources_json_decode_error(self, requests_mock, caplog):
        # New test for the specific JSON decode error handling
        requests_mock.get(
            "https://fake-api.com/api/v1/sources",
            status_code=200,
            text="this is not json",
        )
        with pytest.raises(SystemExit):
            ga.fetch_sources("https://fake-api.com", "fake_key", "fake_supabase_key")
        assert "Failed to decode JSON from the API response" in caplog.text
        assert "Response Body Received: this is not json" in caplog.text

    def test_upload_audiobook_success(self, requests_mock, tmp_path):
        mp3_path = tmp_path / "test.mp3"
        mp3_path.write_text("mp3_data")
        ga.TEMP_AUDIO_MP3 = str(mp3_path)

        requests_mock.post("https://fake-api.com/api/v1/audiobooks", status_code=200)

        mock_metadata = {"title": "Test", "duration": 123}
        with patch("builtins.open", mock_open(read_data="mp3_data")) as mock_file:
            ga.upload_audiobook(
                "https://fake-api.com", "fake_key", "fake_supabase_key", mock_metadata
            )
            mock_file.assert_called_once_with(str(mp3_path), "rb")

        assert requests_mock.called
        assert requests_mock.last_request.headers["Authorization"] == "Bearer fake_key"
        assert requests_mock.last_request.headers["apikey"] == "fake_supabase_key"

    def test_upload_audiobook_failure(self, requests_mock, tmp_path, caplog):
        mp3_path = tmp_path / "test.mp3"
        mp3_path.write_text("mp3_data")
        ga.TEMP_AUDIO_MP3 = str(mp3_path)

        requests_mock.post(
            "https://fake-api.com/api/v1/audiobooks", status_code=403, text="Forbidden"
        )

        with pytest.raises(SystemExit), patch(
            "builtins.open", mock_open(read_data="mp3_data")
        ):
            ga.upload_audiobook(
                "https://fake-api.com", "fake_key", "fake_supabase_key", {}
            )

        assert "HTTP Error occurred while uploading audiobook" in caplog.text
        assert "Response Body: Forbidden" in caplog.text


class TestEmailProcessing:
    @pytest.fixture
    def mock_gmail_service(self, mocker):
        # This can be used by multiple tests with different side effects
        service = MagicMock()
        return service

    def test_process_emails_success(self, mock_gmail_service, mock_email_data):
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }
        mock_gmail_service.users().messages().get().execute.side_effect = (
            mock_email_data
        )

        sources = [
            {"sender_email": "sender1@example.com", "custom_name": "Newsletter One"},
            {"sender_email": "sender2@example.com", "custom_name": "Newsletter Two"},
        ]
        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-27"
        )

        assert "Newsletter from: Newsletter One" in full_text
        assert "This is a plain text newsletter." in full_text
        assert "Newsletter from: Newsletter Two" in full_text
        assert "Hello This is an HTML newsletter." in full_text
        assert len(text_blocks) == 2

    def test_process_email_simple_body(
        self, mock_gmail_service, mock_simple_email_data
    ):
        # New test for non-multipart emails
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_simple"}]
        }
        mock_gmail_service.users().messages().get().execute.side_effect = (
            mock_simple_email_data
        )

        sources = [
            {"sender_email": "simple@example.com", "custom_name": "Simple Newsletter"}
        ]
        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-28"
        )

        assert "Newsletter from: Simple Newsletter" in full_text
        assert "This is a simple body email." in full_text
        assert len(text_blocks) == 1
        assert text_blocks[0]["title"] == "Simple Newsletter"

    def test_process_emails_no_messages_found(self, mock_gmail_service, caplog):
        mock_gmail_service.users().messages().list().execute.return_value = {}
        sources = [
            {"sender_email": "sender1@example.com", "custom_name": "Newsletter One"}
        ]
        with caplog.at_level(logging.INFO):
            full_text, text_blocks = ga.process_emails(
                mock_gmail_service, sources, "2023-10-27"
            )

        assert full_text == ""
        assert text_blocks == []
        assert "No matching emails found" in caplog.text


class TestAudioAndMetadata:
    # No changes needed in this class, it remains the same.
    @patch("os.path.exists", return_value=True)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_metadata_success(self, mock_audio_segment, mock_exists):
        mock_audio_segment.from_mp3.return_value.__len__.return_value = 200000
        text_blocks = [
            {"title": "Chapter 1", "text": "a" * 50},
            {"title": "Chapter 2", "text": "b" * 50},
        ]
        metadata = ga.generate_metadata(text_blocks)
        chapters = json.loads(metadata["chapters_json"])
        assert metadata["duration"] == 200
        assert len(chapters) == 2


class TestMainExecution:
    @patch("generate_audiobook.cleanup")
    @patch("generate_audiobook.upload_audiobook")
    @patch("generate_audiobook.generate_metadata")
    @patch("generate_audiobook.generate_audio")
    @patch("generate_audiobook.process_emails")
    @patch("generate_audiobook.authenticate_gmail")
    @patch("generate_audiobook.fetch_sources")
    @patch("generate_audiobook.initialize_tts_model")
    @patch("generate_audiobook.load_config")
    def test_main_full_success_flow(
        self,
        m_load_config,
        m_init_tts,
        m_fetch_sources,
        m_auth_gmail,
        m_process_emails,
        m_gen_audio,
        m_gen_meta,
        m_upload,
        m_cleanup,
        monkeypatch,
    ):
        # Arrange
        monkeypatch.setattr(ga.sys, "argv", ["script_name", "--date", "2023-01-01"])
        m_load_config.return_value = {
            "api_url": "url",
            "api_key": "key",
            "supabase_anon_key": "s_key",  # Add new key to mock config
            "reference_voice_file": "voice.wav",
            "token_file": "t",
            "credentials_file": "c",
        }
        m_fetch_sources.return_value = [{"email": "a@b.com"}]
        m_process_emails.return_value = (
            "Full Text",
            [{"title": "Chapter", "text": "abc"}],
        )
        m_gen_audio.return_value = True
        m_gen_meta.return_value = {"duration": 100}

        # Act
        ga.main()

        # Assert
        m_load_config.assert_called_once()
        m_init_tts.assert_called_once()
        m_fetch_sources.assert_called_once_with("url", "key", "s_key")  # Check new arg
        m_auth_gmail.assert_called_once()
        m_process_emails.assert_called_once()
        m_gen_audio.assert_called_once_with("Full Text", "voice.wav")
        m_gen_meta.assert_called_once_with([{"title": "Chapter", "text": "abc"}])
        m_upload.assert_called_once_with(
            "url", "key", "s_key", {"duration": 100}
        )  # Check new arg
        m_cleanup.assert_called_once()

    @patch("generate_audiobook.cleanup")
    @patch("generate_audiobook.upload_audiobook")
    @patch("generate_audiobook.process_emails")
    @patch("generate_audiobook.fetch_sources")
    @patch("generate_audiobook.load_config")
    def test_main_exits_if_no_email_content(
        self,
        m_load_config,
        m_fetch_sources,
        m_process_emails,
        m_upload,
        m_cleanup,
        mocker,
        caplog,
        monkeypatch,
    ):
        # Arrange
        monkeypatch.setattr(ga.sys, "argv", ["script_name"])
        mocker.patch("generate_audiobook.initialize_tts_model")
        mocker.patch("generate_audiobook.authenticate_gmail")
        m_load_config.return_value = {
            "api_url": "url",
            "api_key": "key",
            "supabase_anon_key": "s_key",  # Add new key
            "reference_voice_file": "voice.wav",
            "token_file": "t",
            "credentials_file": "c",
        }
        m_fetch_sources.return_value = [{"email": "a@b.com"}]
        m_process_emails.return_value = ("  ", [])

        # Act
        with caplog.at_level(logging.INFO):
            ga.main()

        # Assert
        assert "No content generated" in caplog.text
        m_upload.assert_not_called()
        m_cleanup.assert_called_once()
