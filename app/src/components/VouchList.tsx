// What customers say about a provider: their vouches, newest first, with the suburb and date only.

import { useTranslation } from "react-i18next";
import { useVouches } from "../api/vouches";
import { formatDate } from "../format";
import { Card } from "../ui";

export function VouchList({ providerId }: { providerId: string }) {
  const { t, i18n } = useTranslation();
  const vouches = useVouches(providerId);

  if (!vouches.data || vouches.data.length === 0) {
    return null;
  }
  return (
    <section className="stack">
      <h2 className="section-title">{t("vouch.listTitle")}</h2>
      {vouches.data.map((vouch) => (
        <Card key={vouch.id} tone="raised">
          <p>{vouch.text}</p>
          <p className="small muted">
            {vouch.suburb} · {formatDate(vouch.given_on, i18n.language)}
          </p>
        </Card>
      ))}
    </section>
  );
}
