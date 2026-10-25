"""
Subtitle translation — pluggable engines, routed per detected source language.

Routing: translate_routing.txt (repo root) maps a detected source-language
code to an ordered chain of engine + key file lines (several lines for the
same language = try them in that order). When a key's quota/credit runs out
or it is rejected, it is skipped for the rest of the run and the next one in
the chain takes over; the free, keyless engine is always the last resort, and
any language not listed uses it directly. See that file's header comment for
the exact format, and E:\\API Key\\AGENTS.md for the 2-line key-file convention.

Adding a language later, or moving one to a better engine, is a one-line
edit to translate_routing.txt — no code change needed. Adding a brand-new
engine *type* means one new class here plus one registry entry.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from tqdm import tqdm

from src.srt_reader import read_srt
from src.srt_writer import write_srt
from src.utils import backup_if_exists

_BATCH_SIZE = 20
_MAX_RETRIES = 3
_ROUTING_FILE = Path(__file__).resolve().parent.parent / "translate_routing.txt"

# DeepL rejects a bare "en" as a *target* (source is fine unqualified).
# Add more overrides here if you start targeting other regional variants.
_DEEPL_TARGET_OVERRIDES = {"en": "EN-US"}


class KeyUnusableError(Exception):
    """A key can't be used this run (quota/credit used up, or rejected) — retrying won't help."""


def _is_key_unusable(e: Exception) -> bool:
    # deepl raises QuotaExceededException / AuthorizationException;
    # DeepSeekEngine raises KeyUnusableError for HTTP 401/402.
    name = type(e).__name__
    return isinstance(e, KeyUnusableError) or "Quota" in name or "Authorization" in name


def _call_with_retry(fn, *args, **kwargs):
    """Retry a function up to _MAX_RETRIES times on failure (not when the key is unusable)."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == _MAX_RETRIES or _is_key_unusable(e):
                raise
            wait = 2 ** attempt
            print(f"    Retry {attempt}/{_MAX_RETRIES} in {wait}s: {e}")
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

class DeepLEngine:
    """DeepL API — used for languages routed to it in translate_routing.txt."""

    name = "deepl"

    def __init__(self, key_file: Path):
        try:
            import deepl
        except ImportError:
            raise OSError("deepl is not installed. Run:  pip install deepl")

        lines = key_file.read_text(encoding="utf-8").splitlines()
        api_key = lines[0].strip() if lines else ""
        if not api_key:
            raise OSError(f"DeepL key file is empty: {key_file}")

        # The deepl client auto-selects the free/pro endpoint from the key's
        # ":fx" suffix, so the key file's optional line 2 (endpoint) isn't
        # needed here — it's informational, kept for the raw-REST checker.
        self._translator = deepl.Translator(api_key)

    def translate_batch(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not texts:
            return []
        deepl_target = _DEEPL_TARGET_OVERRIDES.get(target_lang.lower(), target_lang.upper())
        deepl_source = source_lang.upper() if source_lang and source_lang != "auto" else None

        results = _call_with_retry(
            self._translator.translate_text,
            texts,
            source_lang=deepl_source,
            target_lang=deepl_target,
        )
        return [r.text for r in results]


class DeepSeekEngine:
    """DeepSeek chat API (OpenAI-compatible) used as a translator, stdlib HTTP only."""

    name = "deepseek"
    _MODEL = "deepseek-chat"
    _DEFAULT_ENDPOINT = "https://api.deepseek.com"

    def __init__(self, key_file: Path):
        lines = key_file.read_text(encoding="utf-8").splitlines()
        self._api_key = lines[0].strip() if lines else ""
        if not self._api_key:
            raise OSError(f"DeepSeek key file is empty: {key_file}")
        # Line 2 may be the base URL or the full chat-completions URL — accept both.
        endpoint = (lines[1].strip() if len(lines) > 1 else "") or self._DEFAULT_ENDPOINT
        endpoint = endpoint.rstrip("/")
        self._url = endpoint if endpoint.endswith("/chat/completions") else endpoint + "/chat/completions"

    def _post(self, payload: dict) -> dict:
        import json
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 402:
                raise KeyUnusableError("DeepSeek: insufficient balance (HTTP 402)") from None
            if e.code == 401:
                raise KeyUnusableError("DeepSeek: key rejected (HTTP 401)") from None
            if e.code == 404:
                raise KeyUnusableError(f"DeepSeek: endpoint not found (HTTP 404) at {self._url}") from None
            raise RuntimeError(f"DeepSeek HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}") from None

    def _translate_once(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        import json

        source = source_lang if source_lang and source_lang != "auto" else "the source language"
        payload = {
            "model": self._MODEL,
            "temperature": 1.3,  # DeepSeek's recommended setting for translation
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": (
                    f"You translate film/TV subtitle lines from {source} to {target_lang}. "
                    "Lines are consecutive dialogue; use them as context. Keep each line short "
                    "and natural for subtitles. Input is a JSON object of numbered lines. Reply with "
                    'JSON only: {"translations": {"<same number>": "<translation>", ...}} with exactly '
                    "one entry per input number — never merge, split or skip lines."
                )},
                # Numbered keys (not a bare list) so a merged/split line shows up as a missing id.
                {"role": "user", "content": json.dumps(
                    {"lines": {str(n): text for n, text in enumerate(texts, 1)}}, ensure_ascii=False)},
            ],
        }
        data = self._post(payload)
        out = json.loads(data["choices"][0]["message"]["content"])["translations"]
        missing = [str(n) for n in range(1, len(texts) + 1) if str(n) not in out]
        if missing:
            raise ValueError(f"DeepSeek omitted line(s) {', '.join(missing[:5])} of {len(texts)}")
        return [str(out[str(n)]).strip() for n in range(1, len(texts) + 1)]

    def translate_batch(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not texts:
            return []
        return _call_with_retry(self._translate_once, texts, source_lang, target_lang)


class GoogleEngine:
    """Free deep-translator/Google Translate — no API key required. Fallback engine."""

    name = "google"
    _SEP = " ||| "  # delimiter that survives translation in most languages

    def __init__(self):
        self._sub_translators: dict[tuple[str, str], object] = {}

    def _get(self, source_lang: str, target_lang: str):
        key = (source_lang or "auto", target_lang)
        if key not in self._sub_translators:
            try:
                from deep_translator import GoogleTranslator
            except ImportError:
                raise OSError("deep-translator is not installed. Run:  pip install deep-translator")
            self._sub_translators[key] = GoogleTranslator(source=key[0], target=key[1])
        return self._sub_translators[key]

    def translate_batch(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not texts:
            return []
        translator = self._get(source_lang, target_lang)

        combined = self._SEP.join(texts)
        translated_combined = _call_with_retry(translator.translate, combined)

        translated = [t.strip() for t in translated_combined.split(self._SEP)]
        while len(translated) < len(texts):
            translated.append("")
        return translated[:len(texts)]


_ENGINES = {"deepl": DeepLEngine, "deepseek": DeepSeekEngine, "google": GoogleEngine}
_KEYED_ENGINES = (DeepLEngine, DeepSeekEngine)
_FREE = ("google", None)
_engine_cache: dict[str, object] = {}
# Chain entries ("engine:key_file") that can't be used for the rest of this run
# (quota used up, key rejected, key file missing) — the chain moves past them.
_exhausted: set[str] = set()


# ---------------------------------------------------------------------------
# Routing + language detection
# ---------------------------------------------------------------------------

def _load_routing() -> dict[str, list[tuple[str, Path | None]]]:
    """
    Parse translate_routing.txt into {lang: [(engine_name, key_file_or_None), ...]},
    keeping each language's lines in file order (= the order they are tried in).
    """
    routing: dict[str, list[tuple[str, Path | None]]] = {}
    if not _ROUTING_FILE.exists():
        return routing

    for line in _ROUTING_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        lang = parts[0].lower()
        engine = parts[1].lower()
        key_file = Path(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else None
        routing.setdefault(lang, []).append((engine, key_file))

    return routing


def _normalize_lang(code: str) -> str:
    """langdetect emits e.g. 'zh-cn'/'zh-tw' — normalize to the base code."""
    return code.lower().split("-")[0]


def detect_source_language(segments: list[dict]) -> str:
    """
    Detect the source language from a sample of segment texts (not per-line —
    single subtitle lines are often too short to detect reliably).
    Returns 'auto' if detection isn't possible.
    """
    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 0  # deterministic results
    except ImportError:
        raise OSError("langdetect is not installed. Run:  pip install langdetect")

    sample_texts = [seg.get("text", "").strip() for seg in segments[:30] if seg.get("text", "").strip()]
    sample = " ".join(sample_texts)[:2000]
    if not sample:
        return "auto"

    try:
        return _normalize_lang(detect(sample))
    except Exception:
        return "auto"


def get_translator(source_lang: str):
    """
    Return the first usable engine in the language's routing chain, skipping
    entries marked unusable this run. The free engine is always the last resort.
    """
    chain = _load_routing().get(source_lang, []) + [_FREE]

    for engine_name, key_file in chain:
        cache_key = f"{engine_name}:{key_file}"
        if cache_key in _exhausted:
            continue

        engine_cls = _ENGINES.get(engine_name)
        if engine_cls is None:
            print(f"  Unknown engine '{engine_name}' for '{source_lang}' in {_ROUTING_FILE.name}, skipping it.")
            _exhausted.add(cache_key)
            continue

        if cache_key not in _engine_cache:
            if engine_cls in _KEYED_ENGINES:
                if key_file is None or not key_file.exists():
                    print(f"  {engine_name} key file missing for '{source_lang}' ({key_file}), skipping it.")
                    _exhausted.add(cache_key)
                    continue
                try:
                    _engine_cache[cache_key] = engine_cls(key_file)
                except OSError as e:
                    print(f"  {e}; skipping {engine_name} for '{source_lang}'.")
                    _exhausted.add(cache_key)
                    continue
            else:
                _engine_cache[cache_key] = engine_cls()

        engine = _engine_cache[cache_key]
        engine.cache_key = cache_key
        return engine

    raise RuntimeError("No usable translation engine (even the free fallback failed to load).")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate_segments(
    segments: list[dict],
    target_lang: str = "en",
    source_lang: str | None = None,
) -> list[dict]:
    """
    Translate segment texts to target language.

    Source language is auto-detected from the segment text (unless explicitly
    given) and used to route to the right engine per translate_routing.txt.

    Args:
        segments: List of segment dicts with 'start', 'end', 'text' keys
        target_lang: Target language code (e.g., 'en', 'fr', 'ja')
        source_lang: Source language code, or None/'auto' to detect from text

    Returns:
        List of translated segments with same structure
    """
    if not segments:
        return []

    detected = source_lang if source_lang and source_lang != "auto" else detect_source_language(segments)
    engine = get_translator(detected)

    texts = [seg.get("text", "") for seg in segments]
    translated_texts: list[str] = []

    with tqdm(
        total=len(texts),
        unit="text",
        desc=f"  Translating {detected}->{target_lang} ({engine.name})",
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n}/{total}  [{elapsed}<{remaining}]",
        ncols=80,
    ) as pbar:
        i = 0
        while i < len(texts):
            batch = texts[i:i + _BATCH_SIZE]
            try:
                translated = engine.translate_batch(batch, source_lang=detected, target_lang=target_lang)
            except Exception as e:
                if not _is_key_unusable(e) or engine.cache_key == "google:None":
                    raise
                _exhausted.add(engine.cache_key)
                engine = get_translator(detected)
                tqdm.write(f"  Key unusable ({e}); switching to {engine.name} for the rest of this run.")
                pbar.set_description_str(f"  Translating {detected}->{target_lang} ({engine.name})")
                continue  # redo this batch with the next engine in the chain
            translated_texts.extend(translated)
            pbar.update(len(batch))
            i += _BATCH_SIZE

    result = []
    for seg, translated_text in zip(segments, translated_texts):
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": translated_text,
        })

    return result


def translate_existing_srt(srt_path: Path, target_lang: str, overwrite: bool = False) -> bool:
    """
    Load an existing .srt and translate it, writing "<stem>.<target_lang>.srt".

    If that translated file already exists: skipped unless *overwrite* is
    set, in which case the previous translation is backed up to
    "<name>.srt.bak" before being replaced.

    Returns True on success (including "already exists, skipped").
    """
    translated_path = srt_path.parent / f"{srt_path.stem}.{target_lang}.srt"

    if translated_path.exists():
        if not overwrite:
            print(f"  Translation already exists: {translated_path.name}. Skipping.")
            return True
        backup = backup_if_exists(translated_path)
        if backup:
            print(f"  Backed up existing translation -> {backup.name}")

    try:
        segments = read_srt(srt_path)
    except Exception as e:
        print(f"  Failed to read SRT: {e}")
        return False

    if not segments:
        print("  SRT file is empty, skipping translation.")
        return False

    try:
        translated = translate_segments(segments, target_lang=target_lang)
        count = write_srt(translated, translated_path)
        print(f"  {count} entries translated to {target_lang}.")
    except Exception as e:
        print(f"  Translation failed: {e}")
        return False

    return True
