"""The 30-message translation test scores a failed translation as a failure, never as kept."""

import pytest

from lang.backends import TranslationFailedError
from lang.translation_test import TestMessage, run_message

PRICE_MESSAGE = TestMessage(
    id="price", lang="zu", target_lang="en", text="Kubiza R450", must_keep_numbers=["R450"]
)


class RateLimitedBackend:
    def translate(self, text, target_lang, source_lang):
        raise TranslationFailedError("rate limited")


@pytest.fixture(autouse=True)
def rate_limited_backend(monkeypatch):
    monkeypatch.setattr("lang.translation_test.get_backend", lambda name: RateLimitedBackend())


@pytest.mark.parametrize("use_protection", [True, False])
def test_a_failed_translation_keeps_nothing_and_does_not_stop_the_run(use_protection):
    result = run_message(PRICE_MESSAGE, "claude", use_protection)
    assert result.failed is True
    assert result.numbers_kept is False
