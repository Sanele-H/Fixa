// The message under a form when a request failed. A refused request (illegal electricity work) and
// a paused account arrive with their explanation already in the person's language, with the legal
// route for the first, so those show as they came. Everything else shows the usual message.

import { useTranslation } from "react-i18next";
import { ApiError, getErrorMessageKey, REFUSAL_ERROR_CODES } from "../api/errors";
import { Banner } from "../ui";

type ErrorBannerProps = {
  error: unknown;
  /** A message that fits this screen better than the usual one, for a status or code it knows. */
  overrideKey?: string;
};

export function ErrorBanner({ error, overrideKey }: ErrorBannerProps) {
  const { t } = useTranslation();
  if (error instanceof ApiError && error.code && REFUSAL_ERROR_CODES.includes(error.code)) {
    const titleKey = error.code === "prohibited_request" ? "errors.refusedTitle" : "errors.restrictedTitle";
    return (
      <Banner tone="critical" title={t(titleKey)}>
        {error.message}
      </Banner>
    );
  }
  return <Banner tone="warning" title={t(overrideKey ?? getErrorMessageKey(error))} />;
}
