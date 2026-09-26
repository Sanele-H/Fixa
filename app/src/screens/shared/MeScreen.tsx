import { useTranslation } from "react-i18next";
import type { Language, Role } from "../../api/types";
import { PATHS } from "../../app/paths";
import { IdBadgeChip } from "../../components/Badges";
import { sampleMe } from "../../dev/samples";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES, updateLanguage } from "../../i18n";
import { useSession } from "../../session/SessionContext";
import { Avatar, Button, Card, Chip, Icon, RowCard, Screen, ScreenHeader, Segmented, Slot } from "../../ui";

const ROLES: Role[] = ["customer", "provider"];

export default function MeScreen() {
  const { t, i18n } = useTranslation();
  const { role, updateRole } = useSession();
  const me = sampleMe;

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
          <Chip tone="outline">{t(`role.${role}`)}</Chip>
          <IdBadgeChip badge={me.id_badge} />
        </div>
      </Card>

      <section className="stack stack--tight">
        <h2 className="eyebrow">{t("me.language")}</h2>
        <Segmented<Language>
          label={t("me.language")}
          options={SUPPORTED_LANGUAGES.map((language) => ({ value: language, label: LANGUAGE_NAMES[language] }))}
          value={i18n.language as Language}
          onChange={updateLanguage}
        />
        <Slot label="save the language to the account as well" source="PATCH /api/me {lang}" />
      </section>

      {role === "provider" && (
        <section className="stack">
          <RowCard to={PATHS.verifyId} eyebrow={t("me.identity")} title={t("verifyId.title")} badge={<Icon name="chevronRight" />} />
          <RowCard to={PATHS.offAppJob} eyebrow={t("me.work")} title={t("offApp.title")} badge={<Icon name="chevronRight" />} />
        </section>
      )}

      <Card tone="lavender">
        <p className="eyebrow">{t("me.demoRole")}</p>
        <Segmented<Role>
          label={t("me.demoRole")}
          options={ROLES.map((option) => ({ value: option, label: t(`role.${option}`) }))}
          value={role}
          onChange={updateRole}
        />
        <p className="small">{t("me.demoRoleHint")}</p>
      </Card>

      <Button variant="secondary" isBlock>
        {t("me.logOut")}
      </Button>
    </Screen>
  );
}
