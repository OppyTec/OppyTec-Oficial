import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Check, ChevronDown } from "lucide-react";
import {
  getActiveLanguage,
  i18next,
  setActiveLanguage,
  SUPPORTED_LANGUAGES,
  translateKey,
} from "./config";
import { LANGUAGE_FLAG_COMPONENTS } from "./flags";
import type { SupportedLanguage } from "./i18next";

export interface LanguageContextValue {
  readonly language: SupportedLanguage;
  readonly setLanguage: (lang: SupportedLanguage) => void;
}

export const LanguageContext = createContext<LanguageContextValue | null>(null);

export interface LanguageProviderProps {
  readonly children: ReactNode;
  readonly initialLanguage?: SupportedLanguage;
}

/**
 * Top-level provider ensuring reactive language changes across all views,
 * layouts, and subcomponents mounted within the application.
 */
export function LanguageProvider({
  children,
  initialLanguage,
}: LanguageProviderProps) {
  const [language, setLanguageState] = useState<SupportedLanguage>(
    () => initialLanguage ?? getActiveLanguage()
  );

  useEffect(() => {
    const handleLanguageChanged = (lng: string) => {
      if (lng === "es" || lng === "en") {
        setLanguageState(lng);
      }
    };
    i18next.on("languageChanged", handleLanguageChanged);
    return () => {
      i18next.off("languageChanged", handleLanguageChanged);
    };
  }, []);

  const changeLanguage = useCallback((nextLang: SupportedLanguage) => {
    setActiveLanguage(nextLang);
    setLanguageState(nextLang);
  }, []);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage: changeLanguage,
    }),
    [language, changeLanguage]
  );

  return (
    <LanguageContext.Provider value={value}>
      <div key={language} className="contents" data-current-lang={language}>
        {children}
      </div>
    </LanguageContext.Provider>
  );
}

/**
 * Hook to access current language reactively.
 * Falls back gracefully to `getActiveLanguage()` and listens to `i18next` if called outside of `LanguageProvider`.
 */
export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  const [, setTick] = useState(0);

  useEffect(() => {
    if (context) return;
    const onLang = () => setTick((t) => t + 1);
    i18next.on("languageChanged", onLang);
    return () => {
      i18next.off("languageChanged", onLang);
    };
  }, [context]);

  if (!context) {
    return {
      language: getActiveLanguage(),
      setLanguage: setActiveLanguage,
    };
  }
  return context;
}

export interface LanguageFlagSelectorProps {
  readonly value?: SupportedLanguage;
  readonly onLanguageChange?: (lang: SupportedLanguage) => void;
  readonly className?: string;
}

const LANGUAGE_LABELS: Readonly<Record<SupportedLanguage, string>> = {
  es: "Español",
  en: "English",
};

/**
 * Interactive navbar language selector rendering crisp vector SVG flags (`<FlagES />` / `<FlagUS />`)
 * inside a modern, accessible Tailwind dropdown menu.
 * Displays currently selected language and chevron on trigger.
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
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Sync internal state whenever language changes globally
  useEffect(() => {
    const handleLanguageChanged = (lng: string) => {
      if (lng === "es" || lng === "en") {
        setInternalLang(lng);
      }
    };
    i18next.on("languageChanged", handleLanguageChanged);
    return () => {
      i18next.off("languageChanged", handleLanguageChanged);
    };
  }, []);

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const activeLang: SupportedLanguage = value ?? internalLang;
  const ActiveFlag = LANGUAGE_FLAG_COMPONENTS[activeLang];

  const handleSelectLanguage = (nextLang: SupportedLanguage): void => {
    setActiveLanguage(nextLang);
    setInternalLang(nextLang);
    onLanguageChange?.(nextLang);
    setIsOpen(false);
  };

  return (
    <div
      ref={dropdownRef}
      role="group"
      aria-label={translateKey("common", "language.label")}
      data-testid="language-flag-selector"
      data-active-lang={activeLang}
      className={`relative inline-flex items-center ${className}`.trim()}
    >
      {/* Main trigger button showing current active language + flag + chevron */}
      <button
        type="button"
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label={translateKey("common", "language.label")}
        onClick={() => setIsOpen((prev) => !prev)}
        className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-lg border border-border bg-card/90 px-3 py-1.5 text-xs font-semibold text-foreground shadow-sm transition-all hover:bg-secondary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span
          data-testid="active-language-flag"
          className="inline-flex items-center"
        >
          <ActiveFlag
            title={LANGUAGE_LABELS[activeLang]}
            className="h-3.5 w-5 rounded-[2px]"
          />
        </span>
        <span>{LANGUAGE_LABELS[activeLang]}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown menu popover */}
      <div
        role="menu"
        aria-orientation="vertical"
        className={`absolute right-0 top-full mt-1.5 w-36 rounded-lg border border-border bg-popover p-1 shadow-lg z-50 ${
          isOpen ? "block animate-in fade-in-50 zoom-in-95" : "hidden"
        }`}
      >
        {SUPPORTED_LANGUAGES.map((lang) => {
          const isSelected = activeLang === lang;
          const label = LANGUAGE_LABELS[lang];
          const FlagComponent = LANGUAGE_FLAG_COMPONENTS[lang];
          return (
            <button
              key={lang}
              type="button"
              role="menuitem"
              data-testid={`lang-option-${lang}`}
              aria-pressed={isSelected}
              aria-label={translateKey("common", "language.switch_to", {
                lang: label,
              })}
              onClick={() => handleSelectLanguage(lang)}
              className={`touch-target flex w-full items-center justify-between rounded-md px-2.5 py-2 text-xs font-medium transition-all ${
                isSelected
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-foreground hover:bg-secondary"
              }`}
            >
              <div className="flex items-center gap-2">
                <FlagComponent
                  title={label}
                  className="h-3.5 w-5 rounded-[2px]"
                />
                <span className="font-semibold">{label}</span>
              </div>
              {isSelected && <Check className="h-3.5 w-3.5 shrink-0" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
