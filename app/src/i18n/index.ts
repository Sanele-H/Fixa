// App languages with i18next. One JSON file per language in ./locales/, each downloaded only
// when needed. English is the fallback, so a string missing from zu.json or xh.json shows in
// English rather than as a raw key.

import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import type { Language } from "../api/types";

export const SUPPORTED_LANGUAGES: Language[] = ["en", "zu", "xh"];
export const FALLBACK_LANGUAGE: Language = "en";

/** Each language's name in that language. Never translated, so people can always find their own. */
export const LANGUAGE_NAMES: Record<Language, string> = {
  en: "English",
  zu: "isiZulu",
  xh: "isiXhosa",
};

const LANGUAGE_STORAGE_KEY = "fixa.lang";
const TRANSLATION_NAMESPACE = "translation";

type LocaleModule = { default: Record<string, unknown> };

/** One dynamic import per language, so Vite splits each JSON file into its own small download. */
const LOCALE_IMPORTERS: Record<Language, () => Promise<LocaleModule>> = {
  en: () => import("./locales/en.json"),
  zu: () => import("./locales/zu.json"),
  xh: () => import("./locales/xh.json"),
};

/** True if `value` is one of the app's language codes. */
function isSupportedLanguage(value: string | null): value is Language {
  return SUPPORTED_LANGUAGES.includes(value as Language);
}

/**
 * Reads the language the person picked on the first screen, or null if they haven't picked yet.
 * Storage can throw (private mode, blocked site data), which counts as "not picked".
 */
export function getStoredLanguage(): Language | null {
  try {
    const storedValue = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isSupportedLanguage(storedValue) ? storedValue : null;
  } catch {
    return null;
  }
}

/** Remembers the chosen language on this phone. Fails quietly if storage is blocked. */
function updateStoredLanguage(language: Language) {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // Nothing to do: the app still works, it just asks again next time.
  }
}

/** Downloads a language's strings and hands them to i18next, unless they're already loaded. */
async function loadLanguageBundle(language: Language) {
  if (i18next.hasResourceBundle(language, TRANSLATION_NAMESPACE)) {
    return;
  }
  const locale = await LOCALE_IMPORTERS[language]();
  i18next.addResourceBundle(language, TRANSLATION_NAMESPACE, locale.default);
}

/**
 * Loads the chosen language plus the English fallback.
 * Once zu.json and xh.json are complete, P1 can drop the fallback download to save data.
 */
async function loadLanguageBundles(language: Language) {
  const languagesToLoad = new Set<Language>([FALLBACK_LANGUAGE, language]);
  await Promise.all([...languagesToLoad].map(loadLanguageBundle));
}

/** Starts i18next in the stored language (or English). Resolves once the strings are ready to render. */
export async function initI18n() {
  const language = getStoredLanguage() ?? FALLBACK_LANGUAGE;
  await i18next.use(initReactI18next).init({
    lng: language,
    fallbackLng: FALLBACK_LANGUAGE,
    resources: {},
    interpolation: { escapeValue: false }, // React already escapes text
  });
  await loadLanguageBundles(language);
  document.documentElement.lang = language;
}

/**
 * Switches the whole app to `language`: downloads its strings if needed, re-renders every
 * screen, remembers the choice and sets <html lang> so screen readers pronounce it right.
 */
export async function updateLanguage(language: Language) {
  await loadLanguageBundles(language);
  await i18next.changeLanguage(language);
  updateStoredLanguage(language);
  document.documentElement.lang = language;
}
