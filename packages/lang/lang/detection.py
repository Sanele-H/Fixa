"""detect_language(): which language a message is really written in.

People often keep the app in English but write in isiZulu or isiXhosa, so the sender's language
setting alone mislabels their messages, and the reader is never offered a translation. Three
steps, cheapest first:

1. Word markers settle isiZulu versus isiXhosa. The two are close, and Azure mixes them up: on
   data/test_messages.json it called 7 of 18 isiZulu messages isiXhosa or something else, and
   "Ngizofika kusasa" English. A few words tell them apart, starting with "I" (isiZulu ngi-,
   isiXhosa ndi-). On the same messages the markers never picked the wrong language.
2. Text too short to judge ("ok", "R450") keeps the sender's setting.
3. The backend's detector (Azure) decides the rest. It's trusted when it's sure a text is
   English. When it says isiZulu or isiXhosa, the sender's setting wins if it's one of those two,
   since Azure confuses them; otherwise its guess is the best there is.

Anything that fails keeps the sender's setting, which is what every message used before.
Answers are cached, since job pages read the same quote notes every few seconds.
"""

import logging
import re
from collections import OrderedDict

from lang.backends import BackendDetection, get_backend
from lang.models import Lang
from lang.protection import protect
from lang.safety import HIDDEN_CONTACT_TEXT

logger = logging.getLogger(__name__)

WORD_PATTERN = re.compile(r"[a-z]+")
VALUE_PLACEHOLDER_PATTERN = re.compile(r"\[\[\d+\]\]")

# Markers for P3's isiZulu and isiXhosa speaker to check and extend. Only words that belong to
# one language: "kodwa" and "uxolo", used in both, are left out on purpose. "ewe" and "yam" are
# also English words, but rare in chat about a job.
ZULU_PREFIXES = ("ngi", "angi")  # "I": ngi-fika (I arrive), angi-kwazi (I can't)
XHOSA_PREFIXES = ("ndi", "andi")  # "I": ndi-za (I'm coming), andi-kwazi (I can't)
ZULU_WORDS = frozenset({"futhi", "kusasa", "namuhla", "yebo", "yami", "manje", "lapho", "sawubona"})
XHOSA_WORDS = frozenset(
    {"kwaye", "ngomso", "namhlanje", "ewe", "yam", "ngoku", "apho", "molo", "nceda", "enkosi"}
)

# Below this many letters (values and hidden contacts removed), detectors guess wildly.
MIN_LETTERS_TO_DETECT = 8
# Azure scored every real English message 0.96 or more, and short isiZulu words 0.61.
MIN_ENGLISH_SCORE = 0.8
NGUNI_LANGS: frozenset[Lang] = frozenset({"zu", "xh"})

# Each text is detected once per sender setting (the fallback depends on it).
DETECTION_CACHE_MAX_ENTRIES = 5000
_detection_cache: OrderedDict[tuple[str, str], Lang] = OrderedDict()


def detect_language(text: str, sender_lang: Lang) -> Lang:
    """The language `text` is written in, falling back to `sender_lang`, the sender's setting.

    Pass the message after scan_message(), so hidden contact details never reach the detector.
    Values (prices, times, phone numbers) and the hidden-contact marker are removed before
    detecting, since they say nothing about the language. Never raises: if the detector fails,
    the sender's setting is used, and that answer isn't cached so the next read tries again.
    """
    cache_key = (text, sender_lang)
    if cache_key in _detection_cache:
        _detection_cache.move_to_end(cache_key)
        return _detection_cache[cache_key]
    try:
        detected_lang = detect_uncached(text, sender_lang)
    except Exception:  # A missing key, a network error, an odd reply: chat must never break
        logger.warning("Language detection failed, keeping the sender's setting", exc_info=True)
        return sender_lang
    remember_detection(cache_key, detected_lang)
    return detected_lang


def detect_uncached(text: str, sender_lang: Lang) -> Lang:
    """The three steps at the top of this file. Raises if the backend's detector fails."""
    words = remove_values(text)
    marker_lang = detect_by_markers(words)
    if marker_lang:
        return marker_lang
    if count_letters(words) < MIN_LETTERS_TO_DETECT:
        return sender_lang
    return choose_language(get_backend().detect(words), sender_lang)


def remove_values(text: str) -> str:
    """The text without values or the hidden-contact marker: only the words that show language."""
    without_hidden = text.replace(HIDDEN_CONTACT_TEXT, " ")
    return VALUE_PLACEHOLDER_PATTERN.sub(" ", protect(without_hidden).text).strip()


def count_letters(text: str) -> int:
    return sum(character.isalpha() for character in text)


def detect_by_markers(text: str) -> Lang | None:
    """isiZulu or isiXhosa when one has more marker words than the other, else None."""
    words = WORD_PATTERN.findall(text.lower().replace("-", " "))
    zulu_count = sum(word.startswith(ZULU_PREFIXES) or word in ZULU_WORDS for word in words)
    xhosa_count = sum(word.startswith(XHOSA_PREFIXES) or word in XHOSA_WORDS for word in words)
    if zulu_count > xhosa_count:
        return "zu"
    if xhosa_count > zulu_count:
        return "xh"
    return None


def choose_language(detection: BackendDetection | None, sender_lang: Lang) -> Lang:
    """Weighs the backend's guess against the sender's setting (see the steps at the top)."""
    if detection is None:
        return sender_lang
    if detection.code == "en" and detection.score >= MIN_ENGLISH_SCORE:
        return "en"
    if detection.code == "zu" or detection.code == "xh":
        return sender_lang if sender_lang in NGUNI_LANGS else detection.code
    return sender_lang


def remember_detection(cache_key: tuple[str, str], detected_lang: Lang) -> None:
    """Keep an answer, dropping the oldest once the cache is full."""
    _detection_cache[cache_key] = detected_lang
    if len(_detection_cache) > DETECTION_CACHE_MAX_ENTRIES:
        _detection_cache.popitem(last=False)
