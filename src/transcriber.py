"""
Transcription engines:
  LocalTranscriber  — faster-whisper running on local CPU/GPU
  CloudTranscriber  — Google Cloud Speech-to-Text via service account JSON
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from src.extractor import extract_chunk, get_duration
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Local Whisper (via faster-whisper)
# ---------------------------------------------------------------------------

class LocalTranscriber:
    """
    Transcribes audio using faster-whisper (CTranslate2 backend).

    model:  tiny | base | small | medium | large-v2 | large-v3
    language: BCP-47 short code (e.g. 'en', 'ja', 'fr') or None for auto-detect
    device: 'auto' | 'cuda' | 'cpu'
            auto — uses CUDA if available, falls back to CPU
    """

    COMPUTE_TYPES = {"cuda": "int8_float16", "cpu": "int8"}

    def __init__(self, model: str = "base", language: str | None = None, device: str = "auto", max_duration: float | None = None):
        self.model_name = model
        self.language = language
        self.device = device
        self.max_duration = max_duration
        self._model = None

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import ctranslate2
            if "float16" in ctranslate2.get_supported_compute_types("cuda"):
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise EnvironmentError(
                    "faster-whisper is not installed. Run:  pip install faster-whisper"
                )
            resolved = self._resolve_device()
            compute = self.COMPUTE_TYPES[resolved]
            print(f"  Loading Whisper model '{self.model_name}' on {resolved.upper()} ({compute})...")
            self._model = WhisperModel(self.model_name, device=resolved, compute_type=compute)

    def transcribe(self, audio_path: Path) -> list[dict]:
        """Returns a list of segments: [{start, end, text}, ...]"""
        self._load()

        kwargs = {
            "beam_size": 5,
            "vad_filter": True,          # skip non-speech sections, prevents hallucinations
            "condition_on_previous_text": False,  # stops hallucinations from propagating
        }
        if self.language:
            kwargs["language"] = self.language
        if self.max_duration is not None:
            kwargs["word_timestamps"] = True

        segments_gen, info = self._model.transcribe(str(audio_path), **kwargs)

        duration = get_duration(audio_path)
        print(f"  Language: {info.language} ({info.language_probability:.0%} confidence)  |  Duration: {duration/60:.1f} min")

        segments = []
        last_pos = 0.0

        with tqdm(
            total=math.ceil(duration),
            unit="s",
            desc=f"  Whisper ({self.model_name})",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n:.0f}/{total:.0f}s  [{elapsed}<{remaining}]",
            ncols=80,
        ) as pbar:
            for seg in segments_gen:
                entry = {"start": seg.start, "end": seg.end, "text": seg.text}
                if self.max_duration is not None:
                    entry["words"] = seg.words
                segments.append(entry)
                advance = min(seg.end, duration) - last_pos
                pbar.update(advance)
                last_pos = min(seg.end, duration)

        if self.max_duration is not None:
            segments = split_segments(segments, self.max_duration)

        return segments


# ---------------------------------------------------------------------------
# Google Cloud Speech-to-Text
# ---------------------------------------------------------------------------


class CloudTranscriber:
    """
    Transcribes audio using Google Cloud Speech-to-Text API.

    credentials_path: path to service account JSON key file.
    Falls back to GOOGLE_APPLICATION_CREDENTIALS env var if not provided.

    Long audio is automatically split into 55-second chunks and reassembled.
    """

    CHUNK_DURATION = 55  # seconds — safely under the 60s sync API limit

    def __init__(self, credentials_path: str | None = None, language: str | None = None):
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        self.language = language or "en-US"   # Google STT requires a language code
        self._client = None

    def _bcp47(self) -> str:
        """Ensure language is a valid BCP-47 code (e.g. 'ja' -> 'ja-JP')."""
        mappings = {
            "en": "en-US", "ja": "ja-JP", "zh": "zh-CN", "ko": "ko-KR",
            "fr": "fr-FR", "de": "de-DE", "es": "es-ES", "it": "it-IT",
            "pt": "pt-BR", "ru": "ru-RU", "ar": "ar-SA", "hi": "hi-IN",
            "th": "th-TH", "vi": "vi-VN", "id": "id-ID", "ms": "ms-MY",
        }
        lang = self.language.strip().lower()
        return mappings.get(lang, lang)  # pass through if already full (e.g. 'en-US')

    def _load_client(self):
        if self._client is not None:
            return

        try:
            from google.cloud import speech
            from google.oauth2 import service_account
        except ImportError:
            raise EnvironmentError(
                "Google Cloud Speech library not installed. Run:\n"
                "  pip install google-cloud-speech"
            )

        if not self.credentials_path:
            raise ValueError(
                "No Google credentials path provided.\n"
                "Pass --credentials <path_to_json> or set the "
                "GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )

        cred_path = Path(self.credentials_path)
        if not cred_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {cred_path}")

        credentials = service_account.Credentials.from_service_account_file(
            str(cred_path),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        self._client = speech.SpeechClient(credentials=credentials)
        self._speech = speech

    def _transcribe_chunk(self, chunk_path: Path, offset_sec: float) -> list[dict]:
        """Send one audio chunk to Google STT and return segments with corrected timestamps."""
        with open(chunk_path, "rb") as f:
            audio_bytes = f.read()

        audio = self._speech.RecognitionAudio(content=audio_bytes)
        config = self._speech.RecognitionConfig(
            encoding=self._speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=self._bcp47(),
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
        )

        response = self._client.recognize(config=config, audio=audio)

        segments = []
        for result in response.results:
            alt = result.alternatives[0]
            if not alt.words:
                continue

            start = alt.words[0].start_time.total_seconds() + offset_sec
            end = alt.words[-1].end_time.total_seconds() + offset_sec
            segments.append({"start": start, "end": end, "text": alt.transcript})

        return segments

    def transcribe(self, audio_path: Path) -> list[dict]:
        """
        Chunk the audio into 55-second slices, transcribe each via Google STT,
        and return combined segments with accurate timestamps.
        """
        self._load_client()

        duration = get_duration(audio_path)
        total_chunks = int(duration // self.CHUNK_DURATION) + (1 if duration % self.CHUNK_DURATION else 0)
        print(f"  Google Cloud STT  |  {total_chunks} chunks  |  lang: {self._bcp47()}  |  {duration/60:.1f} min")

        all_segments = []
        offset = 0.0

        with tqdm(
            total=total_chunks,
            unit="chunk",
            desc="  Google STT",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total} chunks  [{elapsed}<{remaining}]",
            ncols=80,
        ) as pbar:
            while offset < duration:
                chunk_dur = min(self.CHUNK_DURATION, duration - offset)
                chunk_path = extract_chunk(audio_path, offset, chunk_dur)
                segments = self._transcribe_chunk(chunk_path, offset)
                all_segments.extend(segments)
                offset += self.CHUNK_DURATION
                pbar.update(1)

        return all_segments


# ---------------------------------------------------------------------------
# Segment splitting
# ---------------------------------------------------------------------------

def split_segments(segments: list[dict], max_duration: float) -> list[dict]:
    """
    Re-cut segments that exceed max_duration seconds, splitting at word boundaries.
    Segments without word data (e.g. from cloud engine) are passed through unchanged.
    """
    result = []
    for seg in segments:
        words = seg.get("words")
        if not words or (seg["end"] - seg["start"]) <= max_duration:
            result.append({"start": seg["start"], "end": seg["end"], "text": seg["text"]})
            continue

        # Greedily accumulate words into chunks, flushing when max_duration would be exceeded
        chunk_words = []
        chunk_start = words[0].start

        for word in words:
            if chunk_words and (word.end - chunk_start) > max_duration:
                text = "".join(w.word for w in chunk_words).strip()
                result.append({"start": chunk_start, "end": chunk_words[-1].end, "text": text})
                chunk_words = [word]
                chunk_start = word.start
            else:
                chunk_words.append(word)

        if chunk_words:
            text = "".join(w.word for w in chunk_words).strip()
            result.append({"start": chunk_start, "end": chunk_words[-1].end, "text": text})

    return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_transcriber(engine: str, model: str, language: str | None, credentials: str | None, device: str = "auto", max_duration: float | None = None):
    """Return the appropriate transcriber based on user choice."""
    if engine == "local":
        return LocalTranscriber(model=model, language=language, device=device, max_duration=max_duration)
    elif engine == "cloud":
        return CloudTranscriber(credentials_path=credentials, language=language or "en")
    else:
        raise ValueError(f"Unknown engine '{engine}'. Choose 'local' or 'cloud'.")
