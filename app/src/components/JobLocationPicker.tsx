// "Where is the job?": at the customer's home (the default), or a pin on the map for somewhere
// else, such as a parent's house or a rental. Providers see only the suburb and a rounded
// distance until the customer picks someone, wherever the pin is.

import { lazy, Suspense, useState } from "react";
import { useTranslation } from "react-i18next";
import { getErrorCode } from "../api/errors";
import { useMyArea, type MapPoint, type PinnedPlace } from "../api/places";
import { Banner, Button, Segmented } from "../ui";
import { LoadingNote } from "./LoadState";

// Leaflet only downloads when someone chooses "Somewhere else".
const PinMap = lazy(() => import("./PinMap"));

export type JobPlaceChoice = "home" | "pin";

/** How long the phone may take to find itself before we give up and ask for a pin instead. */
const LOCATION_TIMEOUT_MS = 15_000;
const PIN_DECIMALS = 5;

/** The state of looking up the pin's name, from usePinnedPlace(). */
export type PinnedPlaceLookup = {
  data?: PinnedPlace;
  error: Error | null;
  isFetching: boolean;
};

type JobLocationPickerProps = {
  homeSuburb: string;
  choice: JobPlaceChoice;
  onChoiceChange: (choice: JobPlaceChoice) => void;
  pin: MapPoint | null;
  onPinChange: (pin: MapPoint) => void;
  place: PinnedPlaceLookup;
};

/** What the lookup found, shown under the map: the suburb, or why there isn't one. */
function PinnedPlaceNote({ pin, place }: { pin: MapPoint | null; place: PinnedPlaceLookup }) {
  const { t } = useTranslation();
  if (!pin) {
    return <p className="small muted">{t("newJob.pinFirst")}</p>;
  }
  if (place.isFetching) {
    return <p className="small muted">{t("newJob.placeFinding")}</p>;
  }
  if (place.error) {
    const isOutside = getErrorCode(place.error) === "place_not_found";
    return <Banner tone="warning" title={t(isOutside ? "newJob.placeOutside" : "newJob.placeFailed")} />;
  }
  if (!place.data) {
    return null;
  }
  return (
    <Banner tone="info" title={t("newJob.placeFound", { suburb: place.data.suburb })}>
      {t("newJob.placePrivacy")}
    </Banner>
  );
}

/**
 * "Use where I am now": asks the phone for its location and drops the pin there. Only works on
 * HTTPS (or localhost); when it fails, the customer is asked to tap the map instead.
 */
function UseMyLocationButton({ onPinChange }: { onPinChange: (pin: MapPoint) => void }) {
  const { t } = useTranslation();
  const [isLocating, setIsLocating] = useState(false);
  const [hasFailed, setHasFailed] = useState(false);

  /** Asks for the phone's position once, and drops the pin there. */
  function findMyLocation() {
    if (!("geolocation" in navigator)) {
      setHasFailed(true);
      return;
    }
    setIsLocating(true);
    setHasFailed(false);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setIsLocating(false);
        onPinChange({ lat: Number(coords.latitude.toFixed(PIN_DECIMALS)), lng: Number(coords.longitude.toFixed(PIN_DECIMALS)) });
      },
      () => {
        setIsLocating(false);
        setHasFailed(true);
      },
      { enableHighAccuracy: true, timeout: LOCATION_TIMEOUT_MS },
    );
  }

  return (
    <>
      <Button variant="secondary" isSmall icon="mapPin" onClick={findMyLocation} disabled={isLocating}>
        {isLocating ? t("app.loading") : t("newJob.useMyLocation")}
      </Button>
      {hasFailed && <Banner tone="warning" title={t("newJob.locationDenied")} />}
    </>
  );
}

/** The map, opened on the customer's own area, with the pin and what it's called. */
function PinPicker({ pin, onPinChange, place }: Pick<JobLocationPickerProps, "pin" | "onPinChange" | "place">) {
  const { t } = useTranslation();
  const myArea = useMyArea();
  const start = pin ?? myArea.data;

  return (
    <div className="stack stack--tight">
      <p className="small">{t("newJob.mapHint")}</p>
      {start ? (
        <Suspense fallback={<LoadingNote />}>
          <PinMap start={start} pin={pin} onPinChange={onPinChange} label={t("newJob.mapLabel")} />
        </Suspense>
      ) : (
        <LoadingNote />
      )}
      <UseMyLocationButton onPinChange={onPinChange} />
      <PinnedPlaceNote pin={pin} place={place} />
    </div>
  );
}

/** Home or somewhere else, and the map when it's somewhere else. */
export function JobLocationPicker({ homeSuburb, choice, onChoiceChange, pin, onPinChange, place }: JobLocationPickerProps) {
  const { t } = useTranslation();
  const options = [
    { value: "home" as const, label: t("newJob.whereHome", { suburb: homeSuburb }) },
    { value: "pin" as const, label: t("newJob.whereElsewhere") },
  ];

  return (
    <section className="stack stack--tight">
      <p className="eyebrow">{t("newJob.whereLabel")}</p>
      <Segmented label={t("newJob.whereLabel")} options={options} value={choice} onChange={onChoiceChange} />
      {choice === "pin" && <PinPicker pin={pin} onPinChange={onPinChange} place={place} />}
    </section>
  );
}
