// Customers: the jobs they posted. Providers: jobs they were shortlisted for (in their language).
// Shows the fetch -> render pattern the other screens can copy.
//
// TODO (Role 2, Day 2):
// - Show each job's description in the viewer's language once the backend sends it translated.
// - Show the job state as a clear step ("Waiting for quotes", "Quote accepted"...).
// - Refresh with usePolling so Nomsa sees the new job appear without reloading.

import { useEffect, useState } from "react";

import { api } from "../api/client.js";
import TradeIcon from "../components/TradeIcon.jsx";
import { getUiString } from "../i18n/strings.js";

export default function JobListScreen({ currentUser, languageCode, onJobSelected, onPostJob }) {
  const [jobs, setJobs] = useState([]);
  const [errorText, setErrorText] = useState(null);

  useEffect(() => {
    api
      .listJobs()
      .then(setJobs)
      .catch((error) => setErrorText(error.message));
  }, []);

  return (
    <section>
      <h1>{getUiString(languageCode, "myJobs")}</h1>
      {currentUser.role === "customer" && (
        <button type="button" className="primary" onClick={onPostJob}>
          {getUiString(languageCode, "postJob")}
        </button>
      )}
      {errorText && <p className="error">{errorText}</p>}
      <ul className="card-list">
        {jobs.map((job) => (
          <li key={job.id}>
            <button type="button" className="card" onClick={() => onJobSelected(job)}>
              <TradeIcon tradeId={job.trade} />
              <span>{job.description}</span>
              <span className="muted">{job.state}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
