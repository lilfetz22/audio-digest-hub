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
    python generate_tts_audio.py path/to/digest.txt --output-dir archive_mp3 \
        --voice af_heart --bitrate 64k

System dependency:
    espeak-ng must be installed on the host (e.g. `apt-get install espeak-ng`
    on Debian/Ubuntu). Kokoro uses it for phonemization.
"""
from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import List, Optional, Tuple, Union

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from tqdm.auto import tqdm
import torch # Import torch for no_grad

logger = logging.getLogger(__name__)

# Kokoro TTS configuration
DEFAULT_VOICE = "af_heart"
LANG_CODE = "a"  # American English
SAMPLE_RATE = 24000  # Kokoro outputs at 24 kHz
MAX_CHUNK_LENGTH = 250
DEFAULT_BITRATE = "64k"
MAX_TTS_WORKERS = 4  # default cap; each worker holds its own Kokoro pipeline copy

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


# Per-worker-process Kokoro pipeline, populated by _init_worker. Each worker
# process in the ProcessPoolExecutor loads its own copy once and reuses it
# for every chunk it's asked to synthesize.
_worker_pipeline = None


def _init_worker(device: str) -> None:
    """ProcessPoolExecutor initializer: load one Kokoro pipeline per process.

    Also caps this process's own intra-op thread pool to 1 so N worker
    processes don't each try to claim every CPU core and thrash each other.
    """
    global _worker_pipeline
    torch.set_num_threads(1)
    _worker_pipeline = _load_pipeline(device)


def _worker_synthesize(
    index: int, text: str, voice: str, speed: float
) -> Tuple[int, np.ndarray, Optional[str]]:
    """Run in a worker process: synthesize one chunk.

    Returns (index, audio, error) rather than raising or logging directly —
    logging from a worker process wouldn't reach the main process's handlers,
    so the caller logs using the returned error message instead.
    """
    try:
        with torch.no_grad():
            audio = _synthesize_chunk(_worker_pipeline, text, voice, speed)
        return index, audio, None
    except Exception as exc:  # noqa: BLE001 — keep going on bad chunks
        return index, np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32), str(exc)


def _default_workers() -> int:
    """Worker count when the caller didn't pass max_workers explicitly.

    Honours TTS_MAX_WORKERS so CI/cron can cap parallelism (e.g. on a
    memory-constrained runner) without a code change or redeploy.
    """
    override = os.environ.get("TTS_MAX_WORKERS")
    if override:
        try:
            return max(1, int(override))
        except ValueError:
            logger.warning("Ignoring non-integer TTS_MAX_WORKERS=%r", override)
    # os.process_cpu_count() (3.13+) respects CPU affinity, unlike
    # os.cpu_count(), which can over-provision workers on affinity-limited
    # runners. Fall back to os.cpu_count() while we're on 3.12.
    cpu_count = getattr(os, "process_cpu_count", os.cpu_count)()
    return min(cpu_count or 1, MAX_TTS_WORKERS)


def _synthesize_sequential(
    chunks: List[str],
    voice: str,
    speed: float,
    device: str,
    audio_chunks: List[Optional[np.ndarray]],
) -> int:
    """Synthesize every chunk in this process. Returns the failed-chunk count.

    Used both as the normal single-process path (resolved_workers <= 1) and
    as the fallback when the worker pool dies (BrokenProcessPool).
    """
    pipeline = _load_pipeline(device)
    logger.info("Warming up model...")
    _ = _synthesize_chunk(pipeline, "Warm up.", voice, speed)
    failed = 0
    # Wrap the synthesis loop in torch.no_grad() to prevent gradient accumulation
    with torch.no_grad():
        for i, chunk in enumerate(tqdm(chunks, desc="TTS", unit="chunk")):
            try:
                audio_chunks[i] = _synthesize_chunk(pipeline, chunk, voice, speed)
            except Exception as exc:  # noqa: BLE001 — keep going on bad chunks
                logger.error("Chunk failed (%s): %.80s", exc, chunk)
                audio_chunks[i] = np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32)
                failed += 1
    return failed


def _encode_mp3(wav_path: Path, output_mp3_path: Path, bitrate: str) -> None:
    """Encode `wav_path` to `output_mp3_path` via a direct ffmpeg subprocess.

    We call the `imageio_ffmpeg`-bundled binary directly, rather than relying
    on a PATH-based lookup (as our previous MP3 encoder did), because this
    repo's environments do not reliably have ffmpeg on PATH.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",  # overwrite output if it exists
        "-i", str(wav_path),
        "-b:a", bitrate,
        str(output_mp3_path),
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed to encode MP3 (exit code {result.returncode}): "
            f"{result.stdout}"
        )


def generate_audio_from_text(
    text_content: str,
    output_mp3_path: PathLike,
    *,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    device: str = "cpu",
    bitrate: str = DEFAULT_BITRATE,
    keep_wav: bool = False,
    max_workers: Optional[int] = None,
) -> Path:
    """
    Synthesize TTS audio for `text_content` and write it to `output_mp3_path`.
    Returns the absolute path to the generated MP3.

    `max_workers` controls how many worker processes synthesize chunks in
    parallel (each holds its own Kokoro pipeline). Defaults to
    `min(process_cpu_count(), MAX_TTS_WORKERS)` (falls back to `os.cpu_count()`
    on Python <3.13), overridable via the
    `TTS_MAX_WORKERS` env var; pass `1` to force the original
    single-process sequential path. Never exceeds the number of chunks, and
    for any non-"cpu" device this defaults to a single process (one
    accelerator context) unless `max_workers` is set explicitly.
    """
    if not text_content or not text_content.strip():
        raise ValueError("text_content is empty")

    output_mp3_path = Path(output_mp3_path).resolve()
    output_mp3_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = _process_text(text_content)
    if not chunks:
        raise ValueError("No valid speech chunks after preprocessing")

    resolved_workers = max_workers if max_workers is not None else _default_workers()
    # Never start more pipelines than there is work for — each one costs a
    # full model load before it does anything useful.
    resolved_workers = min(resolved_workers, len(chunks))
    if device != "cpu" and max_workers is None:
        logger.info(
            "device=%s: using a single process (one accelerator context).", device
        )
        resolved_workers = 1

    logger.info(
        "Synthesizing %d chunks on %s (CPU synthesis can take a while)...",
        len(chunks),
        device,
    )
    start = time.time()
    audio_chunks: List[Optional[np.ndarray]] = [None] * len(chunks)
    failed = 0

    if resolved_workers <= 1:
        failed = _synthesize_sequential(chunks, voice, speed, device, audio_chunks)
    else:
        logger.info("Using %d worker processes for TTS synthesis", resolved_workers)
        # set_num_threads(1) in _init_worker only caps ATen intra-op
        # parallelism; OpenMP/OpenBLAS pools (used by numpy and torch's own
        # kernels) are sized from these env vars at library init, which in a
        # spawned child happens during `import torch` — before the
        # initializer runs. Set them here, in the parent, before the pool
        # exists, so N workers don't each still try to claim every core.
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        # Pause markers need no model at all (_synthesize_chunk just returns
        # silence for them) — fill them in here instead of round-tripping
        # ~960 KB of zeros through IPC per pause for no reason.
        work = []
        for i, chunk in enumerate(chunks):
            if chunk == PAUSE_MARKER:
                audio_chunks[i] = np.zeros(
                    int(SAMPLE_RATE * PAUSE_DURATION_SECONDS), dtype=np.float32
                )
            else:
                work.append((i, chunk))
        try:
            with ProcessPoolExecutor(
                max_workers=resolved_workers,
                mp_context=multiprocessing.get_context("spawn"),
                initializer=_init_worker,
                initargs=(device,),
            ) as executor:
                futures = [
                    executor.submit(_worker_synthesize, i, chunk, voice, speed)
                    for i, chunk in work
                ]
                for future in tqdm(
                    as_completed(futures), total=len(futures), desc="TTS", unit="chunk"
                ):
                    index, audio, error = future.result()
                    audio_chunks[index] = audio
                    if error is not None:
                        logger.error("Chunk %d failed (%s): %.80s", index, error, chunks[index])
                        failed += 1
        except BrokenProcessPool as exc:
            logger.error(
                "TTS worker pool died (%s) — likely an OOM kill. Retrying the whole "
                "text with single-process synthesis.",
                exc,
            )
            audio_chunks[:] = [None] * len(chunks)
            failed = _synthesize_sequential(chunks, voice, speed, device, audio_chunks)

    synth_seconds = time.time() - start
    logger.info(
        "Synthesis complete in %.1fs (%d chunks, %d failed)",
        synth_seconds,
        len(chunks),
        failed,
    )

    if failed and failed / len(chunks) > 0.25:
        raise RuntimeError(
            f"{failed}/{len(chunks)} chunks failed to synthesize; refusing to write "
            "a mostly-silent MP3."
        )

    full_audio = np.concatenate(audio_chunks)

    wav_path = output_mp3_path.with_suffix(".wav")
    sf.write(str(wav_path), full_audio, SAMPLE_RATE, subtype="PCM_16")

    _encode_mp3(wav_path, output_mp3_path, bitrate)

    duration_min = len(full_audio) / SAMPLE_RATE / 60.0
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
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "Worker processes for parallel TTS synthesis "
            f"(default: min(process_cpu_count, {MAX_TTS_WORKERS})). Use 1 for "
            "the original sequential single-process path."
        ),
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
        max_workers=args.workers,
    )
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
