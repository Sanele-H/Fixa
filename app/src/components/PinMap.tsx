// A map to drop a pin on, for a job that isn't at the customer's home. Leaflet and its styles
// are imported only here, and this file is only ever loaded with lazy(), so the map's code
// stays out of the app's first load.
//
// Tiles come from OpenStreetMap. Their tile policy asks for the attribution shown in the corner.

import "leaflet/dist/leaflet.css";
import { divIcon, map as createMap, marker as createMarker, tileLayer, type Map, type Marker } from "leaflet";
import { useEffect, useRef } from "react";
import type { MapPoint } from "../api/places";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const MAX_ZOOM = 19;
/** Close enough to see streets, far enough to see the neighbourhood around them. */
const START_ZOOM = 15;
/** Pins keep 5 decimals (about 1 m), like the server stores them. */
const COORDINATE_DECIMALS = 5;
/**
 * A drawn pin instead of Leaflet's image marker, whose image paths break in bundled apps. The
 * shape is on an inner span: Leaflet moves the outer element with its own transform.
 */
const PIN_ICON = divIcon({
  className: "map-pin",
  html: '<span class="map-pin__head"></span>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

type PinMapProps = {
  /** Where the map opens when there's no pin yet: the customer's own area. */
  start: MapPoint;
  pin: MapPoint | null;
  onPinChange: (pin: MapPoint) => void;
  /** Read out by screen readers. Pass a translated string. */
  label: string;
};

/** Rounds a Leaflet point to the precision the server keeps. */
function toMapPoint({ lat, lng }: { lat: number; lng: number }): MapPoint {
  return { lat: Number(lat.toFixed(COORDINATE_DECIMALS)), lng: Number(lng.toFixed(COORDINATE_DECIMALS)) };
}

/**
 * The map, with a pin that moves where the customer taps or drags it. Each move is reported once
 * it's finished (a tap, or letting go of the pin), so the place is looked up once per move.
 * A pin set from outside (such as "use where I am now") moves the pin and the map to it.
 */
export default function PinMap({ start, pin, onPinChange, label }: PinMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const onPinChangeRef = useRef(onPinChange);
  onPinChangeRef.current = onPinChange;

  // Make the map once. The start point is only where it opens, so later changes are ignored.
  useEffect(() => {
    const leafletMap = createMap(containerRef.current!).setView([start.lat, start.lng], START_ZOOM);
    tileLayer(TILE_URL, { maxZoom: MAX_ZOOM, attribution: TILE_ATTRIBUTION }).addTo(leafletMap);
    leafletMap.on("click", (event) => onPinChangeRef.current(toMapPoint(event.latlng)));
    mapRef.current = leafletMap;
    return () => {
      leafletMap.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, []);

  // Put the pin where the screen says it is, making it the first time.
  useEffect(() => {
    const leafletMap = mapRef.current;
    if (!leafletMap || !pin) {
      return;
    }
    if (!markerRef.current) {
      markerRef.current = createMarker([pin.lat, pin.lng], { icon: PIN_ICON, draggable: true, autoPan: true })
        .on("dragend", (event) => onPinChangeRef.current(toMapPoint((event.target as Marker).getLatLng())))
        .addTo(leafletMap);
    }
    markerRef.current.setLatLng([pin.lat, pin.lng]);
    if (!leafletMap.getBounds().contains([pin.lat, pin.lng])) {
      leafletMap.setView([pin.lat, pin.lng], START_ZOOM);
    }
  }, [pin]);

  return <div ref={containerRef} className="pin-map" role="application" aria-label={label} />;
}
