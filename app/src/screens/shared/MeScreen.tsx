import { useTranslation } from "react-i18next";
import { useUpdateMyLanguage } from "../../api/account";
import { getErrorMessageKey } from "../../api/errors";
import type { Language } from "../../api/types";
import { PATHS } from "../../app/paths";
import { IdBadgeChip } from "../../components/Badges";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES, updateLanguage } from "../../i18n";
import { useCurrentUser, useSession } from "../../session/SessionContext";
import { Avatar, Banner, Button, Card, Chip, Icon, RowCard, Screen, ScreenHeader, Segmented } from "../../ui";

export default function MeScreen() {
  const { t, i18n } = useTranslation();
  const me = useCurrentUser();
  const { deleteSession } = useSession();
  const updateMyLanguage = useUpdateMyLanguage();

  /**
   * Shows the app in `language` on this phone, and saves it on the account so the server
   * translates chats, jobs and quotes into it too.
   */
  function selectLanguage(language: Language) {
    updateLanguage(language);
    updateMyLanguage.mutate(language);
  }

  return (
    <Screen hasNav>
      <ScreenHeader title={t("me.title")} />

      <Card tone="raised">
        <div className="row">
          <Avatar displayName={me.display_name} isLarge />
          <div>
            <p className="figure figure--md">{me.display_name}</p>
            <p className="small muted">{me.suburb}</p>
          </div>
        </div>
        <div className="row">
          <Chip tone="outline">{t(`role.${me.role}`)}</Chip>
          <IdBadgeChip badge={me.id_badge} />
        </div>
      </Card>

      <section className="stack stack--tight">
        <h2 className="eyebrow">{t("me.language")}</h2>
        <Segmented<Language>
          label={t("me.language")}
          options={SUPPORTED_LANGUAGES.map((language) => ({ value: language, label: LANGUAGE_NAMES[language] }))}
          value={i18n.language as Language}
          onChange={selectLanguage}
        />
        {updateMyLanguage.isError && <Banner tone="warning" title={t(getErrorMessageKey(updateMyLanguage.error))} />}
      </section>

      {me.role === "provider" && (
        <section className="stack">
          <RowCard to={PATHS.verifyId} eyebrow={t("me.identity")} title={t("verifyId.title")} badge={<Icon name="chevronRight" />} />
          <RowCard to={PATHS.offAppJob} eyebrow={t("me.work")} title={t("offApp.title")} badge={<Icon name="chevronRight" />} />
        </section>
      )}

      <Button variant="secondary" isBlock onClick={deleteSession}>
        {t("me.logOut")}
      </Button>
    </Screen>
  );
}
