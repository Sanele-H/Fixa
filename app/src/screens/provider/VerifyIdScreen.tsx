// ID verification in three steps: POPIA consent, the SA ID number (checked offline first, so a
// typo fails before any paid check), then the Home Affairs check through Smile ID. Only the
// result is stored. The demo verifier knows 8506150123089 (Sipho Dlamini),
// 8001015009087 (Thabo Nkosi) and 9002204321084 (Nosipho Khumalo).

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getErrorMessageKey } from "../../api/errors";
import { useCheckIdNumber, useVerifyIdentity } from "../../api/identity";
import type { IdNumberCheck, IdResult } from "../../api/types";
import { PATHS } from "../../app/paths";
import { IdBadgeChip } from "../../components/Badges";
import { formatDate } from "../../format";
import { useCurrentUser } from "../../session/SessionContext";
import { Banner, Button, Card, Screen, ScreenHeader, TextField } from "../../ui";

const SA_ID_NUMBER_LENGTH = 13;
const STEP_COUNT = 3;

/** What the offline check says about the number, in the reader's language. */
function NumberCheckResult({ check }: { check: IdNumberCheck }) {
  const { t, i18n } = useTranslation();
  if (check.valid && check.date_of_birth) {
    return <Banner tone="info" title={t("verifyId.numberOk", { date: formatDate(check.date_of_birth, i18n.language) })} />;
  }
  return <Banner tone="warning" title={t(`verifyId.reason.${check.reason ?? "checksum"}`)} />;
}

/** Home Affairs' answer: the badge it earned, and what to do if it didn't go all the way. */
function VerifyResult({ result }: { result: IdResult }) {
  const { t } = useTranslation();
  const outcomeKey = result.verified ? (result.name_match ? "verified" : "nameMismatch") : "notFound";
  return (
    <>
      <div className="row">
        <IdBadgeChip badge={result.tier} />
      </div>
      <p className="small">{t(`verifyId.result.${outcomeKey}`)}</p>
    </>
  );
}

export default function VerifyIdScreen() {
  const { t } = useTranslation();
  const me = useCurrentUser();
  const [hasConsented, setHasConsented] = useState(false);
  const [idNumber, setIdNumber] = useState("");
  const [names, setNames] = useState("");
  const checkIdNumber = useCheckIdNumber();
  const verifyIdentity = useVerifyIdentity();
  const isNumberValid = checkIdNumber.data?.valid === true;

  /** A new number needs checking again, so any earlier result goes. */
  function updateIdNumber(nextIdNumber: string) {
    setIdNumber(nextIdNumber);
    checkIdNumber.reset();
    verifyIdentity.reset();
  }

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.me} title={t("verifyId.title")} subtitle={t("verifyId.subtitle")} />

      <div className="row">
        <span className="eyebrow">{t("verifyId.currentBadge")}</span>
        <IdBadgeChip badge={me.id_badge} />
      </div>

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
          value={idNumber}
          onChange={(event) => updateIdNumber(event.target.value)}
        />
        <Button
          variant="secondary"
          isBlock
          disabled={!hasConsented || !idNumber || checkIdNumber.isPending}
          onClick={() => checkIdNumber.mutate(idNumber)}
        >
          {t("verifyId.check")}
        </Button>
        {checkIdNumber.data && <NumberCheckResult check={checkIdNumber.data} />}
        {checkIdNumber.isError && <Banner tone="warning" title={t(getErrorMessageKey(checkIdNumber.error))} />}
      </Card>

      <Card tone="inverse">
        <p className="eyebrow">{t("verifyId.step", { step: 3, total: STEP_COUNT })}</p>
        <h2 className="section-title">{t("verifyId.resultTitle")}</h2>
        <TextField
          label={t("verifyId.namesLabel")}
          hint={t("verifyId.namesHint")}
          autoComplete="name"
          disabled={!isNumberValid}
          value={names}
          onChange={(event) => setNames(event.target.value)}
        />
        <Button
          variant="lime"
          isBlock
          disabled={!isNumberValid || !names.trim() || verifyIdentity.isPending}
          onClick={() => verifyIdentity.mutate({ id_number: idNumber, names: names.trim() })}
        >
          {t("verifyId.homeAffairs")}
        </Button>
        {verifyIdentity.data && <VerifyResult result={verifyIdentity.data} />}
        {verifyIdentity.isError && <Banner tone="warning" title={t(getErrorMessageKey(verifyIdentity.error))} />}
        <p className="small muted">{t("verifyId.resultBody")}</p>
      </Card>
    </Screen>
  );
}
