export {
  FUTURE_LANGUAGE_CODES,
  I18N_NAMESPACES,
  I18N_RESOURCES,
  IMMUTABLE_PROPER_NOUNS,
  LANGUAGE_STORAGE_KEY,
  SUPPORTED_LANGUAGES,
  getActiveLanguage,
  i18next,
  resolveDynamicFieldI18n,
  setActiveLanguage,
  translateKey,
} from "./config";
export {
  FUTURE_LANGUAGES,
  FlagES,
  FlagUS,
  LANGUAGE_FLAG_COMPONENTS,
  type FlagIconProps,
  type FutureLanguageDescriptor,
} from "./flags";
export type {
  FutureLanguage,
  I18nNamespace,
  SupportedLanguage,
  TranslatableDynamicRecord,
  TranslationInterpolationVars,
} from "./i18next";
export {
  LanguageFlagSelector,
  type LanguageFlagSelectorProps,
} from "./LanguageFlagSelector";
