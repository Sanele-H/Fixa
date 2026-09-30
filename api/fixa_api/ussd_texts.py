"""The USSD menu a customer on a feature phone sees to confirm a job, in their own language.

NEEDS A NATIVE-SPEAKER CHECK: the isiZulu and isiXhosa wording is a first draft. Each screen has
to stay short (USSD screens are about 180 characters).
"""

FALLBACK_LANG = "en"

# {provider}: the provider's first name. {task}, {suburb}, {date}: as logged, already cleaned.
TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "which_job": "Fixa: which job?",
        "ask": "Fixa: {provider} says they did {task} for you in {suburb} on {date}.\n"
        "1. Yes, that is right\n2. No",
        "ask_reference": "May we list you as a reference for {provider}?\n1. Yes\n2. No",
        "confirmed": "Thank you. The job is confirmed.",
        "declined": "Thank you. We marked that job as not done.",
        "nothing_waiting": "No job is waiting for your confirmation.",
        "invalid": "That was not a valid choice. Dial again to try again.",
    },
    "zu": {
        "which_job": "Fixa: yimuphi umsebenzi?",
        "ask": "Fixa: U-{provider} uthi wenze {task} e-{suburb} ngo-{date}.\n"
        "1. Yebo, kunjalo\n2. Cha",
        "ask_reference": (
            "Singakufaka ohlwini njengomuntu ongaqinisekisa u-{provider}?\n1. Yebo\n2. Cha"
        ),
        "confirmed": "Siyabonga. Umsebenzi uqinisekisiwe.",
        "declined": "Siyabonga. Siphawule ukuthi umsebenzi awenziwanga.",
        "nothing_waiting": "Alukho umsebenzi olindele ukuqinisekiswa kwakho.",
        "invalid": "Lokho akukona ukukhetha okufanele. Shayela futhi ukuzama kabusha.",
    },
    "xh": {
        "which_job": "Fixa: nguwuphi umsebenzi?",
        "ask": "Fixa: U-{provider} uthi wenze {task} e-{suburb} ngo-{date}.\n"
        "1. Ewe, kunjalo\n2. Hayi",
        "ask_reference": (
            "Singakufaka kuluhlu njengomntu ongangqinela u-{provider}?\n1. Ewe\n2. Hayi"
        ),
        "confirmed": "Enkosi. Umsebenzi uqinisekisiwe.",
        "declined": "Enkosi. Siphawule ukuba lo msebenzi awenziwanga.",
        "nothing_waiting": "Akukho msebenzi ulindele ukuqinisekiswa kwakho.",
        "invalid": "Oko akukhona ukhetho olufanelekileyo. Shayela kwakhona ukuzama kwakhona.",
    },
}
ANSWER_YES = "1"
ANSWER_NO = "2"
MAX_JOBS_LISTED = 3
MENU_TASK_LIMIT = 35  # keeps a screen of several jobs short enough


def text_for(lang: str, key: str, **values: str) -> str:
    template = (TEXTS.get(lang) or TEXTS[FALLBACK_LANG])[key]
    return template.format(**values)
