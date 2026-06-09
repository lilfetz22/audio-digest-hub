#!/usr/bin/env python3
"""
generate_tts_audio.py

CPU-based TTS audio generation using Kokoro. Replaces the Google Colab
notebook (`TTS_Generation_Colab.ipynb`) so the full pipeline can run end-to-end
on a CPU server with no manual upload/download handoff.

Public API:
    generate_audio_from_text(text, output_mp3_path, ...) -> Path
    generate_audio_from_file(text_file_path, output_dir, ...) -> Path

CLI:
    python generate_tts_audio.py path/to/digest.txt
    python generate_tts_audio.py path/to/digest.txt --output-dir archive_mp3 \\
        --voice af_heart --bitrate 64k

System dependency:
    espeak-ng must be installed on the host (e.g. `apt-get install espeak-ng`
    on Debian/Ubuntu). Kokoro uses it for phonemization.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from typing import List, Union

import numpy as np
import soundfile as sf
from pydub import AudioSegment
from tqdm.auto import tqdm

logger = logging.getLogger(__name__)

# Kokoro TTS configuration
DEFAULT_VOICE = "af_heart"
LANG_CODE = "a"  # American English
SAMPLE_RATE = 24000  # Kokoro outputs at 24 kHz
MAX_CHUNK_LENGTH = 250
DEFAULT_BITRATE = "64k"

# Interrogator Q&A: insert silence after each question line (Q1:, Q2:, ...)
# so the listener has time to think before the answer is read.
PAUSE_MARKER = "__PAUSE_10S__"
PAUSE_DURATION_SECONDS = 10
QUESTION_LINE_RE = re.compile(r"^Q\d+:")

PathLike = Union[str, Path]


def _split_into_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _validate_and_split_chunk(chunk: str, max_len: int = MAX_CHUNK_LENGTH) -> List[str]:
    cleaned = re.sub(r"https?://\S+", "", chunk).strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_len:
        return [cleaned]

    sub_chunks: List[str] = []
    while len(cleaned) > max_len:
        split_pos = cleaned.rfind(" ", 0, max_len)
        if split_pos == -1:
            split_pos = max_len
        sub_chunks.append(cleaned[:split_pos])
        cleaned = cleaned[split_pos:].lstrip()
    if cleaned:
        sub_chunks.append(cleaned)
    return sub_chunks


def _is_question_line(text: str) -> bool:
    return bool(QUESTION_LINE_RE.match(text.strip()))


def _process_text(text: str) -> List[str]:
    initial: List[str] = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            initial.extend(_split_into_sentences(paragraph))

    final: List[str] = []
    for chunk in initial:
        final.extend(_validate_and_split_chunk(chunk))

    result: List[str] = []
    for c in final:
        if not c.strip():
            continue
        result.append(c)
        if _is_question_line(c):
            result.append(PAUSE_MARKER)

    pauses = result.count(PAUSE_MARKER)
    logger.info(
        "Prepared %d speech chunks (+ %d pause markers)",
        len(result) - pauses,
        pauses,
    )
    return result


def _load_pipeline(device: str):
    # Lazy import so module-level import doesn't trigger the model download
    # for callers that only want the text-processing helpers.
    from kokoro import KPipeline

    logger.info("Loading Kokoro pipeline (lang=%s, device=%s)...", LANG_CODE, device)
    start = time.time()
    pipeline = KPipeline(lang_code=LANG_CODE, device=device)
    logger.info("Pipeline loaded in %.1fs", time.time() - start)
    return pipeline


def _synthesize_chunk(pipeline, text: str, voice: str, speed: float) -> np.ndarray:
    if text == PAUSE_MARKER:
        return np.zeros(int(SAMPLE_RATE * PAUSE_DURATION_SECONDS), dtype=np.float32)

    generator = pipeline(text, voice=voice, speed=speed)
    audio: List[float] = []
    for _, _, chunk_audio in generator:
        audio.extend(chunk_audio)
    return np.array(audio, dtype=np.float32)


def generate_audio_from_text(
    text_content: str,
    output_mp3_path: PathLike,
    *,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    device: str = "cpu",
    bitrate: str = DEFAULT_BITRATE,
    keep_wav: bool = False,
) -> Path:
    """
    Synthesize TTS audio for `text_content` and write it to `output_mp3_path`.
    Returns the absolute path to the generated MP3.
    """
    if not text_content or not text_content.strip():
        raise ValueError("text_content is empty")

    output_mp3_path = Path(output_mp3_path).resolve()
    output_mp3_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = _process_text(text_content)
    if not chunks:
        raise ValueError("No valid speech chunks after preprocessing")

    pipeline = _load_pipeline(device)

    logger.info("Warming up model...")
    _ = _synthesize_chunk(pipeline, "Warm up.", voice, speed)

    logger.info(
        "Synthesizing %d chunks on %s (CPU synthesis can take a while)...",
        len(chunks),
        device,
    )
    start = time.time()
    audio_chunks: List[np.ndarray] = []
    failed = 0
    for chunk in tqdm(chunks, desc="TTS", unit="chunk"):
        try:
            audio_chunks.append(_synthesize_chunk(pipeline, chunk, voice, speed))
        except Exception as exc:  # noqa: BLE001 — keep going on bad chunks
            logger.error("Chunk failed (%s): %.80s", exc, chunk)
            audio_chunks.append(np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32))
            failed += 1
    synth_seconds = time.time() - start
    logger.info(
        "Synthesis complete in %.1fs (%d chunks, %d failed)",
        synth_seconds,
        len(chunks),
        failed,
    )

    full_audio = np.concatenate(audio_chunks)

    wav_path = output_mp3_path.with_suffix(".wav")
    sf.write(str(wav_path), full_audio, SAMPLE_RATE)

    audio_segment = AudioSegment.from_wav(str(wav_path))
    if audio_segment.sample_width > 2:
        audio_segment = audio_segment.set_sample_width(2)
    audio_segment.export(str(output_mp3_path), format="mp3", bitrate=bitrate)

    duration_min = len(audio_segment) / 1000.0 / 60.0
    mp3_size_mb = output_mp3_path.stat().st_size / (1024 * 1024)
    logger.info(
        "Wrote MP3: %s (%.1f min, %.2f MB, bitrate=%s)",
        output_mp3_path,
        duration_min,
        mp3_size_mb,
        bitrate,
    )

    if not keep_wav:
        wav_path.unlink(missing_ok=True)

    return output_mp3_path


def generate_audio_from_file(
    text_file_path: PathLike,
    output_dir: PathLike = "archive_mp3",
    **kwargs,
) -> Path:
    """
    Convenience wrapper: read a UTF-8 .txt file and synthesize it. The output
    MP3 is named `{stem}_generated_audio.mp3` to match the filename pattern
    `request_user_feedback()` in `generate_audiobook.py` expects.
    """
    text_path = Path(text_file_path).resolve()
    if not text_path.exists():
        raise FileNotFoundError(text_path)

    text = text_path.read_text(encoding="utf-8")
    output_filename = f"{text_path.stem}_generated_audio.mp3"
    output_path = Path(output_dir).resolve() / output_filename
    return generate_audio_from_text(text, output_path, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate TTS audio on CPU using Kokoro.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_file", help="Path to a UTF-8 .txt file to synthesize.")
    parser.add_argument(
        "--output-dir",
        default="archive_mp3",
        help="Directory for the MP3 output.",
    )
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--bitrate", default=DEFAULT_BITRATE)
    parser.add_argument(
        "--keep-wav",
        action="store_true",
        help="Keep the intermediate WAV alongside the MP3.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    output_path = generate_audio_from_file(
        args.input_file,
        output_dir=args.output_dir,
        voice=args.voice,
        speed=args.speed,
        device=args.device,
        bitrate=args.bitrate,
        keep_wav=args.keep_wav,
    )
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
