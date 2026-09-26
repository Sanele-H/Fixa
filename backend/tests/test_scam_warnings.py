"""Role 3's to-do list for scam warnings. Expected to fail until find_scam_warnings exists."""

import pytest

from fixa.safety.scam_warnings import ScamWarning, find_scam_warnings

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="TODO Role 3: scam warnings")


@pytest.mark.parametrize(
    ("message", "expected_warning"),
    [
        ("Please pay a R200 deposit first before I come", ScamWarning.UPFRONT_PAYMENT),
        ("Send me the OTP you just got", ScamWarning.SECRET_CODE_REQUEST),
        ("Pay here: http://bit.ly/abc", ScamWarning.LINK),
        # TODO: the same in Afrikaans and isiZulu
    ],
)
def test_suspicious_requests_raise_a_warning(message, expected_warning):
    assert expected_warning in find_scam_warnings(message)


def test_normal_quote_raises_no_warning():
    assert find_scam_warnings("Ek kan dit regmaak vir R450, Dinsdag om 10:00.") == []
