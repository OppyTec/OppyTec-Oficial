import { useState, useMemo } from "react";
import { Inbox } from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { useRecetas } from "../../hooks/useRecetas";
import { useGruposOpciones } from "../../hooks/useGruposOpciones";
import { INITIAL_PRODUCTOS_MOCK } from "../../useGestion";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { RecetasToolbar } from "./RecetasToolbar";
import { RecetasTable } from "./RecetasTable";
import { RecetaMobileCard } from "./RecetaMobileCard";
import { RecetaDialog } from "../RecetaDialog";
import { RecetaDetalleModal } from "../RecetaDetalleModal";
import { TablePagination } from "../TablePagination";
import type {
  Receta,
  Producto,
  TipoRecetaFiltro,
  RecipeCreateInput,
} from "../../types";

export interface RecetasViewProps {
  productos?: Producto[];
  onNewReceta?: () => void;
  onEditReceta?: (receta: Receta) => void;
  onViewReceta?: (receta: Receta) => void;
  onManageCategorias?: () => void;
}

export function RecetasView({
  productos = INITIAL_PRODUCTOS_MOCK,
  onNewReceta,
  onEditReceta,
  onViewReceta,
  onManageCategorias,
}: RecetasViewProps) {
  const { t } = useTranslation("recipes");
  const isMobile = useIsMobile();
  const {
    recetas,
    recetasFiltradas,
    categorias,
    filter,
    setTipoFiltro,
    setCategoriaFiltro,
    setSearchFiltro,
    createReceta,
    updateReceta,
    deleteReceta,
    isLoading,
  } = useRecetas();

  const { gruposOpciones } = useGruposOpciones();

  // Local optimistic overrides so offline / test creations & edits reflect immediately
  const [localRecetasOverride, setLocalRecetasOverride] = useState<Receta[] | null>(null);

  // Modal states
  const [isRecetaDialogOpen, setIsRecetaDialogOpen] = useState(false);
  const [editingReceta, setEditingReceta] = useState<Receta | null>(null);
  const [isDuplicateMode, setIsDuplicateMode] = useState(false);
  const [viewingReceta, setViewingReceta] = useState<Receta | null>(null);

  const effectiveRecetas = useMemo(() => {
    const source = localRecetasOverride ?? recetasFiltradas;
    return source;
  }, [localRecetasOverride, recetasFiltradas]);

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  const paginatedRecetas = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return effectiveRecetas.slice(startIndex, startIndex + pageSize);
  }, [effectiveRecetas, currentPage, pageSize]);

  const handleOpenNew = () => {
    setEditingReceta(null);
    setIsDuplicateMode(false);
    setIsRecetaDialogOpen(true);
    onNewReceta?.();
  };

  const handleOpenEdit = (receta: Receta) => {
    setEditingReceta(receta);
    setIsDuplicateMode(false);
    setIsRecetaDialogOpen(true);
    onEditReceta?.(receta);
  };

  const handleDuplicate = (receta: Receta) => {
    toast.info(t("views.duplicating_recipe_toast", { name: receta.nombre }));
    setEditingReceta(receta);
    setIsDuplicateMode(true);
    setIsRecetaDialogOpen(true);
  };

  const handleOpenView = (receta: Receta) => {
    setViewingReceta(receta);
    onViewReceta?.(receta);
  };

  const handleSaveReceta = async (
    payload: RecipeCreateInput,
    calculatedReceta: Receta
  ) => {
    try {
      if (editingReceta && !isDuplicateMode) {
        await updateReceta({ id: editingReceta.id, data: payload });
      } else {
        await createReceta(payload);
      }
    } catch {
      // Optimistic local state update when offline
      setLocalRecetasOverride((prev) => {
        const base = prev ?? recetasFiltradas;
        if (editingReceta && !isDuplicateMode) {
          return base.map((r) =>
            String(r.id) === String(editingReceta.id) ? calculatedReceta : r
          );
        }
        return [calculatedReceta, ...base];
      });
    }
  };

  const handleDelete = async (receta: Receta) => {
    try {
      await deleteReceta(receta.id);
    } catch {
      setLocalRecetasOverride((prev) =>
        (prev ?? recetasFiltradas).filter((r) => String(r.id) !== String(receta.id))
      );
    }
  };

  return (
    <div data-testid="recetas-view-root" className="space-y-4 w-full">
      {/* 1. Recetas Toolbar */}
      <RecetasToolbar
        searchQuery={filter.search || ""}
        onSearchChange={(q) => {
          setLocalRecetasOverride(null);
          setSearchFiltro(q);
          setCurrentPage(1);
        }}
        selectedCategoriaId={filter.categoria_id ?? null}
        onSelectCategoria={(catId) => {
          setLocalRecetasOverride(null);
          setCategoriaFiltro(catId);
          setCurrentPage(1);
        }}
        categorias={categorias}
        tipoFiltro={filter.tipo as TipoRecetaFiltro}
        onSelectTipo={(tipo) => {
          setLocalRecetasOverride(null);
          setTipoFiltro(tipo);
          setCurrentPage(1);
        }}
        onNewReceta={handleOpenNew}
        onManageCategorias={onManageCategorias}
      />

      {/* 2. Recetas Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card shadow-sm">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent mb-3" />
          <p className="text-xs font-semibold text-muted-foreground">
            {t("views.loading_recipes")}
          </p>
        </div>
      ) : effectiveRecetas.length === 0 ? (
        <div
          data-testid="recetas-empty-state"
          className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card shadow-sm"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500 mb-3">
            <Inbox className="h-7 w-7" />
          </div>
          <h4 className="text-sm font-bold text-foreground mb-1">
            {t("views.empty_recipes_title")}
          </h4>
          <p className="text-xs text-muted-foreground max-w-sm mb-4">
            {filter.search || filter.categoria_id || filter.tipo !== "todas"
              ? t("views.empty_recipes_filtered_desc")
              : t("views.empty_recipes_default_desc")}
          </p>
          {(filter.search || filter.categoria_id || filter.tipo !== "todas") && (
            <button
              type="button"
              onClick={() => {
                setLocalRecetasOverride(null);
                setSearchFiltro("");
                setCategoriaFiltro(null);
                setTipoFiltro("todas");
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
          {paginatedRecetas.map((r) => (
            <RecetaMobileCard
              key={r.id}
              receta={r}
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
          <RecetasTable
            recetas={paginatedRecetas}
            onView={handleOpenView}
            onEdit={handleOpenEdit}
            onDuplicate={handleDuplicate}
            onDelete={handleDelete}
          />
        </div>
      )}

      {/* 3. Pagination */}
      {effectiveRecetas.length > 0 && (
        <TablePagination
          currentPage={currentPage}
          totalItems={effectiveRecetas.length}
          pageSize={pageSize}
          pageSizeOptions={[10, 25, 50, 100]}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
          itemLabel={t("views.recipes_pagination_label")}
        />
      )}

      {/* 4. Modales Operativos de Recetas (Fase 5) */}
      <RecetaDialog
        open={isRecetaDialogOpen}
        onClose={() => setIsRecetaDialogOpen(false)}
        receta={editingReceta}
        isDuplicate={isDuplicateMode}
        categorias={categorias}
        productos={productos}
        recetasCatalogo={recetas}
        gruposBiblioteca={gruposOpciones}
        onSave={handleSaveReceta}
      />

      <RecetaDetalleModal
        open={Boolean(viewingReceta)}
        onClose={() => setViewingReceta(null)}
        receta={viewingReceta}
        gruposBiblioteca={gruposOpciones}
        onEdit={(rec) => {
          setViewingReceta(null);
          handleOpenEdit(rec);
        }}
      />
    </div>
  );
}

export default RecetasView;
