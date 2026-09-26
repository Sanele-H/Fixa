// ID verification in three steps: POPIA consent, SA ID number (checked offline first),
// then the Home Affairs check through Smile ID. Only the result is stored.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { PATHS } from "../../app/paths";
import { IdBadgeChip } from "../../components/Badges";
import { Button, Card, Screen, ScreenHeader, Slot, TextField } from "../../ui";

const SA_ID_NUMBER_LENGTH = 13;
const STEP_COUNT = 3;

export default function VerifyIdScreen() {
  const { t } = useTranslation();
  const [hasConsented, setHasConsented] = useState(false);

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.me} title={t("verifyId.title")} subtitle={t("verifyId.subtitle")} />

      <Card tone="raised">
        <p className="eyebrow">{t("verifyId.step", { step: 1, total: STEP_COUNT })}</p>
        <h2 className="section-title">{t("verifyId.consentTitle")}</h2>
        <p className="small">{t("verifyId.consentBody")}</p>
        <label className="checkbox-row">
          <input type="checkbox" checked={hasConsented} onChange={(event) => setHasConsented(event.target.checked)} />
          {t("verifyId.consentAgree")}
        </label>
      </Card>

      <Card tone="raised">
        <p className="eyebrow">{t("verifyId.step", { step: 2, total: STEP_COUNT })}</p>
        <TextField
          label={t("verifyId.numberLabel")}
          hint={t("verifyId.numberHint")}
          inputMode="numeric"
          maxLength={SA_ID_NUMBER_LENGTH}
          disabled={!hasConsented}
        />
        <Button variant="secondary" isBlock disabled={!hasConsented}>
          {t("verifyId.check")}
        </Button>
        <Slot label="instant offline result: a typo fails here, before any network call" source="POST /api/identity/check-number" />
      </Card>

      <Card tone="inverse">
        <p className="eyebrow">{t("verifyId.step", { step: 3, total: STEP_COUNT })}</p>
        <h2 className="section-title">{t("verifyId.resultTitle")}</h2>
        <div className="row">
          <IdBadgeChip badge="home_affairs" />
        </div>
        <p className="small muted">{t("verifyId.resultBody")}</p>
        <Slot label="Home Affairs result via Smile ID, with failure and retry states" source="POST /api/identity/verify" />
      </Card>
    </Screen>
  );
}
