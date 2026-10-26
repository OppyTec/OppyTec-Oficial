// oppytec-frontend/src/features/consumo/RegistroConsumoPage.tsx
/**
 * Vista 1: Registro de Consumo (/registro-de-consumo y /consumo)
 * Cumple estrictamente con PLAN_MAESTRO_CONSUMO.md Fases 4 y 5.
 * - SectionHeader centrado (#eab308, UtensilsCrossed).
 * - Toolbar unificado (AreaSelector, BodegaSelector, Switcher, Categorías, Merma, Plantillas, Historial).
 * - Catálogo reactivo con TablePagination y grilla dinámica (5 a 10 cols).
 * - Modales operativos: ConsumoCart, BotonesFlotantes, ConsumoOptionsDialog,
 *   ConsumoTemplateModal, ContingencyModal, LocateStockDialog, ConsumoLog y ConsumoEditDialog.
 */

import { useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  UtensilsCrossed,
  Package,
  CookingPot,
  Layers,
  Tags,
  AlertTriangle,
  History,
  Bookmark,
  ChevronDown,
  ShoppingCart,
} from "lucide-react";
import { usePersistentSearch } from "@/shared/hooks";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { BodegaSelector } from "@/shared/components/layout/BodegaSelector";
import { cn } from "@/shared/lib/utils";
import {
  ConsumoCatalog,
  ConsumoCart,
  ConsumoOptionsDialog,
  ConsumoTemplateModal,
  ContingencyModal,
  LocateStockDialog,
  ConsumoLog,
  ConsumoEditDialog,
} from "./components";
import { useConsumo } from "./hooks/useConsumo";
import type {
  ConsumoCatalogMode,
  ProductoConsumo,
  RecetaConsumo,
  ComboConsumo,
  ConsumptionRecord,
  OptionSelection,
} from "./types";

export function RegistroConsumoPage() {
  const { t } = useTranslation("operations");
  const [bodegaId, setBodegaId] = useState<string>("all");
  const [areaId, setAreaId] = useState<string | null>(null);

  // Hook reactivo central de consumo
  const {
    productos,
    filteredProducts,
    categorias,
    recetas,
    allRecetas,
    combos,
    templates,
    cart,
    loading,
    isSaving,
    addToCart,
    removeFromCart,
    updateQuantity,
    updateCartItemLot,
    updateIngredientLotOverride,
    clearCart,
    getStock,
    getAlertStatus,
    getRecipeAvailability,
    checkContingency,
    registerConsumption,
    saveTemplate,
    deleteTemplate,
    consumptionLog,
    lotsByProduct,
    refetchHistory,
    updateConsumption,
    deleteConsumption,
    colsCount,
    logDate,
    setLogDate,
    logEndDate,
    setLogEndDate,
    isRangeMode,
    setIsRangeMode,
  } = useConsumo({
    bodegaId,
    areaId,
  });

  const [busqueda, setBusqueda] = usePersistentSearch("consumo");
  const [viewMode, setViewMode] = useState<ConsumoCatalogMode>("productos");
  const [showCategories, setShowCategories] = useState<boolean>(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  // Estados de Modales de Fase 5
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState<boolean>(false);
  const [showLogModal, setShowLogModal] = useState<boolean>(false);
  const [showMermaNotice, setShowMermaNotice] = useState<boolean>(false);

  // Estados de Contingencia y Localización
  const [isContingencyOpen, setIsContingencyOpen] = useState<boolean>(false);
  const [contingencyData, setContingencyData] = useState<ReturnType<
    typeof checkContingency
  > | null>(null);
  const [pendingItemToAdd, setPendingItemToAdd] = useState<{
    item: ProductoConsumo | RecetaConsumo | ComboConsumo;
    type: "producto" | "receta" | "combo";
    bodega: string;
  } | null>(null);
  const [isLocateStockOpen, setIsLocateStockOpen] = useState<boolean>(false);

  // Estados de Opciones y Personalización
  const [isOptionsOpen, setIsOptionsOpen] = useState<boolean>(false);
  const [activeOptionItem, setActiveOptionItem] = useState<{
    item: RecetaConsumo | ComboConsumo;
    type: "receta" | "combo";
  } | null>(null);

  // Estados de Edición de Consumo en Historial
  const [isEditOpen, setIsEditOpen] = useState<boolean>(false);
  const [editingRecord, setEditingRecord] = useState<ConsumptionRecord | null>(null);

  // Filtrado según plantilla de consumo seleccionada
  const activeTemplate = useMemo(() => {
    if (!selectedTemplateId || selectedTemplateId === "none") return null;
    return templates.find((t) => t.id === selectedTemplateId) || null;
  }, [selectedTemplateId, templates]);

  const activeProducts = useMemo(() => {
    if (
      !activeTemplate ||
      !activeTemplate.productIds ||
      activeTemplate.productIds.length === 0
    ) {
      return filteredProducts;
    }
    const idSet = new Set(activeTemplate.productIds);
    const subset = filteredProducts.filter((p) => idSet.has(p.id));

    if (activeTemplate.customProductOrder && activeTemplate.customProductOrder.length > 0) {
      const orderMap = new Map(
        activeTemplate.customProductOrder.map((id, index) => [id, index])
      );
      subset.sort((a, b) => {
        const idxA = orderMap.has(a.id) ? orderMap.get(a.id)! : 999;
        const idxB = orderMap.has(b.id) ? orderMap.get(b.id)! : 999;
        return idxA - idxB;
      });
    }
    return subset;
  }, [filteredProducts, activeTemplate]);

  // Manejo de agregar al carrito con verificación de opciones y contingencias
  const handleAddToCart = useCallback(
    (
      item: ProductoConsumo | RecetaConsumo | ComboConsumo,
      type: "producto" | "receta" | "combo"
    ) => {
      const targetBodega = bodegaId === "all" ? "1" : bodegaId;

      // 1. Si es receta o combo con opciones requeridas
      const hasOptionGroups =
        (type === "receta" &&
          (item as RecetaConsumo).ingredientes?.some((i) => !!i.grupo_opciones_id)) ||
        (type === "combo" &&
          (item as ComboConsumo).items?.some((i) => !!i.grupo_opciones_id));

      if (hasOptionGroups) {
        setActiveOptionItem({
          item: item as RecetaConsumo | ComboConsumo,
          type: type as "receta" | "combo",
        });
        setIsOptionsOpen(true);
        return;
      }

      // 2. Verificación de contingencias de lotes vencidos y stock insuficiente
      if (type === "producto") {
        const contingency = checkContingency(item as ProductoConsumo, 1);
        if (contingency.isContingency) {
          setContingencyData(contingency);
          setPendingItemToAdd({ item, type, bodega: targetBodega });
          setIsContingencyOpen(true);
          return;
        }
      }

      // 3. Inserción normal en carrito
      addToCart(item, type, targetBodega);
    },
    [bodegaId, addToCart, checkContingency]
  );

  // Confirmación de opciones seleccionadas
  const handleConfirmOptions = (selections: OptionSelection[]) => {
    if (!activeOptionItem) return;
    const targetBodega = bodegaId === "all" ? "1" : bodegaId;
    addToCart(activeOptionItem.item, activeOptionItem.type, targetBodega, selections);
    setActiveOptionItem(null);
  };

  // Forzar consumo desde modal de contingencia
  const handleForceConsume = () => {
    if (pendingItemToAdd) {
      addToCart(
        pendingItemToAdd.item,
        pendingItemToAdd.type,
        pendingItemToAdd.bodega
      );
      setPendingItemToAdd(null);
    }
  };

  // Total de unidades en carrito
  const totalCartUnits = useMemo(() => {
    return cart.reduce((acc, curr) => acc + (curr.quantity || 0), 0);
  }, [cart]);

  // Lista de productos faltantes para el localizador
  const missingProductIds = useMemo(() => {
    if (!contingencyData || !contingencyData.productName) return [];
    return [contingencyData.productName];
  }, [contingencyData]);

  return (
    <div
      className="relative min-h-screen px-2 md:px-6 py-4 space-y-6 pb-24"
      data-testid="registro-consumo-page"
    >
      {/* ─── 1. CABECERA CANÓNICA CENTRADA (#eab308) ─── */}
      <SectionHeader
        title={t("consumption.registro.title", { defaultValue: "Registro de Consumo" })}
        subtitle={t("consumption.registro.subtitle", {
          defaultValue: "Registra salidas de productos, consumo de personal y mermas en tiempo real",
        })}
        icon={UtensilsCrossed}
        color="#eab308"
        center={true}
      />

      {/* ─── 2. TOOLBAR UNIFICADO DESKTOP & MOBILE ─── */}
      <div
        className="bg-card backdrop-blur-md p-4 rounded-3xl border border-border shadow-xl space-y-4"
        data-testid="consumo-unified-toolbar"
      >
        <div className="bg-muted/40 p-3 rounded-2xl border border-border flex flex-col lg:flex-row items-center justify-between gap-4 w-full">
          {/* Left Column: Selectores de Área y Bodega */}
          <div
            className="flex flex-wrap items-center justify-center lg:justify-start gap-3 w-full lg:w-auto shrink-0"
            data-testid="toolbar-left-selectors"
          >
            <AreaSelector
              className="w-auto shrink-0"
              buttonClassName="h-10 rounded-xl bg-background border-border shadow-sm text-xs font-bold min-w-[150px]"
              selectedAreaId={areaId || "all"}
              onSelectArea={(id: string) => setAreaId(id === "all" ? null : id)}
            />
            <BodegaSelector
              className="w-auto min-w-[170px] shrink-0 h-10 rounded-xl bg-background border-border shadow-sm text-xs font-bold"
              activeWarehouseId={bodegaId}
              onSelectWarehouse={setBodegaId}
              allowAll={true}
            />
          </div>

          {/* Center Column: Switcher de Vista, Toggle Categorías y Merma */}
          <div
            className="flex flex-wrap items-center justify-center gap-2.5 shrink-0"
            data-testid="toolbar-center-actions"
          >
            {/* Switcher de Vista (Productos / Recetas / Combos) */}
            <div className="relative inline-block" data-testid="viewmode-switcher">
              <div className="flex items-center gap-1 p-1 bg-background/80 rounded-2xl border border-border">
                <button
                  type="button"
                  data-testid="viewmode-productos-btn"
                  onClick={() => setViewMode("productos")}
                  className={cn(
                    "flex items-center gap-1.5 h-9 px-3.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer",
                    viewMode === "productos"
                      ? "bg-yellow-500 text-black shadow-md shadow-yellow-500/25 scale-102"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Package className="h-4 w-4 shrink-0" />
                  <span>{t("consumption.registro.modes.productos", { defaultValue: "Productos" })}</span>
                </button>

                <button
                  type="button"
                  data-testid="viewmode-recetas-btn"
                  onClick={() => setViewMode("recetas")}
                  className={cn(
                    "flex items-center gap-1.5 h-9 px-3.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer",
                    viewMode === "recetas"
                      ? "bg-purple-600 text-white shadow-md shadow-purple-600/30 scale-102"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <CookingPot className="h-4 w-4 shrink-0" />
                  <span>{t("consumption.registro.modes.recetas", { defaultValue: "Recetas" })}</span>
                </button>

                <button
                  type="button"
                  data-testid="viewmode-combos-btn"
                  onClick={() => setViewMode("combos")}
                  className={cn(
                    "flex items-center gap-1.5 h-9 px-3.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer",
                    viewMode === "combos"
                      ? "bg-[#1c4c96] text-white shadow-md shadow-[#1c4c96]/30 scale-102"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Layers className="h-4 w-4 shrink-0" />
                  <span>{t("consumption.registro.modes.combos", { defaultValue: "Combos" })}</span>
                </button>
              </div>
            </div>

            {/* Toggle Categorías */}
            <button
              type="button"
              data-testid="toggle-categories-btn"
              onClick={() => setShowCategories(!showCategories)}
              className={cn(
                "flex items-center gap-1.5 h-10 px-4 rounded-xl border text-xs font-black uppercase tracking-wider transition-all cursor-pointer select-none",
                showCategories
                  ? "bg-secondary text-foreground border-border shadow-sm"
                  : "bg-background text-muted-foreground border-border hover:text-foreground"
              )}
            >
              <Tags
                className={cn("h-4 w-4 shrink-0", showCategories && "text-primary")}
              />
              <span className="hidden sm:inline">{t("consumption.registro.toolbar.categories", { defaultValue: "Categorías" })}</span>
            </button>

            {/* Botón Destructivo Merma */}
            <button
              type="button"
              data-testid="merma-trigger-btn"
              onClick={() => setShowMermaNotice(true)}
              className="flex items-center gap-1.5 h-10 px-4 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground text-xs font-black uppercase tracking-wider transition-all shadow-sm active:scale-95 cursor-pointer"
              title="Registrar Merma Operativa"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{t("consumption.registro.toolbar.merma", { defaultValue: "Merma" })}</span>
            </button>
          </div>

          {/* Right Column: Plantillas e Historial */}
          <div
            className="flex items-center justify-center lg:justify-end gap-2.5 w-full lg:w-auto shrink-0"
            data-testid="toolbar-right-actions"
          >
            {/* Gestor de Plantillas */}
            <div className="relative inline-block" data-testid="templates-selector-wrapper">
              <select
                data-testid="templates-select"
                value={selectedTemplateId || "none"}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "__configure__") {
                    setIsTemplateModalOpen(true);
                  } else if (val === "none") {
                    setSelectedTemplateId(null);
                  } else {
                    setSelectedTemplateId(val);
                  }
                }}
                className="h-10 min-h-[40px] pl-8 pr-8 rounded-xl border border-border bg-background text-xs font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer appearance-none"
              >
                <option value="none">{t("consumption.registro.toolbar.templates", { defaultValue: "Plantillas" })}: {t("consumption.registro.toolbar.all_templates", { defaultValue: "Ver Todo" })}</option>
                <option value="__configure__">{t("consumption.registro.toolbar.create_template", { defaultValue: "+ Crear / Configurar..." })}</option>
                {templates.filter((t) => t.isPublic).length > 0 && (
                  <optgroup label={`🌐 ${t("consumption.registro.toolbar.templates", { defaultValue: "Plantillas" })} ${t("consumption.registro.toolbar.public_badge", { defaultValue: "Públicas" })}`}>
                    {templates
                      .filter((t) => t.isPublic)
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                  </optgroup>
                )}
                {templates.filter((t) => !t.isPublic).length > 0 && (
                  <optgroup label={`⭐ ${t("consumption.registro.toolbar.templates", { defaultValue: "Plantillas" })} ${t("consumption.registro.toolbar.private_badge", { defaultValue: "Privadas" })}`}>
                    {templates
                      .filter((t) => !t.isPublic)
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                  </optgroup>
                )}
              </select>
              <Bookmark className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-primary pointer-events-none" />
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>

            {/* Botón Historial de Consumo (Cian #06b6d4) */}
            <button
              type="button"
              data-testid="history-trigger-btn"
              onClick={() => setShowLogModal(true)}
              className="flex items-center justify-center h-10 w-10 min-w-[40px] rounded-xl bg-[#06b6d4]/15 hover:bg-[#06b6d4]/25 text-[#06b6d4] border border-[#06b6d4]/30 transition-all cursor-pointer shadow-sm active:scale-95"
              title="Historial de Movimientos de Consumo"
            >
              <History className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ─── 3. CATÁLOGO CON TablePagination INTEGRADO ─── */}
      <ConsumoCatalog
        loading={loading}
        busqueda={busqueda}
        onBusquedaChange={setBusqueda}
        productos={activeProducts}
        recetas={recetas}
        combos={combos}
        categorias={categorias}
        onAdd={handleAddToCart}
        getStock={getStock}
        getAlertStatus={getAlertStatus}
        getRecipeAvailability={getRecipeAvailability}
        viewMode={viewMode}
        showCategories={showCategories}
        colsCount={colsCount}
      />

      {/* ─── 4. INDICADOR FLOTANTE DE CARRITO Y ACCESOS RÁPIDOS (Fase 5) ─── */}
      {totalCartUnits > 0 && (
        <div
          data-testid="floating-cart-indicator"
          onClick={() => setIsCartOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-3 px-5 py-3 rounded-2xl bg-yellow-500 text-black shadow-2xl shadow-yellow-500/30 border border-yellow-400 animate-in fade-in slide-in-from-bottom-3 duration-300 select-none cursor-pointer hover:scale-105 active:scale-95 transition-all"
        >
          <div className="relative">
            <ShoppingCart className="h-6 w-6" />
            <span
              data-testid="floating-cart-badge"
              className="absolute -top-2.5 -right-2.5 flex h-5 min-w-[20px] px-1 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-xs font-black shadow"
            >
              {totalCartUnits}
            </span>
          </div>
          <div className="flex flex-col text-left">
            <span className="text-xs font-black uppercase tracking-wider">
              Carrito Activo
            </span>
            <span className="text-[10px] font-bold opacity-90">
              {cart.length} {cart.length === 1 ? "ítem" : "ítems"} seleccionados
            </span>
          </div>
        </div>
      )}

      {/* ─── 5. MODAL DE CARRITO LATERAL (ConsumoCart) ─── */}
      <ConsumoCart
        open={isCartOpen}
        onOpenChange={setIsCartOpen}
        cart={cart}
        allRecetas={allRecetas}
        combos={combos}
        productos={productos}
        saving={isSaving}
        lotsByProduct={lotsByProduct}
        onUpdateQty={updateQuantity}
        onRemove={removeFromCart}
        onClearCart={clearCart}
        onSubmit={async () => {
          await registerConsumption({
            bodega_id: bodegaId === "all" ? 1 : Number(bodegaId) || 1,
            items: cart.map((i) => ({
              tipo_item: i.type,
              item_id: i.id,
              cantidad: i.quantity,
              unidad_medida: i.unit,
              lote_codigo: i.selectedLot,
              opciones_seleccionadas: i.optionSelections,
            })),
          });
          setIsCartOpen(false);
        }}
        getStock={getStock}
        onUpdateLot={updateCartItemLot}
        onUpdateIngredientLot={updateIngredientLotOverride}
      />

      {/* ─── 6. MODAL DE OPCIONES Y PERSONALIZACIÓN ─── */}
      <ConsumoOptionsDialog
        open={isOptionsOpen}
        onOpenChange={setIsOptionsOpen}
        item={activeOptionItem?.item || null}
        type={activeOptionItem?.type || "receta"}
        productos={productos}
        recetas={recetas}
        getStock={getStock}
        onConfirm={handleConfirmOptions}
      />

      {/* ─── 7. MODAL DE GESTIÓN DE PLANTILLAS ─── */}
      <ConsumoTemplateModal
        open={isTemplateModalOpen}
        onOpenChange={setIsTemplateModalOpen}
        initialTemplate={activeTemplate}
        productos={productos}
        categorias={categorias}
        onSaveTemplate={async (t) => {
          await saveTemplate(t);
        }}
        onDeleteTemplate={async (id) => {
          await deleteTemplate(id);
        }}
      />

      {/* ─── 8. MODAL DE CONTINGENCIAS DE STOCK / LOTES VENCIDOS ─── */}
      <ContingencyModal
        open={isContingencyOpen}
        onOpenChange={setIsContingencyOpen}
        contingencyResult={contingencyData}
        onForceConsume={handleForceConsume}
        onTriggerMerma={() => setShowMermaNotice(true)}
        onLocateStock={() => setIsLocateStockOpen(true)}
      />

      {/* ─── 9. LOCALIZADOR DE STOCK EN OTRAS BODEGAS ─── */}
      <LocateStockDialog
        open={isLocateStockOpen}
        onOpenChange={setIsLocateStockOpen}
        missingProducts={missingProductIds}
        productos={productos}
        currentBodegaId={bodegaId === "all" ? "1" : bodegaId}
      />

      {/* ─── 10. HISTORIAL DE CONSUMO (ConsumoLog) ─── */}
      {showLogModal && (
        <div data-testid="history-notice-modal">
          <ConsumoLog
            open={showLogModal}
            onOpenChange={setShowLogModal}
            records={consumptionLog}
            onRefresh={refetchHistory}
            onEdit={(record) => {
              setEditingRecord(record);
              setIsEditOpen(true);
            }}
            onDelete={(record) => {
              void deleteConsumption({ id: record.id });
            }}
            logDate={logDate}
            setLogDate={setLogDate}
            logEndDate={logEndDate}
            setLogEndDate={setLogEndDate}
            isRangeMode={isRangeMode}
            setIsRangeMode={setIsRangeMode}
          />
        </div>
      )}

      {/* ─── 11. MODAL DE EDICIÓN DE CONSUMO ─── */}
      <ConsumoEditDialog
        open={isEditOpen}
        onOpenChange={setIsEditOpen}
        record={editingRecord}
        onSave={async (id, data) => {
          await updateConsumption({
            id,
            notas: data.notas || data.motivo_merma || "",
          });
        }}
      />

      {/* ─── 12. DIÁLOGO DE MERMA OPERATIVA ─── */}
      {showMermaNotice && (
        <div
          data-testid="merma-notice-modal"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in"
        >
          <div className="bg-card border border-destructive/40 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-destructive">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-lg font-black uppercase tracking-wider">
                Mermas Operativas
              </h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              El asistente avanzado de registro de mermas directas e incidentes de cocina
              permite seleccionar insumos vencidos o deteriorados y registrarlos con
              trazabilidad en Kardex.
            </p>
            <div className="flex justify-end pt-2 gap-2">
              <button
                type="button"
                onClick={() => setShowMermaNotice(false)}
                className="px-4 py-2 rounded-xl bg-destructive text-destructive-foreground text-xs font-bold uppercase cursor-pointer"
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RegistroConsumoPage;
