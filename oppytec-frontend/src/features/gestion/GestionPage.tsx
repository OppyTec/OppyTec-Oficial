import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { Package, ChefHat, Boxes, TrendingDown, Search, X, Inbox } from "lucide-react";
import { useTranslation } from "react-i18next";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { ComprasView, GestionarMermaView } from "@/features/procurement";
import { GestionTabNav, type GestionTabKey } from "./components/GestionTabNav";
import { RecetasView } from "./components/recetas/RecetasView";
import { CombosView } from "./components/combos/CombosView";
import { DraftRecoveryBanner, type DraftProductData } from "./components/DraftRecoveryBanner";
import { ToolbarGestion, type TablePreset } from "./components/ToolbarGestion";
import { CategoriaSeccion } from "./components/CategoriaSeccion";
import { TablePagination } from "./components/TablePagination";
import { ProductTable } from "./components/ProductTable";
import { ProductMobileCard, type BodegaInfo } from "./components/ProductMobileCard";
import { TableConfigModal } from "./components/TableConfigModal";
import { AdministradorCategoriasDialog } from "./components/AdministradorCategoriasDialog";
import { CatalogosManagerDialog } from "./components/CatalogosManagerDialog";
import { TransferDialog } from "./components/TransferDialog";
import { ProductoWizardDialog } from "./components/ProductoWizardDialog";
import { ExcelImportModal } from "./components/ExcelImportModal";
import { FacturaImportModal } from "./components/FacturaImportModal";
import { useGestion } from "./useGestion";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import {
  type Producto,
  type ColumnKey,
  type ViewMode,
  ALL_COLUMNS,
  DEFAULT_COLUMNS,
  PRODUCT_SORT_OPTIONS,
} from "./types";

export const DEFAULT_BODEGAS: BodegaInfo[] = [
  { id: "bod-central", nombre: "Bodega Principal", color: "#6366F1", icono: "Warehouse" },
  { id: "bod-cocina-central", nombre: "Bodega Cocina Central", color: "#6366F1", icono: "Warehouse" },
  { id: "bod-frio", nombre: "Cámara Fría -18°C", color: "#0284C7", icono: "Snowflake" },
  { id: "bod-camara-fria", nombre: "Cámara Fría -18°C", color: "#0284C7", icono: "Snowflake" },
  { id: "bod-bar", nombre: "Barra & Cava", color: "#8B5CF6", icono: "Wine" },
  { id: "bod-barra-cava", nombre: "Barra & Cava", color: "#8B5CF6", icono: "Wine" },
  { id: "bod-cocina", nombre: "Cocina Caliente", color: "#F97316", icono: "Flame" },
];

export const DEFAULT_BODEGA_MAP: Record<string, BodegaInfo> = Object.fromEntries(
  DEFAULT_BODEGAS.map((b) => [b.id, b])
);

function useSafeSearchParams(): [URLSearchParams, (params: Record<string, string>, opts?: { replace?: boolean }) => void] {
  try {
    const [searchParams, setSearchParams] = useSearchParams();
    return [searchParams, setSearchParams];
  } catch {
    const sp = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : new URLSearchParams();
    return [sp, () => {}];
  }
}

export function GestionPage() {
  const { t } = useTranslation("recipes");
  const isMobile = useIsMobile();
  const [searchParams, setSearchParams] = useSafeSearchParams();
  const rawTab = searchParams.get("tab")?.toLowerCase();

  // Redirect/normalize orphan "grupos-opciones"
  useEffect(() => {
    if (rawTab === "grupos-opciones") {
      setSearchParams({ tab: "productos" }, { replace: true });
    }
  }, [rawTab, setSearchParams]);

  const isPedidosOrCompras = rawTab === "pedidos" || rawTab === "compras";

  const activeTab: GestionTabKey =
    rawTab === "recetas"
      ? "recetas"
      : rawTab === "combos"
      ? "combos"
      : rawTab === "mermas"
      ? "mermas"
      : "productos";

  const handleSelectTab = useCallback(
    (tab: GestionTabKey) => {
      setSearchParams({ tab });
    },
    [setSearchParams]
  );

  const headerConfig = useMemo(() => {
    if (isPedidosOrCompras) {
      return {
        title: t("header.pedidos_title"),
        subtitle: t("header.pedidos_subtitle"),
        icon: Package,
        color: "#10b981",
      };
    }
    switch (activeTab) {
      case "recetas":
        return {
          title: t("header.recetas_title"),
          subtitle: t("header.recetas_subtitle"),
          icon: ChefHat,
          color: "#f59e0b",
        };
      case "combos":
        return {
          title: t("header.combos_title"),
          subtitle: t("header.combos_subtitle"),
          icon: Boxes,
          color: "#ec4899",
        };
      case "mermas":
        return {
          title: t("header.mermas_title"),
          subtitle: t("header.mermas_subtitle"),
          icon: TrendingDown,
          color: "#ef4444",
        };
      case "productos":
      default:
        return {
          title: t("header.productos_title"),
          subtitle: t("header.productos_subtitle"),
          icon: Package,
          color: "#eab308",
        };
    }
  }, [activeTab, isPedidosOrCompras, t]);

  const {
    categorias,
    productos: hookProductos,
    loading,
    marcas,
    tiposEnvase,
    createCategory,
    updateCategory,
    deleteCategory,
    createBrand,
    updateBrand,
    deleteBrand,
    createTipoEnvase,
    updateTipoEnvase,
    deleteTipoEnvase,
    createProduct,
    updateProduct,
  } = useGestion();
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());

  const productos = useMemo(() => {
    if (deletedIds.size === 0) return hookProductos;
    return hookProductos.filter((p) => !deletedIds.has(p.id));
  }, [hookProductos, deletedIds]);

  // Search state with debounce
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery.trim().toLowerCase());
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Scope filter state
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>("bod-cocina-central");

  // Category carrousel state
  const [showCategories, setShowCategories] = useState<boolean>(true);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<Set<string>>(new Set());

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Active columns and view mode
  const [activeColumns, setActiveColumns] = useState<ColumnKey[]>(DEFAULT_COLUMNS);
  const [viewMode, setViewMode] = useState<ViewMode>("agrupado");

  const handleSaveTableConfig = useCallback(
    (params: {
      orderedColumns: ColumnKey[];
      sortConfig: { key: "nombre" | "stock" | "precio" | "vigencia"; direction: "asc" | "desc" };
      viewMode: ViewMode;
      presetId?: string;
    }) => {
      setActiveColumns(params.orderedColumns);
      setViewMode(params.viewMode);
      if (params.presetId) {
        setActivePresetId(params.presetId);
      }
    },
    []
  );

  // Mobile expanded products accordion state
  const [expandedMobileProductIds, setExpandedMobileProductIds] = useState<Set<string>>(new Set());

  const toggleMobileExpand = useCallback((id: string) => {
    setExpandedMobileProductIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // Dialogs state
  const [isTableConfigOpen, setIsTableConfigOpen] = useState(false);
  const [isAdminCategoriasOpen, setIsAdminCategoriasOpen] = useState(false);
  const [isCatalogosOpen, setIsCatalogosOpen] = useState(false);
  const [isTransferOpen, setIsTransferOpen] = useState(false);
  const [isNewProductOpen, setIsNewProductOpen] = useState(false);
  const [isExcelImportOpen, setIsExcelImportOpen] = useState(false);
  const [isFacturaImportOpen, setIsFacturaImportOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Producto | null>(null);

  // Draft recovery state
  const [recoveredDraft, setRecoveredDraft] = useState<DraftProductData | null>(null);

  // Active table preset
  const [activePresetId, setActivePresetId] = useState<string>("preset-general");

  // Category toggle handler
  const handleToggleCategory = useCallback((id: string) => {
    setSelectedCategoryIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    setCurrentPage(1);
  }, []);

  // Delete product handler
  const handleDeleteProduct = useCallback((product: Producto) => {
    setDeletedIds((prev) => {
      const next = new Set(prev);
      next.add(product.id);
      return next;
    });
  }, []);

  // Filtered products calculation
  const filteredProducts = useMemo(() => {
    let result: Producto[] = [...productos];

    // Category filter
    if (selectedCategoryIds.size > 0) {
      result = result.filter(
        (p) => p.categoria_id && selectedCategoryIds.has(p.categoria_id)
      );
    }

    // Search query filter
    if (debouncedQuery) {
      result = result.filter((p) => {
        const nameMatch = p.nombre.toLowerCase().includes(debouncedQuery);
        const fullNameMatch = p.nombre_completo?.toLowerCase().includes(debouncedQuery);
        const skuMatch = p.sku?.toLowerCase().includes(debouncedQuery);
        const barcodeMatch = p.codigo_barra?.includes(debouncedQuery);
        const brandMatch = p.marca?.toLowerCase().includes(debouncedQuery);
        return Boolean(nameMatch || fullNameMatch || skuMatch || barcodeMatch || brandMatch);
      });
    }

    return result;
  }, [productos, selectedCategoryIds, debouncedQuery]);

  // Paginated items
  const paginatedProducts = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredProducts.slice(startIndex, startIndex + pageSize);
  }, [filteredProducts, currentPage, pageSize]);

  // Draft handlers
  const handleRecoverDraft = useCallback((draft: DraftProductData) => {
    setEditingProduct(null);
    setRecoveredDraft(draft);
    setIsNewProductOpen(true);
  }, []);

  // Apply table preset handler
  const handleApplyTablePreset = useCallback((preset: TablePreset) => {
    setActivePresetId(preset.id);
    if (preset.columns && preset.columns.length > 0) {
      const validCols = preset.columns.filter((c): c is ColumnKey =>
        ALL_COLUMNS.some((col) => col.key === c)
      );
      if (validCols.length > 0) {
        setActiveColumns(validCols);
      }
    }
  }, []);

  const activeColsSet = useMemo(() => new Set(activeColumns), [activeColumns]);

  return (
    <div
      data-testid="gestion-page"
      className="container mx-auto px-2 sm:px-4 py-4 md:py-6 max-w-7xl space-y-6 animate-fade-in"
    >
      {/* 1. Header Section */}
      <SectionHeader
        title={headerConfig.title}
        subtitle={headerConfig.subtitle}
        icon={headerConfig.icon}
        color={headerConfig.color}
      />

      {/* 2. Navigation Tabs (Insumos & Productos, Recetas & Escandallos, Combos & Promociones, Mermas) */}
      {!isPedidosOrCompras && (
        <GestionTabNav
          activeTab={activeTab}
          onSelectTab={handleSelectTab}
        />
      )}

      {/* 3. Tab Specific Views */}
      {isPedidosOrCompras ? (
        <div data-testid="gestion-page-pedidos" className="space-y-6">
          <ComprasView />
        </div>
      ) : activeTab === "recetas" ? (
        <RecetasView
          productos={productos}
          onManageCategorias={() => setIsAdminCategoriasOpen(true)}
        />
      ) : activeTab === "combos" ? (
        <CombosView
          productos={productos}
          onManageCategorias={() => setIsAdminCategoriasOpen(true)}
        />
      ) : activeTab === "mermas" ? (
        <GestionarMermaView hideHeader={true} />
      ) : (
        <>
          {/* Draft Recovery Banner */}
          <DraftRecoveryBanner
            onRecoverDraft={handleRecoverDraft}
            onDismiss={() => setRecoveredDraft(null)}
          />

          {/* Unified Toolbar */}
          <ToolbarGestion
            selectedAreaId={selectedAreaId}
            onSelectArea={setSelectedAreaId}
            activeWarehouseId={selectedWarehouseId}
            onSelectWarehouse={setSelectedWarehouseId}
            activePresetId={activePresetId}
            onApplyTablePreset={handleApplyTablePreset}
            onOpenTableConfig={() => setIsTableConfigOpen(true)}
            showCategories={showCategories}
            onToggleShowCategories={() => setShowCategories((prev) => !prev)}
            onOpenAdminCategorias={() => setIsAdminCategoriasOpen(true)}
            onOpenCatalogos={() => setIsCatalogosOpen(true)}
            onOpenTransfer={() => setIsTransferOpen(true)}
            onOpenExcelImport={() => setIsExcelImportOpen(true)}
            onOpenFacturaImport={() => setIsFacturaImportOpen(true)}
            onNewProduct={() => {
              setEditingProduct(null);
              setRecoveredDraft(null);
              setIsNewProductOpen(true);
            }}
          />

          {/* Persistent Search Bar */}
          <div className="relative mb-4 w-full">
            <div className="relative flex items-center">
              <Search className="absolute left-3.5 h-4 w-4 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Buscar por nombre, SKU, código de barra o marca..."
                data-testid="gestion-search-input"
                className="w-full h-11 min-h-[44px] pl-10 pr-10 rounded-2xl border border-input bg-card text-foreground placeholder:text-muted-foreground/70 text-xs sm:text-sm font-medium focus:outline-none focus:border-primary shadow-sm transition-all"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("");
                    setCurrentPage(1);
                  }}
                  data-testid="gestion-clear-search"
                  aria-label="Limpiar búsqueda"
                  className="absolute right-3 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Categoria Carousel (Toggled by showCategories) */}
          {showCategories && (
            <div className="mb-4">
              <CategoriaSeccion
                categorias={categorias}
                selectedIds={selectedCategoryIds}
                onToggle={handleToggleCategory}
              />
            </div>
          )}

          {/* Products Table / View */}
          <div className="w-full">
            {loading ? (
              <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card shadow-sm">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mb-3" />
                <p className="text-xs font-semibold text-muted-foreground">
                  Cargando catálogo de productos...
                </p>
              </div>
            ) : filteredProducts.length === 0 ? (
              <div
                data-testid="gestion-empty-state"
                className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card shadow-sm"
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/60 text-muted-foreground mb-3">
                  <Inbox className="h-7 w-7" />
                </div>
                <h4 className="text-sm font-bold text-foreground mb-1">
                  No se encontraron productos
                </h4>
                <p className="text-xs text-muted-foreground max-w-sm mb-4">
                  {searchQuery || selectedCategoryIds.size > 0
                    ? "Prueba cambiando los filtros o el término de búsqueda para ver más resultados."
                    : "Aún no tienes productos registrados en este catálogo."}
                </p>
                {(searchQuery || selectedCategoryIds.size > 0) && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery("");
                      setSelectedCategoryIds(new Set());
                      setCurrentPage(1);
                    }}
                    className="inline-flex min-h-[36px] items-center gap-1.5 rounded-xl border border-border bg-secondary px-3 py-1.5 text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer select-none"
                  >
                    Limpiar filtros
                  </button>
                )}
              </div>
            ) : isMobile ? (
              /* Mobile View: ProductMobileCard list adaptativo */
              <div className="flex flex-col gap-2.5 pb-4 md:hidden">
                {paginatedProducts.map((p) => (
                  <ProductMobileCard
                    key={p.id}
                    product={p}
                    bodegas={DEFAULT_BODEGAS}
                    bodegaMap={DEFAULT_BODEGA_MAP}
                    selectedWarehouseId={selectedWarehouseId}
                    visibleCols={activeColsSet}
                    isExpanded={expandedMobileProductIds.has(p.id)}
                    onToggleExpand={() => toggleMobileExpand(p.id)}
                    onEdit={(prod) => {
                      setEditingProduct(prod);
                      setRecoveredDraft(null);
                      setIsNewProductOpen(true);
                    }}
                    onDelete={handleDeleteProduct}
                  />
                ))}
              </div>
            ) : (
              /* Desktop View: ProductTable multidimensional */
              <div className="hidden md:block">
                <ProductTable
                  productos={paginatedProducts}
                  categorias={categorias}
                  bodegas={DEFAULT_BODEGAS}
                  bodegaMap={DEFAULT_BODEGA_MAP}
                  selectedWarehouseId={selectedWarehouseId}
                  activeCols={activeColumns}
                  viewMode={viewMode}
                  onEdit={(p) => {
                    setEditingProduct(p);
                    setRecoveredDraft(null);
                    setIsNewProductOpen(true);
                  }}
                  onDelete={handleDeleteProduct}
                />
              </div>
            )}
          </div>

          {/* Table Pagination */}
          {filteredProducts.length > 0 && (
            <TablePagination
              currentPage={currentPage}
              totalItems={filteredProducts.length}
              pageSize={pageSize}
              pageSizeOptions={[10, 30, 50, 100]}
              onPageChange={setCurrentPage}
              onPageSizeChange={setPageSize}
              itemLabel="productos"
            />
          )}
        </>
      )}

      {/* ==================================================================== */}
      {/* MODALES DE GESTIÓN (FASE 4 - ZERO SCREENS BLANK & MOBILE FIRST)     */}
      {/* ==================================================================== */}

      {/* 1. Table Config Modal */}
      <TableConfigModal
        open={isTableConfigOpen}
        onOpenChange={setIsTableConfigOpen}
        sortConfig={{ key: "nombre", direction: "asc" }}
        onSortChange={() => {}}
        sortOptions={PRODUCT_SORT_OPTIONS}
        columns={ALL_COLUMNS}
        visibleColsOrder={activeColumns}
        viewMode={viewMode}
        onSaveConfig={handleSaveTableConfig}
      />

      {/* 2. Admin Categorías Dialog */}
      <AdministradorCategoriasDialog
        open={isAdminCategoriasOpen}
        onOpenChange={setIsAdminCategoriasOpen}
        categorias={categorias}
        productos={productos}
        onCreateCategory={createCategory}
        onUpdateCategory={updateCategory}
        onDeleteCategory={deleteCategory}
      />

      {/* 3. Catálogos Dialog */}
      <CatalogosManagerDialog
        open={isCatalogosOpen}
        onOpenChange={setIsCatalogosOpen}
        marcas={marcas}
        tiposEnvase={tiposEnvase}
        productos={productos}
        onCreateBrand={createBrand}
        onUpdateBrand={updateBrand}
        onDeleteBrand={deleteBrand}
        onCreateTipoEnvase={createTipoEnvase}
        onUpdateTipoEnvase={updateTipoEnvase}
        onDeleteTipoEnvase={deleteTipoEnvase}
      />

      {/* 4. Transferir Stock Dialog */}
      <TransferDialog
        open={isTransferOpen}
        onOpenChange={setIsTransferOpen}
        productos={productos}
        categorias={categorias}
        onSuccess={() => {}}
      />

      {/* 5. ProductoWizardDialog (Wizard Manual en 4 Pasos con Drafting y Multicanal) */}
      <ProductoWizardDialog
        open={isNewProductOpen}
        onOpenChange={(open) => {
          setIsNewProductOpen(open);
          if (!open) {
            setEditingProduct(null);
            setRecoveredDraft(null);
          }
        }}
        editingProduct={editingProduct}
        initialDraft={recoveredDraft}
        categorias={categorias}
        marcas={marcas}
        tiposEnvase={tiposEnvase}
        bodegas={DEFAULT_BODEGAS}
        onCreateBrand={createBrand}
        onCreateTipoEnvase={createTipoEnvase}
        onSave={async (productData) => {
          if (editingProduct?.id) {
            await updateProduct(editingProduct.id, productData);
          } else {
            await createProduct(productData);
          }
          setIsNewProductOpen(false);
          setEditingProduct(null);
          setRecoveredDraft(null);
        }}
        onOpenExcelImport={() => {
          setIsNewProductOpen(false);
          setIsExcelImportOpen(true);
        }}
        onOpenFacturaImport={() => {
          setIsNewProductOpen(false);
          setIsFacturaImportOpen(true);
        }}
      />

      {/* 6. ExcelImportModal (Ingesta Masiva Inteligente de Excel / CSV IA) */}
      <ExcelImportModal
        open={isExcelImportOpen}
        onOpenChange={setIsExcelImportOpen}
        categorias={categorias}
        marcas={marcas}
        onImportComplete={async (importedProducts) => {
          for (const item of importedProducts) {
            try {
              await createProduct(item as any);
            } catch {
              // handled
            }
          }
        }}
      />

      {/* 7. FacturaImportModal (Ingreso de Facturas PDF / XML DTE IA) */}
      <FacturaImportModal
        open={isFacturaImportOpen}
        onOpenChange={setIsFacturaImportOpen}
        productos={productos}
        onInvoiceConfirmed={async () => {
          // Handled, products will refresh
        }}
      />
    </div>
  );
}

export default GestionPage;
