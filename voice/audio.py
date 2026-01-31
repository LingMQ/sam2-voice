"""Audio capture and playback utilities using sounddevice."""

import asyncio
import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("Warning: sounddevice not available. Install with: pip install sounddevice")


@dataclass
class AudioConfig:
    """Audio configuration settings."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    dtype: str = "int16"


class AudioCapture:
    """Captures audio from the microphone using sounddevice.

    Uses a callback-based approach for efficient audio capture.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
    ):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice is required for audio capture")

        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size

        self._stream: Optional[sd.InputStream] = None
        self._is_running = False

        # Queue for audio data
        self._audio_queue: queue.Queue = queue.Queue()

        # Callback for audio data
        self._on_audio: Optional[Callable[[bytes], None]] = None

    def set_callback(self, callback: Callable[[bytes], None]):
        """Set callback for audio data."""
        self._on_audio = callback

    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice stream."""
        if status:
            print(f"Audio capture status: {status}")

        # Convert to bytes
        audio_bytes = indata.tobytes()
        self._audio_queue.put(audio_bytes)

        if self._on_audio:
            self._on_audio(audio_bytes)

    def start(self):
        """Start capturing audio."""
        if self._is_running:
            return

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.chunk_size,
            callback=self._audio_callback,
        )
        self._stream.start()
        self._is_running = True
        print("Audio capture started")

    def stop(self):
        """Stop capturing audio."""
        self._is_running = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        print("Audio capture stopped")

    async def read_audio(self) -> Optional[bytes]:
        """Read audio data from the queue (async).

        Returns:
            Audio bytes or None if queue is empty
        """
        try:
            return self._audio_queue.get_nowait()
        except queue.Empty:
            return None

    async def read_audio_blocking(self, timeout: float = 0.1) -> Optional[bytes]:
        """Read audio data from the queue, waiting if necessary.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Audio bytes or None if timeout
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._audio_queue.get(timeout=timeout)
            )
        except queue.Empty:
            return None

    def terminate(self):
        """Clean up audio resources."""
        self.stop()


class AudioPlayback:
    """Plays audio through the speakers using sounddevice.

    Uses a queue and separate thread for smooth playback.
    """

    def __init__(
        self,
        sample_rate: int = 24000,  # Gemini outputs 24kHz
        channels: int = 1,
        chunk_size: int = 1024,
    ):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice is required for audio playback")

        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size

        self._stream: Optional[sd.OutputStream] = None
        self._is_running = False
        self._thread = None

        # Queue for audio data
        self._audio_queue: queue.Queue = queue.Queue()

    def start(self):
        """Start audio playback."""
        if self._is_running:
            return

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.chunk_size,
        )
        self._stream.start()

        self._is_running = True
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()
        print("Audio playback started")

    def stop(self):
        """Stop audio playback."""
        self._is_running = False

        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        print("Audio playback stopped")

    def _playback_loop(self):
        """Background thread for playing audio."""
        while self._is_running:
            try:
                data = self._audio_queue.get(timeout=0.1)
                # Convert bytes to numpy array
                audio_np = np.frombuffer(data, dtype=np.int16)
                # Reshape for sounddevice (samples, channels)
                audio_np = audio_np.reshape(-1, self.channels)
                self._stream.write(audio_np)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio playback error: {e}")
                break

    def play(self, audio_data: bytes):
        """Queue audio data for playback.

        Args:
            audio_data: Raw PCM audio bytes
        """
        self._audio_queue.put(audio_data)

    def clear_queue(self):
        """Clear the playback queue (for interruptions)."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def terminate(self):
        """Clean up audio resources."""
        self.stop()


class VoiceActivityDetector:
    """Simple voice activity detection based on audio energy."""

    def __init__(
        self,
        threshold: float = 0.01,
        sample_rate: int = 16000,
    ):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._is_speaking = False
        self._silence_frames = 0
        self._silence_threshold = 10  # frames of silence to end speech

    def process(self, audio_data: bytes) -> bool:
        """Process audio and detect voice activity.

        Args:
            audio_data: Raw PCM audio bytes

        Returns:
            True if voice activity detected
        """
        # Convert to numpy array
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        audio_np = audio_np / 32768.0  # Normalize to [-1, 1]

        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_np ** 2))

        if rms > self.threshold:
            self._is_speaking = True
            self._silence_frames = 0
        else:
            self._silence_frames += 1
            if self._silence_frames >= self._silence_threshold:
                self._is_speaking = False

        return self._is_speaking

    @property
    def is_speaking(self) -> bool:
        """Check if user is currently speaking."""
        return self._is_speaking
