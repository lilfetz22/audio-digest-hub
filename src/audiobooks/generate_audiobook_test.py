import pytest
import os
import configparser
import json
import base64
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


# --- Test Classes ---


class TestConfig:
    def test_load_config_success(self, mock_config_file):
        config = ga.load_config(mock_config_file)
        assert config["api_url"] == "https://fake-api.com"
        assert config["api_key"] == "fake_api_key"
        assert config["credentials_file"] == "fake_credentials.json"
        assert config["reference_voice_file"] == "path/to/fake_voice.wav"

    def test_load_config_file_not_found(self, capsys):
        with pytest.raises(SystemExit):
            ga.load_config("non_existent_file.ini")
        captured = capsys.readouterr()
        assert "Configuration file 'non_existent_file.ini' not found" in captured.err

    def test_load_config_missing_key(self, tmp_path, capsys):
        config_path = tmp_path / "invalid_config.ini"
        config_path.write_text("[WebApp]\nAPI_URL = https://fake-api.com\n")
        with pytest.raises(SystemExit):
            ga.load_config(str(config_path))
        captured = capsys.readouterr()
        assert "Missing key in config.ini" in captured.err


class TestTTSInitialization:
    @patch("generate_audiobook.torch.cuda.is_available", return_value=True)
    @patch("generate_audiobook.TTS")
    def test_initialize_tts_model_with_cuda(self, mock_tts, mock_cuda, capsys):
        ga.TTS_CLIENT = None  # Reset global state
        ga.initialize_tts_model()
        mock_cuda.assert_called_once()
        mock_tts.assert_called_with(ga.TTS_MODEL)
        mock_tts.return_value.to.assert_called_with("cuda")
        captured = capsys.readouterr()
        assert "Using device: cuda" in captured.out
        assert ga.TTS_CLIENT is not None

    @patch("generate_audiobook.torch.cuda.is_available", return_value=False)
    @patch("generate_audiobook.TTS")
    def test_initialize_tts_model_with_cpu(self, mock_tts, mock_cuda, capsys):
        ga.TTS_CLIENT = None  # Reset global state
        ga.initialize_tts_model()
        mock_cuda.assert_called_once()
        mock_tts.return_value.to.assert_called_with("cpu")
        captured = capsys.readouterr()
        assert "Using device: cpu" in captured.out

    @patch("generate_audiobook.TTS", side_effect=Exception("Model Load Error"))
    def test_initialize_tts_model_failure(self, mock_tts, capsys):
        ga.TTS_CLIENT = None
        with pytest.raises(SystemExit):
            ga.initialize_tts_model()
        captured = capsys.readouterr()
        assert "Failed to load the TTS model: Model Load Error" in captured.err


class TestGmailAuth:
    @patch("generate_audiobook.Credentials")
    def test_authenticate_gmail_token_valid(self, mock_creds, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        mock_creds.from_authorized_user_file.return_value.valid = True
        creds = ga.authenticate_gmail("token.json", "creds.json")
        assert creds.valid

    @patch("generate_audiobook.Credentials")
    def test_authenticate_gmail_token_expired(self, mock_creds, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        mock_cred_instance = MagicMock()
        mock_cred_instance.valid = False
        mock_cred_instance.expired = True
        mock_cred_instance.refresh_token = "some_token"
        mock_cred_instance.to_json.return_value = '{"refreshed": "token"}'
        mock_creds.from_authorized_user_file.return_value = mock_cred_instance

        m = mock_open()
        with patch("builtins.open", m):
            ga.authenticate_gmail("token.json", "creds.json")

        mock_cred_instance.refresh.assert_called_once()
        m().write.assert_called_once_with('{"refreshed": "token"}')

    @patch("generate_audiobook.InstalledAppFlow")
    def test_authenticate_gmail_first_time_flow(self, mock_flow, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda path: path.endswith("creds.json"))

        mock_creds_obj = MagicMock()
        mock_creds_obj.to_json.return_value = '{"token": "fake_token_from_flow"}'
        mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = (
            mock_creds_obj
        )

        m = mock_open()
        with patch("builtins.open", m):
            creds = ga.authenticate_gmail("token.json", "creds.json")

        assert creds == mock_creds_obj
        m.assert_called_once_with("token.json", "w")
        m().write.assert_called_once_with('{"token": "fake_token_from_flow"}')

    def test_authenticate_gmail_no_credentials_file(self, capsys, monkeypatch):
        monkeypatch.setattr(
            os.path, "exists", lambda path: False
        )  # Both token and creds are missing
        with pytest.raises(SystemExit):
            ga.authenticate_gmail("token.json", "creds.json")
        captured = capsys.readouterr()
        assert "Gmail credentials file ('creds.json') not found" in captured.err


class TestApiInteractions:
    def test_fetch_sources_success(self, requests_mock):
        mock_sources = [
            {"sender_email": "test@example.com", "custom_name": "Test News"}
        ]
        requests_mock.get("https://fake-api.com/api/v1/sources", json=mock_sources)
        sources = ga.fetch_sources("https://fake-api.com", "fake_key")
        assert sources == mock_sources

    def test_fetch_sources_failure(self, requests_mock, capsys):
        requests_mock.get("https://fake-api.com/api/v1/sources", status_code=500)
        with pytest.raises(SystemExit):
            ga.fetch_sources("https://fake-api.com", "fake_key")
        captured = capsys.readouterr()
        assert "Failed to fetch sources from API" in captured.err

    def test_upload_audiobook_success(self, requests_mock, tmp_path):
        mp3_path = tmp_path / "test.mp3"
        mp3_path.write_text("mp3_data")
        ga.TEMP_AUDIO_MP3 = str(mp3_path)

        requests_mock.post("https://fake-api.com/api/v1/audiobooks", status_code=200)

        mock_metadata = {"title": "Test", "duration": 123}
        with patch("builtins.open", mock_open(read_data="mp3_data")) as mock_file:
            ga.upload_audiobook("https://fake-api.com", "fake_key", mock_metadata)
            mock_file.assert_called_once_with(str(mp3_path), "rb")

        assert requests_mock.called
        assert requests_mock.last_request.headers["Authorization"] == "Bearer fake_key"

    def test_upload_audiobook_failure(self, requests_mock, tmp_path, capsys):
        mp3_path = tmp_path / "test.mp3"
        mp3_path.write_text("mp3_data")
        ga.TEMP_AUDIO_MP3 = str(mp3_path)

        requests_mock.post(
            "https://fake-api.com/api/v1/audiobooks", status_code=403, text="Forbidden"
        )

        with pytest.raises(SystemExit), patch(
            "builtins.open", mock_open(read_data="mp3_data")
        ):
            ga.upload_audiobook("https://fake-api.com", "fake_key", {})

        captured = capsys.readouterr()
        assert "Failed to upload audiobook" in captured.err
        assert "Response body: Forbidden" in captured.err


class TestEmailProcessing:
    @pytest.fixture
    def mock_gmail_service(self, mocker, mock_email_data):
        service = MagicMock()
        service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }
        service.users().messages().get().execute.side_effect = mock_email_data
        return service

    def test_process_emails_success(self, mock_gmail_service):
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
        # FIX: The improved HTML stripping now adds a space
        assert "Hello This is an HTML newsletter." in full_text
        assert len(text_blocks) == 2
        assert text_blocks[0]["title"] == "Newsletter One"
        assert text_blocks[1]["title"] == "Newsletter Two"

    def test_process_emails_no_messages_found(self, mock_gmail_service, capsys):
        mock_gmail_service.users().messages().list().execute.return_value = {}
        sources = [
            {"sender_email": "sender1@example.com", "custom_name": "Newsletter One"}
        ]
        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-27"
        )

        assert full_text == ""
        assert text_blocks == []
        captured = capsys.readouterr()
        assert "No matching emails found" in captured.out


class TestAudioAndMetadata:
    @patch("os.path.exists", return_value=True)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_audio_with_reference_voice(
        self, mock_audio_segment, mock_exists, mock_tts_client, capsys
    ):
        ga.generate_audio("some text", "valid/path.wav")
        mock_tts_client.tts_to_file.assert_called_once_with(
            text="some text",
            speaker_wav="valid/path.wav",
            language="en",
            file_path=ga.TEMP_AUDIO_WAV,
            speed=1.0,
        )
        mock_audio_segment.from_wav.assert_called_once_with(ga.TEMP_AUDIO_WAV)
        mock_audio_segment.from_wav.return_value.export.assert_called_once_with(
            ga.TEMP_AUDIO_MP3, format="mp3"
        )
        captured = capsys.readouterr()
        assert "Using reference voice: valid/path.wav" in captured.out

    @patch("os.path.exists", return_value=False)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_audio_with_default_voice(
        self, mock_audio_segment, mock_exists, mock_tts_client, capsys
    ):
        ga.generate_audio("some text", "invalid/path.wav")
        mock_tts_client.tts_to_file.assert_called_once_with(
            text="some text",
            speaker_wav=None,
            language="en",
            file_path=ga.TEMP_AUDIO_WAV,
            speed=1.0,
        )
        captured = capsys.readouterr()
        assert "No valid reference voice found" in captured.out

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
        assert chapters[0]["title"] == "Chapter 1"
        assert chapters[0]["start_time"] == 0
        assert chapters[1]["title"] == "Chapter 2"
        assert chapters[1]["start_time"] == 100


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
        # FIX: Explicitly set sys.argv to avoid pytest interference
        monkeypatch.setattr(ga.sys, "argv", ["script_name", "--date", "2023-01-01"])
        m_load_config.return_value = {
            "api_url": "url",
            "api_key": "key",
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
        m_fetch_sources.assert_called_once()
        m_auth_gmail.assert_called_once()
        m_process_emails.assert_called_once()
        m_gen_audio.assert_called_once_with("Full Text", "voice.wav")
        m_gen_meta.assert_called_once_with([{"title": "Chapter", "text": "abc"}])
        m_upload.assert_called_once()
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
        capsys,
        monkeypatch,
    ):
        # Arrange
        # FIX: Explicitly set sys.argv to avoid pytest interference and test default date
        monkeypatch.setattr(ga.sys, "argv", ["script_name"])
        mocker.patch("generate_audiobook.initialize_tts_model")
        mocker.patch("generate_audiobook.authenticate_gmail")
        m_load_config.return_value = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "voice.wav",
            "token_file": "t",
            "credentials_file": "c",
        }
        m_fetch_sources.return_value = [{"email": "a@b.com"}]
        m_process_emails.return_value = ("  ", [])  # No content, only whitespace

        # Act
        ga.main()

        # Assert
        captured = capsys.readouterr()
        assert "No content generated" in captured.out
        m_upload.assert_not_called()
        m_cleanup.assert_called_once()
