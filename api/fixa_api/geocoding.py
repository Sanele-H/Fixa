"""Place names for a point on the map (reverse geocoding), for jobs that aren't at the customer's
home: a parent's house, a rental, a shop.

Live, this asks OpenStreetMap's Nominatim, and follows its usage policy
(https://operations.osmfoundation.org/policies/nominatim/): at most one request a second across
the whole server, answers cached, and a User-Agent that says who we are. The request is made
here on the server, never from the phone, so the policy holds however many people use the app.

GEOCODER=fake (the tests, or working offline) names the nearest seed suburb instead.
"""

import logging
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol

import httpx

from fixa_api.geo import distance_km
from ranking.seed.places import SUBURB_CENTRES

logger = logging.getLogger(__name__)

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
DEFAULT_USER_AGENT = "Fixa/0.1 (hackathon job marketplace; +https://fixa-2o94.onrender.com)"
SECONDS_BETWEEN_REQUESTS = 1.0  # Nominatim's absolute maximum is one request a second
REQUEST_TIMEOUT_SECONDS = 8
CACHE_SIZE = 2000
CACHE_DECIMALS = 4  # points within about 11 m share one cached answer
SOUTH_AFRICA_COUNTRY_CODE = "za"

# Nominatim's address parts, most local first: the first one present names the suburb.
SUBURB_ADDRESS_PARTS = (
    "suburb",
    "neighbourhood",
    "quarter",
    "city_district",
    "village",
    "town",
    "city",
)

# Some areas only have municipal wards mapped as suburbs ("Johannesburg Ward 39"). Nobody calls
# their street that, so such a name is skipped for the next part, usually the city.
WARD_NAME_PATTERN = re.compile(r"\bWard \d+\b", re.IGNORECASE)

# A rough box around South Africa. A pin outside it is refused before anything is looked up.
SOUTH_AFRICA_LATITUDE_RANGE = (-35.0, -22.0)
SOUTH_AFRICA_LONGITUDE_RANGE = (16.0, 33.0)


@dataclass(frozen=True)
class Place:
    """What a point on the map is called. suburb is public (shown on the job card); label is a
    street address, and is only ever shown to the job's two people once the job is confirmed."""

    suburb: str
    label: str


class PlaceLookupError(Exception):
    """The place service didn't answer (down, slow or refusing). Try again later."""


class Geocoder(Protocol):
    def find_place(self, lat: float, lng: float) -> Place | None:
        """The place at this point, or None when it isn't a place in South Africa."""


def is_in_south_africa(lat: float, lng: float) -> bool:
    """True for a point inside the rough box around South Africa. Nominatim's country code does
    the precise check (Lesotho and Eswatini sit inside the box)."""
    lowest_lat, highest_lat = SOUTH_AFRICA_LATITUDE_RANGE
    lowest_lng, highest_lng = SOUTH_AFRICA_LONGITUDE_RANGE
    return lowest_lat <= lat <= highest_lat and lowest_lng <= lng <= highest_lng


def read_suburb(address: dict[str, str]) -> str | None:
    """The most local name in a Nominatim address, such as "Orlando West", or None. Ward numbers
    are skipped (see WARD_NAME_PATTERN)."""
    names = (address.get(part) for part in SUBURB_ADDRESS_PARTS)
    return next((name for name in names if name and not WARD_NAME_PATTERN.search(name)), None)


def read_label(address: dict[str, str], suburb: str) -> str:
    """A short street address: "12 Vilakazi Street, Orlando West". Without a road, the suburb and
    town, since a pin in a field has no street."""
    street = " ".join(part for part in (address.get("house_number"), address.get("road")) if part)
    town = address.get("city") or address.get("town")
    parts = [street, suburb] if street else [suburb, town]
    return ", ".join(dict.fromkeys(part for part in parts if part))


def read_place(answer: dict) -> Place | None:
    """A Place from Nominatim's jsonv2 answer, or None for the sea, or outside South Africa."""
    address = answer.get("address") or {}
    if address.get("country_code") != SOUTH_AFRICA_COUNTRY_CODE:
        return None
    suburb = read_suburb(address)
    if suburb is None:
        return None
    return Place(suburb=suburb, label=read_label(address, suburb))


class NominatimGeocoder:
    """Nominatim's reverse lookup, one request a second at most, with answers cached.

    The lock and the cache belong to the class, not to one object, since a new geocoder is made
    for each request (see get_geocoder): the limit must hold across all of them.
    """

    _lock = threading.Lock()
    _last_request_at = 0.0  # time.monotonic() of the last request sent
    _cache: OrderedDict[tuple[float, float], Place | None] = OrderedDict()

    def __init__(self, user_agent: str, client: httpx.Client | None = None):
        self.user_agent = user_agent
        self.client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    def find_place(self, lat: float, lng: float) -> Place | None:
        """The cached answer for this point, or a fresh one from Nominatim. Raises
        PlaceLookupError when Nominatim can't answer; failures aren't cached."""
        cache_key = (round(lat, CACHE_DECIMALS), round(lng, CACHE_DECIMALS))
        with NominatimGeocoder._lock:
            if cache_key in NominatimGeocoder._cache:
                NominatimGeocoder._cache.move_to_end(cache_key)
                return NominatimGeocoder._cache[cache_key]
            self.wait_for_turn()
            place = self.request_place(*cache_key)
            self.update_cache(cache_key, place)
        return place

    def wait_for_turn(self) -> None:
        """Sleeps until a second has passed since the last request. Called holding the lock, so
        requests queue up one behind the other."""
        seconds_since_last = time.monotonic() - NominatimGeocoder._last_request_at
        if seconds_since_last < SECONDS_BETWEEN_REQUESTS:
            time.sleep(SECONDS_BETWEEN_REQUESTS - seconds_since_last)
        NominatimGeocoder._last_request_at = time.monotonic()

    def request_place(self, lat: float, lng: float) -> Place | None:
        """One reverse lookup, in English so suburb names match the rest of the app."""
        try:
            response = self.client.get(
                NOMINATIM_REVERSE_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "jsonv2",
                    "zoom": 18,
                    "addressdetails": 1,
                    "accept-language": "en",
                },
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()
            return read_place(response.json())
        except (httpx.HTTPError, ValueError) as problem:
            logger.warning("Nominatim lookup failed: %r", problem)
            raise PlaceLookupError from problem

    @staticmethod
    def update_cache(cache_key: tuple[float, float], place: Place | None) -> None:
        """Keeps the answer, dropping the least recently used one when the cache is full."""
        NominatimGeocoder._cache[cache_key] = place
        if len(NominatimGeocoder._cache) > CACHE_SIZE:
            NominatimGeocoder._cache.popitem(last=False)


class NearestSuburbGeocoder:
    """Offline stand-in: the nearest seed suburb, with no street. For tests and no-network work."""

    def find_place(self, lat: float, lng: float) -> Place | None:
        if not is_in_south_africa(lat, lng):
            return None
        suburb = min(
            SUBURB_CENTRES,
            key=lambda name: distance_km(lat, lng, *SUBURB_CENTRES[name]),
        )
        return Place(suburb=suburb, label=f"Pinned spot in {suburb}")


def get_geocoder() -> Geocoder:
    """Nominatim unless GEOCODER=fake. FastAPI dependency; tests replace it through GEOCODER."""
    if os.environ.get("GEOCODER", "nominatim") == "fake":
        return NearestSuburbGeocoder()
    return NominatimGeocoder(os.environ.get("NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT))
