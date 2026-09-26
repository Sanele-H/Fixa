"""Languages the app can show and translate between.

TODO (whole team, Day 1): pick 2 or 3 pilot languages for the pilot area and mark them.
In Joburg, Sesotho, Setswana and Sepedi may matter more than isiXhosa.

Codes are ISO 639 codes, which Google Translate also uses. Other backends map them
(e.g. NLLB uses "zul_Latn"); keep that mapping inside the backend.
"""

LANGUAGE_NAMES_BY_CODE: dict[str, str] = {
    "en": "English",
    "af": "Afrikaans",
    "zu": "isiZulu",
    "xh": "isiXhosa",
    "st": "Sesotho",
    "tn": "Setswana",
    "nso": "Sepedi",
}

PILOT_LANGUAGE_CODES: tuple[str, ...] = ("af", "zu", "en")


def is_supported_language(language_code: str) -> bool:
    """Return True if the app knows this language code."""
    return language_code in LANGUAGE_NAMES_BY_CODE
