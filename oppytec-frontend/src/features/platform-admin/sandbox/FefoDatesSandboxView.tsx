import { useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Calendar,
  CalendarClock,
  CheckCircle2,
  Clock,
  FastForward,
  Flame,
  Info,
  Play,
  ShieldCheck,
  Warehouse,
  X,
  Zap,
} from "lucide-react";
import { Can } from "@/shared/auth/Can";
import { translateKey, useLanguage } from "@/shared/i18n";
import { formatMoney } from "@/shared/lib";
import { useMockDataMode } from "@/shared/mock/mockModeStorage";
import type {
  FefoBatchCanonicalStatus,
  FefoBatchSimulationImpact,
  FefoDatesSandboxViewProps,
  FefoDemoScenarioId,
  FefoShiftRequest,
  FefoSimulationRequest,
  FefoSimulationResponse,
  FefoSyncTodayRequest,
} from "../sandboxTypes";
import {
  FEFO_DEMO_SCENARIO_CONFIGS,
  FEFO_TIME_TRAVEL_RANGE,
  evaluateBatchSimulation,
  generateScenarioBatches,
  shiftIsoDate,
  summarizeFefoSimulation,
  syncBatchesToToday,
} from "./fefoMath";
import { shiftFefoApi, simulateFefoApi, syncFefoTodayApi } from "./sandboxApi";

export const MOCK_FEFO_BATCHES: readonly FefoBatchSimulationImpact[] = [
  {
    batchId: "LOT-2026-001",
    productSku: "INS-CARNE-01",
    productName: "Lomo Vetado Premium (Kg)",
    originalExpiryDate: "2026-11-20",
    simulatedExpiryDate: "2026-11-05",
    daysToExpiration: 0,
    status: "expired",
    canonicalStatus: "EXPIRED",
    stockQuantity: 18.5,
    unitMeasure: "Kg",
    unitCost: 14500,
    estimatedLossAmount: 268250,
  },
  {
    batchId: "LOT-2026-002",
    productSku: "INS-LACT-04",
    productName: "Queso Mozzarella Fior di Latte",
    originalExpiryDate: "2026-11-25",
    simulatedExpiryDate: "2026-11-10",
    daysToExpiration: 5,
    status: "critical",
    canonicalStatus: "CRITICAL",
    stockQuantity: 24,
    unitMeasure: "Kg",
    unitCost: 8900,
    estimatedLossAmount: 213600,
  },
  {
    batchId: "LOT-2026-003",
    productSku: "INS-VERD-02",
    productName: "Tomate Chonto de Huerto",
    originalExpiryDate: "2026-12-05",
    simulatedExpiryDate: "2026-11-20",
    daysToExpiration: 15,
    status: "warning",
    canonicalStatus: "WARNING",
    stockQuantity: 40,
    unitMeasure: "Kg",
    unitCost: 1800,
    estimatedLossAmount: 72000,
  },
  {
    batchId: "LOT-2026-004",
    productSku: "INS-ABAR-10",
    productName: "Harina de Trigo 0000",
    originalExpiryDate: "2027-04-10",
    simulatedExpiryDate: "2027-03-26",
    daysToExpiration: 141,
    status: "optimal",
    canonicalStatus: "OPTIMAL",
    stockQuantity: 120,
    unitMeasure: "Kg",
    unitCost: 1250,
    estimatedLossAmount: 0,
  },
] as const;

export function FefoDatesSandboxView({
  isReadOnly = false,
  initialTenantSchema = "tenant_genesis",
  initialOffsetDays,
  initialScenario,
  onRunSimulation,
  onApplyDateShift,
  onSyncToday,
}: FefoDatesSandboxViewProps) {
  useLanguage();
  const { isDemo } = useMockDataMode();

  // Fecha calendario real del sistema (Hoy)
  const todayIso = useMemo(
    () => new Date().toISOString().split("T")[0] ?? "2026-11-05",
    []
  );

  // Formato chileno/latino para Header: DD/MM/AAAA
  const todayFormatted = useMemo(() => {
    const parts = todayIso.split("-");
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return todayIso;
  }, [todayIso]);

  // Flags de interacción
  const [userInteracted, setUserInteracted] = useState<boolean>(
    Boolean(initialScenario !== undefined || initialOffsetDays !== undefined)
  );

  // Estados interactivos
  const [tenantSchema, setTenantSchema] = useState<string>(initialTenantSchema);
  const [warehouseId, setWarehouseId] = useState<string>("bod-cocina-central");
  const [dryRun, setDryRun] = useState<boolean>(true);
  const [generateSpoilageEvents, setGenerateSpoilageEvents] = useState<boolean>(true);

  // Escenario seleccionado y offset Time-Travel
  const [selectedScenario, setSelectedScenario] = useState<FefoDemoScenarioId>(
    initialScenario ?? "HEALTHY"
  );
  const [offsetDays, setOffsetDays] = useState<number>(initialOffsetDays ?? 0);

  // Resultado de simulación explícita
  const [simResult, setSimResult] = useState<FefoSimulationResponse | null>(null);

  // Estados de proceso
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [isApplyingShift, setIsApplyingShift] = useState<boolean>(false);
  const [isSyncingToday, setIsSyncingToday] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{
    readonly type: "success" | "error" | "info";
    readonly text: string;
  } | null>(null);

  // Modal de confirmación para mutación destructiva en BD
  const [isShiftModalOpen, setIsShiftModalOpen] = useState<boolean>(false);
  const [confirmStaging, setConfirmStaging] = useState<boolean>(false);

  // Filtro de estado en la matriz FEFO
  const [statusFilter, setStatusFilter] = useState<"ALL" | FefoBatchCanonicalStatus>("ALL");

  // Fecha proyectada simulada en tiempo de ejecución
  const simulatedDate = useMemo(() => {
    return shiftIsoDate(todayIso, offsetDays);
  }, [todayIso, offsetDays]);

  // Colección de lotes dinámicos
  const [customBatches, setCustomBatches] = useState<readonly FefoBatchSimulationImpact[] | null>(null);

  // Lotes evaluados en vivo con cero latencia
  const currentBatches = useMemo(() => {
    if (!userInteracted && !simResult) {
      return isDemo ? MOCK_FEFO_BATCHES : [];
    }

    if (customBatches) {
      return customBatches.map((b) =>
        evaluateBatchSimulation(
          {
            batchId: b.batchId,
            productSku: b.productSku,
            productName: b.productName,
            category: b.category,
            warehouseId: b.warehouseId,
            isBuffetBatch: b.isBuffetBatch,
            originalExpiryDate: b.originalExpiryDate,
            stockQuantity: b.stockQuantity,
            unitMeasure: b.unitMeasure,
            unitCost: b.unitCost,
          },
          todayIso,
          offsetDays
        )
      );
    }

    if (!isDemo) {
      return [];
    }

    const baseBatches = generateScenarioBatches(
      selectedScenario,
      todayIso,
      warehouseId
    );

    return baseBatches.map((b) =>
      evaluateBatchSimulation(
        {
          batchId: b.batchId,
          productSku: b.productSku,
          productName: b.productName,
          category: b.category,
          warehouseId: b.warehouseId,
          isBuffetBatch: b.isBuffetBatch,
          originalExpiryDate: b.originalExpiryDate,
          stockQuantity: b.stockQuantity,
          unitMeasure: b.unitMeasure,
          unitCost: b.unitCost,
        },
        todayIso,
        offsetDays
      )
    );
  }, [isDemo, userInteracted, simResult, customBatches, selectedScenario, todayIso, warehouseId, offsetDays]);

  // Resumen consolidado y KPIs en vivo
  const liveSummary = useMemo(() => {
    return summarizeFefoSimulation(
      currentBatches,
      simulatedDate,
      selectedScenario,
      "CLP",
      "USD"
    );
  }, [currentBatches, simulatedDate, selectedScenario]);

  // Valores de KPIs finales
  const kpiTotal = simResult?.totalBatchesEvaluated ?? (userInteracted ? liveSummary.totalBatchesEvaluated : (isDemo ? 4 : 0));
  const kpiOptimal = simResult?.optimalBatchesCount ?? (userInteracted ? (liveSummary.optimalBatchesCount ?? 0) : (isDemo ? 1 : 0));
  const kpiWarning = simResult?.warningBatchesCount ?? (userInteracted ? (liveSummary.warningBatchesCount ?? 0) : (isDemo ? 1 : 0));
  const kpiCritical = simResult?.criticalBatchesCount ?? (userInteracted ? liveSummary.criticalBatchesCount : (isDemo ? 1 : 0));
  const kpiExpired = simResult?.expiredBatchesCount ?? (userInteracted ? liveSummary.expiredBatchesCount : (isDemo ? 1 : 0));
  const kpiRiskAmount = simResult?.totalSpoilageRiskAmount ?? (userInteracted ? liveSummary.totalSpoilageRiskAmount : (isDemo ? 481850 : 0));

  // Lotes filtrados para la tabla
  const displayedBatches = useMemo(() => {
    const list = (simResult?.batches && simResult.batches.length > 0)
      ? simResult.batches
      : currentBatches;

    if (statusFilter === "ALL") return list;
    return list.filter((b) => {
      const canonical = b.canonicalStatus ?? (b.status.toUpperCase() as FefoBatchCanonicalStatus);
      return canonical === statusFilter;
    });
  }, [simResult, currentBatches, statusFilter]);

  // Manejador de cambio de escenario
  const handleSelectScenario = (scenarioId: FefoDemoScenarioId) => {
    setUserInteracted(true);
    setSimResult(null);
    setSelectedScenario(scenarioId);
    setCustomBatches(null);
    const cfg = FEFO_DEMO_SCENARIO_CONFIGS[scenarioId];
    setOffsetDays(cfg.defaultOffsetDays);
    const scenarioTitle = translateKey("platform_admin", `sandbox.fefo.scenario_${scenarioId.toLowerCase()}.title`);
    setFeedbackMessage({
      type: "info",
      text: translateKey("platform_admin", "sandbox.fefo.scenario_activated_feedback", {
        title: scenarioTitle,
        offset: cfg.defaultOffsetDays >= 0 ? `+${cfg.defaultOffsetDays}` : String(cfg.defaultOffsetDays),
      }),
    });
  };

  // Manejador de botones de acceso rápido del Time-Travel Slider
  const handleQuickOffset = (days: number) => {
    setUserInteracted(true);
    setSimResult(null);
    setOffsetDays(days);
  };

  // Manejador de cambio del slider / select
  const handleOffsetChange = (newOffset: number) => {
    setUserInteracted(true);
    setSimResult(null);
    setOffsetDays(newOffset);
  };

  // Sincronización quirúrgica a "Hoy"
  const handleSyncToday = async () => {
    setIsSyncingToday(true);
    setFeedbackMessage(null);
    setUserInteracted(true);

    const payload: FefoSyncTodayRequest = {
      tenantSchema,
      warehouseId,
      recalculateBuffetLots: true,
      dryRun,
      confirmStagingAction: confirmStaging,
    };

    try {
      if (onSyncToday) {
        await onSyncToday(payload);
      } else {
        await syncFefoTodayApi(payload);
      }

      // Restablecer lotes y Time-Travel a Hoy (offset 0)
      const synced = syncBatchesToToday(currentBatches, todayIso, true);
      setCustomBatches(synced);
      setSimResult(null);
      setOffsetDays(0);

      setFeedbackMessage({
        type: "success",
        text: translateKey("platform_admin", "sandbox.fefo.sync_today_success", {
          date: todayFormatted,
        }),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : translateKey("platform_admin", "sandbox.fefo.sync_today_error");
      setFeedbackMessage({ type: "error", text: msg });
    } finally {
      setIsSyncingToday(false);
    }
  };

  // Simulación explícita (Dry-Run API)
  const handleSimulate = async () => {
    setIsSimulating(true);
    setFeedbackMessage(null);
    setUserInteracted(true);

    const config: FefoSimulationRequest = {
      mode: "relative_offset",
      offsetDays,
      targetDateIso: simulatedDate,
      tenantSchema,
      warehouseId,
      affectCategories: ["all"],
      scenarioPreset: selectedScenario,
      dryRun,
      generateSpoilageEvents,
      currency: "CLP",
    };

    try {
      let res: FefoSimulationResponse;
      if (onRunSimulation) {
        res = await onRunSimulation(config);
      } else {
        res = await simulateFefoApi(config);
      }
      setSimResult(res);
      if (res.batches && res.batches.length > 0) {
        setCustomBatches(res.batches);
      }
      setFeedbackMessage({
        type: "success",
        text: translateKey("platform_admin", "sandbox.fefo.simulation_success"),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : translateKey("platform_admin", "sandbox.fefo.simulation_error");
      setFeedbackMessage({ type: "error", text: msg });
    } finally {
      setIsSimulating(false);
    }
  };

  // Aplicar desplazamiento en BD (Apertura de Modal)
  const handleOpenShiftModal = () => {
    if (isReadOnly) return;
    setIsShiftModalOpen(true);
  };

  // Confirmación de desplazamiento real en BD
  const handleConfirmShift = async () => {
    setIsApplyingShift(true);
    setFeedbackMessage(null);

    const shiftPayload: FefoShiftRequest = {
      mode: "relative_offset",
      offsetDays,
      targetDateIso: simulatedDate,
      tenantSchema,
      warehouseId,
      affectCategories: ["all"],
      dryRun: false,
      generateSpoilageEvents,
      recalculateBuffet: true,
      confirmStagingAction: confirmStaging,
    };

    try {
      if (onApplyDateShift) {
        await onApplyDateShift(shiftPayload);
      } else {
        await shiftFefoApi(shiftPayload);
      }
      setIsShiftModalOpen(false);
      setFeedbackMessage({
        type: "success",
        text: translateKey("platform_admin", "sandbox.fefo.shift_success", {
          days: offsetDays,
          tenant: tenantSchema,
        }),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : translateKey("platform_admin", "sandbox.fefo.shift_error");
      setFeedbackMessage({ type: "error", text: msg });
    } finally {
      setIsApplyingShift(false);
    }
  };

  // Mapeo visual de badges de semáforo
  const statusBadgeMap: Record<string, string> = {
    optimal: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    warning: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
    critical: "bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30",
    expired: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30",
    OPTIMAL: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    WARNING: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
    CRITICAL: "bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30",
    EXPIRED: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30",
  };

  return (
    <div
      data-testid="fefo-dates-sandbox-view"
      className="space-y-6 animate-in fade-in duration-300"
    >
      {/* ====================================================================== */}
      {/* 1. HEADER: Fecha Base, Selector de Bodega, Switch Dry-Run y Sync Hoy   */}
      {/* ====================================================================== */}
      <div className="glass-card p-4 sm:p-5 rounded-2xl border border-border bg-card/80 space-y-4 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
              <CalendarClock size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-extrabold text-foreground tracking-tight">
                  {translateKey("platform_admin", "sandbox.fefo.header_title")}
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/30">
                  {translateKey("platform_admin", "sandbox.fefo.subplan_badge")}
                </span>
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-2">
                <span>{translateKey("platform_admin", "sandbox.fefo.today_prefix")}: <strong className="font-mono text-foreground">{todayFormatted}</strong> ({todayIso})</span>
                <span className="inline-block w-1 h-1 rounded-full bg-border" />
                <span>{translateKey("platform_admin", "sandbox.fefo.tenant_prefix")}: <strong className="font-mono text-foreground">{tenantSchema}</strong></span>
              </p>
            </div>
          </div>

          {/* Controles del Header */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Selector de Tenant */}
            <div className="flex items-center gap-1.5">
              <input
                id="fefo-tenant-input"
                data-testid="input-fefo-tenant"
                type="text"
                value={tenantSchema}
                onChange={(e) => setTenantSchema(e.target.value)}
                className="w-28 sm:w-36 px-3 py-2 rounded-xl border border-border bg-background text-foreground font-mono text-xs focus:ring-2 focus:ring-purple-500/40 focus:outline-none min-h-[44px]"
                placeholder={translateKey("platform_admin", "sandbox.fefo.tenant_placeholder")}
                title={translateKey("platform_admin", "sandbox.fefo.tenant_tooltip")}
              />
            </div>

            {/* Selector de Bodega */}
            <div className="flex items-center gap-1.5">
              <Warehouse size={15} className="text-muted-foreground hidden sm:inline" />
              <select
                id="header-warehouse-select"
                data-testid="select-fefo-warehouse"
                value={warehouseId}
                onChange={(e) => setWarehouseId(e.target.value)}
                className="px-3 py-2 rounded-xl border border-border bg-background text-foreground text-xs font-medium focus:ring-2 focus:ring-purple-500/40 focus:outline-none min-h-[44px]"
              >
                <option value="bod-cocina-central">{translateKey("platform_admin", "sandbox.fefo.warehouse_central")}</option>
                <option value="bod-bar">{translateKey("platform_admin", "sandbox.fefo.warehouse_bar")}</option>
                <option value="bod-camara-frio">{translateKey("platform_admin", "sandbox.fefo.warehouse_cold")}</option>
              </select>
            </div>

            {/* Switch de Dry-Run */}
            <label
              htmlFor="cb-fefo-dry-run"
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border bg-background/60 text-xs font-semibold cursor-pointer hover:bg-secondary/40 transition-colors min-h-[44px]"
            >
              <input
                id="cb-fefo-dry-run"
                data-testid="cb-fefo-dry-run"
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                className="rounded border-border text-purple-600 focus:ring-purple-500 h-4 w-4"
              />
              <span className={dryRun ? "text-purple-600 dark:text-purple-400 font-bold" : "text-muted-foreground"}>
                {translateKey("platform_admin", "sandbox.fefo.dry_run_label")}
              </span>
            </label>

            {/* Botón Quirúrgico: Sincronizar Fechas a Hoy */}
            <button
              type="button"
              data-testid="btn-sync-fefo-today"
              onClick={handleSyncToday}
              disabled={isSyncingToday}
              className="touch-target min-h-[44px] inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold text-amber-700 dark:text-amber-300 bg-amber-500/15 border border-amber-500/30 hover:bg-amber-500/25 transition-all shadow-sm disabled:opacity-50"
              title={translateKey("platform_admin", "sandbox.fefo.sync_today_tooltip")}
            >
              <Zap size={15} className={`text-amber-500 ${isSyncingToday ? "animate-spin" : ""}`} />
              <span>
                {isSyncingToday
                  ? translateKey("platform_admin", "sandbox.fefo.btn_sync_today_loading")
                  : translateKey("platform_admin", "sandbox.fefo.btn_sync_today")}
              </span>
            </button>
          </div>
        </div>

        {/* Date Comparison Banner (Mantiene retrocompatibilidad exacta con tests de i18n) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-border/40">
          {/* Real Date Indicator */}
          <div
            data-testid="card-real-date"
            className="p-3.5 rounded-xl border border-border bg-card/60 flex items-center justify-between"
          >
            <div className="space-y-0.5">
              <span className="text-[11px] font-mono uppercase font-bold text-muted-foreground flex items-center gap-1.5">
                <Calendar size={13} className="text-muted-foreground" />
                {translateKey("platform_admin", "sandbox.fefo.real_date_title")}
              </span>
              <div className="text-xl font-extrabold text-foreground font-mono">
                {todayIso}
              </div>
              <span className="text-[11px] text-muted-foreground">
                {translateKey("platform_admin", "sandbox.fefo.real_date_desc")}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-secondary/60 text-muted-foreground border border-border">
              <Clock size={20} />
            </div>
          </div>

          {/* Simulated Time-Warp Date */}
          <div
            data-testid="card-simulated-date"
            className="p-3.5 rounded-xl border border-purple-500/40 bg-purple-500/10 flex items-center justify-between shadow-sm"
          >
            <div className="space-y-0.5">
              <span className="text-[11px] font-mono uppercase font-bold text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                <FastForward size={13} className="text-purple-500" />
                {translateKey("platform_admin", "sandbox.fefo.simulated_date_title")}
              </span>
              <div
                data-testid="simulated-date-display"
                className="text-xl font-extrabold text-purple-600 dark:text-purple-400 font-mono"
              >
                {simulatedDate}
              </div>
              <span className="text-[11px] text-muted-foreground">
                {translateKey("platform_admin", "sandbox.fefo.simulated_date_desc", { days: offsetDays })}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-purple-500/20 text-purple-500 border border-purple-500/30">
              <CalendarClock size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* ====================================================================== */}
      {/* 2. SELECTOR DE ESCENARIOS DE DEMOSTRACIÓN (3 CARDS INTERACTIVAS)        */}
      {/* ====================================================================== */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Flame size={14} className="text-purple-500" />
            {translateKey("platform_admin", "sandbox.fefo.scenarios_title")}
          </h2>
          <span className="text-[11px] text-muted-foreground">
            {translateKey("platform_admin", "sandbox.fefo.scenarios_subtitle")}
          </span>
        </div>

        <div
          data-testid="fefo-scenarios-selector"
          className="grid grid-cols-1 md:grid-cols-3 gap-3.5"
        >
          {/* Card HEALTHY */}
          {(() => {
            const isSelected = selectedScenario === "HEALTHY";
            return (
              <div
                role="button"
                tabIndex={0}
                data-testid="card-scenario-HEALTHY"
                onClick={() => handleSelectScenario("HEALTHY")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectScenario("HEALTHY");
                  }
                }}
                className={`text-left p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-emerald-500/50 ${
                  isSelected
                    ? "bg-emerald-500/10 border-emerald-500 shadow-md shadow-emerald-500/10"
                    : "bg-card/70 border-border hover:border-emerald-500/40 hover:bg-emerald-500/5"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                      <ShieldCheck size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-foreground">
                        {translateKey("platform_admin", "sandbox.fefo.scenario_healthy.title")}
                      </h3>
                      <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                        {translateKey("platform_admin", "sandbox.fefo.scenario_healthy.subtitle")}
                      </span>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white shadow-sm">
                      {translateKey("platform_admin", "sandbox.fefo.scenario_active_badge")}
                    </span>
                  )}
                </div>

                <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                  {translateKey("platform_admin", "sandbox.fefo.scenario_healthy.description")}
                </p>

                {/* Micro barra de distribución porcentual */}
                <div className="space-y-1.5 pt-2 border-t border-border/40 text-[11px] font-mono">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>{translateKey("platform_admin", "sandbox.fefo.scenario_distribution_label")}</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                      {translateKey("platform_admin", "sandbox.fefo.scenario_healthy.distribution_summary")}
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden flex">
                    <div style={{ width: "90%" }} className="bg-emerald-500 h-full" />
                    <div style={{ width: "10%" }} className="bg-amber-500 h-full" />
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Card WARNING */}
          {(() => {
            const isSelected = selectedScenario === "WARNING";
            return (
              <div
                role="button"
                tabIndex={0}
                data-testid="card-scenario-WARNING"
                onClick={() => handleSelectScenario("WARNING")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectScenario("WARNING");
                  }
                }}
                className={`text-left p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-amber-500/50 ${
                  isSelected
                    ? "bg-amber-500/10 border-amber-500 shadow-md shadow-amber-500/10"
                    : "bg-card/70 border-border hover:border-amber-500/40 hover:bg-amber-500/5"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
                      <AlertTriangle size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-foreground">
                        {translateKey("platform_admin", "sandbox.fefo.scenario_warning.title")}
                      </h3>
                      <span className="text-[10px] font-mono text-amber-600 dark:text-amber-400 font-semibold">
                        {translateKey("platform_admin", "sandbox.fefo.scenario_warning.subtitle")}
                      </span>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500 text-white shadow-sm">
                      {translateKey("platform_admin", "sandbox.fefo.scenario_active_badge")}
                    </span>
                  )}
                </div>

                <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                  {translateKey("platform_admin", "sandbox.fefo.scenario_warning.description")}
                </p>

                {/* Micro barra de distribución porcentual */}
                <div className="space-y-1.5 pt-2 border-t border-border/40 text-[11px] font-mono">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>{translateKey("platform_admin", "sandbox.fefo.scenario_distribution_label")}</span>
                    <span className="text-amber-600 dark:text-amber-400 font-bold">
                      {translateKey("platform_admin", "sandbox.fefo.scenario_warning.distribution_summary")}
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden flex">
                    <div style={{ width: "50%" }} className="bg-emerald-500 h-full" />
                    <div style={{ width: "30%" }} className="bg-amber-500 h-full" />
                    <div style={{ width: "20%" }} className="bg-orange-500 h-full" />
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Card CRITICAL */}
          {(() => {
            const isSelected = selectedScenario === "CRITICAL";
            return (
              <div
                role="button"
                tabIndex={0}
                data-testid="card-scenario-CRITICAL"
                onClick={() => handleSelectScenario("CRITICAL")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectScenario("CRITICAL");
                  }
                }}
                className={`text-left p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-red-500/50 ${
                  isSelected
                    ? "bg-red-500/10 border-red-500 shadow-md shadow-red-500/10"
                    : "bg-card/70 border-border hover:border-red-500/40 hover:bg-red-500/5"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30">
                      <Flame size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-foreground">
                        {translateKey("platform_admin", "sandbox.fefo.scenario_critical.title")}
                      </h3>
                      <span className="text-[10px] font-mono text-red-600 dark:text-red-400 font-semibold">
                        {translateKey("platform_admin", "sandbox.fefo.scenario_critical.subtitle")}
                      </span>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500 text-white shadow-sm">
                      {translateKey("platform_admin", "sandbox.fefo.scenario_active_badge")}
                    </span>
                  )}
                </div>

                <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                  {translateKey("platform_admin", "sandbox.fefo.scenario_critical.description")}
                </p>

                {/* Micro barra de distribución porcentual */}
                <div className="space-y-1.5 pt-2 border-t border-border/40 text-[11px] font-mono">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>{translateKey("platform_admin", "sandbox.fefo.scenario_distribution_label")}</span>
                    <span className="text-red-600 dark:text-red-400 font-bold">
                      {translateKey("platform_admin", "sandbox.fefo.scenario_critical.distribution_summary")}
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden flex">
                    <div style={{ width: "25%" }} className="bg-emerald-500 h-full" />
                    <div style={{ width: "25%" }} className="bg-amber-500 h-full" />
                    <div style={{ width: "35%" }} className="bg-orange-500 h-full" />
                    <div style={{ width: "15%" }} className="bg-red-500 h-full" />
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </div>

      {/* ====================================================================== */}
      {/* 3. CONTROL TIME-TRAVEL SLIDER & ACCESOS RÁPIDOS                         */}
      {/* ====================================================================== */}
      <div className="glass-card p-4 sm:p-5 rounded-2xl border border-border bg-card/70 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
              <FastForward className="text-purple-500" size={18} />
              {translateKey("platform_admin", "sandbox.fefo.warp_params_title")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {translateKey("platform_admin", "sandbox.fefo.warp_params_desc")}
            </p>
          </div>

          {/* Selector de modo y botones de acceso rápido */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-mono uppercase text-muted-foreground mr-1 hidden md:inline">
              {translateKey("platform_admin", "sandbox.fefo.quick_offsets_label")}
            </span>
            <button
              type="button"
              data-testid="btn-quick-offset-minus-7"
              onClick={() => handleQuickOffset(-7)}
              className={`touch-target px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all border ${
                offsetDays === -7
                  ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                  : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.quick_offset_minus_7")}
            </button>
            <button
              type="button"
              data-testid="btn-quick-offset-0"
              onClick={() => handleQuickOffset(0)}
              className={`touch-target px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all border ${
                offsetDays === 0
                  ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                  : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.quick_offset_today")}
            </button>
            <button
              type="button"
              data-testid="btn-quick-offset-plus-7"
              onClick={() => handleQuickOffset(7)}
              className={`touch-target px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all border ${
                offsetDays === 7
                  ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                  : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.quick_offset_plus_7")}
            </button>
            <button
              type="button"
              data-testid="btn-quick-offset-plus-15"
              onClick={() => handleQuickOffset(15)}
              className={`touch-target px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all border ${
                offsetDays === 15
                  ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                  : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.quick_offset_plus_15")}
            </button>
            <button
              type="button"
              data-testid="btn-quick-offset-plus-30"
              onClick={() => handleQuickOffset(30)}
              className={`touch-target px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all border ${
                offsetDays === 30
                  ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                  : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.quick_offset_plus_30")}
            </button>
          </div>
        </div>

        {/* Time-Travel Range Slider Interactivo */}
        <div className="space-y-3 pt-2 border-t border-border/40">
          <div className="flex items-center justify-between text-xs">
            <label
              htmlFor="slider-time-travel"
              className="font-medium text-foreground flex items-center gap-1.5"
            >
              <span>{translateKey("platform_admin", "sandbox.fefo.slider_time_shift_label")}</span>
              <span
                data-testid="slider-offset-display"
                className="font-mono font-bold px-2 py-0.5 rounded-md bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/30"
              >
                {offsetDays > 0
                  ? translateKey("platform_admin", "sandbox.fefo.slider_offset_future", { days: offsetDays })
                  : offsetDays < 0
                    ? translateKey("platform_admin", "sandbox.fefo.slider_offset_past", { days: offsetDays })
                    : translateKey("platform_admin", "sandbox.fefo.slider_offset_today")}
              </span>
            </label>

            <span className="text-muted-foreground font-mono text-[11px]">
              {translateKey("platform_admin", "sandbox.fefo.slider_range_info", {
                min: FEFO_TIME_TRAVEL_RANGE.minDays,
                max: FEFO_TIME_TRAVEL_RANGE.maxDays,
              })}
            </span>
          </div>

          <div className="relative py-1">
            <input
              id="slider-time-travel"
              data-testid="slider-time-travel"
              type="range"
              min={FEFO_TIME_TRAVEL_RANGE.minDays}
              max={FEFO_TIME_TRAVEL_RANGE.maxDays}
              step={FEFO_TIME_TRAVEL_RANGE.stepDays}
              value={offsetDays}
              onChange={(e) => handleOffsetChange(Number(e.target.value))}
              className="w-full h-2.5 bg-secondary rounded-lg appearance-none cursor-pointer accent-purple-600 dark:accent-purple-500"
            />
            {/* Ticks indicadores */}
            <div className="flex justify-between text-[10px] font-mono text-muted-foreground mt-1 px-1">
              <span>{translateKey("platform_admin", "sandbox.fefo.tick_audit")}</span>
              <span>{translateKey("platform_admin", "sandbox.fefo.tick_prev_week")}</span>
              <span className="font-bold text-foreground">{translateKey("platform_admin", "sandbox.fefo.tick_today")}</span>
              <span>{translateKey("platform_admin", "sandbox.fefo.tick_plus_15")}</span>
              <span>{translateKey("platform_admin", "sandbox.fefo.tick_plus_30")}</span>
              <span>{translateKey("platform_admin", "sandbox.fefo.tick_projection")}</span>
            </div>
          </div>

          {/* Select de offset para retrocompatibilidad 100% con tests existentes */}
          <div className="pt-2 flex flex-wrap items-center justify-between gap-3 text-xs border-t border-border/30">
            <div className="flex items-center gap-2">
              <label
                htmlFor="offset-days-select"
                className="text-muted-foreground"
              >
                {translateKey("platform_admin", "sandbox.fefo.offset_days_label")}:
              </label>
              <select
                id="offset-days-select"
                data-testid="select-offset-days"
                value={offsetDays}
                onChange={(e) => handleOffsetChange(Number(e.target.value))}
                className="px-2.5 py-1 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-purple-500 focus:outline-none"
              >
                <option value={-30}>{translateKey("platform_admin", "sandbox.fefo.offset_minus_30")}</option>
                <option value={-7}>{translateKey("platform_admin", "sandbox.fefo.offset_minus_7")}</option>
                <option value={0}>{translateKey("platform_admin", "sandbox.fefo.offset_0")}</option>
                <option value={7}>{translateKey("platform_admin", "sandbox.fefo.offset_7")}</option>
                <option value={15}>{translateKey("platform_admin", "sandbox.fefo.offset_15")}</option>
                <option value={30}>{translateKey("platform_admin", "sandbox.fefo.offset_30")}</option>
                <option value={60}>{translateKey("platform_admin", "sandbox.fefo.offset_60")}</option>
                <option value={90}>{translateKey("platform_admin", "sandbox.fefo.offset_90")}</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                id="cb-spoilage-events"
                data-testid="cb-spoilage-events"
                type="checkbox"
                checked={generateSpoilageEvents}
                onChange={(e) => setGenerateSpoilageEvents(e.target.checked)}
                className="rounded border-border text-purple-600 focus:ring-purple-500"
              />
              <label htmlFor="cb-spoilage-events" className="text-muted-foreground cursor-pointer">
                {translateKey("platform_admin", "sandbox.fefo.alerts_label")}
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* ====================================================================== */}
      {/* 4. PANEL DE KPIS DE IMPACTO EN VIVO                                    */}
      {/* ====================================================================== */}
      <div
        data-testid="fefo-summary-panel"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5"
      >
        {/* Total Lotes Evaluados */}
        <div className="p-3.5 rounded-2xl border border-border bg-card/70 space-y-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground font-bold">
            {translateKey("platform_admin", "sandbox.fefo.kpi_total_batches")}
          </span>
          <div
            data-testid="kpi-fefo-total"
            className="text-2xl font-black text-foreground font-mono"
          >
            {kpiTotal}
          </div>
          <span className="text-[11px] text-muted-foreground block truncate">
            {translateKey("platform_admin", "sandbox.fefo.kpi_total_desc")}
          </span>
        </div>

        {/* Óptimos (Verde) */}
        <div className="p-3.5 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 space-y-1">
          <span className="text-[10px] font-mono uppercase text-emerald-600 dark:text-emerald-400 font-bold">
            {translateKey("platform_admin", "sandbox.fefo.kpi_optimal_batches")}
          </span>
          <div
            data-testid="kpi-fefo-optimal"
            className="text-2xl font-black text-emerald-600 dark:text-emerald-400 font-mono"
          >
            {kpiOptimal}
          </div>
          <span className="text-[11px] text-muted-foreground block truncate">
            {translateKey("platform_admin", "sandbox.fefo.kpi_optimal_desc")}
          </span>
        </div>

        {/* Advertencia (Amarillo) */}
        <div className="p-3.5 rounded-2xl border border-amber-500/30 bg-amber-500/10 space-y-1">
          <span className="text-[10px] font-mono uppercase text-amber-600 dark:text-amber-400 font-bold">
            {translateKey("platform_admin", "sandbox.fefo.kpi_warning_batches")}
          </span>
          <div
            data-testid="kpi-fefo-warning"
            className="text-2xl font-black text-amber-600 dark:text-amber-400 font-mono"
          >
            {kpiWarning}
          </div>
          <span className="text-[11px] text-muted-foreground block truncate">
            {translateKey("platform_admin", "sandbox.fefo.kpi_warning_desc")}
          </span>
        </div>

        {/* Críticos (Naranja) */}
        <div className="p-3.5 rounded-2xl border border-orange-500/30 bg-orange-500/10 space-y-1">
          <span className="text-[10px] font-mono uppercase text-orange-600 dark:text-orange-400 font-bold">
            {translateKey("platform_admin", "sandbox.fefo.kpi_critical_batches")}
          </span>
          <div
            data-testid="kpi-fefo-critical"
            className="text-2xl font-black text-orange-600 dark:text-orange-400 font-mono"
          >
            {kpiCritical}
          </div>
          <span className="text-[11px] text-muted-foreground block truncate">
            {translateKey("platform_admin", "sandbox.fefo.kpi_critical_desc")}
          </span>
        </div>

        {/* Caducados (Rojo) */}
        <div className="p-3.5 rounded-2xl border border-red-500/30 bg-red-500/10 space-y-1">
          <span className="text-[10px] font-mono uppercase text-red-600 dark:text-red-400 font-bold">
            {translateKey("platform_admin", "sandbox.fefo.kpi_expired_batches")}
          </span>
          <div
            data-testid="kpi-fefo-expired"
            className="text-2xl font-black text-red-600 dark:text-red-400 font-mono"
          >
            {kpiExpired}
          </div>
          <span className="text-[11px] text-muted-foreground block truncate">
            {translateKey("platform_admin", "sandbox.fefo.kpi_expired_desc")}
          </span>
        </div>

        {/* Pérdida en Riesgo (Moneda CLP) */}
        <div className="p-3.5 rounded-2xl border border-purple-500/30 bg-purple-500/10 space-y-1">
          <span className="text-[10px] font-mono uppercase text-purple-600 dark:text-purple-400 font-bold">
            {translateKey("platform_admin", "sandbox.fefo.kpi_risk_amount")}
          </span>
          <div
            data-testid="kpi-fefo-risk-amount"
            className="text-xl sm:text-2xl font-black text-purple-600 dark:text-purple-400 font-mono truncate"
          >
            {formatMoney(kpiRiskAmount, "CLP")}
          </div>
          <span className="text-[11px] text-muted-foreground block truncate">
            {translateKey("platform_admin", "sandbox.fefo.kpi_risk_desc")}
          </span>
        </div>
      </div>

      {/* ====================================================================== */}
      {/* 5. MATRIZ DE LOTES FEFO (TABLA INTERACTIVA CON SEMÁFOROS)              */}
      {/* ====================================================================== */}
      <div
        data-testid="fefo-batches-table-card"
        className="glass-card rounded-2xl border border-border bg-card/80 overflow-hidden space-y-3 shadow-sm"
      >
        <div className="p-4 pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
              <Warehouse size={16} className="text-purple-500" />
              {translateKey("platform_admin", "sandbox.fefo.matrix_title")}
            </h3>
            <p className="text-xs text-muted-foreground">
              {translateKey("platform_admin", "sandbox.fefo.matrix_desc")}
            </p>
          </div>

          {/* Filtros rápidos por estado */}
          <div className="flex flex-wrap items-center gap-1 text-xs">
            <button
              type="button"
              onClick={() => setStatusFilter("ALL")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-semibold transition-all ${
                statusFilter === "ALL"
                  ? "bg-foreground text-background"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.filter_all", { count: displayedBatches.length })}
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("OPTIMAL")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-semibold transition-all ${
                statusFilter === "OPTIMAL"
                  ? "bg-emerald-500 text-white"
                  : "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.filter_optimal")}
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("WARNING")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-semibold transition-all ${
                statusFilter === "WARNING"
                  ? "bg-amber-500 text-white"
                  : "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.filter_warning")}
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("CRITICAL")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-semibold transition-all ${
                statusFilter === "CRITICAL"
                  ? "bg-orange-500 text-white"
                  : "bg-orange-500/10 text-orange-600 hover:bg-orange-500/20"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.filter_critical")}
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("EXPIRED")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-semibold transition-all ${
                statusFilter === "EXPIRED"
                  ? "bg-red-500 text-white"
                  : "bg-red-500/10 text-red-600 hover:bg-red-500/20"
              }`}
            >
              {translateKey("platform_admin", "sandbox.fefo.filter_expired")}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-secondary/40 border-y border-border/60 text-muted-foreground font-semibold">
              <tr>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_batch_sku")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_product")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_warehouse")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_original_expiry")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_simulated_expiry")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_days_left")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_fefo_status")}</th>
                <th className="px-4 py-3">{translateKey("platform_admin", "sandbox.fefo.table.col_stock")}</th>
                <th className="px-4 py-3 text-right">{translateKey("platform_admin", "sandbox.fefo.table.col_est_loss")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {displayedBatches.map((batch) => {
                const canonical = batch.canonicalStatus ?? (batch.status.toUpperCase() as FefoBatchCanonicalStatus);
                const isExpired = canonical === "EXPIRED";
                const isCritical = canonical === "CRITICAL";

                return (
                  <tr
                    key={batch.batchId}
                    data-testid={`batch-row-${batch.batchId}`}
                    className={`hover:bg-secondary/30 transition-colors ${
                      isExpired ? "bg-red-500/5" : isCritical ? "bg-orange-500/5" : ""
                    }`}
                  >
                    <td className="px-4 py-3 font-mono font-medium text-foreground">
                      {batch.batchId}
                      <span className="block text-[10px] text-muted-foreground">
                        {batch.productSku}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-foreground flex items-center gap-1.5">
                        <span>{batch.productName}</span>
                        {batch.isBuffetBatch && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/30">
                            {translateKey("platform_admin", "sandbox.fefo.tag_buffet")}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {batch.category ?? translateKey("platform_admin", "sandbox.fefo.default_category")}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground text-[11px]">
                      {batch.warehouseId ?? warehouseId}
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground">
                      {batch.originalExpiryDate}
                    </td>
                    <td className="px-4 py-3 font-mono text-purple-600 dark:text-purple-400 font-semibold">
                      {batch.simulatedExpiryDate}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] ${
                          canonical === "OPTIMAL"
                            ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                            : canonical === "WARNING"
                              ? "text-amber-600 dark:text-amber-400 bg-amber-500/10"
                              : canonical === "CRITICAL"
                                ? "text-orange-600 dark:text-orange-400 bg-orange-500/10"
                                : "text-red-600 dark:text-red-400 bg-red-500/10"
                        }`}
                      >
                        {batch.daysToExpiration}{translateKey("platform_admin", "sandbox.fefo.days_unit")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold border ${
                          statusBadgeMap[canonical]
                        }`}
                      >
                        {translateKey("platform_admin", `sandbox.fefo.status.${canonical.toLowerCase()}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {batch.stockQuantity} {batch.unitMeasure}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-right text-foreground">
                      {formatMoney(batch.estimatedLossAmount, "CLP")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Feedback Message */}
        {feedbackMessage && (
          <div
            data-testid="fefo-feedback-message"
            className={`mx-4 my-2 p-3 rounded-xl border text-xs flex items-center gap-2 ${
              feedbackMessage.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
                : feedbackMessage.type === "error"
                  ? "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300"
                  : "bg-purple-500/10 border-purple-500/30 text-purple-700 dark:text-purple-300"
            }`}
          >
            {feedbackMessage.type === "success" ? (
              <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
            ) : feedbackMessage.type === "error" ? (
              <AlertCircle size={16} className="text-red-500 shrink-0" />
            ) : (
              <Info size={16} className="text-purple-500 shrink-0" />
            )}
            <span className="font-medium">{feedbackMessage.text}</span>
          </div>
        )}

        {/* Action Controls con RBAC */}
        <div className="p-4 border-t border-border/50 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Info size={14} />
            <span>
              {translateKey("platform_admin", "sandbox.fefo.rbac_notice")}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Botón Simular (Dry-Run) */}
            <button
              type="button"
              data-testid="btn-run-fefo-simulation"
              onClick={handleSimulate}
              disabled={isSimulating}
              className="touch-target min-h-[44px] inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border border-purple-500/40 text-purple-600 dark:text-purple-400 hover:bg-purple-500/10 transition-colors disabled:opacity-50"
            >
              <FastForward size={15} />
              <span>
                {isSimulating
                  ? translateKey("platform_admin", "sandbox.fefo.btn_simulating")
                  : translateKey("platform_admin", "sandbox.fefo.btn_simulate")}
              </span>
            </button>

            {/* Botón Aplicar Desplazamiento Real en BD (con confirmación modal) */}
            <Can
              perform="platform_admin.sandbox.manage"
              fallback={
                <span className="text-[11px] text-muted-foreground">
                  {translateKey("platform_admin", "sandbox.fefo.read_only")}
                </span>
              }
            >
              <button
                type="button"
                data-testid="btn-apply-fefo-shift"
                onClick={handleOpenShiftModal}
                disabled={isApplyingShift || isReadOnly}
                className="touch-target min-h-[44px] inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs sm:text-sm font-bold text-white bg-purple-600 hover:bg-purple-700 transition-all shadow-md shadow-purple-600/20 disabled:opacity-50"
              >
                <Play size={15} />
                <span>
                  {isApplyingShift
                    ? translateKey("platform_admin", "sandbox.fefo.btn_apply_shift_loading")
                    : translateKey("platform_admin", "sandbox.fefo.btn_apply_shift")}
                </span>
              </button>
            </Can>
          </div>
        </div>
      </div>

      {/* ====================================================================== */}
      {/* 6. MODAL DE CONFIRMACIÓN PARA CORRIMIENTO REAL EN BD                    */}
      {/* ====================================================================== */}
      {isShiftModalOpen && (
        <div
          data-testid="modal-confirm-shift"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
        >
          <div className="w-full max-w-lg glass-card p-6 rounded-2xl border border-border bg-card shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-purple-500/15 text-purple-600 border border-purple-500/30">
                  <FastForward size={22} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">
                    {translateKey("platform_admin", "sandbox.fefo.modal_shift_title")}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {translateKey("platform_admin", "sandbox.fefo.modal_shift_subtitle")}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsShiftModalOpen(false)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-secondary/50 border border-border text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{translateKey("platform_admin", "sandbox.fefo.modal_tenant_label")}</span>
                <span className="font-mono font-bold text-foreground">{tenantSchema}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{translateKey("platform_admin", "sandbox.fefo.modal_offset_label")}</span>
                <span className="font-mono font-bold text-purple-600 dark:text-purple-400">
                  {offsetDays >= 0 ? `+${offsetDays}` : offsetDays} días
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{translateKey("platform_admin", "sandbox.fefo.modal_simulated_date_label")}</span>
                <span className="font-mono font-bold text-foreground">{simulatedDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{translateKey("platform_admin", "sandbox.fefo.modal_batches_affected_label")}</span>
                <span className="font-mono font-bold text-foreground">
                  {translateKey("platform_admin", "sandbox.fefo.modal_batches_affected_val", { count: kpiTotal })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{translateKey("platform_admin", "sandbox.fefo.modal_risk_amount_label")}</span>
                <span className="font-mono font-bold text-red-600 dark:text-red-400">
                  {formatMoney(kpiRiskAmount, "CLP")}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-xs flex items-start gap-2">
              <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
              <span>
                {translateKey("platform_admin", "sandbox.fefo.modal_warning_text", { tenant: tenantSchema })}
              </span>
            </div>

            {/* Checkbox de confirmación para staging */}
            <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={confirmStaging}
                onChange={(e) => setConfirmStaging(e.target.checked)}
                className="rounded border-border text-purple-600 focus:ring-purple-500"
              />
              <span>{translateKey("platform_admin", "sandbox.fefo.modal_confirm_checkbox")}</span>
            </label>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-border/40">
              <button
                type="button"
                data-testid="btn-cancel-shift-modal"
                onClick={() => setIsShiftModalOpen(false)}
                className="touch-target px-4 py-2 rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              >
                {translateKey("platform_admin", "sandbox.fefo.modal_btn_cancel")}
              </button>
              <button
                type="button"
                data-testid="btn-confirm-shift-modal"
                onClick={handleConfirmShift}
                disabled={isApplyingShift}
                className="touch-target px-5 py-2 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 transition-all shadow-md shadow-purple-600/20 disabled:opacity-50"
              >
                {isApplyingShift
                  ? translateKey("platform_admin", "sandbox.fefo.btn_apply_shift_loading")
                  : translateKey("platform_admin", "sandbox.fefo.modal_btn_confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
