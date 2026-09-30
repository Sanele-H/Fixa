// Customer describes the problem in their own words. The app suggests a trade, urgency and
// size from that description, the customer confirms or changes them, adds a photo if they like,
// and posts. Their address and number stay hidden until they pick someone.

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useNavigate } from "react-router";
import { getErrorMessageKey } from "../../api/errors";
import { useCreateJob, useUnderstandJob, type NewJob } from "../../api/jobs";
import { useUploadPhoto } from "../../api/photos";
import { JOB_SIZES, TRADES, URGENCIES, type JobIntent, type Language, type TradeId } from "../../api/types";
import { PATHS } from "../../app/paths";
import { getTradeLabel } from "../../components/Badges";
import { useCurrentUser } from "../../session/SessionContext";
import { shrinkPhoto } from "../../shrinkPhoto";
import { Banner, Button, Card, Icon, Screen, ScreenHeader, Segmented, TextArea } from "../../ui";

/** What the customer confirms after the suggestion: the trade, how soon and how big. */
type JobDetails = Pick<NewJob, "trade" | "urgency" | "size">;

/** The trade choices: the known trades, plus the suggested one if the app doesn't list it yet. */
function listTradeOptions(suggestedTrade: TradeId) {
  return TRADES.includes(suggestedTrade) ? TRADES : [...TRADES, suggestedTrade];
}

/**
 * Shrinks the photo the customer picks and uploads it straight away, so posting doesn't wait.
 * If the phone can't shrink it (some formats), the original goes up and the server shrinks it.
 */
function useJobPhoto() {
  const uploadPhoto = useUploadPhoto();
  const [isShrinking, setIsShrinking] = useState(false);

  async function addPhoto(photo: File) {
    setIsShrinking(true);
    const shrunkPhoto = await shrinkPhoto(photo).catch(() => photo);
    setIsShrinking(false);
    uploadPhoto.mutate(shrunkPhoto);
  }

  return {
    photo: uploadPhoto.data ?? null,
    isBusy: isShrinking || uploadPhoto.isPending,
    error: uploadPhoto.error,
    addPhoto,
    removePhoto: uploadPhoto.reset,
  };
}

type PhotoPickerProps = ReturnType<typeof useJobPhoto>;

/** The dashed "Add a photo" tile, or the photo once it's uploaded, with a way to remove it. */
function PhotoPicker({ photo, isBusy, error, addPhoto, removePhoto }: PhotoPickerProps) {
  const { t } = useTranslation();

  /** Starts the upload for the file the customer picked, if any. */
  function pickPhoto(event: ChangeEvent<HTMLInputElement>) {
    const pickedPhoto = event.target.files?.[0];
    if (pickedPhoto) {
      addPhoto(pickedPhoto);
    }
    event.target.value = "";
  }

  if (photo) {
    return (
      <div className="stack stack--tight">
        <img className="job-photo" src={photo.url} alt={t("newJob.photoAlt")} />
        <Button variant="secondary" isSmall onClick={removePhoto}>
          {t("newJob.removePhoto")}
        </Button>
      </div>
    );
  }
  return (
    <>
      <label className="photo-tile" aria-busy={isBusy}>
        <input className="visually-hidden" type="file" accept="image/*" onChange={pickPhoto} disabled={isBusy} />
        <Icon name="camera" sizePx={28} />
        <span>{isBusy ? t("newJob.photoAdding") : t("newJob.addPhoto")}</span>
        <span className="muted">{t("newJob.photoHint")}</span>
      </label>
      {error ? <Banner tone="warning" title={t(getErrorMessageKey(error))} /> : null}
    </>
  );
}

type DetailsCardProps = {
  details: JobDetails;
  onChange: (details: JobDetails) => void;
};

/** The suggested trade, urgency and size, each one a tap to change. */
function DetailsCard({ details, onChange }: DetailsCardProps) {
  const { t } = useTranslation();
  const tradeOptions = listTradeOptions(details.trade).map((trade) => ({ value: trade, label: getTradeLabel(t, trade) }));
  return (
    <Card tone="inverse">
      <p className="eyebrow">{t("newJob.suggested")}</p>
      <Segmented
        label={t("newJob.trade")}
        options={tradeOptions}
        value={details.trade}
        onChange={(trade) => onChange({ ...details, trade })}
      />
      <p className="eyebrow">{t("newJob.urgency")}</p>
      <Segmented
        label={t("newJob.urgency")}
        options={URGENCIES.map((option) => ({ value: option, label: t(`urgency.${option}`) }))}
        value={details.urgency}
        onChange={(urgency) => onChange({ ...details, urgency })}
      />
      <p className="eyebrow">{t("newJob.size")}</p>
      <Segmented
        label={t("newJob.size")}
        options={JOB_SIZES.map((option) => ({ value: option, label: t(`size.${option}`) }))}
        value={details.size}
        onChange={(size) => onChange({ ...details, size })}
      />
    </Card>
  );
}

export default function NewJobScreen() {
  const { t, i18n } = useTranslation();
  const me = useCurrentUser();
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const [details, setDetails] = useState<JobDetails | null>(null);
  const understandJob = useUnderstandJob();
  const createJob = useCreateJob();
  const jobPhoto = useJobPhoto();
  const language = i18n.language as Language;
  const requestError = createJob.error ?? understandJob.error;

  /** Asks the server what kind of job this is, and fills the details card with its guess. */
  function suggestDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    understandJob.mutate(
      { text: description, lang: language },
      { onSuccess: ({ trade, urgency, size }: JobIntent) => setDetails({ trade, urgency, size }) },
    );
  }

  /** Posts the job, then shows who can help with it. */
  function postJob(confirmedDetails: JobDetails) {
    const newJob: NewJob = {
      ...confirmedDetails,
      description,
      lang: language,
      suburb: me.suburb,
      photo_id: jobPhoto.photo?.photo_id,
    };
    createJob.mutate(newJob, { onSuccess: (job) => navigate(generatePath(PATHS.jobProviders, { jobId: job.id })) });
  }

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.home} title={t("newJob.title")} subtitle={t("newJob.subtitle")} />

      <form className="stack" onSubmit={suggestDetails}>
        <TextArea
          label={t("newJob.describeLabel")}
          placeholder={t("newJob.describeExample")}
          required
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        {!details && (
          <Button type="submit" isBlock disabled={understandJob.isPending || !description.trim()}>
            {understandJob.isPending ? t("app.loading") : t("newJob.next")}
          </Button>
        )}
      </form>

      {details && (
        <>
          <DetailsCard details={details} onChange={setDetails} />
          <PhotoPicker {...jobPhoto} />
        </>
      )}

      {requestError && <Banner tone="warning" title={t(getErrorMessageKey(requestError))} />}

      {details && (
        <Button isBlock onClick={() => postJob(details)} disabled={createJob.isPending || jobPhoto.isBusy}>
          {t("newJob.post")}
        </Button>
      )}
    </Screen>
  );
}
