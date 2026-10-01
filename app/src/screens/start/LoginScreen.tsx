// Log in with a phone number and the code from the SMS. The demo sends no SMS: every account's
// code is DEMO_OTP from .env. Customers are 082 000 0001 to 0080, providers 071 000 0001 to 0060.
// Once logged in, this screen sends the person back to the page they opened (a shared link), or
// to their home tab.
//
// The language picked on this phone becomes the account's language, so there's one language
// per person: the buttons are in it, and the server translates chats, jobs and quotes into it.

import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router";
import { useSendLoginCode, useUpdateMyLanguage, useVerifyLoginCode } from "../../api/account";
import { ApiError, getErrorMessageKey } from "../../api/errors";
import type { AuthResult, Language } from "../../api/types";
import { getPathAfterLogin, PATHS, type LoginReturnState } from "../../app/paths";
import { useSession } from "../../session/SessionContext";
import { Banner, Button, Card, Screen, ScreenHeader, TextField } from "../../ui";

const OTP_LENGTH = 6;
/** POST /api/auth/verify answers 401 for a wrong number and a wrong code alike. */
const WRONG_LOGIN_STATUS = 401;

/** The message for a failed login: a 401 means the number or code is wrong, anything else is generic. */
function getLoginErrorKey(error: unknown) {
  if (error instanceof ApiError && error.status === WRONG_LOGIN_STATUS) {
    return "login.wrongCode";
  }
  return getErrorMessageKey(error);
}

export default function LoginScreen() {
  const { t, i18n } = useTranslation();
  const { user, createSession } = useSession();
  const location = useLocation();
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const sendLoginCode = useSendLoginCode();
  const verifyLoginCode = useVerifyLoginCode();
  const updateMyLanguage = useUpdateMyLanguage();
  const loginError = verifyLoginCode.error ?? sendLoginCode.error;

  if (user) {
    return <Navigate to={getPathAfterLogin(location.state as LoginReturnState, user.role)} replace />;
  }

  /** Asks the server to send a code to the number typed in. */
  function sendCode() {
    if (phone.trim()) {
      sendLoginCode.mutate(phone);
    }
  }

  /**
   * Starts the session, which moves on to the home tab, then saves this phone's language on
   * the account if the account had another one. The save finishes after this screen has gone.
   */
  function startSession(authResult: AuthResult) {
    const appLanguage = i18n.language as Language;
    createSession(authResult);
    if (authResult.user.lang !== appLanguage) {
      updateMyLanguage.mutate(appLanguage);
    }
  }

  /** Checks the number and code, then starts the session. */
  function logIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    verifyLoginCode.mutate({ phone, otp }, { onSuccess: startSession });
  }

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.welcome} title={t("login.title")} subtitle={t("login.subtitle")} />

      <form className="stack" onSubmit={logIn}>
        <Card tone="raised">
          <TextField
            label={t("login.phoneLabel")}
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="082 000 0001"
            required
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
          <Button variant="secondary" isBlock onClick={sendCode} disabled={sendLoginCode.isPending}>
            {t("login.sendCode")}
          </Button>
          {sendLoginCode.isSuccess && (
            <p className="small muted" role="status">
              {t("login.codeSent")}
            </p>
          )}
        </Card>

        <Card tone="raised">
          <TextField
            label={t("login.codeLabel")}
            hint={t("login.demoHint")}
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern={`\\d{${OTP_LENGTH}}`}
            maxLength={OTP_LENGTH}
            required
            value={otp}
            onChange={(event) => setOtp(event.target.value)}
          />
        </Card>

        {loginError && <Banner tone="warning" title={t(getLoginErrorKey(loginError))} />}

        <Button type="submit" isBlock disabled={verifyLoginCode.isPending}>
          {t("login.logIn")}
        </Button>
      </form>
    </Screen>
  );
}
