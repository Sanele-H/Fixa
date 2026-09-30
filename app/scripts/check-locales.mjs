import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const localesDir = resolve(__dirname, "../src/i18n/locales");

function loadJson(file) {
  const content = readFileSync(resolve(localesDir, file), "utf-8");
  return JSON.parse(content);
}

function flatten(obj, prefix = "") {
  let res = {};
  for (const [key, value] of Object.entries(obj)) {
    if (key === "_about") continue;
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      Object.assign(res, flatten(value, fullKey));
    } else {
      res[fullKey] = String(value);
    }
  }
  return res;
}

function getPlaceholders(str) {
  const matches = str.match(/\{\{([^}]+)\}\}/g) || [];
  return matches.map((m) => m.replace(/[\{\}]/g, "").trim()).sort();
}

const en = flatten(loadJson("en.json"));
const locales = ["zu.json", "xh.json"];

let hasErrors = false;

for (const localeFile of locales) {
  const target = flatten(loadJson(localeFile));
  
  const enKeys = new Set(Object.keys(en));
  const targetKeys = new Set(Object.keys(target));

  // Check missing keys
  for (const key of enKeys) {
    if (!targetKeys.has(key)) {
      console.error(`[${localeFile}] Missing key: "${key}"`);
      hasErrors = true;
    }
  }

  // Check extra keys
  for (const key of targetKeys) {
    if (!enKeys.has(key)) {
      console.error(`[${localeFile}] Extra key not in en.json: "${key}"`);
      hasErrors = true;
    }
  }

  // Check placeholders
  for (const key of enKeys) {
    if (targetKeys.has(key)) {
      const enVars = getPlaceholders(en[key]);
      const targetVars = getPlaceholders(target[key]);

      if (JSON.stringify(enVars) !== JSON.stringify(targetVars)) {
        console.error(
          `[${localeFile}] Mismatched placeholders at "${key}": expected [${enVars.join(", ")}], got [${targetVars.join(", ")}]`
        );
        hasErrors = true;
      }
    }
  }
}

if (hasErrors) {
  console.error("\nLocale validation failed!");
  process.exit(1);
} else {
  console.log("All locale files (zu.json, xh.json) match en.json structure and placeholders perfectly!");
}
