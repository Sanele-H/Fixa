// "Who are you?" - the demo stand-in for login. This screen already works end to end:
// it lists the seeded users (from the backend, or mockData.js in mock mode) and shows
// whether the backend is running.

import { useEffect, useState } from "react";

import { api, isUsingMockApi, readBackendHealth } from "../api/client.js";
import TradeIcon from "../components/TradeIcon.jsx";

const USER_SHORTCUT_PARAMETER = "as";

/** Returns the user named in ?as=<user id> (then drops it from the URL, so "Switch user" works). */
function findShortcutUser(users) {
  const url = new URL(window.location.href);
  const shortcutUserId = url.searchParams.get(USER_SHORTCUT_PARAMETER);
  url.searchParams.delete(USER_SHORTCUT_PARAMETER);
  window.history.replaceState(null, "", url);
  return users.find((user) => user.id === shortcutUserId);
}

export default function ChooseUserScreen({ onUserChosen }) {
  const [users, setUsers] = useState([]);
  const [backendStatusText, setBackendStatusText] = useState("checking...");
  const [errorText, setErrorText] = useState(null);

  useEffect(() => {
    readBackendHealth()
      .then((health) => setBackendStatusText(`running (translation: ${health.translationBackend})`))
      .catch(() => setBackendStatusText("not reachable - is `npm run dev` running?"));

    api
      .listUsers()
      .then((loadedUsers) => {
        setUsers(loadedUsers);
        const shortcutUser = findShortcutUser(loadedUsers);
        if (shortcutUser) {
          onUserChosen(shortcutUser);
        }
      })
      .catch((error) => setErrorText(error.message));
    // Run once on mount only; onUserChosen just sets state in App.
  }, []);

  return (
    <main className="app">
      <h1>Who are you?</h1>
      {errorText && <p className="error">{errorText}</p>}
      <ul className="card-list">
        {users.map((user) => (
          <li key={user.id}>
            <button type="button" className="card" onClick={() => onUserChosen(user)}>
              {user.trades?.map((tradeId) => <TradeIcon key={tradeId} tradeId={tradeId} />)}
              <strong>{user.displayName}</strong>
              <span className="muted">
                {user.role} · {user.preferredLanguage}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p className="muted small">
        Backend: {backendStatusText}
        <br />
        Data: {isUsingMockApi ? "mock (VITE_USE_MOCK_API=true)" : "live backend"}
      </p>
    </main>
  );
}
