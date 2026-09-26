// First screen: pick the app's language. The choice is remembered, and the screen switches
// language as soon as a row is tapped so people can check they've picked the right one.

import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import type { Language } from "../../api/types";
import { PATHS } from "../../app/paths";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES, updateLanguage } from "../../i18n";
import { AppMark, Button, Icon, RowCard, Screen } from "../../ui";

export default function WelcomeScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const currentLanguage = i18n.language as Language;

  /** Saves the language shown now (even if untouched) and moves on to login. */
  async function continueToLogin() {
    await updateLanguage(currentLanguage);
    navigate(PATHS.login);
  }

  return (
    <Screen>
      <AppMark />
      <div className="stack">
        <h1 className="figure figure--hero">Fixa</h1>
        <p className="section-title">{t("app.tagline")}</p>
      </div>

      <div className="stack" role="radiogroup" aria-labelledby="language-heading">
        <p id="language-heading" className="eyebrow">
          {t("language.title")}
        </p>
        {SUPPORTED_LANGUAGES.map((language) => (
          <RowCard
            key={language}
            eyebrow={language.toUpperCase()}
            title={<span lang={language}>{LANGUAGE_NAMES[language]}</span>}
            isSelected={language === currentLanguage}
            onSelect={() => updateLanguage(language)}
            badge={language === currentLanguage ? <Icon name="check" /> : undefined}
          />
        ))}
      </div>

      <Button isBlock onClick={continueToLogin}>
        {t("language.continue")}
      </Button>
    </Screen>
  );
}
