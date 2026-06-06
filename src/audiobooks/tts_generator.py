
import re
import time
import numpy as np
import torch
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import psutil
from pydub import AudioSegment
import soundfile as sf
from kokoro import KPipeline
from tqdm.auto import tqdm
import logging

# --- Configuration ---
# These should align with or be configurable from generate_audiobook.py
DEFAULT_VOICE = "af_heart"  # Or other kokoro voices: "am_adam", "bf_emma", "bm_george"
LANG_CODE = "a"  # American English ("b" for British, etc.)
SAMPLE_RATE = 24000  # Kokoro default output sample rate
MAX_CHUNK_LENGTH = 250  # Max characters per chunk for optimal processing
PAUSE_MARKER = "__PAUSE_10S__"
PAUSE_DURATION_SECONDS = 10

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Global Variables ---
tts_pipeline = None
device = "cpu"
gpu_memory_gb = 0
memory_manager = None
perf_tracker = None

# --- GPU Management ---
class GPUMemoryManager:
    def __init__(self, device: str):
        self.device = device
        self.memory_threshold = 0.9  # 90% memory usage threshold
        self.cleanup_threshold = 0.95  # 95% triggers aggressive cleanup

    def get_memory_info(self) -> Dict[str, float]:
        if self.device == "cpu":
            return {"allocated": 0, "reserved": 0, "total": 100, "used_percent": 0}

        allocated = torch.cuda.memory_allocated(0) / (1024**3)  # GB
        reserved = torch.cuda.memory_reserved(0) / (1024**3)   # GB
        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        free = total - allocated
        used_percent = allocated / total

        return {
            "allocated": allocated,
            "reserved": reserved,
            "total": total,
            "free": free,
            "used_percent": used_percent
        }

    def print_memory_status(self, prefix: str = ""):
        if self.device == "cpu":
            logger.info(f"{prefix}💾 CPU Mode - No GPU memory tracking")
            return

        info = self.get_memory_info()
        logger.info(f"{prefix}💾 GPU Memory: {info['allocated']:.2f}GB/{info['total']:.2f}GB ({info['used_percent']*100:.1f}%)")

    def cleanup_memory(self, aggressive: bool = False):
        if self.device == "cpu":
            return

        if aggressive:
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.debug("Aggressive GPU memory cleanup completed")
        else:
            torch.cuda.empty_cache()

    def check_memory_and_cleanup(self) -> bool:
        if self.device == "cpu":
            return True

        info = self.get_memory_info()

        if info['used_percent'] > self.cleanup_threshold:
            logger.warning(f"High memory usage ({info['used_percent']*100:.1f}%), performing aggressive cleanup...")
            self.cleanup_memory(aggressive=True)
            return False
        elif info['used_percent'] > self.memory_threshold:
            logger.debug(f"Memory usage high ({info['used_percent']*100:.1f}%), performing light cleanup...")
            self.cleanup_memory(aggressive=False)
            return True
        return True

    def monitor_memory_during_batch(self, batch_id: int, batch_size: int):
        if self.device == "cpu":
            return
        info = self.get_memory_info()
        if info['used_percent'] > 0.8:  # 80% threshold for warnings
            logger.warning(f"Batch {batch_id}: High memory usage {info['used_percent']*100:.1f}%")

# --- Performance Tracking ---
class PerformanceTracker:
    def __init__(self):
        self.start_time = None
        self.chunk_times = []
        self.batch_times = []

    def start(self):
        self.start_time = time.time()

    def log_chunk(self):
        if self.start_time is not None:
            self.chunk_times.append(time.time() - self.start_time)

    def log_batch(self, batch_size):
        if self.start_time is not None:
            batch_time = time.time() - self.start_time
            self.batch_times.append((batch_time, batch_size))
            self.start_time = time.time()  # Reset for next batch

    def get_stats(self) -> str:
        if not self.chunk_times:
            return "No performance data available"

        avg_chunk_time = sum(self.chunk_times) / len(self.chunk_times)
        total_chunks = len(self.chunk_times)

        stats = f"📊 Performance Stats:\n"
        stats += f"   Total chunks: {total_chunks}\n"
        stats += f"   Average time per chunk: {avg_chunk_time:.2f}s\n"

        if self.batch_times:
            total_batch_time = sum(t for t, _ in self.batch_times)
            total_batch_chunks = sum(s for _, s in self.batch_times)
            stats += f"   Total processing time: {total_batch_time:.2f}s\n"
            stats += f"   Throughput: {total_batch_chunks/total_batch_time:.2f} chunks/sec"
        return stats

# --- Initialization ---
def initialize_tts_engine(gpu_mem_gb: float = 14.7):
    """Initializes the Kokoro TTS pipeline and memory manager."""
    global tts_pipeline, device, gpu_memory_gb, memory_manager, perf_tracker

    # Detect device
    if torch.cuda.is_available():
        device = "cuda"
        gpu_memory_gb = gpu_mem_gb # Use provided or detected memory
        torch.backends.cudnn.benchmark = True
        torch.cuda.empty_cache()
        logger.info(f"🚀 GPU Available: {torch.cuda.get_device_name(0)}")
        logger.info(f"   GPU Memory: {gpu_memory_gb:.1f} GB")
    else:
        device = "cpu"
        gpu_memory_gb = 0
        logger.warning("⚠️ GPU not available, using CPU (this will be much slower)")

    # Initialize memory manager
    memory_manager = GPUMemoryManager(device)
    logger.info("🧠 GPU Memory Manager initialized")
    memory_manager.print_memory_status("Initial ")

    # Initialize performance tracker
    perf_tracker = PerformanceTracker()

    # Load Kokoro TTS pipeline
    logger.info("🔄 Loading Kokoro TTS pipeline...")
    start_time = time.time()
    try:
        tts_pipeline = KPipeline(lang_code=LANG_CODE, device=device)
        load_time = time.time() - start_time
        logger.info(f"✅ Kokoro TTS pipeline loaded successfully in {load_time:.1f} seconds")

        # Warm-up model
        logger.info("🔥 Warming up model with test synthesis...")
        try:
            test_text = "This is a test to warm up the model."
            # Use a minimal number of steps for warming up
            for _ in tts_pipeline(test_text, voice=DEFAULT_VOICE, speed=1.0, steps=10):
                pass # Consume the generator
            logger.info("✅ Model warmed up successfully")
        except Exception as e:
            logger.warning(f"⚠️ Model warming failed: {e}")

        # Configure batch size based on memory
        OPTIMAL_BATCH_SIZE = calculate_optimal_batch_size(gpu_memory_gb, device)
        MAX_WORKERS = min(4, OPTIMAL_BATCH_SIZE)
        logger.info(f"⚙️ Batch Processing Configuration:")
        logger.info(f"   Optimal batch size: {OPTIMAL_BATCH_SIZE}")
        logger.info(f"   Max concurrent workers: {MAX_WORKERS}")
        logger.info(f"   Interrogator pause: {PAUSE_DURATION_SECONDS}s after each question")

    except Exception as e:
        logger.error(f"❌ Failed to load Kokoro TTS pipeline: {e}", exc_info=True)
        raise

# --- Text Processing Functions ---
def calculate_optimal_batch_size(gpu_memory_gb: float, device: str) -> int:
    if device == "cpu":
        return 1
    if gpu_memory_gb >= 12: return 16
    if gpu_memory_gb >= 8: return 12
    if gpu_memory_gb >= 6: return 8
    return 4

def _is_question_line(text: str) -> bool:
    return bool(re.match(r'^Q\d+:', text.strip()))

def split_into_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def validate_and_process_chunk(chunk: str, max_len: int = MAX_CHUNK_LENGTH) -> List[str]:
    cleaned_chunk = re.sub(r"https?://\\S+", "", chunk).strip()
    if not cleaned_chunk: return []
    if len(cleaned_chunk) <= max_len: return [cleaned_chunk]

    sub_chunks = []
    while len(cleaned_chunk) > max_len:
        split_pos = cleaned_chunk.rfind(" ", 0, max_len)
        if split_pos == -1: split_pos = max_len
        sub_chunks.append(cleaned_chunk[:split_pos])
        cleaned_chunk = cleaned_chunk[split_pos:].lstrip()
    if cleaned_chunk: sub_chunks.append(cleaned_chunk)
    return sub_chunks

def process_text_content(text_content: str) -> List[str]:
    """Processes full text content into valid chunks for TTS generation."""
    logger.debug("Processing text content into chunks...")
    paragraphs = text_content.split("\\n")
    initial_chunks = []
    for paragraph in paragraphs:
        if paragraph.strip():
            sentences = split_into_sentences(paragraph)
            initial_chunks.extend(sentences)

    final_chunks = []
    for chunk in initial_chunks:
        sub_chunks = validate_and_process_chunk(chunk, max_len=MAX_CHUNK_LENGTH)
        final_chunks.extend(sub_chunks)

    valid_chunks = []
    for c in final_chunks:
        if not c.strip(): continue
        valid_chunks.append(c)
        if _is_question_line(c):
            valid_chunks.append(PAUSE_MARKER)

    pause_count = valid_chunks.count(PAUSE_MARKER)
    logger.debug(f"Processed {len(initial_chunks)} initial chunks, {len(valid_chunks) - pause_count} valid + {pause_count} pauses.")
    return valid_chunks

# --- Audio Generation Functions ---
def generate_audio_batch(text_chunks: List[str], batch_id: int, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> List[np.ndarray]:
    """Generate audio for a batch of text chunks using Kokoro."""
    audio_arrays = []
    if memory_manager:
        memory_manager.monitor_memory_during_batch(batch_id, len(text_chunks))

    for i, text in enumerate(text_chunks):
        if text == PAUSE_MARKER:
            silence = np.zeros(int(SAMPLE_RATE * PAUSE_DURATION_SECONDS), dtype=np.float32)
            audio_arrays.append(silence)
            continue

        try:
            generator = tts_pipeline(text, voice=voice, speed=speed)
            chunk_audio = []
            for _, _, audio in generator:
                chunk_audio.extend(audio)
            audio_arrays.append(np.array(chunk_audio, dtype=np.float32))
        except Exception as e:
            logger.error(f"Error generating audio for chunk {i} in batch {batch_id}: {e}")
            silence = np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32) # 0.5 sec silence
            audio_arrays.append(silence)
    return audio_arrays

def create_batches(items: List, batch_size: int) -> List[List]:
    """Split a list into batches of specified size."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

def generate_audio_from_text(text_content: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> Tuple[Optional[np.ndarray], int]:
    """
    Processes text content and generates concatenated audio.
    Returns (audio_numpy_array, sample_rate) or (None, 0) on failure.
    """
    if not tts_pipeline:
        logger.error("TTS pipeline not initialized. Call initialize_tts_engine() first.")
        return None, 0

    text_chunks = process_text_content(text_content)
    if not text_chunks:
        logger.error("No valid text chunks generated.")
        return None, 0

    OPTIMAL_BATCH_SIZE = calculate_optimal_batch_size(gpu_memory_gb, device)
    batches = create_batches(text_chunks, OPTIMAL_BATCH_SIZE)

    perf_tracker.start()
    all_audio_chunks = []
    successful_chunks = 0
    failed_chunks = 0

    logger.info(f"Starting TTS generation for {len(text_chunks)} chunks...")
    try:
        with tqdm(total=len(text_chunks), desc="Generating Audio", unit="chunk") as pbar:
            for batch_id, batch_chunks in enumerate(batches, 1):
                batch_start_time = time.time()

                if memory_manager:
                    memory_manager.check_memory_and_cleanup()
                    memory_manager.monitor_memory_during_batch(batch_id, len(batch_chunks))

                try:
                    batch_audio = generate_audio_batch(batch_chunks, batch_id, voice, speed)

                    if len(batch_audio) == len(batch_chunks):
                        all_audio_chunks.extend(batch_audio)
                        successful_chunks += len(batch_chunks)
                    else:
                        logger.warning(f"Batch {batch_id}: Expected {len(batch_chunks)} audio chunks, got {len(batch_audio)}")
                        all_audio_chunks.extend(batch_audio) # Add whatever was generated
                        successful_chunks += len(batch_audio)
                        failed_chunks += len(batch_chunks) - len(batch_audio)

                    pbar.update(len(batch_chunks))
                    batch_time = time.time() - batch_start_time
                    perf_tracker.log_batch(len(batch_chunks))
                    chunks_per_sec = len(batch_chunks) / batch_time
                    pbar.set_postfix({
                        'chunks/sec': f'{chunks_per_sec:.1f}',
                        'batch_time': f'{batch_time:.1f}s',
                        'success': successful_chunks,
                        'failed': failed_chunks
                    })

                    if batch_id % 3 == 0 and memory_manager: # Clean up every few batches
                        memory_manager.cleanup_memory(aggressive=False)

                except Exception as e:
                    logger.error(f"Error processing batch {batch_id}: {e}", exc_info=True)
                    failed_chunks += len(batch_chunks)
                    # Add silence for failed batches to maintain sequence
                    silence_duration = int(SAMPLE_RATE * 2) # 2 seconds silence
                    for _ in batch_chunks:
                        all_audio_chunks.append(np.zeros(silence_duration, dtype=np.float32))

        if all_audio_chunks:
            logger.info("Concatenating audio chunks...")
            full_audio_np = np.concatenate(all_audio_chunks)
            logger.info(f"TTS generation complete. Final audio length: {len(full_audio_np)} samples")
            return full_audio_np, SAMPLE_RATE
        else:
            logger.error("No audio chunks were generated.")
            return None, 0

    finally:
        if memory_manager:
            memory_manager.cleanup_memory(aggressive=True)
            memory_manager.print_memory_status("Final ")

# --- Export Audio ---
def export_audio(audio_data: np.ndarray, sample_rate: int, output_path: str, bitrate: str = "64k") -> float:
    """
    Exports audio data to WAV and MP3 formats.
    Returns the size of the MP3 file in MB.
    """
    base_path = Path(output_path).with_suffix('') # Remove any existing suffix
    wav_path = str(base_path) + ".wav"
    mp3_path = str(base_path) + ".mp3"

    logger.debug(f"Exporting WAV to: {wav_path}")
    try:
        sf.write(wav_path, audio_data, sample_rate)
    except Exception as e:
        logger.error(f"Failed to write WAV file: {e}")
        return 0.0

    try:
        logger.debug(f"Exporting MP3 to: {mp3_path} with bitrate {bitrate}")
        audio_segment = AudioSegment.from_wav(wav_path)

        # Convert to 16-bit if higher bit depth
        if audio_segment.sample_width > 2:
            audio_segment = audio_segment.set_sample_width(2)
            logger.debug("Converted audio to 16-bit")

        # Export MP3
        audio_segment.export(mp3_path, format="mp3", bitrate=bitrate)
        mp3_size_bytes = Path(mp3_path).stat().st_size
        mp3_size_mb = mp3_size_bytes / (1024 * 1024)
        logger.debug(f"MP3 file saved. Size: {mp3_size_mb:.2f} MB")
        return mp3_size_mb

    except Exception as e:
        logger.error(f"Failed to export MP3 file: {e}")
        return 0.0

# --- Main TTS Generation Function ---
def synthesize_speech(text_content: str, output_filename_base: str) -> Tuple[Optional[str], float]:
    """
    Main function to synthesize speech from text content.
    Returns the path to the generated MP3 file and its size in MB on success,
    or (None, 0.0) on failure.
    """
    if not text_content.strip():
        logger.warning("No text content provided for synthesis.")
        return None, 0.0

    # Ensure engine is initialized
    if tts_pipeline is None:
        # Attempt initialization if not already done.
        # In a real application, this might need more robust error handling or
        # explicit initialization call before use.
        logger.warning("TTS pipeline not initialized. Attempting to initialize now.")
        try:
            # You might need to determine GPU memory here if not passed explicitly.
            # For simplicity, using a default value or trying to detect.
            initialize_tts_engine()
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            return None, 0.0

    # Generate audio data in memory
    audio_data, sample_rate = generate_audio_from_text(text_content)

    if audio_data is None or sample_rate == 0:
        logger.error("Audio generation failed.")
        return None, 0.0

    # Export audio to WAV and MP3
    output_path_base = f"./{output_filename_base}" # Save locally for now
    mp3_size_mb = export_audio(audio_data, sample_rate, output_path_base, bitrate="64k") # Use 64k bitrate

    if mp3_size_mb > 0:
        final_mp3_path = f"{output_path_base}.mp3"
        logger.info(f"MP3 audio synthesized and saved to: {final_mp3_path} ({mp3_size_mb:.2f} MB)")
        return final_mp3_path, mp3_size_mb
    else:
        logger.error("Failed to export audio files.")
        return None, 0.0

# Example usage (for testing the module directly):
if __name__ == "__main__":
    # Initialize the engine first
    try:
        # Attempt to detect GPU memory or use a default if detection fails
        try:
            if torch.cuda.is_available():
                gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            else:
                gpu_mem = 0
        except Exception:
            gpu_mem = 8.0 # Default to 8GB if detection fails
            logger.warning("Could not detect GPU memory, using default 8GB.")

        initialize_tts_engine(gpu_mem_gb=gpu_mem)
    except Exception as e:
        logger.critical(f"Failed to initialize TTS engine for example usage: {e}")
        exit(1)

    # Sample text content
    sample_text = '''
    This is the first sentence.
    This is the second sentence, which is a bit longer and might need to be split.
    Q1: What is the capital of France?
    Paris is the capital of France.
    Q2: What is the primary function of a CPU?
    The primary function of a CPU is to execute instructions from a computer program.
    This is a final sentence.
    '''
    output_base = "test_audio_output"

    print(f"\\n--- Running TTS synthesis example ---")
    mp3_file, mp3_size = synthesize_speech(sample_text, output_base)

    if mp3_file:
        print(f"\\nSuccess! MP3 file generated at: {mp3_file} ({mp3_size:.2f} MB)")
        # Optional: Clean up the generated files if needed for testing
        # import os
        # if os.path.exists(mp3_file): os.remove(mp3_file)
        # if os.path.exists(mp3_file.replace('.mp3', '.wav')): os.remove(mp3_file.replace('.mp3', '.wav'))
    else:
        print("\\nTTS synthesis failed.")
