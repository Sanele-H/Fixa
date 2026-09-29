"""Distances. Exact coordinates stay on the server; only a rounded distance is ever sent."""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance between two points, rounded to 0.1 km like the ranked list."""
    d_lat, d_lng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(a)), 1)
