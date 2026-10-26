export type SupportedLanguage = "es" | "en";

export type FutureLanguage = "pt" | "fr" | "it" | "de";

export type I18nNamespace =
  | "common"
  | "auth"
  | "rbac_audit"
  | "catalog"
  | "inventory"
  | "recipes"
  | "procurement"
  | "operations"
  | "analytics"
  | "oppyfy"
  | "platform_admin"
  | "configuracion"
  | "profile"
  | "users"
  | "navigation"
  | "gestion"
  | "products"
  | "excel_import"
  | "factura_import"
  | "alerts"
  | "history"
  | "notifications";

export type TranslationInterpolationVars = Readonly<
  Record<string, string | number>
>;

export interface TranslatableDynamicRecord {
  readonly name: string;
  readonly name_i18n?: Readonly<
    Partial<Record<SupportedLanguage | FutureLanguage | string, string>>
  >;
  readonly is_proper_noun?: boolean;
}
