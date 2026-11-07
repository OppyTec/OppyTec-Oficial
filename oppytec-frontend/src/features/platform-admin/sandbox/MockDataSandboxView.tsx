import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Coffee,
  Database,
  Download,
  FileCode2,
  Flame,
  HardDrive,
  Info,
  Layers,
  type LucideIcon,
  Play,
  RotateCcw,
  Sparkles,
  Trash2,
  UtensilsCrossed,
  Zap,
} from "lucide-react";
import { Can } from "@/shared/auth/Can";
import { translateKey, useLanguage } from "@/shared/i18n";
import { formatMoney } from "@/shared/lib";
import mockDataBackup from "@/shared/mock/mock_data_backup.json";
import {
  MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY,
  MOCK_DATA_RESET_EVENT_NAME,
  useMockDataMode,
} from "@/shared/mock/mockModeStorage";
import type {
  GastronomicPresetId,
  MockDataEntityCategory,
  MockDataGenerationConfig,
  MockDataGenerationProgress,
  MockDataSandboxViewProps,
  MockDataVolume,
} from "../sandboxTypes";
import { executeFactoryReset } from "./api";

export interface MockDataPresetCard {
  readonly id: string;
  readonly title: string;
  readonly subtitle?: string;
  readonly description: string;
  readonly icon: LucideIcon;
  readonly volume: MockDataVolume;
  readonly categories: readonly MockDataEntityCategory[];
  readonly badge: string;
  readonly color: string;
  readonly estimatedVolumeClp: number;
  readonly defaultTenantSchema?: string;
  readonly kpis?: {
    readonly totalSkus: number;
    readonly totalWarehouses: number;
    readonly totalFefoBatches: number;
    readonly totalRecipes: number;
    readonly criticalBatches: number;
  };
}

export const MOCK_DATA_PRESETS: readonly MockDataPresetCard[] = [
  // 4 Presets Canónicos Gastronómicos Multi-Tenant
  {
    id: "fast-food-pollo-king",
    title: "Fast Food & Pollo King",
    description: "Cadena de comida rápida, freidoras, combos express y alta rotación de packaging.",
    icon: Flame,
    volume: "medium",
    categories: ["holdings", "tenants", "users", "catalog", "inventory_fefo", "recipes"],
    badge: "ALTA ROTACIÓN",
    color: "#f59e0b",
    estimatedVolumeClp: 3850000,
    defaultTenantSchema: "tenant_pollo_king_mall",
    kpis: {
      totalSkus: 6,
      totalWarehouses: 3,
      totalFefoBatches: 5,
      totalRecipes: 2,
      criticalBatches: 1,
    },
  },
  {
    id: "carnes-angus-cava",
    title: "Carnes Angus & Cava",
    description: "Steakhouse premium, cortes dry-aged madurados en seco y cava subterránea de vinos.",
    icon: UtensilsCrossed,
    volume: "medium",
    categories: ["holdings", "tenants", "users", "catalog", "inventory_fefo", "recipes"],
    badge: "ALTA GAMA",
    color: "#991b1b",
    estimatedVolumeClp: 8940000,
    defaultTenantSchema: "tenant_angus_vitacura",
    kpis: {
      totalSkus: 6,
      totalWarehouses: 4,
      totalFefoBatches: 6,
      totalRecipes: 2,
      criticalBatches: 1,
    },
  },
  {
    id: "hotel-desayuno-buffet",
    title: "Hotel & Desayuno Buffet",
    description: "Hospitality, estaciones buffet matutino, panadería artesanal y eventos corporativos.",
    icon: Coffee,
    volume: "medium",
    categories: ["holdings", "tenants", "users", "catalog", "inventory_fefo", "recipes"],
    badge: "HOSPITALITY",
    color: "#0284c7",
    estimatedVolumeClp: 4120000,
    defaultTenantSchema: "tenant_hotel_andes_central",
    kpis: {
      totalSkus: 6,
      totalWarehouses: 4,
      totalFefoBatches: 6,
      totalRecipes: 2,
      criticalBatches: 1,
    },
  },
  {
    id: "clean-slate",
    title: "Clean Slate (Base Virgen)",
    description: "Base de datos 100% limpia para verificar Empty States auténticos y onboarding.",
    icon: HardDrive,
    volume: "small",
    categories: ["tenants"],
    badge: "EMPTY STATE",
    color: "#3b82f6",
    estimatedVolumeClp: 0,
    defaultTenantSchema: "tenant_clean_slate_01",
    kpis: {
      totalSkus: 0,
      totalWarehouses: 1,
      totalFefoBatches: 0,
      totalRecipes: 0,
      criticalBatches: 0,
    },
  },
  // Presets Operacionales de Respaldo / Estrés QA
  {
    id: "preset-full-restaurant",
    title: "Restaurante Gourmet Completo",
    description: "Holding, 2 locales, 40+ insumos, lotes FEFO con fechas variadas, recetas, facturas y bolsas de créditos IA.",
    icon: Sparkles,
    volume: "medium",
    categories: ["holdings", "tenants", "users", "catalog", "inventory_fefo", "recipes", "invoices", "finops_credits"],
    badge: "RECOMENDADO",
    color: "#f59e0b",
    estimatedVolumeClp: 2450000,
  },
  {
    id: "preset-finops-isolation",
    title: "FinOps IA & Aislamiento de Créditos",
    description: "Siembra bolsas de créditos IA por tenant/holding y bitácora sintética en llm_request_logs.",
    icon: Sparkles,
    volume: "small",
    categories: ["holdings", "tenants", "finops_credits"],
    badge: "FINOPS IA",
    color: "#8b5cf6",
    estimatedVolumeClp: 450000,
  },
  {
    id: "preset-fefo-stress",
    title: "Estrés FEFO & Proyección de Mermas",
    description: "Inyección de 200+ lotes con fechas próximas a expirar, lotes vencidos y anomalías intencionales.",
    icon: AlertTriangle,
    volume: "large",
    categories: ["inventory_fefo", "catalog"],
    badge: "STRESS QA",
    color: "#ef4444",
    estimatedVolumeClp: 5820000,
  },
  {
    id: "preset-pos-quick",
    title: "Operación POS & Ventas Rápidas",
    description: "Configuración mínima de catálogo con productos combos, recetas y cajeros para flujo de caja.",
    icon: Zap,
    volume: "small",
    categories: ["catalog", "users", "recipes"],
    badge: "LIGERO",
    color: "#10b981",
    estimatedVolumeClp: 890000,
  },
  {
    id: "preset-clean-tenant",
    title: "Tenant Virgen / Esquema Limpio",
    description: "Inicializa únicamente la estructura base multi-tenant sin datos transaccionales.",
    icon: HardDrive,
    volume: "small",
    categories: ["tenants", "users"],
    badge: "LIMPIO",
    color: "#3b82f6",
    estimatedVolumeClp: 0,
  },
] as const;

export function MockDataSandboxView({
  isReadOnly = false,
  initialTenantSchema = "tenant_genesis",
  onExecuteGeneration,
}: MockDataSandboxViewProps) {
  const { language } = useLanguage();
  const { mode: mockMode, isDemo, setMode: setMockMode, toggleMode } = useMockDataMode();

  // Mode: "synthetic_demo" vs "real_isolated_db"
  const [generationMode, setGenerationMode] = useState<"synthetic_demo" | "real_isolated_db">(
    mockMode === "demo" ? "synthetic_demo" : "real_isolated_db"
  );

  // Sync generationMode when mockMode changes
  useEffect(() => {
    setGenerationMode(mockMode === "demo" ? "synthetic_demo" : "real_isolated_db");
  }, [mockMode]);

  const [selectedTenant, setSelectedTenant] = useState<string>(initialTenantSchema);
  const [selectedVolume, setSelectedVolume] = useState<MockDataVolume>("medium");
  const [selectedPreset, setSelectedPreset] = useState<string>("preset-full-restaurant");
  const [preserveExisting, setPreserveExisting] = useState<boolean>(true);
  const [dryRun, setDryRun] = useState<boolean>(true);
  const [injectFefoAnomalies, setInjectFefoAnomalies] = useState<boolean>(true);
  const [isResetModalOpen, setIsResetModalOpen] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  // Status and Progress State
  const [progress, setProgress] = useState<MockDataGenerationProgress>({
    step: translateKey("platform_admin", "sandbox.mock_data.ready_step"),
    percent: 0,
    recordsCreated: {
      holdings: 0,
      tenants: 0,
      users: 0,
      catalog: 0,
      inventory_fefo: 0,
      recipes: 0,
      invoices: 0,
      finops_credits: 0,
    },
    status: "idle",
    errorMessage: null,
    executionDurationMs: 0,
  });

  const dynamicPresets: readonly MockDataPresetCard[] = useMemo(
    () =>
      MOCK_DATA_PRESETS.map((p) => {
        if (p.id === "fast-food-pollo-king") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.fast_food_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.fast_food_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.fast_food_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.fast_food_badge"),
          };
        }
        if (p.id === "carnes-angus-cava") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.steakhouse_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.steakhouse_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.steakhouse_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.steakhouse_badge"),
          };
        }
        if (p.id === "hotel-desayuno-buffet") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.buffet_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.buffet_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.buffet_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.buffet_badge"),
          };
        }
        if (p.id === "clean-slate") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.clean_slate_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.clean_slate_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.clean_slate_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.clean_slate_badge"),
          };
        }
        if (p.id === "preset-full-restaurant") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.full_restaurant_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.full_restaurant_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.full_restaurant_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.full_restaurant_badge"),
          };
        }
        if (p.id === "preset-finops-isolation") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.finops_isolation_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.finops_isolation_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.finops_isolation_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.finops_isolation_badge"),
          };
        }
        if (p.id === "preset-fefo-stress") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.fefo_stress_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.fefo_stress_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.fefo_stress_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.fefo_stress_badge"),
          };
        }
        if (p.id === "preset-pos-quick") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.pos_quick_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.pos_quick_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.pos_quick_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.pos_quick_badge"),
          };
        }
        if (p.id === "preset-clean-tenant") {
          return {
            ...p,
            title: translateKey("platform_admin", "sandbox.mock_data.presets.clean_tenant_title"),
            subtitle: translateKey("platform_admin", "sandbox.mock_data.presets.clean_tenant_subtitle"),
            description: translateKey("platform_admin", "sandbox.mock_data.presets.clean_tenant_desc"),
            badge: translateKey("platform_admin", "sandbox.mock_data.presets.clean_tenant_badge"),
          };
        }
        return p;
      }),
    [language]
  );

  const fallbackPreset = dynamicPresets[0] ?? MOCK_DATA_PRESETS[0]!;
  const activePreset: MockDataPresetCard =
    dynamicPresets.find((p) => p.id === selectedPreset) ?? fallbackPreset;

  const handleApplyPreset = (preset: MockDataPresetCard) => {
    setSelectedPreset(preset.id);
    setSelectedVolume(preset.volume);
    if (preset.defaultTenantSchema) {
      setSelectedTenant(preset.defaultTenantSchema);
    }
    if (preset.id === "preset-fefo-stress" || preset.id === "fast-food-pollo-king") {
      setInjectFefoAnomalies(true);
    }
  };

  const handleModeChange = (targetMode: "synthetic_demo" | "real_isolated_db") => {
    setGenerationMode(targetMode);
    setMockMode(targetMode === "synthetic_demo" ? "demo" : "clean");
  };

  const handleExecute = async () => {
    if (isReadOnly) return;

    const preset = MOCK_DATA_PRESETS.find((p) => p.id === selectedPreset);
    const config: MockDataGenerationConfig = {
      tenantSchema: selectedTenant,
      categories: preset ? preset.categories : ["all"],
      volume: selectedVolume,
      seedRandom: 42,
      preserveExisting,
      dryRun,
      injectFefoAnomalies,
    };

    setProgress({
      step: translateKey("platform_admin", "sandbox.mock_data.starting_step"),
      percent: 15,
      recordsCreated: {
        holdings: 0,
        tenants: 0,
        users: 0,
        catalog: 0,
        inventory_fefo: 0,
        recipes: 0,
        invoices: 0,
        finops_credits: 0,
      },
      status: "generating",
      errorMessage: null,
      executionDurationMs: 0,
    });

    const startTime = Date.now();

    try {
      if (onExecuteGeneration) {
        await onExecuteGeneration(config);
      } else {
        // Simulated execution progress for sandbox UI preview
        await new Promise((resolve) => setTimeout(resolve, 300));
        setProgress((prev) => ({
          ...prev,
          step: translateKey("platform_admin", "sandbox.mock_data.catalog_step"),
          percent: 50,
          recordsCreated: { ...prev.recordsCreated, catalog: 45, users: 4 },
        }));
        await new Promise((resolve) => setTimeout(resolve, 300));
        setProgress((prev) => ({
          ...prev,
          step: translateKey("platform_admin", "sandbox.mock_data.fefo_step"),
          percent: 85,
          recordsCreated: {
            ...prev.recordsCreated,
            catalog: 45,
            users: 4,
            inventory_fefo: 82,
            invoices: 18,
            recipes: 12,
          },
        }));
        await new Promise((resolve) => setTimeout(resolve, 200));
      }

      const duration = Date.now() - startTime;
      setProgress({
        step: dryRun
          ? translateKey("platform_admin", "sandbox.mock_data.success_dry_run")
          : translateKey("platform_admin", "sandbox.mock_data.success_db"),
        percent: 100,
        recordsCreated: {
          holdings: 1,
          tenants: 2,
          users: 6,
          catalog: 45,
          inventory_fefo: 82,
          recipes: 12,
          invoices: 18,
          finops_credits: 20,
        },
        status: "success",
        errorMessage: null,
        executionDurationMs: duration,
      });
    } catch (err: unknown) {
      const duration = Date.now() - startTime;
      const msg = err instanceof Error ? err.message : translateKey("platform_admin", "sandbox.mock_data.failed_step");
      setProgress((prev) => ({
        ...prev,
        step: translateKey("platform_admin", "sandbox.mock_data.failed_step"),
        percent: 100,
        status: "failed",
        errorMessage: msg,
        executionDurationMs: duration,
      }));
    }
  };

  const handleReset = () => {
    setProgress({
      step: translateKey("platform_admin", "sandbox.mock_data.ready_step"),
      percent: 0,
      recordsCreated: {
        holdings: 0,
        tenants: 0,
        users: 0,
        catalog: 0,
        inventory_fefo: 0,
        recipes: 0,
        invoices: 0,
        finops_credits: 0,
      },
      status: "idle",
      errorMessage: null,
      executionDurationMs: 0,
    });
  };

  const handleConfirmFactoryReset = async () => {
    setIsResetting(true);
    try {
      const isCleanPreset =
        selectedPreset === "clean-slate" || selectedPreset === "preset-clean-tenant";
      const targetPresetId: GastronomicPresetId = isCleanPreset
        ? "clean-slate"
        : selectedPreset === "fast-food-pollo-king" ||
            selectedPreset === "carnes-angus-cava" ||
            selectedPreset === "hotel-desayuno-buffet"
          ? selectedPreset
          : "fast-food-pollo-king";

      if (targetPresetId === "clean-slate") {
        setMockMode("clean");
      }

      const res = await executeFactoryReset(selectedTenant, targetPresetId, true);
      setIsResetModalOpen(false);
      setProgress({
        step: translateKey("platform_admin", "sandbox.mock_data.factory_reset_success"),
        percent: 100,
        recordsCreated: {
          holdings: targetPresetId === "clean-slate" ? 0 : 1,
          tenants: targetPresetId === "clean-slate" ? 0 : 1,
          users: targetPresetId === "clean-slate" ? 1 : 2,
          catalog: res.recordsReseeded.products ?? (targetPresetId === "clean-slate" ? 0 : 6),
          inventory_fefo: res.recordsReseeded.batches ?? (targetPresetId === "clean-slate" ? 0 : 6),
          recipes: res.recordsReseeded.recipes ?? (targetPresetId === "clean-slate" ? 0 : 2),
          invoices: 0,
          finops_credits: targetPresetId === "clean-slate" ? 0 : 1,
        },
        status: "success",
        errorMessage: null,
        executionDurationMs: res.durationMs,
      });
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : translateKey("platform_admin", "sandbox.mock_data.factory_reset_error");
      setProgress((prev) => ({
        ...prev,
        status: "failed",
        errorMessage: msg,
      }));
    } finally {
      setIsResetting(false);
    }
  };

  const handleDownloadBackupJson = () => {
    if (typeof window === "undefined") return;
    try {
      const jsonString = JSON.stringify(mockDataBackup, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      if (typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "mock_data_backup.json";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        if (typeof URL.revokeObjectURL === "function") {
          URL.revokeObjectURL(url);
        }
      }
    } catch {
      // Ignore download errors in headless test environments
    }
  };

  const handlePurgeAllCleanSlate = async () => {
    if (isReadOnly) return;
    setIsResetting(true);
    try {
      setSelectedPreset("clean-slate");
      setMockMode("clean");
      if (typeof window !== "undefined" && typeof window.localStorage !== "undefined") {
        try {
          window.localStorage.removeItem(MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY);
        } catch {
          // Ignore storage restrictions
        }
      }
      const res = await executeFactoryReset(selectedTenant, "clean-slate", true);
      setProgress({
        step: translateKey("platform_admin", "sandbox.mock_data.purge_clean_slate_success"),
        percent: 100,
        recordsCreated: {
          holdings: 0,
          tenants: 0,
          users: 1,
          catalog: 0,
          inventory_fefo: 0,
          recipes: 0,
          invoices: 0,
          finops_credits: 0,
        },
        status: "success",
        errorMessage: null,
        executionDurationMs: res.durationMs,
      });
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : translateKey("platform_admin", "sandbox.mock_data.factory_reset_error");
      setProgress((prev) => ({
        ...prev,
        status: "failed",
        errorMessage: msg,
      }));
    } finally {
      setIsResetting(false);
    }
  };

  const handleRestoreFromBackup = async () => {
    if (isReadOnly) return;
    setIsResetting(true);
    try {
      setSelectedPreset("fast-food-pollo-king");
      setMockMode("demo");
      if (typeof window !== "undefined" && typeof window.localStorage !== "undefined") {
        try {
          window.localStorage.setItem(
            MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY,
            JSON.stringify({
              restoredFrom: "mock_data_backup.json",
              version: mockDataBackup.metadata.version,
              restoredAt: new Date().toISOString(),
            })
          );
        } catch {
          // Ignore storage restrictions
        }
        if (typeof window.dispatchEvent === "function") {
          window.dispatchEvent(
            new CustomEvent(MOCK_DATA_RESET_EVENT_NAME, {
              detail: { tenantSchema: selectedTenant, targetPresetId: "fast-food-pollo-king" },
            })
          );
        }
      }
      const res = await executeFactoryReset(selectedTenant, "fast-food-pollo-king", true);
      setProgress({
        step: translateKey("platform_admin", "sandbox.mock_data.restore_backup_success"),
        percent: 100,
        recordsCreated: {
          holdings: mockDataBackup.postgresql_pre_clean_snapshot.holdings.length || 1,
          tenants: mockDataBackup.postgresql_pre_clean_snapshot.tenants.length || 2,
          users: 6,
          catalog: res.recordsReseeded.products ?? 6,
          inventory_fefo: res.recordsReseeded.batches ?? 6,
          recipes: res.recordsReseeded.recipes ?? 2,
          invoices: 18,
          finops_credits: 20,
        },
        status: "success",
        errorMessage: null,
        executionDurationMs: res.durationMs,
      });
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : translateKey("platform_admin", "sandbox.mock_data.factory_reset_error");
      setProgress((prev) => ({
        ...prev,
        status: "failed",
        errorMessage: msg,
      }));
    } finally {
      setIsResetting(false);
    }
  };

  // KPI metadata for selected preset if available
  const activeKpis = activePreset.kpis;

  return (
    <div
      data-testid="mock-data-sandbox-view"
      className="space-y-6 animate-in fade-in duration-300"
    >
      {/* Mode Selector Header Bar & Switch Maestro */}
      <div className="glass-card p-4 sm:p-5 rounded-2xl border border-border bg-card/70 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
              <Database className="text-amber-500" size={20} />
              {translateKey("platform_admin", "sandbox.mock_data.title")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {translateKey("platform_admin", "sandbox.mock_data.subtitle")}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Switch Maestro Reactivo */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-secondary/40 border border-border">
              <button
                type="button"
                data-testid="mock-data-master-switch"
                onClick={toggleMode}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-1 ${
                  isDemo ? "bg-amber-500" : "bg-emerald-600"
                }`}
                title={
                  isDemo
                    ? translateKey("platform_admin", "sandbox.mock_data.master_switch_title_demo")
                    : translateKey("platform_admin", "sandbox.mock_data.master_switch_title_clean")
                }
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isDemo ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
              <span
                data-testid="mock-mode-badge"
                className={`text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                  isDemo
                    ? "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                    : "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {isDemo
                  ? translateKey("platform_admin", "sandbox.mock_data.master_switch_badge_demo")
                  : translateKey("platform_admin", "sandbox.mock_data.master_switch_badge_clean")}
              </span>
            </div>

            {/* Factory Reset Action Button */}
            <Can perform="platform_admin.sandbox.manage">
              <button
                type="button"
                data-testid="btn-factory-reset"
                onClick={() => setIsResetModalOpen(true)}
                disabled={progress.status === "generating" || isResetting || isReadOnly}
                className="touch-target px-3 py-1.5 rounded-xl border border-red-500/30 text-red-600 dark:text-red-400 bg-red-500/10 hover:bg-red-500/20 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
                title={translateKey("platform_admin", "sandbox.mock_data.factory_reset_btn")}
              >
                <RotateCcw size={14} className={isResetting ? "animate-spin" : ""} />
                <span>{translateKey("platform_admin", "sandbox.mock_data.factory_reset_btn")}</span>
              </button>
            </Can>

            {/* Legacy Mode Selector Tabs */}
            <div
              data-testid="mock-mode-selector"
              className="flex items-center gap-1.5 p-1 rounded-xl bg-secondary/60 border border-border"
            >
              <button
                type="button"
                data-testid="btn-mode-synthetic"
                onClick={() => handleModeChange("synthetic_demo")}
                className={`touch-target px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  generationMode === "synthetic_demo"
                    ? "bg-amber-500 text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {translateKey("platform_admin", "sandbox.mock_data.mode_synthetic")}
              </button>
              <button
                type="button"
                data-testid="btn-mode-isolated-db"
                onClick={() => handleModeChange("real_isolated_db")}
                className={`touch-target px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  generationMode === "real_isolated_db"
                    ? "bg-amber-500 text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {translateKey("platform_admin", "sandbox.mock_data.mode_isolated_db")}
              </button>
            </div>
          </div>
        </div>

        {/* Tenant Schema Input & Volume */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-border/50 text-xs">
          <div>
            <label
              htmlFor="target-tenant-input"
              className="block font-medium text-foreground mb-1"
            >
              {translateKey("platform_admin", "sandbox.mock_data.target_schema")}
            </label>
            <input
              id="target-tenant-input"
              data-testid="input-target-tenant"
              type="text"
              value={selectedTenant}
              onChange={(e) => setSelectedTenant(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground font-mono text-xs focus:ring-1 focus:ring-amber-500 focus:outline-none"
              placeholder="tenant_genesis"
            />
          </div>

          <div>
            <label
              htmlFor="volume-select"
              className="block font-medium text-foreground mb-1"
            >
              {translateKey("platform_admin", "sandbox.mock_data.data_volume")}
            </label>
            <select
              id="volume-select"
              data-testid="select-volume"
              value={selectedVolume}
              onChange={(e) => setSelectedVolume(e.target.value as MockDataVolume)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-amber-500 focus:outline-none"
            >
              <option value="small">{translateKey("platform_admin", "sandbox.mock_data.volume_small")}</option>
              <option value="medium">{translateKey("platform_admin", "sandbox.mock_data.volume_medium")}</option>
              <option value="large">{translateKey("platform_admin", "sandbox.mock_data.volume_large")}</option>
              <option value="stress">{translateKey("platform_admin", "sandbox.mock_data.volume_stress")}</option>
            </select>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              id="cb-preserve-existing"
              data-testid="cb-preserve-existing"
              type="checkbox"
              checked={preserveExisting}
              onChange={(e) => setPreserveExisting(e.target.checked)}
              className="rounded border-border text-amber-500 focus:ring-amber-500"
            />
            <label htmlFor="cb-preserve-existing" className="text-foreground font-medium cursor-pointer">
              {translateKey("platform_admin", "sandbox.mock_data.preserve_existing")}
            </label>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              id="cb-dry-run"
              data-testid="cb-dry-run"
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="rounded border-border text-amber-500 focus:ring-amber-500"
            />
            <label htmlFor="cb-dry-run" className="text-foreground font-medium cursor-pointer">
              {translateKey("platform_admin", "sandbox.mock_data.dry_run")}
            </label>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              id="cb-fefo-anomalies"
              data-testid="cb-fefo-anomalies"
              type="checkbox"
              checked={injectFefoAnomalies}
              onChange={(e) => setInjectFefoAnomalies(e.target.checked)}
              className="rounded border-border text-amber-500 focus:ring-amber-500"
            />
            <label htmlFor="cb-fefo-anomalies" className="text-foreground font-medium cursor-pointer">
              {translateKey("platform_admin", "sandbox.mock_data.inject_fefo_anomalies")}
            </label>
          </div>
        </div>
      </div>

      {/* Master JSON Backup Vault Card (mock_data_backup.json) */}
      <div
        data-testid="mock-data-backup-vault-card"
        className="glass-card p-4 sm:p-5 rounded-2xl border border-border bg-card/70 flex flex-col lg:flex-row lg:items-center justify-between gap-4"
      >
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <FileCode2 size={16} className="text-emerald-500" />
            {translateKey("platform_admin", "sandbox.mock_data.backup_vault_title")}
          </h3>
          <p className="text-xs text-muted-foreground">
            {translateKey("platform_admin", "sandbox.mock_data.backup_vault_desc")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="btn-download-mock-backup-json"
            onClick={handleDownloadBackupJson}
            className="touch-target px-3 py-2 rounded-xl border border-border bg-secondary/50 hover:bg-secondary text-foreground text-xs font-semibold flex items-center gap-1.5 transition-all"
          >
            <Download size={14} />
            <span>{translateKey("platform_admin", "sandbox.mock_data.btn_download_backup")}</span>
          </button>

          <Can perform="platform_admin.sandbox.manage">
            <button
              type="button"
              data-testid="btn-purge-all-clean-slate"
              onClick={handlePurgeAllCleanSlate}
              disabled={progress.status === "generating" || isResetting || isReadOnly}
              className="touch-target px-3 py-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <Trash2 size={14} />
              <span>{translateKey("platform_admin", "sandbox.mock_data.btn_purge_clean_slate")}</span>
            </button>

            <button
              type="button"
              data-testid="btn-restore-mock-backup"
              onClick={handleRestoreFromBackup}
              disabled={progress.status === "generating" || isResetting || isReadOnly}
              className="touch-target px-3 py-2 rounded-xl border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <RotateCcw size={14} />
              <span>{translateKey("platform_admin", "sandbox.mock_data.btn_restore_backup")}</span>
            </button>
          </Can>
        </div>
      </div>

      {/* Selected Preset Detailed Metrics Banner */}
      {activeKpis && (
        <div
          data-testid="selected-preset-metrics-banner"
          className="glass-card p-4 rounded-xl border border-border bg-card/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
        >
          <div className="flex items-center gap-2">
            <div
              className="p-2 rounded-lg"
              style={{
                backgroundColor: `rgba(${activePreset.color === "#f59e0b" ? "245,158,11" : "128,128,128"}, 0.15)`,
                color: activePreset.color,
              }}
            >
              <activePreset.icon size={16} />
            </div>
            <div>
              <span className="font-bold text-foreground block">{activePreset.title}</span>
              <span className="text-[11px] text-muted-foreground font-mono">
                {translateKey("platform_admin", "sandbox.mock_data.schema_prefix")}: {selectedTenant}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center">
            <div className="p-1.5 rounded-lg bg-secondary/30 border border-border/40">
              <span className="block text-[10px] text-muted-foreground font-mono uppercase">
                {translateKey("platform_admin", "sandbox.mock_data.kpi_skus")}
              </span>
              <span data-testid="kpi-metric-skus" className="font-bold text-foreground">
                {activeKpis.totalSkus}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-secondary/30 border border-border/40">
              <span className="block text-[10px] text-muted-foreground font-mono uppercase">
                {translateKey("platform_admin", "sandbox.mock_data.kpi_warehouses")}
              </span>
              <span data-testid="kpi-metric-warehouses" className="font-bold text-foreground">
                {activeKpis.totalWarehouses}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-secondary/30 border border-border/40">
              <span className="block text-[10px] text-muted-foreground font-mono uppercase">
                {translateKey("platform_admin", "sandbox.mock_data.kpi_fefo_batches")}
              </span>
              <span data-testid="kpi-metric-batches" className="font-bold text-foreground">
                {activeKpis.totalFefoBatches}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-secondary/30 border border-border/40">
              <span className="block text-[10px] text-muted-foreground font-mono uppercase">
                {translateKey("platform_admin", "sandbox.mock_data.kpi_recipes")}
              </span>
              <span data-testid="kpi-metric-recipes" className="font-bold text-foreground">
                {activeKpis.totalRecipes}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
              <span className="block text-[10px] font-mono uppercase">
                {translateKey("platform_admin", "sandbox.mock_data.kpi_critical")}
              </span>
              <span data-testid="kpi-metric-critical" className="font-bold">
                {activeKpis.criticalBatches}
              </span>
            </div>
            <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400">
              <span className="block text-[10px] font-mono uppercase">
                {translateKey("platform_admin", "sandbox.mock_data.kpi_stock_value")}
              </span>
              <span data-testid="kpi-metric-stock-value" className="font-bold font-mono">
                {formatMoney(activePreset.estimatedVolumeClp, "CLP")}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Presets Cards Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Layers size={16} />
            {translateKey("platform_admin", "sandbox.mock_data.presets_title")}
          </h3>
          <span className="text-xs text-muted-foreground">
            {translateKey("platform_admin", "sandbox.mock_data.presets_subtitle")}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {dynamicPresets.map((preset) => {
            const isSelected = selectedPreset === preset.id;
            const PresetIcon = preset.icon;
            return (
              <div
                key={preset.id}
                data-testid={`card-preset-${preset.id}`}
                onClick={() => handleApplyPreset(preset)}
                className={`cursor-pointer p-4 rounded-xl border transition-all duration-200 flex flex-col justify-between gap-3 text-left ${
                  isSelected
                    ? "border-amber-500 bg-amber-500/10 shadow-md ring-1 ring-amber-500"
                    : "border-border bg-card/60 hover:border-amber-500/50 hover:bg-card"
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div
                      className="p-2 rounded-lg"
                      style={{
                        backgroundColor: `rgba(${preset.color === "#f59e0b" ? "245,158,11" : "128,128,128"}, 0.15)`,
                        color: preset.color,
                      }}
                    >
                      <PresetIcon size={18} />
                    </div>
                    <span
                      className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded font-bold"
                      style={{
                        backgroundColor: `rgba(${preset.color === "#f59e0b" ? "245,158,11" : "128,128,128"}, 0.15)`,
                        color: preset.color,
                      }}
                    >
                      {preset.badge}
                    </span>
                  </div>
                  <h4 className="font-bold text-sm text-foreground">{preset.title}</h4>
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {preset.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px] text-muted-foreground">
                  <div className="space-y-0.5">
                    <span>{translateKey("platform_admin", "sandbox.mock_data.volume_label", { volume: preset.volume })}</span>
                    <span className="block font-mono text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
                      {formatMoney(preset.estimatedVolumeClp, "CLP")}
                    </span>
                  </div>
                  <span className="font-semibold text-amber-500">
                    {isSelected ? translateKey("platform_admin", "sandbox.mock_data.selected") : translateKey("platform_admin", "sandbox.mock_data.apply")}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Progress & Status Panel */}
      <div
        data-testid="mock-data-status-panel"
        className="glass-card p-5 rounded-2xl border border-border bg-card/70 space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
              <FileCode2 size={16} className="text-amber-500" />
              {translateKey("platform_admin", "sandbox.mock_data.status_title")}
            </h3>
            <p className="text-xs text-muted-foreground">{progress.step}</p>
          </div>

          <div className="flex items-center gap-2">
            {progress.status === "success" && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                <CheckCircle2 size={14} />
                {translateKey("platform_admin", "sandbox.mock_data.completed_in", { duration: progress.executionDurationMs })}
              </span>
            )}
            {progress.status === "failed" && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20">
                <AlertTriangle size={14} />
                {translateKey("platform_admin", "sandbox.mock_data.error_badge")}
              </span>
            )}

            <button
              type="button"
              data-testid="btn-reset-mock-status"
              onClick={handleReset}
              disabled={progress.status === "generating"}
              className="touch-target p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-secondary/60 disabled:opacity-50"
              title={translateKey("platform_admin", "sandbox.mock_data.reset_tooltip")}
            >
              <RotateCcw size={16} />
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-secondary/60 h-2.5 rounded-full overflow-hidden border border-border/40">
          <div
            data-testid="mock-progress-bar"
            className="h-full bg-amber-500 transition-all duration-300 rounded-full"
            style={{ width: `${progress.percent}%` }}
          />
        </div>

        {/* Records Created KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 pt-2 text-center text-xs">
          {Object.entries(progress.recordsCreated).map(([entity, count]) => (
            <div
              key={entity}
              className="p-2 rounded-lg border border-border/60 bg-secondary/20"
            >
              <span className="block text-[10px] font-mono text-muted-foreground uppercase truncate">
                {entity}
              </span>
              <span
                data-testid={`kpi-record-${entity}`}
                className="font-bold text-sm text-foreground"
              >
                {count}
              </span>
            </div>
          ))}

          {/* Financial Volume KPI Formatted with formatMoney */}
          <div className="p-2 rounded-lg border border-amber-500/30 bg-amber-500/10">
            <span className="block text-[10px] font-mono text-amber-600 dark:text-amber-400 uppercase truncate">
              {translateKey("platform_admin", "sandbox.mock_data.est_financial_volume")}
            </span>
            <span
              data-testid="kpi-record-financial-volume"
              className="font-bold text-sm text-amber-600 dark:text-amber-400 font-mono"
            >
              {formatMoney(activePreset?.estimatedVolumeClp ?? 0, "CLP")}
            </span>
          </div>
        </div>

        {/* Execution Error Notice */}
        {progress.errorMessage && (
          <div
            data-testid="mock-error-message"
            className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs"
          >
            {progress.errorMessage}
          </div>
        )}

        {/* Action Trigger Buttons with RBAC */}
        <div className="pt-3 border-t border-border/50 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Info size={14} />
            <span>
              {translateKey("platform_admin", "sandbox.mock_data.rbac_notice")}
            </span>
          </div>

          <Can
            perform="platform_admin.sandbox.manage"
            fallback={
              <button
                type="button"
                disabled
                className="touch-target min-h-[44px] px-5 py-2 rounded-xl text-xs font-semibold bg-secondary text-muted-foreground cursor-not-allowed"
              >
                {translateKey("platform_admin", "sandbox.mock_data.read_only_badge")}
              </button>
            }
          >
            <button
              type="button"
              data-testid="btn-execute-mock-generation"
              onClick={handleExecute}
              disabled={progress.status === "generating" || isReadOnly}
              className="touch-target min-h-[44px] inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-white bg-amber-500 hover:bg-amber-600 transition-all shadow-md shadow-amber-500/20 disabled:opacity-50"
            >
              <Play size={16} />
              <span>
                {progress.status === "generating"
                  ? translateKey("platform_admin", "sandbox.mock_data.btn_generating")
                  : dryRun
                    ? translateKey("platform_admin", "sandbox.mock_data.btn_simulate")
                    : translateKey("platform_admin", "sandbox.mock_data.btn_inject_real")}
              </span>
            </button>
          </Can>
        </div>
      </div>

      {/* Confirmation Modal: Factory Reset */}
      {isResetModalOpen && (
        <div
          data-testid="dialog-factory-reset"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in"
        >
          <div className="glass-card max-w-md w-full p-6 rounded-2xl border border-red-500/30 bg-card shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-red-500">
              <AlertTriangle size={24} />
              <h3 className="font-bold text-base text-foreground">
                {translateKey("platform_admin", "sandbox.mock_data.factory_reset_title")}
              </h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {translateKey("platform_admin", "sandbox.mock_data.factory_reset_confirm", {
                schema: selectedTenant,
              })}
            </p>
            <p className="text-xs text-muted-foreground">
              {translateKey("platform_admin", "sandbox.mock_data.factory_reset_desc")}
            </p>
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <button
                type="button"
                data-testid="btn-cancel-factory-reset"
                onClick={() => setIsResetModalOpen(false)}
                disabled={isResetting}
                className="touch-target px-4 py-2 rounded-xl border border-border text-xs font-semibold hover:bg-secondary/60 text-muted-foreground"
              >
                {translateKey("platform_admin", "sandbox.mock_data.factory_reset_btn_cancel")}
              </button>
              <button
                type="button"
                data-testid="btn-confirm-factory-reset"
                onClick={handleConfirmFactoryReset}
                disabled={isResetting}
                className="touch-target px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow-md shadow-red-600/20 flex items-center gap-2"
              >
                {isResetting && <RotateCcw size={14} className="animate-spin" />}
                <span>
                  {translateKey("platform_admin", "sandbox.mock_data.factory_reset_btn_confirm")}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
