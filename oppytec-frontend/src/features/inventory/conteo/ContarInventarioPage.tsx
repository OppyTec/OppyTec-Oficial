// oppytec-frontend/src/features/inventory/conteo/ContarInventarioPage.tsx
import { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ClipboardCheck,
  Play,
  CheckCircle,
  CheckCircle2,
  Search,
  Barcode,
  RotateCcw,
  HardDrive,
  Send,
  Plus,
  ArrowLeft,
  Warehouse,
  History,
  Home,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { apiRequest } from "@/shared/api/httpClient";
import { useContarInventario } from "../hooks/useContarInventario";
import { InventarioTable, type CatalogProduct } from "./InventarioTable";
import { MOCK_BODEGAS, MOCK_STOCK_ITEMS } from "../mockData";
import type { ConteoItemDraft } from "../types";

export function ContarInventarioPage() {
  const { t } = useTranslation("inventory");
  const navigate = useNavigate();
  const {
    step,
    setStep,
    bodegaId,
    items,
    setItems,
    notas,
    setNotas,
    isSubmitting,
    hasOfflineDraft,
    startSession,
    recordCount,
    removeItem,
    clearOfflineDraft,
    resumeDraft,
    finalizeSession,
  } = useContarInventario();

  // Estados locales para la selección en Idle
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [selectedBodegaId, setSelectedBodegaNum] = useState<number>(1);
  const [productSearch, setProductSearch] = useState<string>("");
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Catálogo unificado de productos disponibles para auditar
  const [productos, setProductos] = useState<CatalogProduct[]>(() => {
    const map = new Map<number, CatalogProduct>();
    for (const it of MOCK_STOCK_ITEMS) {
      if (!map.has(it.producto_id)) {
        map.set(it.producto_id, {
          id: it.producto_id,
          nombre: it.nombre,
          sku: it.sku,
          categoria: it.categoria,
          categoria_color: it.categoria_color,
          categoria_icono: it.categoria_icono,
          unidad_medida: it.unidad_medida,
          costo_unitario_ppp: it.costo_unitario_ppp,
          no_perecible: it.no_perecible,
        });
      }
    }
    return Array.from(map.values());
  });

  // Intentar cargar productos desde backend si estuvieran disponibles
  useEffect(() => {
    let active = true;
    apiRequest<any[]>("/api/v1/inventory/products", {
      method: "GET",
      fallbackData: [],
    })
      .then((res) => {
        if (!active || !Array.isArray(res.data) || res.data.length === 0) return;
        const valid = res.data.filter(
          (p) => p.estado !== "borrador" && p.estado !== "borrador_incompleto"
        );
        if (valid.length > 0) {
          setProductos(
            valid.map((p) => ({
              id: p.id,
              nombre: p.nombre,
              sku: p.sku,
              categoria: p.categoria,
              categoria_color: p.categoria_color,
              categoria_icono: p.categoria_icono,
              unidad_medida: p.unidad_medida,
              costo_unitario_ppp: p.costo_unitario_ppp,
              no_perecible: p.no_perecible,
            }))
          );
        }
      })
      .catch(() => {
        // En offline, se usan los productos iniciales de fallback
      });
    return () => {
      active = false;
    };
  }, []);

  // Autofocus en el buscador de productos al entrar en estado 'counting'
  useEffect(() => {
    if (step === "counting") {
      const timer = setTimeout(() => {
        searchInputRef.current?.focus();
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [step]);

  // Bodega activa
  const activeBodega = useMemo(() => {
    const idToFind = step === "idle" ? selectedBodegaId : bodegaId;
    return MOCK_BODEGAS.find((b) => b.id === idToFind) ?? MOCK_BODEGAS[0];
  }, [step, selectedBodegaId, bodegaId]);

  // Filtrado de productos en el buscador interactivo
  const filteredProducts = useMemo(() => {
    if (!productSearch.trim()) return [];
    const query = productSearch.toLowerCase().trim();
    return productos.filter(
      (p) =>
        p.nombre.toLowerCase().includes(query) ||
        (p.sku && p.sku.toLowerCase().includes(query)) ||
        (p.categoria && p.categoria.toLowerCase().includes(query))
    );
  }, [productos, productSearch]);

  // Adición rápida de producto a la lista de conteo
  const handleAddProduct = (prod: CatalogProduct) => {
    const existing = items.find((i) => i.producto_id === prod.id);
    if (existing) {
      toast.info(t("conteo.toast_already_added", { name: prod.nombre, defaultValue: `"${prod.nombre}" ya está en la lista de recuento` }));
    } else {
      recordCount({
        producto_id: prod.id,
        producto_nombre: prod.nombre,
        unidad_medida: prod.unidad_medida,
        stock_fisico_contado: 0,
        costo_unitario_ppp: prod.costo_unitario_ppp,
      });
      toast.success(t("conteo.toast_added", { name: prod.nombre, defaultValue: `"${prod.nombre}" añadido al recuento` }));
    }
    setProductSearch("");
    setIsSearchOpen(false);
  };

  // Manejo de Enter o Escaneo de Código de Barras / SKU
  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = productSearch.trim();
      if (!trimmed) return;

      // Buscar coincidencia exacta por SKU primero (típico de pistola láser)
      const exactSku = productos.find(
        (p) => p.sku?.toLowerCase() === trimmed.toLowerCase()
      );
      if (exactSku) {
        handleAddProduct(exactSku);
        return;
      }

      // Si hay un único resultado en la búsqueda filtrada, agregarlo
      if (filteredProducts.length === 1 && filteredProducts[0]) {
        handleAddProduct(filteredProducts[0]);
        return;
      }

      if (filteredProducts.length > 1 && filteredProducts[0]) {
        handleAddProduct(filteredProducts[0]);
      }
    }
  };

  // Actualización de campos de un ítem
  const handleUpdateItem = (
    localId: string,
    field: keyof ConteoItemDraft,
    value: any
  ) => {
    setItems((prev) =>
      prev.map((it) => (it.localId === localId ? { ...it, [field]: value } : it))
    );
  };

  // Total de unidades físicas contadas
  const totalPhysicalUnits = useMemo(() => {
    return items.reduce((acc, it) => acc + (Number(it.stock_fisico_contado) || 0), 0);
  }, [items]);

  // Iniciar el recuento desde Idle
  const handleStartCount = async () => {
    const areaIdNum = selectedAreaId === "all" ? null : 1;
    await startSession(selectedBodegaId, areaIdNum);
  };

  // Cancelar conteo activo y regresar a Idle
  const handleCancelCount = () => {
    if (
      items.length > 0 &&
      !window.confirm(
        t("conteo.cancel_confirm", "¿Deseas cancelar el recuento activo? El borrador local se mantendrá disponible para reanudar más tarde.")
      )
    ) {
      return;
    }
    setStep("idle");
  };

  // Envío final y transición
  const handleConfirmAndFinalize = async () => {
    if (items.length === 0) {
      toast.error(t("conteo.toast_min_items", "Debes contar al menos 1 insumo antes de finalizar"));
      return;
    }
    const success = await finalizeSession();
    if (success) {
      setStep("finished");
    }
  };

  return (
    <div
      data-testid="contar-inventario-container"
      className="container mx-auto px-2 sm:px-4 py-4 md:py-6 max-w-7xl space-y-6 animate-fade-in"
    >
      {/* 1. Encabezado Centrado con ADN OppyTec Legacy (Verde Esmeralda #10b981) */}
      <SectionHeader
        title={t("conteo.title", "Recuento de Inventario")}
        subtitle={t("conteo.subtitle", "Sincroniza el stock físico con el sistema (Conteo Ciego)")}
        icon={ClipboardCheck}
        color="#10b981"
        center={true}
      />

      {/* =========================================================================
          ESTADO 1: IDLE (Selector de Área y Bodega, Resumen y Botón Comenzar)
          ========================================================================= */}
      {step === "idle" && (
        <div
          data-testid="conteo-step-idle"
          className="bg-card max-w-xl mx-auto p-6 sm:p-10 border border-border/80 rounded-2xl shadow-xl space-y-6 text-center backdrop-blur-md"
        >
          {/* Icono circular de Play destacado */}
          <div className="mx-auto w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center shadow-inner">
            <Play className="h-8 w-8 fill-emerald-500/20 translate-x-0.5" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-black tracking-tight text-foreground">
              {t("conteo.start_title", "Iniciar nuevo recuento")}
            </h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              {t("conteo.start_description", "Selecciona el área operativa y la bodega correspondiente para comenzar la toma física de existencias.")}
            </p>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              <span>{t("conteo.blind_audit_badge", "Auditoría Ciega: Cero sesgo de stock teórico")}</span>
            </div>
          </div>

          {/* Banner de Borrador Offline Detectado si existe */}
          {hasOfflineDraft && (
            <div
              data-testid="conteo-offline-draft-banner"
              className="p-4 rounded-xl border border-primary/30 bg-primary/5 text-left space-y-2.5"
            >
              <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
                <HardDrive className="h-4 w-4 shrink-0" />
                <span>{t("conteo.draft_banner_title", "Borrador offline guardado en este equipo")}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("conteo.draft_banner_desc", "Existe un conteo previo en progreso guardado automáticamente en tu navegador. Puedes reanudarlo sin perder datos.")}
              </p>
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  data-testid="conteo-resume-draft-btn"
                  onClick={resumeDraft}
                  className="touch-target px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-bold shadow-xs hover:bg-primary/90 transition-colors"
                >
                  {t("conteo.resume_draft", "Reanudar borrador")}
                </button>
                <button
                  type="button"
                  data-testid="conteo-discard-draft-btn"
                  onClick={() => {
                    if (window.confirm(t("conteo.discard_confirm", "¿Seguro que deseas descartar el borrador offline?"))) {
                      clearOfflineDraft();
                      toast.info(t("conteo.toast_draft_discarded", "Borrador descartado"));
                    }
                  }}
                  className="touch-target px-3.5 py-1.5 rounded-lg border border-border bg-background text-xs font-medium text-muted-foreground hover:bg-muted transition-colors"
                >
                  {t("conteo.discard_draft", "Descartar")}
                </button>
              </div>
            </div>
          )}

          {/* Selectores de Área Operativa y Bodega */}
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4 py-3">
            <div className="flex flex-col items-center sm:items-start gap-1.5 w-full sm:w-auto">
              <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground ml-1">
                {t("conteo.operational_area", "Área Operativa")}
              </span>
              <AreaSelector
                selectedAreaId={selectedAreaId}
                onSelectArea={setSelectedAreaId}
                buttonClassName="w-full sm:w-[220px] h-10 rounded-xl bg-background border-border"
              />
            </div>

            <div className="flex flex-col items-center sm:items-start gap-1.5 w-full sm:w-auto">
              <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground ml-1">
                {t("conteo.warehouse_label", "Bodega de Conteo")}
              </span>
              <select
                aria-label={t("conteo.warehouse_label", "Bodega de Conteo")}
                data-testid="conteo-bodega-select"
                value={selectedBodegaId}
                onChange={(e) => setSelectedBodegaNum(Number(e.target.value))}
                className="touch-target w-full sm:w-[220px] h-10 px-3 rounded-xl border border-border bg-background text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
              >
                {MOCK_BODEGAS.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Botón Principal: Comenzar Recuento */}
          <button
            type="button"
            data-testid="conteo-start-btn"
            onClick={handleStartCount}
            disabled={!selectedBodegaId}
            className="touch-target w-full sm:w-auto px-8 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-bold text-sm shadow-lg shadow-emerald-600/20 transition-all inline-flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <Play className="h-4 w-4 fill-white" />
            <span>
              {t("conteo.start_in_warehouse", {
                name: activeBodega ? activeBodega.nombre : "Bodega",
                defaultValue: `Comenzar en ${activeBodega ? activeBodega.nombre : "Bodega"}`,
              })}
            </span>
          </button>
        </div>
      )}

      {/* =========================================================================
          ESTADO 2: COUNTING (Toma física activa de inventario ciego)
          ========================================================================= */}
      {step === "counting" && (
        <div data-testid="conteo-step-counting" className="space-y-4">
          {/* Header Informativo y Barra de Herramientas de la Sesión */}
          <div className="bg-card p-4 rounded-2xl border border-border shadow-md flex flex-wrap items-center justify-between gap-4">
            {/* Información de la Bodega y Estado */}
            <div className="flex items-center gap-3">
              <div
                className="h-10 w-10 rounded-xl flex items-center justify-center border shadow-xs"
                style={{
                  backgroundColor: activeBodega?.color
                    ? `${activeBodega.color}20`
                    : "rgba(16, 185, 129, 0.15)",
                  color: activeBodega?.color || "#10b981",
                  borderColor: activeBodega?.color || "#10b981",
                }}
              >
                <Warehouse className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-foreground">
                    {activeBodega?.nombre || "Bodega Activa"}
                  </h3>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                    {t("conteo.counting_badge", "Conteo En Progreso")}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                  <span>
                    {t("conteo.counted_items", { count: items.length, defaultValue: `Ítems contados: ${items.length}` })}
                  </span>
                  <span>•</span>
                  <span>
                    {t("conteo.physical_units", { count: totalPhysicalUnits, defaultValue: `Unidades físicas: ${totalPhysicalUnits}` })}
                  </span>
                </div>
              </div>
            </div>

            {/* Banner de Persistencia Offline Automática */}
            <div
              data-testid="conteo-offline-indicator"
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs font-semibold text-emerald-600 dark:text-emerald-400"
            >
              <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <HardDrive className="h-3.5 w-3.5" />
              <span>{t("conteo.offline_indicator", "Guardado en local automáticamente")}</span>
            </div>

            {/* Botones de Acción de Cabecera: Cancelar y Finalizar */}
            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                data-testid="conteo-cancel-btn"
                onClick={handleCancelCount}
                className="touch-target px-3 py-2 rounded-xl border border-border bg-background text-xs font-bold text-muted-foreground hover:bg-muted transition-colors cursor-pointer"
              >
                {t("conteo.cancel_count", "Cancelar Conteo")}
              </button>

              <button
                type="button"
                data-testid="conteo-review-btn"
                onClick={() => {
                  if (items.length === 0) {
                    toast.error(t("conteo.toast_min_items", "Debes añadir al menos 1 producto antes de finalizar"));
                    return;
                  }
                  setStep("reviewing");
                }}
                disabled={items.length === 0}
                className="touch-target px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition-all inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{t("conteo.finalize_count", "Finalizar Conteo")}</span>
              </button>
            </div>
          </div>

          {/* Buscador Interactivo con Soporte de Escaneo de Código de Barras / SKU */}
          <div className="bg-card p-4 rounded-2xl border border-border shadow-sm space-y-2 relative">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Search className="h-3.5 w-3.5 text-primary" />
                {t("conteo.search_label", "Buscador de Insumos & Escaneo de Código")}
              </span>
              <span className="text-[10px] text-muted-foreground/80 lowercase">
                {t("conteo.search_hint", "(escribe o escanea con lector láser y presiona enter)")}
              </span>
            </label>

            <div className="relative">
              <div className="relative flex items-center">
                <Search className="absolute left-3.5 h-4 w-4 text-muted-foreground pointer-events-none" />
                <input
                  ref={searchInputRef}
                  type="text"
                  data-testid="conteo-search-input"
                  aria-label={t("conteo.search_placeholder", "Buscar por nombre, SKU o escanear código de barra...")}
                  placeholder={t("conteo.search_placeholder", "Buscar por nombre, SKU o escanear código de barra...")}
                  value={productSearch}
                  onChange={(e) => {
                    setProductSearch(e.target.value);
                    setIsSearchOpen(true);
                  }}
                  onFocus={() => {
                    if (productSearch.trim()) setIsSearchOpen(true);
                  }}
                  onBlur={() => {
                    setTimeout(() => setIsSearchOpen(false), 200);
                  }}
                  onKeyDown={handleSearchKeyDown}
                  className="touch-target h-11 w-full pl-10 pr-24 rounded-xl border border-border bg-background text-sm font-medium text-foreground shadow-inner focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
                <div className="absolute right-2.5 flex items-center gap-1 text-[10px] font-mono text-muted-foreground bg-muted/60 px-2 py-1 rounded-md border border-border/40">
                  <Barcode className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">{t("conteo.scanning_badge", "Escaneo")}</span>
                </div>
              </div>

              {/* Menú desplegable de sugerencias de productos */}
              {isSearchOpen && filteredProducts.length > 0 && (
                <div
                  data-testid="conteo-search-results"
                  className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 max-h-60 overflow-y-auto rounded-xl border border-border bg-card p-1.5 shadow-2xl space-y-1"
                >
                  {filteredProducts.map((p) => {
                    const isAlreadyAdded = items.some((i) => i.producto_id === p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        data-testid={`conteo-search-item-${p.id}`}
                        onMouseDown={() => handleAddProduct(p)}
                        className="w-full flex items-center justify-between p-2 rounded-lg text-left hover:bg-accent/60 transition-colors group cursor-pointer"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div
                            className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0"
                            style={{
                              backgroundColor: p.categoria_color
                                ? `${p.categoria_color}20`
                                : "rgba(16, 185, 129, 0.1)",
                              color: p.categoria_color || "#10b981",
                            }}
                          >
                            <CategoryIcon
                              name={p.categoria_icono || "package"}
                              className="h-3.5 w-3.5"
                            />
                          </div>
                          <div className="min-w-0">
                            <span className="font-bold text-xs text-foreground block truncate">
                              {p.nombre}
                            </span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              {p.sku || `ID: ${p.id}`} • {p.unidad_medida}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {isAlreadyAdded ? (
                            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                              {t("conteo.badge_added", "Agregado")}
                            </span>
                          ) : (
                            <span className="text-[10px] font-bold text-primary group-hover:underline flex items-center gap-1">
                              <Plus className="h-3 w-3" />
                              {t("conteo.btn_add", "Añadir")}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Grilla Principal de Recuento Ciego */}
          <InventarioTable
            items={items}
            productos={productos}
            onUpdate={handleUpdateItem}
            onRemove={removeItem}
          />

          {/* Barra inferior fija / flotante para finalizar recuento */}
          {items.length > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-card rounded-2xl border border-border shadow-sm">
              <div className="text-xs text-muted-foreground">
                {t("conteo.lines_counted_summary", {
                  lines: items.length,
                  units: totalPhysicalUnits,
                  defaultValue: `Total de líneas contadas: ${items.length} • Unidades físicas totales: ${totalPhysicalUnits}`,
                })}
              </div>

              <button
                type="button"
                data-testid="conteo-bottom-finalize-btn"
                onClick={() => setStep("reviewing")}
                className="touch-target w-full sm:w-auto px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition-all inline-flex items-center justify-center gap-2 cursor-pointer"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{t("conteo.review_finalize_btn", { count: items.length, defaultValue: `Revisar y Finalizar Conteo (${items.length} ítems)` })}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          ESTADO 3: REVIEWING (Resumen, Notas y Confirmación Final)
          ========================================================================= */}
      {step === "reviewing" && (
        <div
          data-testid="conteo-step-reviewing"
          className="bg-card max-w-2xl mx-auto p-6 sm:p-8 border border-border rounded-2xl shadow-xl space-y-6"
        >
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h2 className="text-xl font-black text-foreground">
                {t("conteo.review_title", "Revisión del Recuento Físico")}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("conteo.review_subtitle", {
                  name: activeBodega?.nombre,
                  count: items.length,
                  defaultValue: `Bodega: ${activeBodega?.nombre} • ${items.length} productos registrados`,
                })}
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-bold text-amber-600">
              {t("conteo.final_step_badge", "Paso Final")}
            </span>
          </div>

          {/* Resumen de ítems contados */}
          <div className="border border-border rounded-xl overflow-hidden max-h-64 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="bg-muted/50 border-b border-border">
                <tr className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                  <th className="p-2.5 pl-4 text-left">{t("conteo.table_header_item", "Insumo")}</th>
                  <th className="p-2.5 text-center">{t("conteo.table_header_unit", "Unidad")}</th>
                  <th className="p-2.5 text-right pr-4">{t("conteo.table_header_qty", "Cantidad Física")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {items.map((it) => (
                  <tr key={it.localId} className="hover:bg-accent/40">
                    <td className="p-2.5 pl-4 font-semibold text-foreground">
                      {it.producto_nombre}
                      {it.lote_codigo && (
                        <span className="block text-[10px] text-muted-foreground font-mono">
                          {t("conteo.lot_prefix", { code: it.lote_codigo, defaultValue: `Lote: ${it.lote_codigo}` })}
                        </span>
                      )}
                    </td>
                    <td className="p-2.5 text-center font-mono font-bold text-muted-foreground uppercase">
                      {it.unidad_medida}
                    </td>
                    <td className="p-2.5 pr-4 text-right font-mono font-black text-sm text-foreground">
                      {it.stock_fisico_contado}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Campo de Notas y Observaciones de la Auditoría */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              {t("conteo.notes_label", "Notas u Observaciones del Recuento")}
            </label>
            <textarea
              data-testid="conteo-notas-input"
              rows={3}
              aria-label={t("conteo.notes_label", "Notas u Observaciones del Recuento")}
              placeholder={t("conteo.notes_placeholder", "Ej: Conteo físico regular fin de turno. Sin novedades en congeladores...")}
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              className="w-full p-3 rounded-xl border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
            />
          </div>

          {/* Alerta de Conciliación Administrativa */}
          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
            <p>
              {t("conteo.admin_alert", "Al enviar, la sesión quedará en estado PENDIENTE_APROBACION. Las existencias en el Kardex no serán alteradas hasta que la jefatura o administración valide y concilie los datos.")}
            </p>
          </div>

          {/* Botones de Navegación: Volver a Contar / Confirmar y Enviar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <button
              type="button"
              data-testid="conteo-back-to-counting-btn"
              onClick={() => setStep("counting")}
              className="touch-target w-full sm:w-auto px-4 py-2.5 rounded-xl border border-border bg-background text-xs font-bold text-foreground hover:bg-muted transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>{t("conteo.back_to_counting", "Volver a Modificar")}</span>
            </button>

            <button
              type="button"
              data-testid="conteo-confirm-finalize-btn"
              onClick={handleConfirmAndFinalize}
              disabled={isSubmitting}
              className="touch-target w-full sm:w-auto px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition-all inline-flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              <span>{isSubmitting ? t("conteo.sending", "Enviando Recuento...") : t("conteo.confirm_send", "Confirmar y Enviar Recuento")}</span>
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          ESTADO 4: FINISHED (Éxito 1:1 OppyTec-Legacy con Redirecciones Claras)
          ========================================================================= */}
      {step === "finished" && (
        <div
          data-testid="conteo-step-finished"
          className="bg-card max-w-xl mx-auto p-8 sm:p-12 border border-border rounded-2xl shadow-xl space-y-6 text-center backdrop-blur-md"
        >
          {/* Icono de CheckCircle Verde Esmeralda */}
          <div className="mx-auto w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center shadow-inner">
            <CheckCircle className="h-10 w-10 text-emerald-500" />
          </div>

          <div className="space-y-3">
            <h2 className="text-2xl font-black tracking-tight text-foreground">
              {t("conteo.success_title", "¡Recuento Enviado!")}
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {t("conteo.success_desc_prefix", "El recuento de inventario ha sido registrado en estado")}{" "}
              <span className="font-semibold text-amber-600 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                {t("conteo.status_pending", "pendiente")}
              </span>{" "}
              {t("conteo.success_desc_suffix", "y enviado a la administración para su revisión y conciliación.")}
            </p>
            <p className="text-xs text-muted-foreground">
              {t("conteo.success_note", "El stock real no cambiará hasta que un administrador o propietario apruebe esta sesión de conteo.")}
            </p>
          </div>

          <div className="pt-4 flex flex-col sm:flex-row justify-center gap-3">
            <button
              type="button"
              data-testid="conteo-start-another-btn"
              onClick={() => {
                clearOfflineDraft();
                setStep("idle");
                setItems([]);
              }}
              className="touch-target px-5 py-2.5 rounded-xl border border-border bg-background text-xs font-bold text-foreground hover:bg-muted transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <RotateCcw className="h-4 w-4 text-primary" />
              <span>{t("conteo.start_another", "Iniciar otro conteo")}</span>
            </button>

            <button
              type="button"
              data-testid="conteo-go-recuentos-btn"
              onClick={() => navigate("/recuentos")}
              className="touch-target px-5 py-2.5 rounded-xl bg-secondary text-secondary-foreground text-xs font-bold hover:bg-secondary/80 transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <History className="h-4 w-4" />
              <span>{t("conteo.view_history", "Ver Historial de Recuentos")}</span>
            </button>

            <button
              type="button"
              data-testid="conteo-go-home-btn"
              onClick={() => navigate("/")}
              className="touch-target px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Home className="h-4 w-4" />
              <span>{t("conteo.go_home", "Volver al Inicio")}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ContarInventarioPage;
