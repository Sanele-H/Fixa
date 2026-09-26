// Demo step 1: Mrs. van Wyk photographs the leak, types in Afrikaans, and the app suggests
// "Plumbing, small job".
//
// TODO (Role 2, Day 2):
// - Photo input: <input type="file" accept="image/*" capture="environment"> opens the camera on Android.
// - Send the photo to api.suggestTrade(photoFile, description) and show the suggestion
//   as a pre-selected, changeable choice (icon + label).
// - Description box, area, then api.createJob({ trade, size, description, descriptionLanguage, area }).
// - Big tap targets and icons beside text: test it on a cheap Android phone.

import { getUiString } from "../i18n/strings.js";

export default function PostJobScreen({ languageCode, onDone }) {
  return (
    <section>
      <h1>{getUiString(languageCode, "postJob")}</h1>
      <p className="placeholder">TODO Role 2: photo, description, trade suggestion, post button.</p>
      <button type="button" onClick={onDone}>
        {getUiString(languageCode, "back")}
      </button>
    </section>
  );
}
