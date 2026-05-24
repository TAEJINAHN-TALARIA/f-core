import { getLocales } from "expo-localization";
import { I18n } from "i18n-js";
import en from "../locales/en";
import ko from "../locales/ko";

const i18n = new I18n({ en, ko });

const deviceLocale = getLocales()[0]?.languageCode ?? "en";
i18n.locale = ["en", "ko"].includes(deviceLocale) ? deviceLocale : "en";
i18n.enableFallback = true;
i18n.defaultLocale = "en";

export default i18n;
export type TranslationKeys = typeof en;
