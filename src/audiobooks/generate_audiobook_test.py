# --- START OF FILE generate_audiobook_test.py ---

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
    """Prevents sys.exit() from stopping the test suite."""
    monkeypatch.setattr(ga.sys, "exit", lambda x: (_ for _ in ()).throw(SystemExit(x)))


@pytest.fixture
def mock_tts_client(mocker):
    """Mocks the global TTS_CLIENT for chunking and its methods."""
    mock_client = MagicMock()
    mock_synthesizer = MagicMock()
    # Simulate the initial sentence split
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
def mock_email_data():
    """Provides mock email data for parsing tests."""
    text_content = "This is a plain text newsletter."
    html_content = "<h1>Hello</h1><p>This is an HTML newsletter.</p>"
    # This message is malformed - its body data is not valid base64
    malformed_msg = {
        "id": "msg3",
        "payload": {
            "headers": [{"name": "From", "value": "Bad Sender <sender3@example.com>"}],
            "parts": [{"mimeType": "text/plain", "body": {"data": "not-base64"}}],
        },
    }
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
        assert "HTTP Error occurred" in caplog.text
        assert "Status Code: 500" in caplog.text

    def test_fetch_sources_json_decode_error(self, requests_mock, caplog):
        requests_mock.get(
            "https://fake-api.com/sources", status_code=200, text="not-json"
        )
        with pytest.raises(SystemExit):
            ga.fetch_sources("https://fake-api.com", "fake_key")
        assert "Failed to decode JSON" in caplog.text
        assert "Response Body Received: not-json" in caplog.text

    def test_upload_audiobook_success(self, requests_mock, tmp_path, caplog):
        ga.TEMP_AUDIO_MP3 = str(tmp_path / "test.mp3")
        (tmp_path / "test.mp3").write_text("mp3_data")
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=200, json={"status": "ok"}
        )
        with patch("builtins.open", mock_open(read_data="mp3_data")):
            with caplog.at_level(logging.INFO):
                ga.upload_audiobook(
                    "https://fake-api.com", "fake_key", {"title": "test"}
                )
        assert "Upload successful. Server response:" in caplog.text

    def test_upload_audiobook_http_error(self, requests_mock, tmp_path, caplog):
        ga.TEMP_AUDIO_MP3 = str(tmp_path / "test.mp3")
        (tmp_path / "test.mp3").write_text("mp3_data")
        requests_mock.post(
            "https://fake-api.com/audiobooks", status_code=400, text="Bad Request"
        )
        with patch("builtins.open", mock_open(read_data="mp3_data")):
            with pytest.raises(SystemExit):
                ga.upload_audiobook(
                    "https://fake-api.com", "fake_key", {"title": "test"}
                )
        assert "HTTP Error occurred while uploading audiobook" in caplog.text


class TestGmailInteraction:
    @pytest.fixture
    def mock_gmail_service(self):
        """A basic mock for the gmail service. Specifics are configured in each test."""
        return MagicMock()

    # FIX: Set side_effect to [False, False] to ensure the code path that
    # checks for the credentials file is actually triggered.
    @patch("generate_audiobook.os.path.exists", side_effect=[False, False])
    @patch("generate_audiobook.Credentials.from_authorized_user_file")
    @patch("generate_audiobook.InstalledAppFlow.from_client_secrets_file")
    def test_authenticate_gmail_credentials_not_found(
        self, m_flow, m_creds, m_exists, caplog
    ):
        # This will now correctly enter the block where credentials_file is needed but not found.
        with pytest.raises(SystemExit):
            ga.authenticate_gmail("token.json", "creds.json")
        assert "Gmail credentials file ('creds.json') not found." in caplog.text

    # FIX: Isolate the mock's behavior to this test to ensure it only "finds" the two good emails.
    def test_process_emails_success(self, mock_gmail_service, mock_email_data):
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }
        mock_gmail_service.users().messages().get().execute.side_effect = [
            mock_email_data[0],
            mock_email_data[1],
        ]

        sources = [
            {"sender_email": "sender1@example.com", "custom_name": "Newsletter One"},
            {"sender_email": "sender2@example.com", "custom_name": "Newsletter Two"},
        ]
        full_text, text_blocks = ga.process_emails(
            mock_gmail_service, sources, "2023-10-27"
        )
        assert "This is a plain text newsletter." in full_text
        assert "HelloThis is an HTML newsletter." in full_text
        # The assertion is now correct because only 2 messages are processed.
        assert len(text_blocks) == 2

    # FIX: Isolate the mock's behavior to only find the single malformed email.
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
        # This assertion is now correct because the custom name is found before the parse fails.
        assert text_blocks[0]["title"] == "Bad Newsletter (Error)"
        assert "Failed to parse email from Bad Newsletter" in caplog.text

    # FIX: Set the logging level to INFO so the message can be captured.
    def test_process_emails_no_matching_emails(self, mock_gmail_service, caplog):
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


class TestHelperFunctions:
    def test_remove_markdown_links(self):
        text = "Check [this link](http://a.com) and [another one](http://b.com)."
        expected = "Check this link and another one."
        assert ga.remove_markdown_links(text) == expected
        assert ga.remove_markdown_links("No links here.") == "No links here."

    @pytest.mark.parametrize(
        "chunk, expected",
        [
            ("Short clean sentence.", ["Short clean sentence."]),
            (
                "Sentence with a url https://example.com to remove.",
                ["Sentence with a url to remove."],
            ),
            ("", []),
            ("https://just-a-url.com", []),
            (
                "A very long sentence" * 20,
                [
                    "A very long sentence" * 5,
                    "A very long sentence" * 5,
                    "A very long sentence" * 5,
                    "A very long sentence" * 5,
                ],
            ),
        ],
    )
    @patch("generate_audiobook.logger")
    def test_validate_and_process_chunk(self, mock_logger, chunk, expected):
        # A long chunk needs to be split
        if len(chunk) > 250:
            result = ga.validate_and_process_chunk(
                chunk, max_len=100
            )  # use smaller max_len for test
            assert len(result) > 1
            assert all(len(c) <= 100 for c in result)
        else:
            assert ga.validate_and_process_chunk(chunk) == expected


class TestAudioAndMetadata:
    @patch("os.path.exists", return_value=True)
    @patch("generate_audiobook.AudioSegment")
    @patch(
        "generate_audiobook.validate_and_process_chunk",
        return_value=["valid chunk 1.", "valid chunk 2."],
    )
    def test_generate_audio_with_reference_voice(
        self, m_validate, mock_audio_segment, mock_exists, mock_tts_client, caplog
    ):
        with caplog.at_level(logging.INFO):
            assert ga.generate_audio("some text.\nmore text.", "valid/path.wav") is True

        # FIX: The assertion was wrong. The function is called with the *output* of
        # split_into_sentences, not the raw paragraph. This checks it was called correctly.
        m_validate.assert_any_call("sentence 1.")

        assert "Using reference voice for cloning: valid/path.wav" in caplog.text
        # Check that TTS is called with the *validated* chunks
        mock_tts_client.tts.assert_any_call(
            text="valid chunk 1.",
            speaker=None,
            speaker_wav="valid/path.wav",
            language="en",
        )
        mock_tts_client.tts.assert_any_call(
            text="valid chunk 2.",
            speaker=None,
            speaker_wav="valid/path.wav",
            language="en",
        )

    @patch("os.path.exists", return_value=False)
    @patch("generate_audiobook.AudioSegment")
    @patch(
        "generate_audiobook.validate_and_process_chunk", return_value=["valid chunk."]
    )
    def test_generate_audio_with_default_voice(
        self, m_validate, mock_audio_segment, mock_exists, mock_tts_client, caplog
    ):
        with caplog.at_level(logging.INFO):
            assert ga.generate_audio("some text.", "invalid/path.wav") is True
        assert "Using default built-in speaker: Claribel Dervla" in caplog.text
        mock_tts_client.tts.assert_called_with(
            text="valid chunk.",
            speaker="Claribel Dervla",
            speaker_wav=None,
            language="en",
        )

    # FIX: Set logging level to capture the INFO message.
    def test_generate_audio_empty_text(self, caplog):
        with caplog.at_level(logging.INFO):
            assert ga.generate_audio("   ", "voice.wav") is False
        assert "No text content to synthesize" in caplog.text

    @patch("os.path.exists", return_value=True)
    @patch("generate_audiobook.AudioSegment")
    def test_generate_metadata_success(
        self, mock_audio_segment, mock_exists, monkeypatch
    ):
        # Because `datetime.date` is an immutable C-type, we must use `monkeypatch`
        class FakeDate(datetime.date):
            def __new__(cls, *args, **kwargs):
                return super().__new__(cls, 2023, 10, 27)

            @classmethod
            def today(cls):
                return cls(2023, 10, 27)

        monkeypatch.setattr(ga.datetime, "date", FakeDate)
        mock_audio_segment.from_mp3.return_value.__len__.return_value = 200000
        text_blocks = [{"title": "Chapter 1", "text": "a" * 100}]

        metadata = ga.generate_metadata(text_blocks)
        assert metadata["title"] == "Daily Digest for 2023-10-27"
        assert metadata["duration"] == 200

    # FIX: Set logging level to capture the INFO message.
    @patch("os.path.exists", return_value=False)
    def test_generate_metadata_no_mp3(self, mock_exists, caplog):
        with caplog.at_level(logging.INFO):
            assert ga.generate_metadata([]) is None
        assert "MP3 file does not exist, skipping metadata generation." in caplog.text


class TestMainExecutionAndCleanup:
    @patch("generate_audiobook.cleanup")
    @patch("generate_audiobook.upload_audiobook")
    @patch("generate_audiobook.generate_metadata")
    @patch("generate_audiobook.generate_audio")
    @patch(
        "generate_audiobook.remove_markdown_links", side_effect=lambda x: f"cleaned_{x}"
    )
    @patch("generate_audiobook.process_emails")
    @patch("generate_audiobook.authenticate_gmail")
    @patch("generate_audiobook.fetch_sources")
    @patch("generate_audiobook.initialize_tts_model")
    @patch("generate_audiobook.load_config")
    @patch("generate_audiobook.setup_logging")
    def test_main_full_success_flow(
        self,
        m_setup,
        m_load_config,
        m_init_tts,
        m_fetch,
        m_auth,
        m_process,
        m_clean_text,
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
        m_fetch.return_value = [{"email": "a@b.com"}]
        m_process.return_value = (
            "Full Text",
            [{"title": "Chapter", "text": "Original Text"}],
        )
        m_gen_audio.return_value = True
        m_gen_meta.return_value = {"duration": 100}

        ga.main()

        m_setup.assert_called_once()
        m_init_tts.assert_called_once()
        m_fetch.assert_called_once_with("url", "key")

        # Verify text cleaning happens correctly
        m_clean_text.assert_any_call("Full Text")
        m_clean_text.assert_any_call("Original Text")

        # Verify the CLEANED text is used
        m_gen_audio.assert_called_once_with("cleaned_Full Text", "v.wav")
        # Verify metadata is generated with the cleaned block
        m_gen_meta.assert_called_once_with(
            [{"title": "Chapter", "text": "cleaned_Original Text"}]
        )

        m_upload.assert_called_once_with("url", "key", {"duration": 100})
        m_cleanup.assert_called_once()

    def test_main_no_content(self, monkeypatch):
        monkeypatch.setattr(ga.sys, "argv", ["script_name"])
        with patch("generate_audiobook.load_config") as m_load, patch(
            "generate_audiobook.initialize_tts_model"
        ), patch("generate_audiobook.fetch_sources") as m_fetch, patch(
            "generate_audiobook.authenticate_gmail"
        ), patch(
            "googleapiclient.discovery.build"
        ), patch(
            "generate_audiobook.process_emails", return_value=(" ", [])
        ) as m_process, patch(
            "generate_audiobook.generate_audio"
        ) as m_gen_audio:

            ga.main()
            # Assert that audio generation is NOT called if there's no content
            m_gen_audio.assert_not_called()

    @patch("os.path.exists", side_effect=[True, True, False])
    @patch("os.remove", side_effect=[None, OSError("Permission denied")])
    def test_cleanup(self, m_remove, m_exists, caplog):
        ga.cleanup()
        assert m_remove.call_count == 2
        m_remove.assert_any_call(ga.TEMP_AUDIO_WAV)
        m_remove.assert_any_call(ga.TEMP_AUDIO_MP3)
        assert (
            f"Could not remove temporary file {ga.TEMP_AUDIO_MP3}: Permission denied"
            in caplog.text
        )
