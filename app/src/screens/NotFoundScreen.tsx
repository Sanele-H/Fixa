import { useTranslation } from "react-i18next";
import { PATHS } from "../app/paths";
import { ButtonLink, Screen, ScreenHeader } from "../ui";

export default function NotFoundScreen() {
  const { t } = useTranslation();
  return (
    <Screen>
      <ScreenHeader title={t("notFound.title")} subtitle={t("notFound.body")} />
      <ButtonLink to={PATHS.start} isBlock>
        {t("notFound.home")}
      </ButtonLink>
    </Screen>
  );
}
