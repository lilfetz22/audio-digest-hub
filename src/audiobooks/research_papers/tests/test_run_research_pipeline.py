import configparser
from pathlib import Path

import run_research_pipeline as rrp


def _write_config(path: Path, *, credentials="credentials.json", token="token.json"):
    config = configparser.ConfigParser()
    config["WebApp"] = {
        "API_URL": "https://fake-api.com",
        "API_KEY": "fake-api-key",
    }
    config["Gmail"] = {
        "CREDENTIALS_FILE": credentials,
        "TOKEN_FILE": token,
    }
    config["Gemini"] = {
        "API_KEY": "fake-gemini-key",
        "GENERATION_MODEL": "fake-model",
    }
    config["ResearchPapers"] = {
        "ARXIV_SENDERS": "no-reply@arxiv.org",
        "HUGGINGFACE_SENDERS": "daily@huggingface.co",
    }
    with path.open("w", encoding="utf-8") as fh:
        config.write(fh)


def test_load_config_resolves_paths_relative_to_config_file(tmp_path):
    config_path = tmp_path / "config.ini"
    _write_config(config_path)

    config = rrp.load_config(str(config_path))

    assert config["credentials_file"] == str(tmp_path / "credentials.json")
    assert config["token_file"] == str(tmp_path / "token.json")


def test_load_config_preserves_absolute_paths(tmp_path):
    config_path = tmp_path / "config.ini"
    absolute_credentials = tmp_path / "nested" / "credentials.json"
    absolute_token = tmp_path / "nested" / "token.json"
    _write_config(
        config_path,
        credentials=str(absolute_credentials),
        token=str(absolute_token),
    )

    config = rrp.load_config(str(config_path))

    assert config["credentials_file"] == str(absolute_credentials)
    assert config["token_file"] == str(absolute_token)
