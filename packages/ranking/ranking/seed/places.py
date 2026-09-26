"""Where seed users are: rough suburb centres, made-up exact spots, and distances between them.

A location is a (latitude, longitude) pair in degrees.
"""

import math

import numpy as np

# Real Johannesburg suburbs with rough centre points. People's exact spots are made up
# around these, so that distances in the demo look right.
SUBURB_CENTRES = {
    "Braamfontein": (-26.1929, 28.0305),
    "Parktown": (-26.1780, 28.0350),
    "Hillbrow": (-26.1880, 28.0470),
    "Berea": (-26.1830, 28.0540),
    "Yeoville": (-26.1830, 28.0650),
    "Newtown": (-26.2040, 28.0330),
    "Fordsburg": (-26.2050, 28.0200),
    "Mayfair": (-26.2030, 28.0100),
    "Auckland Park": (-26.1830, 28.0000),
    "Melville": (-26.1760, 28.0080),
    "Rosebank": (-26.1460, 28.0440),
    "Randburg": (-26.0940, 28.0060),
    "Sandton": (-26.1080, 28.0570),
    "Alexandra": (-26.1030, 28.0970),
    "Soweto": (-26.2490, 27.8540),
    "Tembisa": (-25.9960, 28.2270),
}
DEMO_SUBURB = "Braamfontein"  # where the demo customer lives

LOCATION_SPREAD_DEGREES = 0.004  # exact spots scatter about 400 m around a suburb's centre
COORDINATE_DECIMALS = 5  # about 1 m
EARTH_RADIUS_KM = 6371.0
KM_PER_DEGREE_OF_LATITUDE = 111.2


def create_location(rng: np.random.Generator, suburb: str) -> tuple[float, float]:
    """Creates a made-up exact spot near a suburb's centre."""
    centre_latitude, centre_longitude = SUBURB_CENTRES[suburb]
    latitude = centre_latitude + rng.normal(0.0, LOCATION_SPREAD_DEGREES)
    longitude = centre_longitude + rng.normal(0.0, LOCATION_SPREAD_DEGREES)
    return round(float(latitude), COORDINATE_DECIMALS), round(float(longitude), COORDINATE_DECIMALS)


def move_location(
    location: tuple[float, float], north_km: float, east_km: float
) -> tuple[float, float]:
    """Returns the spot the given distances north and east of a location."""
    latitude, longitude = location
    km_per_degree_of_longitude = KM_PER_DEGREE_OF_LATITUDE * math.cos(math.radians(latitude))
    return (
        round(latitude + north_km / KM_PER_DEGREE_OF_LATITUDE, COORDINATE_DECIMALS),
        round(longitude + east_km / km_per_degree_of_longitude, COORDINATE_DECIMALS),
    )


def get_location(row: dict) -> tuple[float, float]:
    """Returns the location stored on a user or job row."""
    return row["lat"], row["lng"]


def calculate_distance_km(start: tuple[float, float], end: tuple[float, float]) -> float:
    """Returns the straight-line (great-circle) distance between two locations, in km."""
    start_latitude, start_longitude = (math.radians(degrees) for degrees in start)
    end_latitude, end_longitude = (math.radians(degrees) for degrees in end)
    haversine = (
        math.sin((end_latitude - start_latitude) / 2) ** 2
        + math.cos(start_latitude)
        * math.cos(end_latitude)
        * math.sin((end_longitude - start_longitude) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))


def list_nearby_suburbs(location: tuple[float, float], max_distance_km: float) -> list[str]:
    """Lists the suburbs whose centres are within max_distance_km of a location."""
    return [
        suburb
        for suburb, centre in SUBURB_CENTRES.items()
        if calculate_distance_km(location, centre) <= max_distance_km
    ]
