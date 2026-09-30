// A customer's few words about a provider whose job is finished. One per provider: the server
// hides contact details and refuses illegal requests, and never shows who wrote it.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCreateVouch } from "../api/vouches";
import { Banner, Button, Card, TextArea } from "../ui";
import { ErrorBanner } from "./ErrorBanner";

const MIN_VOUCH_CHARS = 10;
const MAX_VOUCH_CHARS = 300;
const ALREADY_VOUCHED_STATUS = 409;

export function VouchForm({ providerId, providerName }: { providerId: string; providerName: string }) {
  const { t } = useTranslation();
  const createVouch = useCreateVouch(providerId);
  const [text, setText] = useState("");
  const error = createVouch.error as { status?: number } | null;

  if (createVouch.isSuccess) {
    return <Banner tone="info" title={t("vouch.thanks", { name: providerName })} />;
  }
  return (
    <Card tone="raised">
      <p className="section-title">{t("vouch.title", { name: providerName })}</p>
      <p className="small muted">{t("vouch.hint")}</p>
      <TextArea
        label={t("vouch.label")}
        value={text}
        maxLength={MAX_VOUCH_CHARS}
        onChange={(event) => setText(event.target.value)}
      />
      {createVouch.isError && (
        <ErrorBanner
          error={createVouch.error}
          overrideKey={error?.status === ALREADY_VOUCHED_STATUS ? "vouch.alreadyDone" : undefined}
        />
      )}
      <Button
        isBlock
        onClick={() => createVouch.mutate(text.trim())}
        disabled={createVouch.isPending || text.trim().length < MIN_VOUCH_CHARS}
      >
        {t("vouch.send")}
      </Button>
    </Card>
  );
}
