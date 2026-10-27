import { useState, useMemo } from "react";
import { Boxes } from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { useCombos } from "../../hooks/useCombos";
import { useRecetas } from "../../hooks/useRecetas";
import { useGruposOpciones } from "../../hooks/useGruposOpciones";
import { INITIAL_PRODUCTOS_MOCK } from "../../useGestion";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { CombosToolbar } from "./CombosToolbar";
import { CombosTable } from "./CombosTable";
import { ComboMobileCard } from "./ComboMobileCard";
import { ComboDialog } from "../ComboDialog";
import { TablePagination } from "../TablePagination";
import type { Combo, Producto, ComboCreateInput } from "../../types";

export interface CombosViewProps {
  productos?: Producto[];
  onNewCombo?: () => void;
  onEditCombo?: (combo: Combo) => void;
  onViewCombo?: (combo: Combo) => void;
  onManageCategorias?: () => void;
}

export function CombosView({
  productos = INITIAL_PRODUCTOS_MOCK,
  onNewCombo,
  onEditCombo,
  onViewCombo,
  onManageCategorias,
}: CombosViewProps) {
  const { t } = useTranslation("recipes");
  const isMobile = useIsMobile();
  const {
    combosFiltrados,
    categorias,
    filter,
    setCategoriaFiltro,
    setSearchFiltro,
    createCombo,
    updateCombo,
    deleteCombo,
    isLoading,
  } = useCombos();

  const { recetas } = useRecetas();
  const { gruposOpciones } = useGruposOpciones();

  const [localCombosOverride, setLocalCombosOverride] = useState<Combo[] | null>(null);
  const [isComboDialogOpen, setIsComboDialogOpen] = useState(false);
  const [editingCombo, setEditingCombo] = useState<Combo | null>(null);
  const [isDuplicateMode, setIsDuplicateMode] = useState(false);

  const effectiveCombos = useMemo(
    () => localCombosOverride ?? combosFiltrados,
    [localCombosOverride, combosFiltrados]
  );

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  const paginatedCombos = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return effectiveCombos.slice(startIndex, startIndex + pageSize);
  }, [effectiveCombos, currentPage, pageSize]);

  const handleOpenNew = () => {
    setEditingCombo(null);
    setIsDuplicateMode(false);
    setIsComboDialogOpen(true);
    onNewCombo?.();
  };

  const handleOpenEdit = (combo: Combo) => {
    setEditingCombo(combo);
    setIsDuplicateMode(false);
    setIsComboDialogOpen(true);
    onEditCombo?.(combo);
  };

  const handleOpenView = (combo: Combo) => {
    setEditingCombo(combo);
    setIsDuplicateMode(false);
    setIsComboDialogOpen(true);
    onViewCombo?.(combo);
  };

  const handleDuplicate = (combo: Combo) => {
    toast.info(t("views.duplicating_combo_toast", { name: combo.nombre }));
    setEditingCombo(combo);
    setIsDuplicateMode(true);
    setIsComboDialogOpen(true);
  };

  const handleSaveCombo = async (
    payload: ComboCreateInput,
    calculatedCombo: Combo
  ) => {
    try {
      if (editingCombo && !isDuplicateMode) {
        await updateCombo({ id: editingCombo.id, data: payload });
      } else {
        await createCombo(payload);
      }
    } catch {
      setLocalCombosOverride((prev) => {
        const base = prev ?? combosFiltrados;
        if (editingCombo && !isDuplicateMode) {
          return base.map((c) =>
            String(c.id) === String(editingCombo.id) ? calculatedCombo : c
          );
        }
        return [calculatedCombo, ...base];
      });
    }
  };

  const handleDelete = async (combo: Combo) => {
    try {
      await deleteCombo(combo.id);
    } catch {
      setLocalCombosOverride((prev) =>
        (prev ?? combosFiltrados).filter((c) => String(c.id) !== String(combo.id))
      );
    }
  };

  return (
    <div data-testid="combos-view-root" className="space-y-4 w-full">
      {/* 1. Combos Toolbar */}
      <CombosToolbar
        searchQuery={filter.search || ""}
        onSearchChange={(q) => {
          setLocalCombosOverride(null);
          setSearchFiltro(q);
          setCurrentPage(1);
        }}
        selectedCategoriaId={filter.categoria_id ?? null}
        onSelectCategoria={(catId) => {
          setLocalCombosOverride(null);
          setCategoriaFiltro(catId);
          setCurrentPage(1);
        }}
        categorias={categorias}
        onNewCombo={handleOpenNew}
        onManageCategorias={onManageCategorias}
      />

      {/* 2. Combos Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card shadow-sm">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-pink-500 border-t-transparent mb-3" />
          <p className="text-xs font-semibold text-muted-foreground">
            {t("views.loading_combos")}
          </p>
        </div>
      ) : effectiveCombos.length === 0 ? (
        <div
          data-testid="combos-empty-state"
          className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card shadow-sm"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-pink-500/10 text-pink-600 mb-3">
            <Boxes className="h-7 w-7" />
          </div>
          <h4 className="text-sm font-bold text-foreground mb-1">
            {t("views.empty_combos_title")}
          </h4>
          <p className="text-xs text-muted-foreground max-w-sm mb-4">
            {filter.search || filter.categoria_id
              ? t("views.empty_combos_filtered_desc")
              : t("views.empty_combos_default_desc")}
          </p>
          {(filter.search || filter.categoria_id) && (
            <button
              type="button"
              onClick={() => {
                setLocalCombosOverride(null);
                setSearchFiltro("");
                setCategoriaFiltro(null);
                setCurrentPage(1);
              }}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-xl border border-border bg-secondary px-3 py-1.5 text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer select-none"
            >
              {t("views.reset_filters")}
            </button>
          )}
        </div>
      ) : isMobile ? (
        /* Mobile Cards List */
        <div className="flex flex-col gap-2.5 pb-4 md:hidden">
          {paginatedCombos.map((c) => (
            <ComboMobileCard
              key={c.id}
              combo={c}
              onView={handleOpenView}
              onEdit={handleOpenEdit}
              onDuplicate={handleDuplicate}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        /* Desktop Table */
        <div className="hidden md:block">
          <CombosTable
            combos={paginatedCombos}
            onView={handleOpenView}
            onEdit={handleOpenEdit}
            onDuplicate={handleDuplicate}
            onDelete={handleDelete}
          />
        </div>
      )}

      {/* 3. Pagination */}
      {effectiveCombos.length > 0 && (
        <TablePagination
          currentPage={currentPage}
          totalItems={effectiveCombos.length}
          pageSize={pageSize}
          pageSizeOptions={[10, 25, 50, 100]}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
          itemLabel={t("views.combos_pagination_label")}
        />
      )}

      {/* 4. Modal Maestro de Combos (Fase 5) */}
      <ComboDialog
        open={isComboDialogOpen}
        onClose={() => setIsComboDialogOpen(false)}
        combo={editingCombo}
        isDuplicate={isDuplicateMode}
        categorias={categorias}
        productos={productos}
        recetas={recetas}
        gruposBiblioteca={gruposOpciones}
        onSave={handleSaveCombo}
      />
    </div>
  );
}

export default CombosView;
