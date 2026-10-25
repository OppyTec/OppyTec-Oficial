// oppytec-frontend/src/features/inventory/stock/StockRegistroPage.tsx
import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardList,
  Search,
  X,
  Loader2,
} from "lucide-react";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { TablePagination } from "@/shared/components/ui/TablePagination";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { cn } from "@/shared/lib";
import { useStock } from "../hooks/useStock";
import { StockActions, StockTable } from "./components";
import {
  TransferDialog,
  AdjustmentDialog,
  MermaDialog,
  AddingMercaderiaDialog,
  SolicitudesDialog,
} from "./dialogs";
import type { StockItem, StockSortOption } from "../types";

const springTransition = {
  duration: 0.28,
  ease: [0.16, 1, 0.3, 1] as const,
};

export function StockRegistroPage() {
  const { t } = useTranslation("inventory");
  const {
    stockItems,
    filteredStockItems,
    bodegas,
    isStockLoading,
    filter,
    setFilter,
    viewMode,
    setViewMode,
    transferStockBulk,
    registerMovement,
    reportMerma,
  } = useStock();

  // Estados locales para la visualización y paginación
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [showCategories, setShowCategories] = useState<boolean>(true);
  const [sortOption, setSortOption] = useState<StockSortOption>("urgency");
  const [selectedCategoryName, setSelectedCategoryName] = useState<string>("ALL");

  // Estados para diálogos modales especializados
  const [selectedItemForAction, setSelectedItemForAction] = useState<StockItem | null>(null);
  const [isMermaOpen, setIsMermaOpen] = useState(false);
  const [isTransferOpen, setIsTransferOpen] = useState(false);
  const [isAdjustmentOpen, setIsAdjustmentOpen] = useState(false);
  const [isReceiveOpen, setIsReceiveOpen] = useState(false);
  const [isSolicitudesOpen, setIsSolicitudesOpen] = useState(false);

  // Filtrado reactivo en cliente (término de búsqueda + categoría seleccionada + orden)
  const processedProducts = useMemo(() => {
    let result = [...filteredStockItems];

    // Filtro por categoría seleccionada
    if (selectedCategoryName !== "ALL") {
      result = result.filter((it) => it.categoria === selectedCategoryName);
    }

    // Filtro por término de búsqueda si no fue filtrado por hook
    if (filter.search && filter.search.trim() !== "") {
      const q = filter.search.toLowerCase().trim();
      result = result.filter(
        (it) =>
          it.nombre.toLowerCase().includes(q) ||
          it.sku.toLowerCase().includes(q) ||
          it.categoria.toLowerCase().includes(q) ||
          it.bodega_nombre.toLowerCase().includes(q)
      );
    }

    // Ordenamiento
    result.sort((a, b) => {
      if (sortOption === "az") return a.nombre.localeCompare(b.nombre);
      if (sortOption === "za") return b.nombre.localeCompare(a.nombre);
      if (sortOption === "stock_asc") return a.stock_actual - b.stock_actual;
      if (sortOption === "stock_desc") return b.stock_actual - a.stock_actual;

      // Por defecto: 'urgency' (Crítico primero, luego Mínimo, luego Óptimo)
      const severityScore = (item: StockItem) => {
        if (item.semaforo === "CRITICO" || item.stock_actual <= 0) return 3;
        if (item.semaforo === "MINIMO") return 2;
        return 1;
      };
      return severityScore(b) - severityScore(a);
    });

    return result;
  }, [filteredStockItems, selectedCategoryName, filter.search, sortOption]);

  // Paginación sobre los productos procesados
  const totalItems = processedProducts.length;
  const paginatedProducts = useMemo(() => {
    const from = (currentPage - 1) * pageSize;
    return processedProducts.slice(from, from + pageSize);
  }, [processedProducts, currentPage, pageSize]);

  // Lista de categorías únicas para la sección de badges
  const availableCategories = useMemo(() => {
    const set = new Set<string>();
    for (const it of stockItems) {
      if (it.categoria) set.add(it.categoria);
    }
    return Array.from(set);
  }, [stockItems]);

  // Handlers para abrir modales desde filas
  const handleOpenSolicitarItem = (item: StockItem) => {
    setSelectedItemForAction(item);
    setIsSolicitudesOpen(true);
  };

  const handleOpenTransferItem = (item: StockItem) => {
    setSelectedItemForAction(item);
    setIsTransferOpen(true);
  };

  const handleOpenMermaItem = (item: StockItem) => {
    setSelectedItemForAction(item);
    setIsMermaOpen(true);
  };

  return (
    <div
      data-testid="stock-registro-container"
      className="container mx-auto px-2 sm:px-4 py-4 md:py-6 max-w-7xl space-y-6 animate-fade-in"
    >
      {/* 1. Encabezado Centrado con ADN OppyTec Legacy */}
      <SectionHeader
        title={t("stock.title")}
        subtitle={t("stock.subtitle")}
        icon={ClipboardList}
        color="#3b82f6"
        center={true}
      />

      {/* 2. Barra de Acciones Unificada (Toolbar) */}
      <StockActions
        selectedAreaId={String(filter.area_operativa_id ?? "all")}
        onSelectArea={(areaId) =>
          setFilter((prev) => ({
            ...prev,
            area_operativa_id: areaId === "all" ? "all" : Number(areaId) || "all",
          }))
        }
        activeWarehouseId={String(filter.bodega_id ?? "all")}
        onSelectWarehouse={(whId) =>
          setFilter((prev) => ({
            ...prev,
            bodega_id: whId === "all" ? "all" : Number(whId) || "all",
          }))
        }
        onOpenSolicitar={() => {
          setSelectedItemForAction(null);
          setIsSolicitudesOpen(true);
        }}
        onOpenMerma={() => {
          setSelectedItemForAction(stockItems[0] || null);
          setIsMermaOpen(true);
        }}
        onOpenAdjustment={() => {
          setSelectedItemForAction(stockItems[0] || null);
          setIsAdjustmentOpen(true);
        }}
        onOpenReceive={() => setIsReceiveOpen(true)}
        showCategories={showCategories}
        onToggleCategories={() => setShowCategories((prev) => !prev)}
        sortOption={sortOption}
        onSortChange={setSortOption}
        viewMode={viewMode}
        onToggleViewMode={() =>
          setViewMode((prev) => (prev === "agrupado" ? "plano" : "agrupado"))
        }
      />

      {/* 3. Filtro de Categorías y Buscador Interactivo */}
      <div className="flex flex-col space-y-3">
        {/* Badges de Categoría */}
        <AnimatePresence>
          {showCategories && (
            <motion.div
              key="stock-category-badges-container"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={springTransition}
              className="overflow-x-auto pb-1"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  data-testid="category-badge-all"
                  onClick={() => {
                    setSelectedCategoryName("ALL");
                    setCurrentPage(1);
                  }}
                  className={cn(
                    "px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer",
                    selectedCategoryName === "ALL"
                      ? "bg-primary text-primary-foreground shadow-xs shadow-primary/30"
                      : "border border-border bg-card text-muted-foreground hover:text-foreground"
                  )}
                >
                  {t("stock.all_categories")}
                </button>
                {availableCategories.map((catName) => {
                  const isSelected = selectedCategoryName === catName;
                  return (
                    <button
                      key={`cat-pill-${catName}`}
                      type="button"
                      data-testid={`category-badge-${catName}`}
                      onClick={() => {
                        setSelectedCategoryName(isSelected ? "ALL" : catName);
                        setCurrentPage(1);
                      }}
                      className={cn(
                        "px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1.5",
                        isSelected
                          ? "bg-primary text-primary-foreground shadow-xs shadow-primary/30"
                          : "border border-border bg-card text-muted-foreground hover:text-foreground"
                      )}
                    >
                      <CategoryIcon name="Package" className="h-3.5 w-3.5" />
                      <span>{catName}</span>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Buscador Interactivo con Resplandor Azul OppyTec */}
        <div className="relative group w-full">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 p-1 rounded-lg bg-[#3b82f6]/10 text-[#3b82f6]">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            data-testid="stock-search-input"
            placeholder={t("stock.search_placeholder")}
            value={filter.search}
            onChange={(e) => {
              setFilter((prev) => ({ ...prev, search: e.target.value }));
              setCurrentPage(1);
            }}
            className="w-full pl-11 pr-10 h-11 bg-card border border-[#3b82f6]/30 shadow-[0_0_12px_rgba(59,130,246,0.08)] focus:border-[#3b82f6] focus:ring-2 focus:ring-[#3b82f6]/20 rounded-xl text-sm font-medium text-foreground transition-all outline-none"
          />
          {filter.search && (
            <button
              type="button"
              data-testid="stock-search-clear"
              onClick={() => {
                setFilter((prev) => ({ ...prev, search: "" }));
                setCurrentPage(1);
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* 4. Estado de Carga o Tabla Principal */}
      {isStockLoading ? (
        <div
          data-testid="stock-loading-spinner"
          className="flex flex-col items-center justify-center py-24 space-y-3"
        >
          <Loader2 className="h-9 w-9 text-primary animate-spin" />
          <p className="text-xs font-black uppercase tracking-widest text-muted-foreground">
            {t("stock.loading")}
          </p>
        </div>
      ) : (
        <>
          <StockTable
            items={paginatedProducts}
            showCategories={showCategories && selectedCategoryName === "ALL"}
            viewMode={viewMode}
            sortOption={sortOption}
            onSortChange={setSortOption}
            onOpenSolicitar={handleOpenSolicitarItem}
            onOpenTransfer={handleOpenTransferItem}
            onOpenMerma={handleOpenMermaItem}
          />

          {/* 5. Paginador al pie */}
          <TablePagination
            currentPage={currentPage}
            totalItems={totalItems}
            pageSize={pageSize}
            pageSizeOptions={[10, 25, 50, 100]}
            onPageChange={setCurrentPage}
            onPageSizeChange={(newSize) => {
              setPageSize(newSize);
              setCurrentPage(1);
            }}
            itemLabel={t("stock.items_label")}
          />
        </>
      )}

      {/* =========================================================================
          MODALES DE ACCIÓN ESPECIALIZADOS DE STOCK (Fase 5)
          ========================================================================= */}

      {/* Modal 1: Transferencia de Stock Inter-Bodega */}
      <TransferDialog
        open={isTransferOpen}
        onClose={() => {
          setIsTransferOpen(false);
          setSelectedItemForAction(null);
        }}
        stockItems={stockItems}
        bodegas={bodegas}
        initialProduct={selectedItemForAction}
        onTransfer={transferStockBulk}
      />

      {/* Modal 2: Ajuste Directo de Inventario */}
      <AdjustmentDialog
        open={isAdjustmentOpen}
        onClose={() => {
          setIsAdjustmentOpen(false);
          setSelectedItemForAction(null);
        }}
        stockItems={stockItems}
        bodegas={bodegas}
        initialProduct={selectedItemForAction}
        onRegisterMovement={registerMovement}
      />

      {/* Modal 3: Reporte de Merma Operativa */}
      <MermaDialog
        open={isMermaOpen}
        onClose={() => {
          setIsMermaOpen(false);
          setSelectedItemForAction(null);
        }}
        stockItems={stockItems}
        bodegas={bodegas}
        initialProduct={selectedItemForAction}
        onReportMerma={reportMerma}
      />

      {/* Modal 4: Recepción e Ingreso de Mercadería */}
      <AddingMercaderiaDialog
        open={isReceiveOpen}
        onClose={() => setIsReceiveOpen(false)}
        stockItems={stockItems}
        bodegas={bodegas}
        onRegisterMovement={registerMovement}
      />

      {/* Modal 5: Solicitudes de Reposición Interna */}
      <SolicitudesDialog
        open={isSolicitudesOpen}
        onClose={() => {
          setIsSolicitudesOpen(false);
          setSelectedItemForAction(null);
        }}
        stockItems={stockItems}
        bodegas={bodegas}
        initialProduct={selectedItemForAction}
      />
    </div>
  );
}

export default StockRegistroPage;
