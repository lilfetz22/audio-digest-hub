# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Email notification on TTS readiness** — `generate_audiobook.py` now sends a self-addressed Gmail notification when the pipeline is waiting for a TTS-generated MP3, so the user knows to run the Colab notebook without monitoring the terminal.
- **Multi-tier API key fallback for transcript generation** — `GeminiTranscriptGenerator` now supports `backup_api_key` and `paid_api_key`/`paid_model_name` parameters. On quota exhaustion (429), the system automatically rotates through backup free-tier keys before falling back to a paid key as a last resort.
- **Model fallback chain** — Transcript generation now tries a configurable chain of models (`gemini-3.1-flash-lite-preview` → `gemini-3-flash-preview` → `gemini-2.5-pro`) before giving up on a given API key tier.
- **Model locking** — Once a model succeeds, it is reused for all subsequent calls in the same run. If the locked-in model later fails, the full fallback chain is re-entered.
- **New config keys** — `BACKUP_API_KEY`, `PAID_API_KEY`, and `PAID_GENERATION_MODEL` in the `[Gemini]` section of `config.ini` (all optional with safe fallbacks).

### Changed
- `gmail.send` scope added alongside `gmail.modify` in `generate_audiobook.py` to support sending notification emails.
- `_generate_realtime` retry logic refactored into `_try_model` with 10 retries (up from 4) and exponential backoff capped at 10 minutes.
- Network errors (`httpx.ReadError`, `httpx.ConnectError`, `httpx.RemoteProtocolError`) are now retried instead of immediately failing.
- Fixed `ServerError` attribute check from `status_code` to `code`.
