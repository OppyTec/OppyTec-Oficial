/**
 * oppytec-frontend/src/features/projection/components/ProyeccionCategoryFilter.tsx
 * Filtro táctil deslizante por categorías para el módulo de Proyección.
 * Píldoras horizontales con botón "Todas", conteo de productos y compatibilidad con multi-selección.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";

export interface CategoryFilterItem {
  readonly id: string | number;
  readonly name: string;
  readonly count?: number;
}

export interface ProyeccionCategoryFilterProps {
  readonly categories: readonly CategoryFilterItem[];
  readonly selectedCategoryId?: string | number | "all";
  readonly selectedCategoryIds?: readonly (string | number)[];
  readonly onSelectCategory: (categoryId: string | number | "all") => void;
  readonly onToggleCategory?: (categoryId: string | number) => void;
  readonly className?: string;
}

export const ProyeccionCategoryFilter: FC<ProyeccionCategoryFilterProps> = ({
  categories,
  selectedCategoryId = "all",
  selectedCategoryIds,
  onSelectCategory,
  onToggleCategory,
  className,
}) => {
  const { t } = useTranslation("projection");

  const isMultiSelect = Array.isArray(selectedCategoryIds);

  const isAllSelected = isMultiSelect
    ? selectedCategoryIds.length === 0
    : selectedCategoryId === "all";

  const isCategorySelected = (catId: string | number): boolean => {
    if (isMultiSelect) {
      return selectedCategoryIds.some((id) => String(id) === String(catId));
    }
    return String(selectedCategoryId) === String(catId);
  };

  const handleCategoryClick = (catId: string | number) => {
    if (isMultiSelect && onToggleCategory) {
      onToggleCategory(catId);
    } else {
      // Si ya está seleccionada la misma categoría, deseleccionar a "all"
      if (String(selectedCategoryId) === String(catId)) {
        onSelectCategory("all");
      } else {
        onSelectCategory(catId);
      }
    }
  };

  const handleSelectAll = () => {
    onSelectCategory("all");
  };

  if (categories.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="proyeccion-category-filter"
      className={cn(
        "flex w-full items-center gap-2 overflow-x-auto py-1 scroll-smooth select-none no-scrollbar",
        className
      )}
    >
      {/* Botón "Todas" */}
      <button
        type="button"
        onClick={handleSelectAll}
        data-testid="category-pill-all"
        className={cn(
          "flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3.5 text-xs font-bold transition-all cursor-pointer",
          isAllSelected
            ? "bg-emerald-600 text-white shadow-sm shadow-emerald-600/30 ring-1 ring-emerald-600"
            : "border border-border bg-card text-muted-foreground hover:bg-secondary hover:text-foreground"
        )}
      >
        <span>{t("categories.all", { defaultValue: "Todas" })}</span>
      </button>

      {/* Píldoras de Categorías */}
      {categories.map((cat) => {
        const selected = isCategorySelected(cat.id);
        return (
          <button
            key={`cat-pill-${cat.id}`}
            type="button"
            onClick={() => handleCategoryClick(cat.id)}
            data-testid={`category-pill-${cat.id}`}
            className={cn(
              "flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3.5 text-xs font-bold transition-all cursor-pointer",
              selected
                ? "bg-emerald-600 text-white shadow-sm shadow-emerald-600/30 ring-1 ring-emerald-600"
                : "border border-border bg-card text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
          >
            <span>{cat.name}</span>
            {cat.count !== undefined && (
              <span
                className={cn(
                  "ml-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-black",
                  selected
                    ? "bg-white/20 text-white"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {cat.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default ProyeccionCategoryFilter;
