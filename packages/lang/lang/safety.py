"""scan_message(): hide contact details and warn about scams before a chat message is shown.

People try to swap numbers early so they can deal off the app, and they disguise them to get past a
simple filter: "o82 one two three…", "zero eight two double one…", "nomsa at gmail dot com". So
every word that can stand for a digit is turned into one first, and any run of 9 or more digits in
a row is a phone number. Contact details stay hidden until the job is confirmed; scam warnings
always apply.

Run it before translate(), so contact details never reach a translation service, and store its
safe_text as the message's original too, so "See original" can't leak a number.
"""

import json
import re
from pathlib import Path

from lang.models import Finding, Lang, SafetyResult

HIDDEN_CONTACT_TEXT = "[contact hidden until the job is confirmed]"
MIN_PHONE_DIGITS = 9  # 082 123 4567 has 10; 9 allows for one missed digit

NUMBER_WORDS_PATH = Path(__file__).resolve().parents[3] / "data" / "number_words.json"
FALLBACK_NUMBER_WORDS = {
    "en": {
        "0": ["zero", "oh", "nought"],
        "1": ["one"],
        "2": ["two"],
        "3": ["three"],
        "4": ["four"],
        "5": ["five"],
        "6": ["six"],
        "7": ["seven"],
        "8": ["eight"],
        "9": ["nine"],
    }
}
# "double two" is 22 and "triple five" is 555, the way South Africans read out numbers.
REPEAT_WORDS = {"double": 2, "triple": 3}
# Letters that look like digits inside a number: "o82", "O82", "0l2"
LOOKALIKE_DIGITS = str.maketrans({"o": "0", "O": "0", "l": "1", "I": "1"})
LOOKALIKE_NUMBER_PATTERN = re.compile(r"^[0-9oOlI]+$")

# A token is a word, a number (with a leading + for +27, or starting with a look-alike letter as in
# "o82") or a single other character. Letters and digits are split apart, because isiZulu and
# isiXhosa glue prefixes straight onto numbers: "ngu0821234567" is "ngu" + "0821234567".
TOKEN_PATTERN = re.compile(r"\+?\d[0-9oOlI]*|[oOlI]+\d[0-9oOlI]*|[^\W\d_]+|[^\w\s]")
# What may sit between the digits of one phone number. A colon ends it, and so does a comma
# followed by a space, so "10:00, 082…" hides only the number, but "082,123,4567" is one number.
RUN_JOINERS = {"-", ".", "(", ")", "/", "+"}
COMMA = ","

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
SPOKEN_EMAIL_PATTERN = re.compile(
    r"\b[\w.]+\s*(?:\(at\)|\[at\]|\bat\b)\s*"
    r"(?:gmail|yahoo|outlook|hotmail|icloud|webmail|mweb|telkomsa)"
    r"\s*(?:\(dot\)|\[dot\]|\bdot\b|\.)\s*(?:com|co\s*\.?\s*za|net)\b",
    re.IGNORECASE,
)
LINK_PATTERN = re.compile(
    r"(?:https?://|www\.)\S+|\bwa\.me/\S+|\b[\w-]+\.(?:co\.za|com|net|org|link|ly|me)(?:/\S*)?",
    re.IGNORECASE,
)
STREET_WORDS = "street|st|road|rd|avenue|ave|drive|dr|crescent|cres|lane|close|straat|weg|laan"
ADDRESS_PATTERN = re.compile(
    rf"(?<!\d)\d{{1,5}}[a-z]?\s+(?:[A-Z][\w'-]*\s+){{1,3}}(?:{STREET_WORDS})\b\.?", re.IGNORECASE
)

# Scam warnings are codes; the app shows each one in the reader's language.
SCAM_WARNING_UPFRONT_PAYMENT = "upfront_payment"
SCAM_WARNING_ONE_TIME_PIN = "one_time_pin"
SCAM_WARNING_SUSPICIOUS_LINK = "suspicious_link"
# What the app shows for each warning, in the reader's language. Written by P3 (isiZulu and
# isiXhosa as a first-language speaker).
SCAM_WARNING_TEXTS: dict[str, dict[str, str]] = {
    SCAM_WARNING_UPFRONT_PAYMENT: {
        "en": "Be careful: never pay a deposit before the job is confirmed on Fixa. "
        "Pay when the work is done.",
        "zu": "Qaphela: ungalokothi ukhokhe idiphozi ngaphambi kokuthi umsebenzi uqinisekiswe "
        "ku-Fixa. Khokha uma umsebenzi usuphelile.",
        "xh": "Qaphela: ungaze uhlawule idiphozithi ngaphambi kokuba umsebenzi uqinisekiswe "
        "kwi-Fixa. Hlawula xa umsebenzi uqityiwe.",
    },
    SCAM_WARNING_ONE_TIME_PIN: {
        "en": "Never share a one-time PIN or code. Fixa will never ask you for it.",
        "zu": "Ungalokothi wabelane ngephinikhodi yesikhathi esisodwa noma ikhodi. "
        "UFixa akasoze akucela.",
        "xh": "Ungaze wabelane nge-PIN yexesha elinye okanye ikhowudi. UFixa soze akucele.",
    },
    SCAM_WARNING_SUSPICIOUS_LINK: {
        "en": "Be careful with links from people you don't know. "
        "Don't enter your personal details.",
        "zu": "Qaphela izixhumanisi ezivela kubantu ongabazi. Ungafaki imininingwane yakho siqu.",
        "xh": "Lumka ngamakhonkco abantu ongabaziyo. Ungafaki iinkcukacha zakho.",
    },
}
# isiZulu and isiXhosa phrases need a first-language check (P3 is the isiZulu speaker).
SCAM_PHRASE_PATTERNS: dict[str, re.Pattern[str]] = {
    SCAM_WARNING_UPFRONT_PAYMENT: re.compile(
        r"\b(?:deposit|upfront|pay (?:me )?first|pay before|send (?:me )?(?:money|cash)|"
        r"e-?wallet|cash ?send|instant money|airtime|voucher|call-?out fee first|"
        r"idiphozithi|idiphozi|idipozithi|khokha kuqala|khokhela kuqala|ngithumele imali|"
        r"thumela imali|"
        r"hlawula kuqala|ndithumelele imali)\b",
        re.IGNORECASE,
    ),
    SCAM_WARNING_ONE_TIME_PIN: re.compile(
        r"\b(?:otp|one[- ]time[- ]pin|pin(?: code)?|verification code|"
        r"the code (?:you|u) (?:got|received)|iphinikhodi|ikhodi oyitholile|ikhowudi)\b",
        re.IGNORECASE,
    ),
}


def load_number_words() -> dict[str, str]:
    """Map every digit word in data/number_words.json (all languages) to its digit."""
    try:
        number_words = json.loads(NUMBER_WORDS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        number_words = FALLBACK_NUMBER_WORDS
    word_to_digit: dict[str, str] = {}
    for lang_code, digits in number_words.items():
        if lang_code.startswith("_"):
            continue
        for digit, words in digits.items():
            for word in words:
                word_to_digit[word.lower()] = digit
    return word_to_digit


WORD_TO_DIGIT = load_number_words()


def token_to_digits(token: str) -> str | None:
    """The digits a token stands for ("082" → "082", "o82" → "082", "eight" → "8"), else None."""
    if token.startswith("+") and token[1:].isdigit():
        return token[1:]
    if token.isdigit():
        return token
    if LOOKALIKE_NUMBER_PATTERN.match(token) and any(char.isdigit() for char in token):
        return token.translate(LOOKALIKE_DIGITS)
    return WORD_TO_DIGIT.get(token.lower())


def is_digit_at(text: str, position: int) -> bool:
    """True when the character at position is a digit, as after the commas in "082,123,4567"."""
    return position < len(text) and text[position].isdigit()


def find_phone_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of runs that add up to a phone number, however it's written."""
    spans: list[tuple[int, int]] = []
    run_start: int | None = None
    run_end = 0
    run_digits = ""
    pending_repeat = 1

    def close_run() -> None:
        if run_start is not None and len(run_digits) >= MIN_PHONE_DIGITS:
            spans.append((run_start, run_end))

    for match in TOKEN_PATTERN.finditer(text):
        token = match.group()
        repeat = REPEAT_WORDS.get(token.lower())
        digits = token_to_digits(token)
        if repeat and run_start is not None:
            pending_repeat = repeat
        elif repeat:
            run_start, run_end, run_digits, pending_repeat = match.start(), match.end(), "", repeat
        elif digits is not None:
            if run_start is None:
                run_start, run_digits = match.start(), ""
            run_digits += digits[0] * pending_repeat + digits[1:]
            run_end = match.end()
            pending_repeat = 1
        elif token in RUN_JOINERS and run_start is not None:
            continue
        elif token == COMMA and run_start is not None and is_digit_at(text, match.end()):
            continue
        else:
            close_run()
            run_start, run_digits, pending_repeat = None, "", 1
    close_run()
    return spans


def find_contact_findings(text: str) -> list[Finding]:
    """Every phone number, email, link and street address in the text, left to right.

    Emails and links are found first, so "wa.me/27821234567" counts as a link, not a phone.
    """
    findings: list[Finding] = []

    def add_if_new(kind: str, start: int, end: int) -> None:
        if not any(start < found.end and found.start < end for found in findings):
            findings.append(Finding(kind=kind, start=start, end=end))

    for kind, pattern in (
        ("email", EMAIL_PATTERN),
        ("email", SPOKEN_EMAIL_PATTERN),
        ("link", LINK_PATTERN),
    ):
        for match in pattern.finditer(text):
            add_if_new(kind, match.start(), match.end())
    for start, end in find_phone_spans(text):
        add_if_new("phone", start, end)
    for match in ADDRESS_PATTERN.finditer(text):
        add_if_new("address", match.start(), match.end())
    return sorted(findings, key=lambda finding: finding.start)


def find_scam_warnings(text: str, findings: list[Finding]) -> list[str]:
    """Warning codes for scam patterns: upfront payment, one-time PINs and links."""
    warnings = [code for code, pattern in SCAM_PHRASE_PATTERNS.items() if pattern.search(text)]
    if any(finding.kind == "link" for finding in findings):
        warnings.append(SCAM_WARNING_SUSPICIOUS_LINK)
    return warnings


def hide_findings(text: str, findings: list[Finding]) -> str:
    """Replace each finding's span with the hidden-contact text."""
    pieces: list[str] = []
    position = 0
    for finding in findings:
        pieces.append(text[position : finding.start])
        pieces.append(HIDDEN_CONTACT_TEXT)
        position = finding.end
    pieces.append(text[position:])
    return "".join(pieces)


def scan_message(text: str, lang: Lang, contacts_unlocked: bool) -> SafetyResult:
    """Hide phones, emails, links and addresses (however they're disguised) and warn about scams.

    Contact details stay hidden until contacts_unlocked is True (the job is confirmed). Scam
    warnings apply either way. lang is the sender's language; number words from every language
    are checked, since people mix languages.
    """
    findings = find_contact_findings(text)
    scam_warnings = find_scam_warnings(text, findings)
    if contacts_unlocked:
        return SafetyResult(safe_text=text, findings=findings, scam_warnings=scam_warnings)
    return SafetyResult(
        safe_text=hide_findings(text, findings), findings=findings, scam_warnings=scam_warnings
    )


def get_scam_warning_texts(scam_warnings: list[str], lang: Lang) -> list[str]:
    """The warning text for each code, in the reader's language (English if a text is missing)."""
    return [
        SCAM_WARNING_TEXTS[code].get(lang) or SCAM_WARNING_TEXTS[code]["en"]
        for code in scam_warnings
        if code in SCAM_WARNING_TEXTS
    ]
