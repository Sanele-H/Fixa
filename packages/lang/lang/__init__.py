"""Language and safety for Fixa (P3).

Owner: P3. Only P3 edits files in packages/lang/. P2's API imports this package.

Public functions (the contract; signatures change only with the team's agreement):
    translate(text, target_lang, source_lang=None)
        -> Translation(text, original, source_lang, flagged, flag_reason)
    understand_job(text, lang) -> JobIntent(trade, urgency, size, confidence)
    scan_message(text, lang, contacts_unlocked) -> SafetyResult(safe_text, findings, scam_warnings)
    extract_quote(text) -> Quote(amount_rands, when) | None

Data P3 owns: data/glossary.json, data/test_messages.json, data/number_words.json.

Step 0 (Day 1): stubs with the correct return types, so the API can import them.
"""
