// One-time setup for a new laptop: Python venv + API and packages, app packages, .env.
// Usage (from the repo root): npm install && npm run setup
// Safe to run again: it skips anything that already exists.

import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { getVenvPythonPath } from "./run-python.mjs";

const repoRootPath = join(dirname(fileURLToPath(import.meta.url)), "..");
const minimumPythonVersion = [3, 11];
const pythonCandidates = [["python3"], ["python"], ["py", "-3"]];
const isWindows = process.platform === "win32";

function runStep(description, command, commandArguments, options = {}) {
  console.log(`\n==> ${description}`);
  const result = spawnSync(command, commandArguments, { cwd: repoRootPath, stdio: "inherit", ...options });
  if (result.status !== 0) {
    console.error(`\nFailed: ${description}`);
    process.exit(result.status ?? 1);
  }
}

function findSystemPython() {
  const versionCheck = `import sys; sys.exit(0 if sys.version_info >= (${minimumPythonVersion.join(", ")}) else 1)`;
  for (const [command, ...prefixArguments] of pythonCandidates) {
    const result = spawnSync(command, [...prefixArguments, "-c", versionCheck], { stdio: "ignore" });
    if (result.status === 0) {
      return [command, ...prefixArguments];
    }
  }
  console.error(`Python ${minimumPythonVersion.join(".")}+ not found. Install it from python.org and try again.`);
  process.exit(1);
}

function createVirtualEnvironment() {
  if (existsSync(getVenvPythonPath())) {
    console.log("\n==> .venv already exists, skipping creation");
    return;
  }
  const [pythonCommand, ...prefixArguments] = findSystemPython();
  runStep("Creating .venv", pythonCommand, [...prefixArguments, "-m", "venv", ".venv"]);
}

function installPythonPackages() {
  const venvPythonPath = getVenvPythonPath();
  runStep("Upgrading pip", venvPythonPath, ["-m", "pip", "install", "--upgrade", "pip"]);
  runStep("Installing the API and the three packages (editable)", venvPythonPath, [
    "-m", "pip", "install",
    "-e", "api[dev]", "-e", "packages/lang", "-e", "packages/ranking", "-e", "packages/record",
  ]);
}

function installFrontendPackages() {
  // Run inside app/ rather than `npm --prefix app install`, which would add the root
  // package to app/package.json as a dependency.
  runStep("Installing app packages", "npm", ["install"], {
    cwd: join(repoRootPath, "app"),
    shell: isWindows,
  });
}

function createEnvFile() {
  const envFilePath = join(repoRootPath, ".env");
  if (existsSync(envFilePath)) {
    console.log("\n==> .env already exists, leaving it alone");
    return;
  }
  copyFileSync(join(repoRootPath, ".env.example"), envFilePath);
  console.log("\n==> Created .env from .env.example (add API keys there, never commit it)");
}

createVirtualEnvironment();
installPythonPackages();
installFrontendPackages();
createEnvFile();
console.log("\nDone. Start everything with: npm run dev");
