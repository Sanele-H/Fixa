// Top-level navigation. Deliberately simple: one piece of state says which screen is showing.
// Add react-router only if this gets painful.
//
// Each browser TAB remembers its own demo user (sessionStorage), so you can test both sides
// on one laptop with two tabs. Shortcut: open /?as=provider-nomsa to skip the picker.

import { useState } from "react";

import { setCurrentUserId } from "./api/client.js";
import ChooseUserScreen from "./screens/ChooseUserScreen.jsx";
import JobDetailScreen from "./screens/JobDetailScreen.jsx";
import JobListScreen from "./screens/JobListScreen.jsx";
import PostJobScreen from "./screens/PostJobScreen.jsx";

const CURRENT_USER_STORAGE_KEY = "fixa.currentUser";

function readStoredUser() {
  try {
    return JSON.parse(sessionStorage.getItem(CURRENT_USER_STORAGE_KEY));
  } catch {
    return null;
  }
}

function storeUser(user) {
  try {
    if (user) {
      sessionStorage.setItem(CURRENT_USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      sessionStorage.removeItem(CURRENT_USER_STORAGE_KEY);
    }
  } catch {
    // Private browsing can block storage; the app still works for this page load.
  }
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    const storedUser = readStoredUser();
    setCurrentUserId(storedUser?.id ?? null);
    return storedUser;
  });
  const [screen, setScreen] = useState({ name: "jobList" });

  function chooseUser(user) {
    setCurrentUserId(user?.id ?? null);
    storeUser(user);
    setCurrentUser(user);
    setScreen({ name: "jobList" });
  }

  if (!currentUser) {
    return <ChooseUserScreen onUserChosen={chooseUser} />;
  }

  const languageCode = currentUser.preferredLanguage;
  const showJobList = () => setScreen({ name: "jobList" });

  return (
    <main className="app">
      <header className="app-header">
        <strong>Fixa</strong>
        <span className="muted">{currentUser.displayName}</span>
        <button type="button" onClick={() => chooseUser(null)}>
          Switch user
        </button>
      </header>
      {screen.name === "jobList" && (
        <JobListScreen
          currentUser={currentUser}
          languageCode={languageCode}
          onJobSelected={(job) => setScreen({ name: "jobDetail", job })}
          onPostJob={() => setScreen({ name: "postJob" })}
        />
      )}
      {screen.name === "postJob" && <PostJobScreen languageCode={languageCode} onDone={showJobList} />}
      {screen.name === "jobDetail" && (
        <JobDetailScreen currentUser={currentUser} job={screen.job} languageCode={languageCode} onBack={showJobList} />
      )}
    </main>
  );
}
