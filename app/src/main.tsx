// Starting shell for the PWA (P1). It proves the toolchain runs, and nothing more.
// P1's first step is to read contracts/api.md and contracts/fixtures/, then propose the
// routes, the MSW setup and the i18n file layout (see P1's starting prompt in the build plan).

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

function App() {
  return <h1>Fixa</h1>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
