import pytest
import os
import configparser
import json
import base64
import logging
import datetime
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
    """Prevents sys.exit() from stopping the test suite and mocks logging setup."""
    monkeypatch.setattr(ga.sys, "exit", lambda x: (_ for _ in ()).throw(SystemExit(x)))
    monkeypatch.setattr(ga, "setup_logging", lambda: None)


@pytest.fixture
def mock_tts_client(mocker):
    """Mocks the global TTS_CLIENT for chunking and its methods."""
    mock_client = MagicMock()
    mock_synthesizer = MagicMock()
    mock_synthesizer.split_into_sentences.return_value = ["sentence 1.", "sentence 2."]
    mock_client.synthesizer = mock_synthesizer
    mock_client.tts.return_value = [0.1, 0.2]  # Mock a numpy array chunk
    mocker.patch.object(ga, "TTS_CLIENT", mock_client)
    mocker.patch("generate_audiobook.np.concatenate", return_value=[0.1, 0.2, 0.1, 0.2])
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

    def test_load_config_missing_key(self, tmp_path, caplog):
        config_path = tmp_path / "invalid_config.ini"
        config_path.write_text("[WebApp]\nAPI_URL = https://fake-api.com\n")
        with pytest.raises(SystemExit):
            ga.load_config(str(config_path))
        assert "Missing key in config.ini: 'API_KEY'" in caplog.text


class TestApiInteractions:
    def test_fetch_sources_success(self, requests_mock):
        requests_mock.get(
            "https://fake-api.com/sources", json=[{"sender_email": "test@example.com"}]
        )
        sources = ga.fetch_sources("https://fake-api.com", "fake_key")
        assert sources is not None

    def test_upload_audiobook_success(self, requests_mock, tmp_path, caplog):
        ga.TEMP_AUDIO_MP3 = str(tmp_path / "test.mp3")
        (tmp_path / "test.mp3").write_text("mp3_data")
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=200, json={"status": "ok"}
        )
        with patch("builtins.open", mock_open(read_data="mp3_data")):
            with caplog.at_level(logging.INFO):
                ga.upload_audiobook("https://fake-api.com", "fake_key", {})
        assert "Upload successful. Server response:" in caplog.text


class TestEmailProcessing:
    @pytest.fixture
    def mock_gmail_service(self, mock_email_data):
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
        full_text, _ = ga.process_emails(mock_gmail_service, sources, "2023-10-27")
        assert "This is a plain text newsletter." in full_text
        assert "HelloThis is an HTML newsletter." in full_text


class TestAudioAndMetadata:
    @patch("os.path.exists", return_value=True)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_audio_with_reference_voice(
        self, mock_audio_segment, mock_exists, mock_tts_client, caplog
    ):
        with caplog.at_level(logging.INFO):
            assert ga.generate_audio("some text.", "valid/path.wav") is True
        assert "Using reference voice for cloning: valid/path.wav" in caplog.text
        mock_tts_client.tts.assert_any_call(
            text="sentence 1.",
            speaker=None,
            speaker_wav="valid/path.wav",
            language="en",
        )

    @patch("os.path.exists", return_value=False)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_audio_with_default_voice(
        self, mock_audio_segment, mock_exists, mock_tts_client, caplog
    ):
        with caplog.at_level(logging.INFO):
            assert ga.generate_audio("some text.", "invalid/path.wav") is True
        assert "Using default built-in speaker: Claribel Dervla" in caplog.text
        mock_tts_client.tts.assert_any_call(
            text="sentence 1.",
            speaker="Claribel Dervla",
            speaker_wav=None,
            language="en",
        )

    @patch("os.path.exists", return_value=True)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_metadata_success(
        self, mock_audio_segment, mock_exists, monkeypatch
    ):
        # FIX: Because `datetime.date` is an immutable C-type, we cannot use `patch`.
        # We must use `monkeypatch` to replace the entire class with a fake one.
        class FakeDate:
            def strftime(self, format_string):
                return "2023-10-27"

        class FakeDateTime:
            @classmethod
            def today(cls):
                return FakeDate()

        monkeypatch.setattr(ga.datetime, "date", FakeDateTime)

        mock_audio_segment.from_mp3.return_value.__len__.return_value = 200000
        text_blocks = [{"title": "Chapter 1", "text": "a" * 100}]

        metadata = ga.generate_metadata(text_blocks)

        assert metadata["title"] == "Daily Digest for 2023-10-27"
        assert metadata["duration"] == 200


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

        monkeypatch.setattr(ga.sys, "argv", ["script_name", "--date", "2023-01-01"])
        m_load_config.return_value = {
            "api_url": "url",
            "api_key": "key",
            "reference_voice_file": "v.wav",
            "token_file": "t",
            "credentials_file": "c",
        }
        m_fetch_sources.return_value = [{"email": "a@b.com"}]
        m_process_emails.return_value = ("Full Text", [{"title": "Chapter"}])
        m_gen_audio.return_value = True
        m_gen_meta.return_value = {"duration": 100}

        tts_mock_for_main = MagicMock(is_multi_speaker=True, speakers=["speaker1"])
        ga.TTS_CLIENT = tts_mock_for_main

        ga.main()

        m_fetch_sources.assert_called_once_with("url", "key")
        m_upload.assert_called_once_with("url", "key", {"duration": 100})
        m_cleanup.assert_called_once()
