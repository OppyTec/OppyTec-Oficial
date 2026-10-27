import { Search, X, Plus, Tags } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { CategoriaCombo } from "../../types";

export interface CombosToolbarProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedCategoriaId: string | number | null;
  onSelectCategoria: (id: string | number | null) => void;
  categorias: CategoriaCombo[];
  onNewCombo: () => void;
  onManageCategorias?: () => void;
}

export function CombosToolbar({
  searchQuery,
  onSearchChange,
  selectedCategoriaId,
  onSelectCategoria,
  categorias,
  onNewCombo,
  onManageCategorias,
}: CombosToolbarProps) {
  const { t } = useTranslation("recipes");

  return (
    <div
      data-testid="combos-toolbar"
      className="space-y-3.5 bg-card border border-border/80 rounded-2xl p-3 sm:p-4 shadow-sm"
    >
      <div className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center justify-between">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t("toolbar.search_combos_placeholder")}
            data-testid="combos-search-input"
            className="w-full h-11 min-h-[44px] pl-10 pr-10 rounded-xl border border-input bg-background text-foreground placeholder:text-muted-foreground/70 text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary shadow-sm transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              data-testid="combos-clear-search"
              aria-label={t("toolbar.clear_search")}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer min-h-[32px] min-w-[32px] flex items-center justify-center"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Actions & Category Selector */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
          {/* Category Select */}
          <select
            data-testid="combos-categoria-select"
            aria-label={t("toolbar.filter_category")}
            value={selectedCategoriaId ?? ""}
            onChange={(e) => onSelectCategoria(e.target.value ? e.target.value : null)}
            className="h-11 min-h-[44px] px-3.5 rounded-xl border border-input bg-background text-foreground text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary shadow-sm cursor-pointer flex-1 sm:flex-initial"
          >
            <option value="">{t("toolbar.all_categories")}</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={String(cat.id)}>
                {cat.nombre}
              </option>
            ))}
          </select>

          {/* Manage Categories (Secondary) */}
          {onManageCategorias && (
            <button
              type="button"
              data-testid="btn-combo-categories"
              onClick={onManageCategorias}
              className="h-11 min-h-[44px] px-3.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground font-bold text-xs sm:text-sm inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-sm select-none"
            >
              <Tags className="h-4 w-4 text-muted-foreground" />
              <span className="hidden sm:inline">
                {t("toolbar.combo_categories")}
              </span>
            </button>
          )}

          {/* New Combo (Primary) */}
          <button
            type="button"
            data-testid="btn-new-combo"
            onClick={onNewCombo}
            className="h-11 min-h-[44px] px-4 rounded-xl bg-pink-600 hover:bg-pink-700 text-white font-extrabold text-xs sm:text-sm inline-flex items-center justify-center gap-2 transition-all shadow-md shadow-pink-600/20 cursor-pointer select-none"
          >
            <Plus className="h-4 w-4 stroke-[3px]" />
            <span>{t("toolbar.new_combo")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default CombosToolbar;
