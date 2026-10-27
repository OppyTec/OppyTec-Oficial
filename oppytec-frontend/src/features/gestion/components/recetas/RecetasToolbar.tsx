import React from "react";
import { Search, X, Plus, Tags, Sparkles, ScrollText, CookingPot } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import type { CategoriaReceta, TipoRecetaFiltro } from "../../types";

export interface RecetasToolbarProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedCategoriaId: string | number | null;
  onSelectCategoria: (id: string | number | null) => void;
  categorias: CategoriaReceta[];
  tipoFiltro: TipoRecetaFiltro;
  onSelectTipo: (tipo: TipoRecetaFiltro) => void;
  onNewReceta: () => void;
  onManageCategorias?: () => void;
}

export function RecetasToolbar({
  searchQuery,
  onSearchChange,
  selectedCategoriaId,
  onSelectCategoria,
  categorias,
  tipoFiltro,
  onSelectTipo,
  onNewReceta,
  onManageCategorias,
}: RecetasToolbarProps) {
  const { t } = useTranslation("recipes");

  const tipoOptions: Array<{
    id: TipoRecetaFiltro;
    label: string;
    icon?: React.ElementType;
    badgeEmoji?: string;
  }> = [
    { id: "todas", label: t("toolbar.type_all") },
    { id: "dinamicas", label: t("toolbar.type_dynamic"), icon: Sparkles },
    { id: "estaticas", label: t("toolbar.type_static"), icon: ScrollText },
    { id: "subrecetas", label: t("toolbar.type_subrecipes"), icon: CookingPot },
  ];

  return (
    <div
      data-testid="recetas-toolbar"
      className="space-y-3.5 bg-card border border-border/80 rounded-2xl p-3 sm:p-4 shadow-sm"
    >
      {/* Upper row: Search, Category Selector & Actions */}
      <div className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center justify-between">
        {/* Search input */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t("toolbar.search_recipes_placeholder")}
            data-testid="recetas-search-input"
            className="w-full h-11 min-h-[44px] pl-10 pr-10 rounded-xl border border-input bg-background text-foreground placeholder:text-muted-foreground/70 text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary shadow-sm transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              data-testid="recetas-clear-search"
              aria-label={t("toolbar.clear_search")}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer min-h-[32px] min-w-[32px] flex items-center justify-center"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Category selector & Action Buttons */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
          {/* Category Select */}
          <select
            data-testid="recetas-categoria-select"
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
              data-testid="btn-receta-categories"
              onClick={onManageCategorias}
              className="h-11 min-h-[44px] px-3.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground font-bold text-xs sm:text-sm inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-sm select-none"
            >
              <Tags className="h-4 w-4 text-muted-foreground" />
              <span className="hidden sm:inline">
                {t("toolbar.recipe_categories")}
              </span>
            </button>
          )}

          {/* New Recipe (Primary) */}
          <button
            type="button"
            data-testid="btn-new-receta"
            onClick={onNewReceta}
            className="h-11 min-h-[44px] px-4 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-extrabold text-xs sm:text-sm inline-flex items-center justify-center gap-2 transition-all shadow-md shadow-amber-500/20 cursor-pointer select-none"
          >
            <Plus className="h-4 w-4 stroke-[3px]" />
            <span>{t("toolbar.new_recipe")}</span>
          </button>
        </div>
      </div>

      {/* Lower row: Type filter segmented controls */}
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-1">
        <span className="text-[11px] font-black uppercase tracking-wider text-muted-foreground mr-1 hidden sm:inline">
          {t("toolbar.type_label")}
        </span>
        <div className="inline-flex p-1 rounded-xl bg-secondary/60 border border-border/60 gap-1">
          {tipoOptions.map((opt) => {
            const isSelected = tipoFiltro === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                data-testid={`recetas-tipo-${opt.id}`}
                onClick={() => onSelectTipo(opt.id)}
                className={cn(
                  "inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all min-h-[38px] cursor-pointer select-none",
                  isSelected
                    ? "bg-card text-foreground shadow-sm font-extrabold border border-border/80"
                    : "text-muted-foreground hover:text-foreground hover:bg-card/50"
                )}
              >
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default RecetasToolbar;
