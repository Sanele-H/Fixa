"""Places on the map, for customers choosing where a job is.

Nothing here sends an exact location: the customer's own area comes back rounded to about a
kilometre (enough to open the map on their neighbourhood), and a pin's lookup returns names only.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from fixa_api.auth import require_role
from fixa_api.geocoding import Geocoder, Place, PlaceLookupError, get_geocoder, is_in_south_africa
from fixa_api.models import Customer

router = APIRouter(prefix="/api", tags=["places"])

AREA_DECIMALS = 2  # about 1 km: where to open the map, not where the customer lives
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
PlaceFinder = Annotated[Geocoder, Depends(get_geocoder)]
Latitude = Annotated[float, Query(ge=-90, le=90)]
Longitude = Annotated[float, Query(ge=-180, le=180)]


def find_place_or_refuse(geocoder: Geocoder, lat: float, lng: float) -> Place:
    """The place at a pin, or the error the app shows: 422 outside South Africa (or in the sea),
    503 when the place service can't answer right now."""
    outside = HTTPException(
        status_code=422,
        detail={"error": "place_not_found", "message": "Pick a place in South Africa"},
    )
    if not is_in_south_africa(lat, lng):
        raise outside
    try:
        place = geocoder.find_place(lat, lng)
    except PlaceLookupError:
        raise HTTPException(
            status_code=503,
            detail={"error": "place_lookup_failed", "message": "Couldn't look up that place"},
        ) from None
    if place is None:
        raise outside
    return place


@router.get("/me/area")
def read_my_area(customer: CustomerUser):
    """Where to open the job map: the customer's home suburb, and its point rounded to ~1 km."""
    return {
        "suburb": customer.suburb,
        "lat": round(customer.lat, AREA_DECIMALS),
        "lng": round(customer.lng, AREA_DECIMALS),
    }


@router.get("/places/reverse")
def read_place(lat: Latitude, lng: Longitude, customer: CustomerUser, geocoder: PlaceFinder):
    """What the pin the customer dropped is called: {suburb, label}. The label is the street
    address that providers see once the job is confirmed."""
    place = find_place_or_refuse(geocoder, lat, lng)
    return {"suburb": place.suburb, "label": place.label}
