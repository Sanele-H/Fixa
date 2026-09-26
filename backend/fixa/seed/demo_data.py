"""The people in the demo story.

Owner: Role 2. Role 4's simulation does not use this; it generates its own providers.

The demo needs:
- Mrs. van Wyk: an Afrikaans-only customer in Mondeor with a leaking geyser pipe.
- Nomsa: an isiZulu-first plumber with no reviews yet. She should win the newcomer slot.
- Enough established, well-rated plumbers that sort-by-rating would never show Nomsa.

All phone numbers and addresses are made up. Never put a real person's details here.

TODO (Role 2, Day 2): add the rest of the established plumbers, and a second customer
for testing that speaks another pilot language.
"""

from fixa.domain.models import ContactDetails, User, UserRole

DEMO_AREA = "Mondeor"


def create_demo_users() -> list[User]:
    """Return the seeded users, customers first. Called on startup and on demo reset."""
    return [
        User(
            id="customer-van-wyk",
            display_name="Mrs. van Wyk",
            role=UserRole.CUSTOMER,
            preferred_language="af",
            area=DEMO_AREA,
        ),
        User(
            id="provider-nomsa",
            display_name="Nomsa",
            role=UserRole.PROVIDER,
            preferred_language="zu",
            area=DEMO_AREA,
            trades=["plumbing"],
            service_areas=[DEMO_AREA],
            badges=["id_checked"],
        ),
        User(
            id="provider-established-1",
            display_name="TODO established plumber",
            role=UserRole.PROVIDER,
            preferred_language="en",
            area=DEMO_AREA,
            trades=["plumbing"],
            service_areas=[DEMO_AREA],
            badges=["id_checked"],
            completed_job_count=48,
            rating_sum=4.8 * 40,
            rating_count=40,
        ),
    ]


def create_demo_contact_details() -> list[ContactDetails]:
    """Return fake contact details for every seeded user. Revealed only after unlock."""
    return [
        ContactDetails(
            user_id="customer-van-wyk",
            phone_number="082 555 0101",
            street_address="12 Sample Street, Mondeor",
        ),
        ContactDetails(user_id="provider-nomsa", phone_number="071 555 0102"),
        ContactDetails(user_id="provider-established-1", phone_number="083 555 0103"),
    ]
