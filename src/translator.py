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


def _call_with_retry(fn, *args, **kwargs):
    """Retry a function up to _MAX_RETRIES times on failure."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == _MAX_RETRIES:
                raise
            wait = 2 ** attempt
            print(f"    Retry {attempt}/{_MAX_RETRIES} in {wait}s: {e}")
            time.sleep(wait)


def _translate_batch(translator, texts: list[str]) -> list[str]:
    """Translate a batch of texts and return translated list."""
    if not texts:
        return []
    
    combined = _SEP.join(texts)
    translated_combined = _call_with_retry(
        translator.translate,
        combined,
    )
    
    # Split back by separator, handling potential spacing variations
    translated = [t.strip() for t in translated_combined.split(_SEP)]
    
    # Pad with empty strings if splitting didn't preserve count
    while len(translated) < len(texts):
        translated.append("")
    
    return translated[:len(texts)]


def translate_segments(
    segments: list[dict],
    target_lang: str = "en",
    source_lang: str = "auto",
) -> list[dict]:
    """
    Translate segment texts to target language.
    
    Args:
        segments: List of segment dicts with 'start', 'end', 'text' keys
        target_lang: Target language code (e.g., 'en', 'fr', 'ja')
        source_lang: Source language code or 'auto' for auto-detection
        
    Returns:
        List of translated segments with same structure
    """
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        raise OSError(
            "deep-translator is not installed. Run:  pip install deep-translator"
        )
    
    if not segments:
        return []
    
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    
    # Collect all texts to translate
    texts = [seg.get("text", "") for seg in segments]
    
    # Translate in batches
    translated_texts = []
    total_batches = (len(texts) + _BATCH_SIZE - 1) // _BATCH_SIZE
    
    with tqdm(
        total=len(texts),
        unit="text",
        desc=f"  Translating to {target_lang}",
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total}  [{elapsed}<{remaining}]",
        ncols=80,
    ) as pbar:
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i:i + _BATCH_SIZE]
            translated_batch = _translate_batch(translator, batch)
            translated_texts.extend(translated_batch)
            pbar.update(len(batch))
    
    # Reconstruct segments with translated text
    result = []
    for seg, translated_text in zip(segments, translated_texts):
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": translated_text,
        })
    
    return result