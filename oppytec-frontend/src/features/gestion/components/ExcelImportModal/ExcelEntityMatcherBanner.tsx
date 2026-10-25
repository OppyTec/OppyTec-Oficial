// oppytec-frontend/src/features/gestion/components/ExcelImportModal/ExcelEntityMatcherBanner.tsx
import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CheckCircle2, Sparkles, Tags, Award } from "lucide-react";
import type { Categoria, Marca } from "../../types";

export interface ExcelEntityMatcherBannerProps {
  readonly detectedCategories: readonly string[];
  readonly detectedBrands: readonly string[];
  readonly existingCategories: readonly Categoria[];
  readonly existingBrands: readonly Marca[];
  readonly categoryMappings: Record<string, string>; // excelCat -> catId or '__new__'
  readonly brandMappings: Record<string, string>; // excelBrand -> brandId or '__new__'
  readonly onCategoryMappingChange: (excelCat: string, targetCatId: string) => void;
  readonly onBrandMappingChange: (excelBrand: string, targetBrandId: string) => void;
  readonly onAutoCreateAll: () => void;
}

export const ExcelEntityMatcherBanner: React.FC<ExcelEntityMatcherBannerProps> = ({
  detectedCategories,
  detectedBrands,
  existingCategories,
  existingBrands,
  categoryMappings,
  brandMappings,
  onCategoryMappingChange,
  onBrandMappingChange,
  onAutoCreateAll,
}) => {
  const { t } = useTranslation(["excel_import", "gestion"]);

  // Existing names maps (case-insensitive)
  const existingCatNames = useMemo(() => {
    const map = new Map<string, string>();
    existingCategories.forEach((c) => map.set(c.nombre.toLowerCase().trim(), c.id));
    return map;
  }, [existingCategories]);

  const existingBrandNames = useMemo(() => {
    const map = new Map<string, string>();
    existingBrands.forEach((b) => map.set(b.nombre.toLowerCase().trim(), b.id));
    return map;
  }, [existingBrands]);

  // Identify new entities
  const newCategories = useMemo(() => {
    return detectedCategories.filter(
      (cat) => cat.trim() && !existingCatNames.has(cat.toLowerCase().trim())
    );
  }, [detectedCategories, existingCatNames]);

  const newBrands = useMemo(() => {
    return detectedBrands.filter(
      (b) => b.trim() && !existingBrandNames.has(b.toLowerCase().trim())
    );
  }, [detectedBrands, existingBrandNames]);

  const totalNew = newCategories.length + newBrands.length;

  if (totalNew === 0) {
    return (
      <div
        data-testid="excel-entity-all-matched"
        className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-600 dark:text-emerald-400 text-xs font-semibold"
      >
        <CheckCircle2 className="h-5 w-5 shrink-0" />
        <span>
          {t("entity_matcher.all_matched", {
            catCount: detectedCategories.length,
            brandCount: detectedBrands.length,
            defaultValue: `Todas las categorías (${detectedCategories.length}) y marcas (${detectedBrands.length}) detectadas en el archivo ya existen en tu catálogo maestro.`,
          })}
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="excel-entity-matcher-banner"
      className="space-y-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-foreground"
    >
      {/* Alert Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-black uppercase text-amber-700 dark:text-amber-300">
              {t("entity_matcher.new_detected_title", {
                total: totalNew,
                defaultValue: `Detección de Nuevas Entidades (${totalNew})`,
              })}
            </h4>
            <p className="text-[11px] text-muted-foreground">
              {t("entity_matcher.new_detected_desc", {
                catCount: newCategories.length,
                brandCount: newBrands.length,
                defaultValue: `Encontramos ${newCategories.length} categoría(s) y ${newBrands.length} marca(s) en la planilla que no existen en el sistema.`,
              })}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onAutoCreateAll}
          data-testid="btn-auto-create-entities"
          className="touch-target inline-flex min-h-[44px] px-3.5 items-center gap-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-black uppercase tracking-wider shadow-sm cursor-pointer select-none shrink-0"
        >
          <Sparkles className="h-4 w-4" />
          <span>{t("entity_matcher.auto_create_all", "Crear Todas al Vuelo")}</span>
        </button>
      </div>

      {/* Grid of unmatched categories and brands */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {/* Categorías Nuevas */}
        {newCategories.length > 0 && (
          <div className="space-y-2 p-3 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 pb-1 border-b border-border">
              <Tags className="h-4 w-4 text-primary shrink-0" />
              <span className="text-xs font-black uppercase text-foreground">
                {t("entity_matcher.missing_categories", "Categorías Inexistentes")} ({newCategories.length})
              </span>
            </div>

            <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1 custom-scrollbar">
              {newCategories.map((cat) => {
                const selected = categoryMappings[cat] || "__new__";
                return (
                  <div
                    key={cat}
                    data-testid={`entity-row-cat-${cat}`}
                    className="flex items-center justify-between gap-2 p-2 rounded-lg bg-secondary/30 text-xs"
                  >
                    <span className="font-bold text-foreground truncate max-w-[140px]">
                      {cat}
                    </span>
                    <select
                      value={selected}
                      onChange={(e) => onCategoryMappingChange(cat, e.target.value)}
                      data-testid={`select-cat-mapping-${cat}`}
                      className="h-9 px-2 rounded-lg bg-background border border-input text-[11px] font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer truncate max-w-[180px]"
                    >
                      <option value="__new__">
                        {t("entity_matcher.create_new_option", "+ Crear como nueva")}
                      </option>
                      {existingCategories.map((c) => (
                        <option key={c.id} value={c.id}>
                          Mapear a: {c.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Marcas Nuevas */}
        {newBrands.length > 0 && (
          <div className="space-y-2 p-3 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 pb-1 border-b border-border">
              <Award className="h-4 w-4 text-primary shrink-0" />
              <span className="text-xs font-black uppercase text-foreground">
                {t("entity_matcher.missing_brands", "Marcas Inexistentes")} ({newBrands.length})
              </span>
            </div>

            <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1 custom-scrollbar">
              {newBrands.map((brand) => {
                const selected = brandMappings[brand] || "__new__";
                return (
                  <div
                    key={brand}
                    data-testid={`entity-row-brand-${brand}`}
                    className="flex items-center justify-between gap-2 p-2 rounded-lg bg-secondary/30 text-xs"
                  >
                    <span className="font-bold text-foreground truncate max-w-[140px]">
                      {brand}
                    </span>
                    <select
                      value={selected}
                      onChange={(e) => onBrandMappingChange(brand, e.target.value)}
                      data-testid={`select-brand-mapping-${brand}`}
                      className="h-9 px-2 rounded-lg bg-background border border-input text-[11px] font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer truncate max-w-[180px]"
                    >
                      <option value="__new__">
                        {t("entity_matcher.create_new_option", "+ Crear como nueva")}
                      </option>
                      {existingBrands.map((b) => (
                        <option key={b.id} value={b.id}>
                          Mapear a: {b.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
