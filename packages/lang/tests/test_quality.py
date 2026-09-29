"""The cheap checks catch the failures Sanele's Azure and Gemini test found."""

from lang.quality import (
    FLAG_REASON_LENGTH_MISMATCH,
    FLAG_REASON_NOT_TRANSLATED,
    FLAG_REASON_REPEATED_TEXT,
    find_quality_problem,
)


def test_a_good_translation_passes():
    assert (
        find_quality_problem("Ngingafika ngoLwesibili, [[0]].", "I can come on Tuesday, [[0]].")
        is None
    )


def test_english_handed_back_for_setswana_is_not_translated():
    source = "My geyser is leaking, water everywhere"
    assert find_quality_problem(source, "My geyser is leaking - water everywhere!") == (
        FLAG_REASON_NOT_TRANSLATED
    )


def test_a_short_reply_may_come_back_unchanged():
    assert find_quality_problem("OK [[0]]", "OK [[0]]") is None


def test_one_word_for_a_whole_sentence_is_a_length_mismatch():
    source = "The electricity keeps tripping when I switch on the kettle"
    assert find_quality_problem(source, "Geile") == FLAG_REASON_LENGTH_MISMATCH


def test_short_texts_skip_the_length_check():
    assert find_quality_problem("Yebo", "Yes") is None


def test_a_backend_stuck_in_a_loop_is_repeated_text():
    source = "Water is everywhere in the kitchen and the bathroom"
    looping = "go ne go na le metsi gongwe le gongwe go ne go na le metsi gongwe le gongwe"
    assert find_quality_problem(source, looping) == FLAG_REASON_REPEATED_TEXT
