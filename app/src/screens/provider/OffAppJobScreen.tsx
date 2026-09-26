// Provider logs a job done outside the app. The customer confirms by replying to an SMS in
// their language, and only then does it count towards the provider's record.

import { useTranslation } from "react-i18next";
import { PATHS } from "../../app/paths";
import { Banner, Button, Card, Screen, ScreenHeader, Slot, TextField } from "../../ui";

export default function OffAppJobScreen() {
  const { t } = useTranslation();

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.myRecord} title={t("offApp.title")} subtitle={t("offApp.subtitle")} />

      <Card tone="raised">
        <TextField label={t("offApp.customerPhone")} type="tel" inputMode="tel" placeholder="082 000 0001" />
        <TextField label={t("offApp.tradeTask")} placeholder={t("offApp.tradeTaskExample")} />
        <TextField label={t("offApp.date")} type="date" />
        <TextField label={t("offApp.suburb")} />
        <TextField label={t("offApp.amount")} hint={t("offApp.amountHint")} inputMode="numeric" />
      </Card>

      <Banner tone="info" title={t("offApp.smsNoteTitle")}>
        {t("offApp.smsNoteBody")}
      </Banner>

      <Button isBlock icon="send">
        {t("offApp.submit")}
      </Button>
      <Slot
        label="after sending: the job with its state (awaiting_sms_reply); one tap for 'I did more work for this customer'"
        source="POST /api/off-app-jobs"
      />
    </Screen>
  );
}
