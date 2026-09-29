"""The SMS people get when a job's details unlock, in each person's own language.

NEEDS A NATIVE-SPEAKER CHECK: the isiZulu and isiXhosa wording below is a first draft. P3 owns
SMS templates ("SMS templates in en, zu, xh"); when theirs are on main, use them instead.
"""

from fixa_api.models import Customer, Job, Provider

# {name}: the other person's first name. {phone} and {address} are shared only now that both
# sides have said yes.
TO_CUSTOMER = {
    "en": "Fixa: {name} confirmed your job. Their number: {phone}.",
    "zu": "Fixa: U-{name} uqinisekise umsebenzi wakho. Inombolo yakhe: {phone}.",
    "xh": "Fixa: U-{name} uqinisekise umsebenzi wakho. Inombolo yakhe: {phone}.",
}
TO_PROVIDER = {
    "en": "Fixa: {name} confirmed your job. Number: {phone}. Address: {address}.",
    "zu": "Fixa: U-{name} uqinisekise umsebenzi wakho. Inombolo: {phone}. Ikheli: {address}.",
    "xh": "Fixa: U-{name} uqinisekise umsebenzi wakho. Inombolo: {phone}. Ikheli: {address}.",
}
FALLBACK_LANG = "en"


def details_unlocked_messages(
    job: Job, customer: Customer, provider: Provider
) -> list[tuple[str, str]]:
    """(phone number to send to, text) for the customer and for the provider."""
    to_customer = TO_CUSTOMER.get(customer.lang, TO_CUSTOMER[FALLBACK_LANG]).format(
        name=provider.display_name, phone=provider.phone
    )
    to_provider = TO_PROVIDER.get(provider.lang, TO_PROVIDER[FALLBACK_LANG]).format(
        name=customer.display_name, phone=customer.phone, address=job.address
    )
    return [(customer.phone, to_customer), (provider.phone, to_provider)]


# Sent to the customer of a job a provider logged from before they joined. The customer replies
# "YES <code>" (or NO), and adds REF if they agree to be listed as a reference.
# {provider}: the provider's first name. {task}: what was done, already cleaned of contact details.
OFF_APP_CONFIRMATION = {
    "en": (
        "Fixa: {provider} says they did {task} for you in {suburb} on {date}. "
        "Reply YES {code} to confirm or NO {code}. Add REF if we may list you as a reference."
    ),
    "zu": (
        "Fixa: U-{provider} uthi wenze {task} e-{suburb} ngo-{date}. "
        "Phendula YEBO {code} ukuqinisekisa noma CHA {code}. "
        "Engeza REF uma uvuma ukubalwa njengomuntu ongaqinisekisa."
    ),
    "xh": (
        "Fixa: U-{provider} uthi wenze {task} e-{suburb} ngo-{date}. "
        "Phendula EWE {code} ukuqinisekisa okanye HAYI {code}. "
        "Yongeza REF ukuba uyavuma ukubalwa njengomntu ongangqinela."
    ),
}


def off_app_confirmation_message(
    lang: str, provider_name: str, task: str, suburb: str, date: str, code: str
) -> str:
    template = OFF_APP_CONFIRMATION.get(lang, OFF_APP_CONFIRMATION[FALLBACK_LANG])
    return template.format(provider=provider_name, task=task, suburb=suburb, date=date, code=code)
