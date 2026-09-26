// Runs a command with the project's virtual-environment Python, on Windows, macOS or Linux.
// Usage: node scripts/run-python.mjs -m pytest backend/tests
// npm scripts use this so nobody has to activate the venv by hand.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRootPath = join(dirname(fileURLToPath(import.meta.url)), "..");

/** Returns the path of the venv's Python executable for this operating system. */
export function getVenvPythonPath() {
  const isWindows = process.platform === "win32";
  return isWindows
    ? join(repoRootPath, ".venv", "Scripts", "python.exe")
    : join(repoRootPath, ".venv", "bin", "python");
}

function runPythonCommand(pythonArguments) {
  const venvPythonPath = getVenvPythonPath();
  if (!existsSync(venvPythonPath)) {
    console.error("No .venv found. Run `npm install` and then `npm run setup` from the repo root first.");
    process.exit(1);
  }
  const result = spawnSync(venvPythonPath, pythonArguments, { cwd: repoRootPath, stdio: "inherit" });
  process.exit(result.status ?? 1);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runPythonCommand(process.argv.slice(2));
}
