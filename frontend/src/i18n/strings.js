// Fixed UI text (buttons, headings) in each language. Chat and job text is translated by the
// backend; this file is only for the app's own words.
//
// TODO (Role 2):
// - Get a first-language speaker to write or check every language. Don't machine-translate these.
// - Add strings for scam warning codes (backend/fixa/safety/scam_warnings.py) and job states.
// Missing strings fall back to English, so the app never shows a blank button.

const UI_STRINGS_BY_LANGUAGE = {
  en: {
    myJobs: "My jobs",
    postJob: "Post a job",
    back: "Back",
    seeOriginal: "See original",
    numberHidden: "Number hidden",
    contactHiddenUntilApproved: "Contact details hidden until you both approve the job.",
  },
  af: {
    // TODO: check with an Afrikaans speaker
    myJobs: "My werke",
    postJob: "Plaas 'n werk",
    back: "Terug",
    seeOriginal: "Sien oorspronklike",
  },
  zu: {
    // TODO: needs a first-language isiZulu speaker. From the sprint plan draft, not yet checked:
    contactHiddenUntilApproved: "Imininingwane yokuxhumana ifihliwe.",
  },
};

const FALLBACK_LANGUAGE_CODE = "en";

/** Returns the UI string for `key` in `languageCode`, falling back to English, then to the key. */
export function getUiString(languageCode, key) {
  return (
    UI_STRINGS_BY_LANGUAGE[languageCode]?.[key] ?? UI_STRINGS_BY_LANGUAGE[FALLBACK_LANGUAGE_CODE][key] ?? key
  );
}
