import { useState } from "react";
import {
  getActiveLanguage,
  setActiveLanguage,
  SUPPORTED_LANGUAGES,
  translateKey,
} from "./config";
import { FlagES, FlagUS, LANGUAGE_FLAG_COMPONENTS } from "./flags";
import type { SupportedLanguage } from "./i18next";

export interface LanguageFlagSelectorProps {
  readonly value?: SupportedLanguage;
  readonly onLanguageChange?: (lang: SupportedLanguage) => void;
  readonly className?: string;
}

const LANGUAGE_LABELS: Readonly<Record<SupportedLanguage, string>> = {
  es: "Español",
  en: "English (US)",
};

/**
 * Interactive navbar language selector rendering crisp vector SVG flags (`<FlagES />` / `<FlagUS />`).
 * Operates completely independently of the currency selector (`<CurrencySelector />`).
 */
export function LanguageFlagSelector({
  value,
  onLanguageChange,
  className = "",
}: LanguageFlagSelectorProps) {
  const [internalLang, setInternalLang] = useState<SupportedLanguage>(() =>
    getActiveLanguage()
  );

  const activeLang: SupportedLanguage = value ?? internalLang;
  const ActiveFlag = LANGUAGE_FLAG_COMPONENTS[activeLang];

  const handleSelectLanguage = (nextLang: SupportedLanguage): void => {
    setActiveLanguage(nextLang);
    setInternalLang(nextLang);
    onLanguageChange?.(nextLang);
  };

  return (
    <div
      role="group"
      aria-label={translateKey("common", "language.label")}
      data-testid="language-flag-selector"
      data-active-lang={activeLang}
      className={`inline-flex items-center gap-1.5 rounded-lg border border-border bg-card/80 p-1 ${className}`.trim()}
    >
      <span
        data-testid="active-language-flag"
        className="inline-flex items-center px-1.5"
      >
        <ActiveFlag title={LANGUAGE_LABELS[activeLang]} />
      </span>

      {SUPPORTED_LANGUAGES.map((lang) => {
        const isSelected = activeLang === lang;
        const label = LANGUAGE_LABELS[lang];
        return (
          <button
            key={lang}
            type="button"
            data-testid={`lang-option-${lang}`}
            aria-pressed={isSelected}
            aria-label={translateKey("common", "language.switch_to", {
              lang: label,
            })}
            onClick={() => handleSelectLanguage(lang)}
            className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all ${
              isSelected
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
            }`}
          >
            {lang === "es" ? (
              <FlagES title={label} className="h-3.5 w-5 rounded-[2px]" />
            ) : (
              <FlagUS title={label} className="h-3.5 w-5 rounded-[2px]" />
            )}
            <span className="uppercase">{lang}</span>
          </button>
        );
      })}
    </div>
  );
}
