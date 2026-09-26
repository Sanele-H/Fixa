import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { getHomePath, PATHS } from "../../app/paths";
import { useSession } from "../../session/SessionContext";
import { Button, Card, Screen, ScreenHeader, Slot, TextField } from "../../ui";

const OTP_LENGTH = 6;

export default function LoginScreen() {
  const { t } = useTranslation();
  const { role } = useSession();
  const navigate = useNavigate();

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.welcome} title={t("login.title")} subtitle={t("login.subtitle")} />

      <Card tone="raised">
        <TextField label={t("login.phoneLabel")} type="tel" inputMode="tel" autoComplete="tel" placeholder="082 000 0001" />
        <Button variant="secondary" isBlock>
          {t("login.sendCode")}
        </Button>
      </Card>

      <Card tone="raised">
        <TextField
          label={t("login.codeLabel")}
          hint={t("login.demoHint")}
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={OTP_LENGTH}
        />
      </Card>

      <Slot
        label="send the code, verify it, keep the token, load the user; OTP autofill (WebOTP)"
        source="POST /api/auth/otp · POST /api/auth/verify · GET /api/me"
      />

      <Button isBlock onClick={() => navigate(getHomePath(role))}>
        {t("login.logIn")}
      </Button>
    </Screen>
  );
}
