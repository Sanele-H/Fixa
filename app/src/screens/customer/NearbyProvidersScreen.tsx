// "Who works near you": a customer looks at who does a trade around them before there's a job.
// It's for looking, not picking. Cards show evidence but no trust range, the list is nearest
// first, and the only way forward is "Describe a job", so hiring still goes through the fair
// ranked list with its newcomer slot.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TRADES, type Language, type NearbyProvider, type TradeId } from "../../api/types";
import { PATHS } from "../../app/paths";
import { getTradeLabel } from "../../components/Badges";
import { DescribeJobCard } from "../../components/DescribeJobCard";
import { NearbyProviderCard } from "../../components/ProviderCard";
import { sampleNearbyProviders } from "../../dev/samples";
import { formatRadiusKm } from "../../format";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from "../../i18n";
import { useCurrentUser } from "../../session/SessionContext";
import { Button, Card, Screen, ScreenHeader, Segmented, Slot } from "../../ui";

/** The radius choices, in km. The server allows up to 30 km. */
const RADIUS_OPTIONS_KM = [2, 5, 10, 20];
/** The same default as the server's radius_km for GET /api/providers. */
const DEFAULT_RADIUS_KM = 10;
const RADIUS_STORAGE_KEY = "fixa.nearbyRadiusKm";

const ANY_LANGUAGE = "any";
/** Keep everyone, or only the people who speak one app language. */
type LanguageFilter = Language | typeof ANY_LANGUAGE;
const LANGUAGE_FILTERS: LanguageFilter[] = [ANY_LANGUAGE, ...SUPPORTED_LANGUAGES];

/**
 * Reads the radius the customer last picked on this phone, or the default.
 * Storage can throw (private mode, blocked site data), which counts as "never picked".
 */
function getStoredRadiusKm(): number {
  try {
    const storedRadiusKm = Number(localStorage.getItem(RADIUS_STORAGE_KEY));
    return RADIUS_OPTIONS_KM.includes(storedRadiusKm) ? storedRadiusKm : DEFAULT_RADIUS_KM;
  } catch {
    return DEFAULT_RADIUS_KM;
  }
}

/** Remembers the picked radius on this phone. Fails quietly if storage is blocked. */
function updateStoredRadiusKm(radiusKm: number) {
  try {
    localStorage.setItem(RADIUS_STORAGE_KEY, String(radiusKm));
  } catch {
    // Nothing to do: the list still works, it just starts from the default next time.
  }
}

/** The customer's radius: starts from the one they last picked, and remembers each change. */
function useRadiusKm() {
  const [radiusKm, setRadiusKm] = useState(getStoredRadiusKm);
  function updateRadiusKm(nextRadiusKm: number) {
    setRadiusKm(nextRadiusKm);
    updateStoredRadiusKm(nextRadiusKm);
  }
  return [radiusKm, updateRadiusKm] as const;
}

/**
 * Stands in for the server until GET /api/providers is wired up: the same trade, language and
 * radius filters, over the sample list. The sample is the plumbing answer, so "Electrical"
 * only shows the people who do both.
 */
function filterSampleProviders(
  providers: NearbyProvider[],
  trade: TradeId,
  language: LanguageFilter,
  radiusKm: number,
) {
  return providers.filter(
    (provider) =>
      provider.trades.includes(trade) &&
      provider.distance_km <= radiusKm &&
      (language === ANY_LANGUAGE || provider.langs.includes(language)),
  );
}

type NearbyFiltersProps = {
  trade: TradeId;
  onTradeChange: (trade: TradeId) => void;
  language: LanguageFilter;
  onLanguageChange: (language: LanguageFilter) => void;
  radiusKm: number;
  onRadiusChange: (radiusKm: number) => void;
};

/** The three choices: which trade, which language (or any), and how far counts as near. */
function NearbyFilters(props: NearbyFiltersProps) {
  const { t } = useTranslation();
  const tradeOptions = TRADES.map((option) => ({ value: option, label: getTradeLabel(t, option) }));
  const languageOptions = LANGUAGE_FILTERS.map((option) => ({
    value: option,
    label: option === ANY_LANGUAGE ? t("nearby.anyLanguage") : LANGUAGE_NAMES[option],
  }));
  const radiusOptions = RADIUS_OPTIONS_KM.map((option) => ({ value: String(option), label: formatRadiusKm(option) }));

  return (
    <Card>
      <p className="eyebrow">{t("nearby.trade")}</p>
      <Segmented label={t("nearby.trade")} options={tradeOptions} value={props.trade} onChange={props.onTradeChange} />
      <p className="eyebrow">{t("nearby.language")}</p>
      <Segmented
        label={t("nearby.language")}
        options={languageOptions}
        value={props.language}
        onChange={props.onLanguageChange}
      />
      <p className="eyebrow">{t("nearby.radius")}</p>
      <Segmented
        label={t("nearby.radius")}
        options={radiusOptions}
        value={String(props.radiusKm)}
        onChange={(value) => props.onRadiusChange(Number(value))}
      />
    </Card>
  );
}

type NearbyEmptyProps = {
  radiusKm: number;
  onRadiusChange: (radiusKm: number) => void;
};

/** Nobody matched. Offers the next wider radius, if there is one. */
function NearbyEmpty({ radiusKm, onRadiusChange }: NearbyEmptyProps) {
  const { t } = useTranslation();
  const widerRadiusKm = RADIUS_OPTIONS_KM.find((option) => option > radiusKm);
  return (
    <Card>
      <p className="section-title">{t("nearby.emptyTitle")}</p>
      <p className="muted">{t("nearby.emptyBody")}</p>
      {widerRadiusKm !== undefined && (
        <Button variant="secondary" onClick={() => onRadiusChange(widerRadiusKm)}>
          {t("nearby.widen", { radius: formatRadiusKm(widerRadiusKm) })}
        </Button>
      )}
    </Card>
  );
}

export default function NearbyProvidersScreen() {
  const { t } = useTranslation();
  const me = useCurrentUser();
  const [trade, setTrade] = useState<TradeId>(TRADES[0]);
  const [language, setLanguage] = useState<LanguageFilter>(ANY_LANGUAGE);
  const [radiusKm, updateRadiusKm] = useRadiusKm();
  const providers = filterSampleProviders(sampleNearbyProviders, trade, language, radiusKm);

  return (
    <Screen>
      <ScreenHeader
        backTo={PATHS.home}
        eyebrow={me.suburb}
        title={t("nearby.title")}
        subtitle={t("nearby.subtitle", { suburb: me.suburb })}
      />

      <NearbyFilters
        trade={trade}
        onTradeChange={setTrade}
        language={language}
        onLanguageChange={setLanguage}
        radiusKm={radiusKm}
        onRadiusChange={updateRadiusKm}
      />

      <section className="stack">
        <h2 className="section-title">
          {t("nearby.count", { count: providers.length, radius: formatRadiusKm(radiusKm) })}
        </h2>
        {providers.length === 0 ? (
          <NearbyEmpty radiusKm={radiusKm} onRadiusChange={updateRadiusKm} />
        ) : (
          providers.map((provider) => <NearbyProviderCard key={provider.provider_id} provider={provider} />)
        )}
      </section>

      <Slot label="loading and error states; refetch when a filter changes" source="GET /api/providers?trade=&lang=&radius_km=" />

      <DescribeJobCard hint={t("nearby.describeHint")} />
    </Screen>
  );
}
