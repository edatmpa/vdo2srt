"""
Subtitle translation via Google Translate (no API key required).
Segments are sent in batches to minimise HTTP round-trips.
"""

from __future__ import annotations

import time

from tqdm import tqdm

_BATCH_SIZE = 20
_SEP = " ||| "   # delimiter that survives translation in most languages
_MAX_RETRIES = 3


def _call_with_retry(fn, *args):
    """Call fn(*args), retrying up to _MAX_RETRIES times on any network error."""
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args)
        except Exception:
            if attempt < _MAX_RETRIES - 1:
                wait = 5 * (attempt + 1)
                print(f"\n  Network error, retrying in {wait}s...", end="", flush=True)
                time.sleep(wait)
            else:
                raise


def _translate_batch(translator, texts: list[str]) -> list[str]:
    """Translate a list of strings as a single request, split them back out."""
    sanitized = [t.replace(_SEP.strip(), " ") for t in texts]
    combined = _SEP.join(sanitized)
    translated = _call_with_retry(translator.translate, combined)
    parts = [p.strip() for p in translated.split(_SEP.strip())]
    if len(parts) == len(texts):
        return parts
    # Separator was mangled — fall back to one request per segment
    return [_call_with_retry(translator.translate, t) or t for t in texts]


def translate_segments(
    segments: list[dict],
    target_lang: str = "en",
    source_lang: str = "auto",
) -> list[dict]:
    """
    Translate the text of each segment to target_lang.
    Returns a new list of segments with the same timing but translated text.
    """
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        raise EnvironmentError(
            "deep-translator is not installed. Run:  pip install deep-translator"
        )

    translator = GoogleTranslator(source=source_lang, target=target_lang)
    texts = [seg["text"] for seg in segments]
    translated_texts: list[str] = []

    batches = [texts[i : i + _BATCH_SIZE] for i in range(0, len(texts), _BATCH_SIZE)]

    with tqdm(
        total=len(segments),
        unit="seg",
        desc=f"  Translating → {target_lang}",
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total} segs  [{elapsed}<{remaining}]",
        ncols=80,
    ) as pbar:
        for batch in batches:
            translated_texts.extend(_translate_batch(translator, batch))
            pbar.update(len(batch))

    return [
        {"start": seg["start"], "end": seg["end"], "text": t}
        for seg, t in zip(segments, translated_texts)
    ]
