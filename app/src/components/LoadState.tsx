// What a screen shows while its data loads, when a read failed, and when a list is empty.
// Every screen that reads from the API uses these, so waiting and failing look the same everywhere.

import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { getErrorMessageKey } from "../api/errors";
import { Banner, Button, Card } from "../ui";

/** "Loading…", announced to screen readers as busy. */
export function LoadingNote() {
  const { t } = useTranslation();
  return (
    <p className="muted" aria-busy="true">
      {t("app.loading")}
    </p>
  );
}

type LoadErrorProps = {
  error: unknown;
  /** Usually the query's refetch. */
  onRetry: () => void;
};

/** A read that failed: the translated reason, and a button to try again. */
export function LoadError({ error, onRetry }: LoadErrorProps) {
  const { t } = useTranslation();
  return (
    <Banner tone="warning" title={t(getErrorMessageKey(error))}>
      <Button variant="secondary" isSmall onClick={onRetry}>
        {t("errors.tryAgain")}
      </Button>
    </Banner>
  );
}

/** An empty list: a title, and a line saying what happens next. */
export function EmptyNote({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card>
      <p className="section-title">{title}</p>
      {children && <p className="muted">{children}</p>}
    </Card>
  );
}
