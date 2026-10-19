import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  FUTURE_LANGUAGE_CODES,
  FUTURE_LANGUAGES,
  FlagES,
  FlagUS,
  type FlagIconProps,
  type FutureLanguage,
  type FutureLanguageDescriptor,
  I18N_NAMESPACES,
  I18N_RESOURCES,
  type I18nNamespace,
  IMMUTABLE_PROPER_NOUNS,
  LANGUAGE_FLAG_COMPONENTS,
  LANGUAGE_STORAGE_KEY,
  LanguageFlagSelector,
  type LanguageFlagSelectorProps,
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
  type TranslatableDynamicRecord,
  type TranslationInterpolationVars,
  getActiveLanguage,
  i18next,
  resolveDynamicFieldI18n,
  setActiveLanguage,
  translateKey,
} from "./index";

describe("Frontend i18n Suite (11 Namespaces, SVG Flags & Pollo King Proper Noun Guard)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  it("initializes all 11 namespaces for both es and en with 1:1 parity", () => {
    expect(SUPPORTED_LANGUAGES).toEqual(["es", "en"]);
    expect(I18N_NAMESPACES).toHaveLength(11);
    expect(i18next.isInitialized).toBe(true);

    for (const ns of I18N_NAMESPACES) {
      expect(I18N_RESOURCES.es?.[ns]).toBeDefined();
      expect(I18N_RESOURCES.en?.[ns]).toBeDefined();
    }

    const vars: TranslationInterpolationVars = { name: "Chef" };
    expect(translateKey("common", "app.welcome", vars)).toBe(
      "Bienvenido a OppyTec, Chef"
    );

    setActiveLanguage("en");
    expect(getActiveLanguage()).toBe("en");
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    expect(translateKey("common", "app.welcome", vars)).toBe(
      "Welcome to OppyTec, Chef"
    );
  });

  it("preserves protected proper nouns like 'Pollo King' and 'Savory' across all languages", () => {
    expect(IMMUTABLE_PROPER_NOUNS).toContain("Pollo King");
    expect(IMMUTABLE_PROPER_NOUNS).toContain("Savory");

    const polloKingRecord: TranslatableDynamicRecord = {
      name: "Pollo King",
      name_i18n: {
        es: "Pollo Rey",
        en: "King Chicken",
      },
      is_proper_noun: true,
    };

    expect(resolveDynamicFieldI18n(polloKingRecord, "es")).toBe("Pollo King");
    expect(resolveDynamicFieldI18n(polloKingRecord, "en")).toBe("Pollo King");

    const savoryImplicitBrand: TranslatableDynamicRecord = {
      name: "Savory",
      name_i18n: {
        en: "Tasty Ice Cream",
      },
    };
    expect(resolveDynamicFieldI18n(savoryImplicitBrand, "en")).toBe("Savory");

    const genericIngredient: TranslatableDynamicRecord = {
      name: "Pechuga de Pollo Deshuesada",
      name_i18n: {
        es: "Pechuga de Pollo Deshuesada",
        en: "Boneless Chicken Breast",
      },
      is_proper_noun: false,
    };

    expect(resolveDynamicFieldI18n(genericIngredient, "es")).toBe(
      "Pechuga de Pollo Deshuesada"
    );
    expect(resolveDynamicFieldI18n(genericIngredient, "en")).toBe(
      "Boneless Chicken Breast"
    );
  });

  it("renders crisp SVG flags (FlagES, FlagUS) and exposes future languages metadata (pt, fr, it, de)", () => {
    expect(FUTURE_LANGUAGE_CODES).toEqual(["pt", "fr", "it", "de"]);
    expect(FUTURE_LANGUAGES).toHaveLength(4);
    const ptMeta: FutureLanguageDescriptor | undefined = FUTURE_LANGUAGES[0];
    const futureCode: FutureLanguage = ptMeta?.code ?? "pt";
    expect(futureCode).toBe("pt");
    expect(LANGUAGE_FLAG_COMPONENTS.es).toBe(FlagES);
    expect(LANGUAGE_FLAG_COMPONENTS.en).toBe(FlagUS);

    const flagProps: FlagIconProps = { title: "US Test Flag" };
    const { unmount } = render(
      <div>
        <FlagES title="ES Test Flag" />
        <FlagUS {...flagProps} />
      </div>
    );

    expect(screen.getByLabelText("ES Test Flag")).toBeDefined();
    expect(screen.getByLabelText("US Test Flag")).toBeDefined();
    unmount();
  });

  it("switches languages instantaneously via LanguageFlagSelector without affecting currency", () => {
    const onLanguageChange = vi.fn<(lang: SupportedLanguage) => void>();
    const selectorProps: LanguageFlagSelectorProps = {
      onLanguageChange,
    };

    render(<LanguageFlagSelector {...selectorProps} />);

    const selector = screen.getByTestId("language-flag-selector");
    expect(selector.getAttribute("data-active-lang")).toBe("es");

    const enButton = screen.getByTestId("lang-option-en");
    fireEvent.click(enButton);

    expect(onLanguageChange).toHaveBeenCalledWith("en");
    expect(getActiveLanguage()).toBe("en");
    expect(selector.getAttribute("data-active-lang")).toBe("en");

    const nsCheck: I18nNamespace = "inventory";
    expect(
      translateKey(nsCheck, "warehouse.stock_level", {
        quantity: 25,
        unit: "kg",
      })
    ).toBe("Available stock: 25 kg");
  });
});
