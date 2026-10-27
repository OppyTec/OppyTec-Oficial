import i18next, { type Resource } from "i18next";
import { initReactI18next } from "react-i18next";
import type {
  FutureLanguage,
  I18nNamespace,
  SupportedLanguage,
  TranslatableDynamicRecord,
  TranslationInterpolationVars,
} from "./i18next";

import analyticsEn from "./locales/en/analytics.json";
import authEn from "./locales/en/auth.json";
import catalogEn from "./locales/en/catalog.json";
import commonEn from "./locales/en/common.json";
import inventoryEn from "./locales/en/inventory.json";
import operationsEn from "./locales/en/operations.json";
import oppyfyEn from "./locales/en/oppyfy.json";
import platformAdminEn from "./locales/en/platform_admin.json";
import procurementEn from "./locales/en/procurement.json";
import rbacAuditEn from "./locales/en/rbac_audit.json";
import recipesEn from "./locales/en/recipes.json";
import configuracionEn from "./locales/en/configuracion.json";
import profileEn from "./locales/en/profile.json";
import usersEn from "./locales/en/users.json";
import navigationEn from "./locales/en/navigation.json";
import gestionEn from "./locales/en/gestion.json";
import productsEn from "./locales/en/products.json";
import excelImportEn from "./locales/en/excel_import.json";
import facturaImportEn from "./locales/en/factura_import.json";
import alertsEn from "./locales/en/alerts.json";
import historyEn from "./locales/en/history.json";
import notificationsEn from "./locales/en/notifications.json";

import analyticsEs from "./locales/es/analytics.json";
import authEs from "./locales/es/auth.json";
import catalogEs from "./locales/es/catalog.json";
import commonEs from "./locales/es/common.json";
import inventoryEs from "./locales/es/inventory.json";
import operationsEs from "./locales/es/operations.json";
import oppyfyEs from "./locales/es/oppyfy.json";
import platformAdminEs from "./locales/es/platform_admin.json";
import procurementEs from "./locales/es/procurement.json";
import rbacAuditEs from "./locales/es/rbac_audit.json";
import recipesEs from "./locales/es/recipes.json";
import configuracionEs from "./locales/es/configuracion.json";
import profileEs from "./locales/es/profile.json";
import usersEs from "./locales/es/users.json";
import navigationEs from "./locales/es/navigation.json";
import gestionEs from "./locales/es/gestion.json";
import productsEs from "./locales/es/products.json";
import excelImportEs from "./locales/es/excel_import.json";
import facturaImportEs from "./locales/es/factura_import.json";
import alertsEs from "./locales/es/alerts.json";
import historyEs from "./locales/es/history.json";
import notificationsEs from "./locales/es/notifications.json";

export const LANGUAGE_STORAGE_KEY = "oppytec_lang";

export const SUPPORTED_LANGUAGES: readonly SupportedLanguage[] = [
  "es",
  "en",
] as const;

export const FUTURE_LANGUAGE_CODES: readonly FutureLanguage[] = [
  "pt",
  "fr",
  "it",
  "de",
] as const;

export const I18N_NAMESPACES: readonly I18nNamespace[] = [
  "common",
  "auth",
  "rbac_audit",
  "catalog",
  "inventory",
  "recipes",
  "procurement",
  "operations",
  "analytics",
  "oppyfy",
  "platform_admin",
  "configuracion",
  "profile",
  "users",
  "navigation",
  "gestion",
  "products",
  "excel_import",
  "factura_import",
  "alerts",
  "history",
  "notifications",
] as const;

/**
 * Canonical list of protected proper nouns / gastronomic brand names
 * that must never be translated across locales (Rule 15 — "Pollo King" invariant).
 */
export const IMMUTABLE_PROPER_NOUNS: readonly string[] = [
  "Pollo King",
  "Savory",
  "Coca-Cola",
  "Nescafé",
  "Soprole",
  "Colun",
  "Ariztía",
  "Super Pollo",
  "NotCo",
  "Kunstmann",
  "Distribuidora Austral Food SpA",
  "Agrícola y Comercial Valle Central Ltda",
  "Lácteos del Sur S.A.",
  "Importadora y Distribuidora Gourmet Pacific",
] as const;

export const I18N_RESOURCES: Resource = {
  es: {
    common: commonEs,
    auth: authEs,
    rbac_audit: rbacAuditEs,
    catalog: catalogEs,
    inventory: inventoryEs,
    recipes: recipesEs,
    procurement: procurementEs,
    operations: operationsEs,
    analytics: analyticsEs,
    oppyfy: oppyfyEs,
    platform_admin: platformAdminEs,
    configuracion: configuracionEs,
    profile: profileEs,
    users: usersEs,
    navigation: navigationEs,
    gestion: gestionEs,
    products: productsEs,
    excel_import: excelImportEs,
    factura_import: facturaImportEs,
    alerts: alertsEs,
    history: historyEs,
    notifications: notificationsEs,
  },
  en: {
    common: commonEn,
    auth: authEn,
    rbac_audit: rbacAuditEn,
    catalog: catalogEn,
    inventory: inventoryEn,
    recipes: recipesEn,
    procurement: procurementEn,
    operations: operationsEn,
    analytics: analyticsEn,
    oppyfy: oppyfyEn,
    platform_admin: platformAdminEn,
    configuracion: configuracionEn,
    profile: profileEn,
    users: usersEn,
    navigation: navigationEn,
    gestion: gestionEn,
    products: productsEn,
    excel_import: excelImportEn,
    factura_import: facturaImportEn,
    alerts: alertsEn,
    history: historyEn,
    notifications: notificationsEn,
  },
};

const memoryFallbackStorage = new Map<string, string>();

function ensureBrowserStorage(): Pick<
  Storage,
  "getItem" | "setItem" | "removeItem" | "clear"
> {
  if (typeof window !== "undefined") {
    const ls = window.localStorage as unknown as
      | Partial<Storage>
      | undefined;
    if (
      ls &&
      typeof ls.getItem === "function" &&
      typeof ls.setItem === "function" &&
      typeof ls.clear === "function"
    ) {
      return ls as Pick<
        Storage,
        "getItem" | "setItem" | "removeItem" | "clear"
      >;
    }
    const polyfill: Storage = {
      get length() {
        return memoryFallbackStorage.size;
      },
      clear() {
        memoryFallbackStorage.clear();
      },
      getItem(key: string) {
        return memoryFallbackStorage.get(key) ?? null;
      },
      key(index: number) {
        return Array.from(memoryFallbackStorage.keys())[index] ?? null;
      },
      removeItem(key: string) {
        memoryFallbackStorage.delete(key);
      },
      setItem(key: string, value: string) {
        memoryFallbackStorage.set(key, String(value));
      },
    };
    Object.defineProperty(window, "localStorage", {
      value: polyfill,
      configurable: true,
      writable: true,
    });
    return polyfill;
  }
  return {
    getItem: (k: string) => memoryFallbackStorage.get(k) ?? null,
    setItem: (k: string, v: string) => {
      memoryFallbackStorage.set(k, String(v));
    },
    removeItem: (k: string) => {
      memoryFallbackStorage.delete(k);
    },
    clear: () => {
      memoryFallbackStorage.clear();
    },
  };
}

function readPersistedLanguage(): SupportedLanguage {
  const storage = ensureBrowserStorage();
  const stored = storage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored === "en" || stored === "es") {
    return stored;
  }
  return "es";
}

if (!i18next.isInitialized) {
  void i18next.use(initReactI18next).init({
    resources: I18N_RESOURCES,
    lng: readPersistedLanguage(),
    fallbackLng: "es",
    defaultNS: "common",
    ns: [...I18N_NAMESPACES],
    interpolation: {
      escapeValue: false,
    },
    returnNull: false,
  });
}

export function getActiveLanguage(): SupportedLanguage {
  const current = i18next.language;
  if (current === "en" || current === "es") {
    return current;
  }
  return readPersistedLanguage();
}

export function setActiveLanguage(lang: SupportedLanguage): SupportedLanguage {
  ensureBrowserStorage().setItem(LANGUAGE_STORAGE_KEY, lang);
  if (typeof document !== "undefined") {
    document.documentElement.lang = lang;
  }
  void i18next.changeLanguage(lang);
  return lang;
}

export function translateKey(
  namespace: I18nNamespace,
  key: string,
  vars?: TranslationInterpolationVars
): string {
  return String(
    i18next.t(key, {
      ns: namespace,
      ...(vars ?? {}),
    })
  );
}

function isProtectedProperNoun(text: string): boolean {
  const normalized = text.trim().toLowerCase();
  return IMMUTABLE_PROPER_NOUNS.some(
    (noun) => noun.toLowerCase() === normalized
  );
}

/**
 * Resolves dynamic database fields (`name_i18n` JSONB pattern) while strictly
 * preserving protected proper nouns / brands such as `"Pollo King"` and `"Savory"`.
 */
export function resolveDynamicFieldI18n(
  record: TranslatableDynamicRecord,
  lang: SupportedLanguage = getActiveLanguage()
): string {
  const baseName = record.name.trim();
  if (record.is_proper_noun === true || isProtectedProperNoun(baseName)) {
    return record.name;
  }

  const candidate = record.name_i18n?.[lang];
  if (typeof candidate === "string" && candidate.trim().length > 0) {
    return candidate;
  }

  const fallbackEs = record.name_i18n?.["es"];
  if (typeof fallbackEs === "string" && fallbackEs.trim().length > 0) {
    return fallbackEs;
  }

  return record.name;
}

export { i18next };
