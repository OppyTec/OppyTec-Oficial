import type { FutureLanguage, SupportedLanguage } from "../i18next";
import { FlagES } from "./FlagES";
import { type FlagIconProps, FlagUS } from "./FlagUS";

export { FlagES, FlagUS, type FlagIconProps };

export interface FutureLanguageDescriptor {
  readonly code: FutureLanguage;
  readonly label: string;
  readonly region: string;
  readonly enabled: false;
}

export const FUTURE_LANGUAGES: readonly FutureLanguageDescriptor[] = [
  { code: "pt", label: "Português", region: "BR/PT", enabled: false },
  { code: "fr", label: "Français", region: "FR", enabled: false },
  { code: "it", label: "Italiano", region: "IT", enabled: false },
  { code: "de", label: "Deutsch", region: "DE", enabled: false },
] as const;

export const LANGUAGE_FLAG_COMPONENTS: Record<
  SupportedLanguage,
  typeof FlagES | typeof FlagUS
> = {
  es: FlagES,
  en: FlagUS,
};
