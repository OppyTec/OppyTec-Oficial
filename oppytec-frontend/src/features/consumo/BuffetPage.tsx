// oppytec-frontend/src/features/consumo/BuffetPage.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  UtensilsCrossed,
  Camera,
  Plus,
  History,
  Bookmark,
  Sparkles,
  CheckCircle2,
  Calendar,
} from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { BodegaSelector } from "@/shared/components/layout/BodegaSelector";
import { cn } from "@/shared/lib/utils";
import { useCurrencyFormatter } from "@/shared/currency";
import { useBuffet } from "./hooks/useBuffet";
import {
  StationCameraScanner,
  BuffetItemsTable,
  BuffetConciliationDialog,
  BuffetTemplateModal,
} from "./components/buffet";
import type {
  BuffetSessionItem,
  BuffetItemDetection,
} from "./types";

export function BuffetPage() {
  const { t } = useTranslation("operations");
  const { format } = useCurrencyFormatter();
  const [selectedAreaId, setSelectedAreaId] = useState<string>("area-cocina");
  const [selectedBodegaId, setSelectedBodegaId] = useState<string>("bod-cocina-central");

  const [activeTab, setActiveTab] = useState<"sesion_activa" | "historial">("sesion_activa");
  const [selectedStationFilter, setSelectedStationFilter] = useState<string>("all");
  const [currentStage, setCurrentStage] = useState<"apertura" | "reposicion" | "cierre">("apertura");

  // Modales
  const [scannerOpen, setScannerOpen] = useState(false);
  const [conciliationOpen, setConciliationOpen] = useState(false);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [newSessionOpen, setNewSessionOpen] = useState(false);
  const [manualItemOpen, setManualItemOpen] = useState(false);

  // Estados de formulario de nueva sesión
  const [newSessionName, setNewSessionName] = useState("");
  const [newSessionTipo, setNewSessionTipo] = useState<string>("DESAYUNO");
  const [selectedTemplateForNewSession, setSelectedTemplateForNewSession] = useState<string>("none");

  // Estados para ítem manual
  const [manualItemName, setManualItemName] = useState("");
  const [manualItemType, setManualItemType] = useState<"producto" | "receta">("producto");
  const [manualItemQty, setManualItemQty] = useState("1");
  const [manualItemUnit, setManualItemUnit] = useState("kg");
  const [manualItemStation, setManualItemStation] = useState("Estación Calientes & Huevos");

  const {
    sessions,
    setActiveSessionId,
    activeSession,
    templates,
    sessionMetrics,
    startSession,
    finalizeSession,
    createTemplate,
    isFinalizing,
  } = useBuffet({
    bodegaId: selectedBodegaId,
  });

  // Ítems locales editables para la sesión activa
  const [localItems, setLocalItems] = useState<BuffetSessionItem[]>(() => {
    return activeSession?.items ? [...activeSession.items] : [];
  });

  // Sincronizar items locales cuando cambia activeSession
  useEffect(() => {
    if (activeSession?.items) {
      setLocalItems([...activeSession.items]);
    }
  }, [activeSession]);

  // Lista de estaciones únicas para selector de pestañas
  const uniqueStations = useMemo(() => {
    const stSet = new Set<string>();
    if (activeSession?.estaciones) {
      activeSession.estaciones.forEach((e) => stSet.add(e.nombre_estacion));
    }
    localItems.forEach((it) => {
      if (it.estacion_nombre) stSet.add(it.estacion_nombre);
    });
    return Array.from(stSet);
  }, [activeSession, localItems]);

  // Ítems filtrados por estación
  const displayedItems = useMemo(() => {
    if (selectedStationFilter === "all") return localItems;
    return localItems.filter((it) => it.estacion_nombre === selectedStationFilter);
  }, [localItems, selectedStationFilter]);

  // Handlers de la tabla de ítems
  const handleUpdateItemQuantity = (
    itemId: string,
    field: "cantidad_apertura" | "cantidad_reposiciones" | "cantidad_cierre",
    delta: number
  ) => {
    setLocalItems((prev) =>
      prev.map((it) => {
        if (it.id !== itemId) return it;
        const currentVal = Number(it[field] || 0);
        const newVal = Math.max(0, Math.round((currentVal + delta) * 10) / 10);
        const ap = field === "cantidad_apertura" ? newVal : Number(it.cantidad_apertura || 0);
        const rep = field === "cantidad_reposiciones" ? newVal : Number(it.cantidad_reposiciones || 0);
        const cie = field === "cantidad_cierre" ? newVal : Number(it.cantidad_cierre || 0);
        const con = Math.max(0, Math.round((ap + rep - cie) * 10) / 10);

        return {
          ...it,
          [field]: newVal,
          cantidad_consumida: con,
          cantidad_sobrante: cie,
        };
      })
    );
  };

  const handleToggleAccionSobrante = (itemId: string) => {
    setLocalItems((prev) =>
      prev.map((it) => {
        if (it.id !== itemId) return it;
        const nextAction: "retornar" | "merma" =
          it.accion_sobrante === "retornar" ? "merma" : "retornar";
        return { ...it, accion_sobrante: nextAction };
      })
    );
  };

  const handleRemoveItem = (itemId: string) => {
    setLocalItems((prev) => prev.filter((it) => it.id !== itemId));
    toast.info("Ítem removido del balance");
  };

  const handleUpdateMotivoMerma = (itemId: string, motivo: string) => {
    setLocalItems((prev) =>
      prev.map((it) => (it.id === itemId ? { ...it, motivo_merma: motivo } : it))
    );
  };

  // Handler de confirmación del escáner visual
  const handleConfirmStationScan = (data: {
    station_name: string;
    foto_url: string;
    detections: BuffetItemDetection[];
  }) => {
    const newItems: BuffetSessionItem[] = data.detections.map((det) => {
      const existing = localItems.find((it) => it.nombre === det.name);
      if (existing) {
        return existing;
      }

      const count = det.count;
      return {
        id: `scan-item-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        item_type: det.item_type,
        nombre: det.name,
        unidad: det.unit || "kg",
        estacion_nombre: data.station_name,
        cantidad_apertura: currentStage === "apertura" ? count : 0,
        cantidad_reposiciones: currentStage === "reposicion" ? count : 0,
        cantidad_cierre: currentStage === "cierre" ? count : 0,
        cantidad_consumida: currentStage === "cierre" ? 0 : count,
        cantidad_sobrante: currentStage === "cierre" ? count : 0,
        accion_sobrante: "retornar",
      };
    });

    setLocalItems((prev) => {
      const merged = [...prev];
      newItems.forEach((ni) => {
        const idx = merged.findIndex((it) => it.nombre === ni.nombre);
        if (idx >= 0) {
          const current = merged[idx]!;
          if (currentStage === "apertura") {
            current.cantidad_apertura += ni.cantidad_apertura;
          } else if (currentStage === "reposicion") {
            current.cantidad_reposiciones += ni.cantidad_reposiciones;
          } else if (currentStage === "cierre") {
            current.cantidad_cierre += ni.cantidad_cierre;
            current.cantidad_sobrante = current.cantidad_cierre;
          }
          current.cantidad_consumida = Math.max(
            0,
            current.cantidad_apertura + current.cantidad_reposiciones - current.cantidad_cierre
          );
        } else {
          merged.push(ni);
        }
      });
      return merged;
    });

    toast.success(`Estación "${data.station_name}" agregada con ${data.detections.length} insumos`);
  };

  // Agregar ítem manual
  const handleAddManualItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualItemName.trim()) {
      toast.error("Ingresa el nombre del producto o receta");
      return;
    }
    const qty = parseFloat(manualItemQty) || 1;

    const newItem: BuffetSessionItem = {
      id: `manual-item-${Date.now()}`,
      item_type: manualItemType,
      nombre: manualItemName.trim(),
      unidad: manualItemUnit,
      estacion_nombre: manualItemStation,
      cantidad_apertura: currentStage === "apertura" ? qty : 0,
      cantidad_reposiciones: currentStage === "reposicion" ? qty : 0,
      cantidad_cierre: currentStage === "cierre" ? qty : 0,
      cantidad_consumida: currentStage === "cierre" ? 0 : qty,
      cantidad_sobrante: currentStage === "cierre" ? qty : 0,
      accion_sobrante: "retornar",
    };

    setLocalItems((prev) => [...prev, newItem]);
    toast.success(`"${newItem.nombre}" agregado al balance`);
    setManualItemName("");
    setManualItemQty("1");
    setManualItemOpen(false);
  };

  // Iniciar nueva sesión
  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSessionName.trim()) {
      toast.error("Ingresa un nombre para la sesión de buffet");
      return;
    }

    try {
      await startSession({
        bodega_id: selectedBodegaId,
        tipo_servicio: newSessionTipo,
        area_operativa_id: selectedAreaId,
        template_id: selectedTemplateForNewSession !== "none" ? selectedTemplateForNewSession : undefined,
        estaciones: [
          { nombre: "Estación Calientes & Huevos", orden: 1 },
          { nombre: "Estación Fríos & Ensaladas", orden: 2 },
          { nombre: "Panadería & Bollería", orden: 3 },
        ],
      });
      setNewSessionOpen(false);
      setNewSessionName("");
    } catch {
      // Toast ya manejado en useBuffet
    }
  };

  // Liquidar sesión
  const handleFinalize = async (pax: number, valorSobrante: number) => {
    if (!activeSession) return;
    await finalizeSession({
      sessionId: activeSession.id,
      payload: {
        pax,
        leftover_reusable_value: valorSobrante,
      },
    });
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background text-foreground">
      {/* 1. Cabecera Visual Centrada */}
      <SectionHeader
        title={t("consumption.buffet.title", { defaultValue: "Buffet Inteligente" })}
        subtitle={t("consumption.buffet.subtitle", {
          defaultValue: "Control de estaciones, pesaje y liquidación de consumo por comensal",
        })}
        icon={UtensilsCrossed}
        color="#06b6d4"
        center={true}
      />

      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-4 space-y-5">
        {/* 2. Selectores de Área Operativa y Bodega */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-2xl bg-card border border-border/60 shadow-xs">
          <div className="flex flex-wrap items-center gap-3">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={setSelectedAreaId}
            />
            <BodegaSelector
              activeWarehouseId={selectedBodegaId}
              onSelectWarehouse={setSelectedBodegaId}
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("sesion_activa")}
              data-testid="tab-sesion-activa"
              className={cn(
                "px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer",
                activeTab === "sesion_activa"
                  ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {t("consumption.buffet.tabs.active_session", { defaultValue: "Sesión Activa" })}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("historial")}
              data-testid="tab-historial-buffet"
              className={cn(
                "px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5",
                activeTab === "historial"
                  ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              <History className="w-3.5 h-3.5" />
              {t("consumption.buffet.tabs.history", { defaultValue: "Historial de Sesiones" })}
            </button>
          </div>
        </div>

        {activeTab === "sesion_activa" ? (
          <>
            {/* 3. Panel de Sesión Activa y Plantillas */}
            <div className="p-4 rounded-3xl bg-card border border-border/80 shadow-xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-foreground" data-testid="active-session-title">
                        {activeSession?.nombre || "Servicio Buffet del Día"}
                      </h2>
                      <span className="text-[10px] uppercase font-black px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                        {activeSession?.estado || "abierto"}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Servicio: {activeSession?.tipo_servicio || "DESAYUNO"} • Registrado por Chef de Turno
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setTemplateModalOpen(true)}
                    data-testid="open-buffet-templates-btn"
                    className="px-3.5 py-2 rounded-xl bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
                  >
                    <Bookmark className="w-3.5 h-3.5 text-cyan-400" />
                    Plantillas ({templates.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewSessionOpen(true)}
                    data-testid="open-new-session-modal-btn"
                    className="px-3.5 py-2 rounded-xl bg-muted hover:bg-muted/80 text-foreground text-xs font-semibold flex items-center gap-1.5 cursor-pointer border border-border"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Nueva Sesión
                  </button>
                </div>
              </div>

              {/* 4. Métricas Financieras en Vivo y Costo Pax */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
                <div className="p-3.5 rounded-2xl bg-muted/30 border border-border/50 text-center">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
                    {t("consumption.buffet.metrics.total_montaje", { defaultValue: "Costo Total Montaje" })}
                  </span>
                  <span className="text-base font-mono font-bold text-foreground" data-testid="metric-costo-montaje">
                    {format(sessionMetrics.totalMontaje || 120000)}
                  </span>
                </div>

                <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <span className="text-[10px] uppercase font-bold text-emerald-500 block mb-1">
                    {t("consumption.buffet.metrics.total_sobrante", { defaultValue: "Sobrante Reutilizable" })}
                  </span>
                  <span className="text-base font-mono font-bold text-emerald-400" data-testid="metric-sobrante">
                    {format(sessionMetrics.totalSobrante || 30000)}
                  </span>
                </div>

                <div className="p-3.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-center">
                  <span className="text-[10px] uppercase font-bold text-cyan-500 block mb-1">
                    {t("consumption.buffet.metrics.total_consumido", { defaultValue: "Consumo Neto Servido" })}
                  </span>
                  <span className="text-base font-mono font-bold text-cyan-400" data-testid="metric-consumido">
                    {format(sessionMetrics.totalConsumido || 90000)}
                  </span>
                </div>

                <div className="p-3.5 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 border border-cyan-500/30 text-center">
                  <span className="text-[10px] uppercase font-bold text-cyan-300 block mb-1">
                    {t("consumption.buffet.metrics.costo_pax", { defaultValue: "Costo Neto / Pax" })} ({activeSession?.pax_comensales || 45} Pax)
                  </span>
                  <span className="text-lg font-mono font-black text-cyan-400" data-testid="metric-costo-pax">
                    {format(sessionMetrics.costoNetoPax || 2000)}
                  </span>
                </div>
              </div>
            </div>

            {/* 5. Selector de Fase y Controles de Escaneo */}
            <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-3xl bg-card border border-border/80 shadow-xs">
              {/* Selector de Fase Operativa */}
              <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-muted/60 border border-border">
                {(["apertura", "reposicion", "cierre"] as const).map((stage) => (
                  <button
                    key={stage}
                    type="button"
                    onClick={() => setCurrentStage(stage)}
                    data-testid={`stage-selector-${stage}`}
                    className={cn(
                      "px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                      currentStage === stage
                        ? "bg-cyan-500 text-black shadow-md shadow-cyan-500/20"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {stage === "apertura"
                      ? "1. Apertura"
                      : stage === "reposicion"
                      ? "2. Reposición"
                      : "3. Cierre"}
                  </button>
                ))}
              </div>

              {/* Botones de acción */}
              <div className="flex flex-wrap items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setManualItemOpen(true)}
                  data-testid="open-manual-item-btn"
                  className="px-3.5 py-2.5 rounded-xl bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-bold flex items-center gap-1.5 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Agregar Ítem Manual
                </button>

                <button
                  type="button"
                  onClick={() => setScannerOpen(true)}
                  data-testid="open-station-scanner-btn"
                  className="touch-target px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-black font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer"
                >
                  <Camera className="w-4 h-4" />
                  Escanear Estación con Cámara
                </button>

                <button
                  type="button"
                  onClick={() => setConciliationOpen(true)}
                  data-testid="open-conciliation-modal-btn"
                  className="touch-target px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/20 cursor-pointer"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Finalizar y Liquidar Buffet
                </button>
              </div>
            </div>

            {/* 6. Filtro por Estaciones */}
            {uniqueStations.length > 0 && (
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                <span className="text-xs font-bold text-muted-foreground shrink-0 uppercase tracking-wider">
                  Estaciones:
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedStationFilter("all")}
                  data-testid="filter-station-all"
                  className={cn(
                    "px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer shrink-0 transition-colors",
                    selectedStationFilter === "all"
                      ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                      : "bg-muted text-muted-foreground hover:text-foreground"
                  )}
                >
                  Todas ({localItems.length})
                </button>
                {uniqueStations.map((st) => {
                  const count = localItems.filter((it) => it.estacion_nombre === st).length;
                  return (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setSelectedStationFilter(st)}
                      data-testid={`filter-station-${st}`}
                      className={cn(
                        "px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer shrink-0 transition-colors",
                        selectedStationFilter === st
                          ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                          : "bg-muted text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {st} ({count})
                    </button>
                  );
                })}
              </div>
            )}

            {/* 7. Tabla de Cuadratura de Insumos */}
            <BuffetItemsTable
              items={displayedItems}
              stage={currentStage}
              onUpdateItemQuantity={handleUpdateItemQuantity}
              onToggleAccionSobrante={handleToggleAccionSobrante}
              onRemoveItem={handleRemoveItem}
              onUpdateMotivoMerma={handleUpdateMotivoMerma}
            />
          </>
        ) : (
          /* Vista de Historial de Sesiones Pasadas */
          <div className="space-y-4" data-testid="buffet-history-view">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Calendar className="w-4 h-4 text-cyan-400" />
                Historial de Sesiones Liquidada
              </h3>
              <span className="text-xs text-muted-foreground">
                Total registradas: {sessions.length}
              </span>
            </div>

            <div className="space-y-3">
              {sessions.map((sess) => (
                <div
                  key={sess.id}
                  data-testid={`session-card-${sess.id}`}
                  className="p-4 rounded-2xl bg-card border border-border/80 flex flex-wrap items-center justify-between gap-4 shadow-xs hover:border-cyan-500/40 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-foreground">
                        {sess.nombre || "Sesión de Buffet"}
                      </span>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        {sess.estado}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Fecha: {sess.created_at.slice(0, 10)} • Comensales: {sess.pax_comensales ?? 0} Pax
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <span className="text-[11px] text-muted-foreground block">{t("consumption.buffet.metrics.costo_pax", { defaultValue: "Costo / Pax" })}</span>
                      <span className="text-sm font-mono font-bold text-cyan-400">
                        {format(sess.costo_neto_pax ?? 0)}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setActiveSessionId(sess.id);
                        setActiveTab("sesion_activa");
                        toast.info(`Cargando sesión: ${sess.nombre}`);
                      }}
                      data-testid={`btn-select-session-${sess.id}`}
                      className="px-3.5 py-1.5 rounded-xl bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-semibold cursor-pointer"
                    >
                      Ver Detalle
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 8. MODAL DE ESCÁNER VISUAL DE CÁMARA */}
      <StationCameraScanner
        open={scannerOpen}
        onClose={() => setScannerOpen(false)}
        bodegaId={selectedBodegaId}
        stage={currentStage}
        defaultStationName={
          selectedStationFilter !== "all" ? selectedStationFilter : "Estación Calientes & Huevos"
        }
        onConfirmStation={handleConfirmStationScan}
      />

      {/* 9. MODAL DE LIQUIDACIÓN Y CONCILIACIÓN PAX */}
      <BuffetConciliationDialog
        open={conciliationOpen}
        onClose={() => setConciliationOpen(false)}
        session={activeSession}
        onFinalize={handleFinalize}
        isFinalizing={isFinalizing}
      />

      {/* 10. MODAL DE GESTIÓN DE PLANTILLAS */}
      <BuffetTemplateModal
        open={templateModalOpen}
        onClose={() => setTemplateModalOpen(false)}
        onSaveTemplate={async (data) => {
          await createTemplate(data);
        }}
      />

      {/* 11. MODAL DE NUEVA SESIÓN DE BUFFET */}
      {newSessionOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Nueva Sesión de Buffet"
          data-testid="new-buffet-session-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
        >
          <div className="w-full max-w-md rounded-3xl bg-card border border-border p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-foreground">Iniciar Nueva Sesión de Buffet</h3>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-foreground mb-1">
                  Nombre de la Sesión
                </label>
                <input
                  type="text"
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                  placeholder="Ej. Desayuno Buffet Ejecutivo"
                  required
                  data-testid="new-session-name-input"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-foreground mb-1">
                  Tipo de Servicio
                </label>
                <select
                  value={newSessionTipo}
                  onChange={(e) => setNewSessionTipo(e.target.value)}
                  data-testid="new-session-tipo-select"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
                >
                  <option value="DESAYUNO">Desayuno</option>
                  <option value="ALMUERZO">Almuerzo</option>
                  <option value="BRUNCH">Brunch / Evento</option>
                  <option value="CENA">Cena</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-foreground mb-1">
                  Plantilla Base (Opcional)
                </label>
                <select
                  value={selectedTemplateForNewSession}
                  onChange={(e) => setSelectedTemplateForNewSession(e.target.value)}
                  data-testid="new-session-template-select"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
                >
                  <option value="none">Sin plantilla (Montaje libre)</option>
                  {templates.map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>
                      {tpl.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setNewSessionOpen(false)}
                  className="px-4 py-2 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  data-testid="submit-new-session-btn"
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs cursor-pointer shadow-md"
                >
                  Iniciar Sesión
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 12. MODAL DE AGREGAR ÍTEM MANUAL */}
      {manualItemOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Agregar Ítem Manual al Buffet"
          data-testid="manual-item-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
        >
          <div className="w-full max-w-md rounded-3xl bg-card border border-border p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-foreground">Agregar Ítem al Balance</h3>
            <form onSubmit={handleAddManualItem} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-foreground mb-1">
                  Nombre del Insumo / Receta
                </label>
                <input
                  type="text"
                  value={manualItemName}
                  onChange={(e) => setManualItemName(e.target.value)}
                  placeholder="Ej. Salmón Ahumado en Láminas"
                  required
                  data-testid="manual-item-name-input"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">Tipo</label>
                  <select
                    value={manualItemType}
                    onChange={(e) => setManualItemType(e.target.value as "producto" | "receta")}
                    className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground focus:outline-none"
                  >
                    <option value="producto">Producto</option>
                    <option value="receta">Receta</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">Unidad</label>
                  <input
                    type="text"
                    value={manualItemUnit}
                    onChange={(e) => setManualItemUnit(e.target.value)}
                    placeholder="kg, porción, litro"
                    className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">Cantidad</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={manualItemQty}
                    onChange={(e) => setManualItemQty(e.target.value)}
                    required
                    data-testid="manual-item-qty-input"
                    className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">Estación</label>
                  <input
                    type="text"
                    value={manualItemStation}
                    onChange={(e) => setManualItemStation(e.target.value)}
                    placeholder="Estación..."
                    className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setManualItemOpen(false)}
                  className="px-4 py-2 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  data-testid="confirm-add-manual-item-btn"
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs cursor-pointer shadow-md"
                >
                  Agregar al Balance
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
export default BuffetPage;
