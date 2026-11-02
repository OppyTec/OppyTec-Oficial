import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Bot,
  Brain,
  Check,
  CheckCircle2,
  Clock,
  Cpu,
  Edit3,
  Eye,
  Info,
  Layers,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Star,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Can } from "@/shared/auth/Can";
import { useAiModels } from "./api";
import type {
  AiModelCreatePayload,
  AiModelEngineTier,
  AiModelItem,
  AiModelProvider,
  AiModelUpdatePayload,
} from "./types";

interface FormErrors {
  model_slug?: string;
  display_name?: string;
  provider?: string;
  engine_tier?: string;
  input_cost_per_1m_usd?: string;
  output_cost_per_1m_usd?: string;
  cached_cost_per_1m_usd?: string;
  embedding_cost_per_1m_usd?: string;
  latency_p95_ms?: string;
  min_confidence_score?: string;
  max_context_tokens?: string;
}

export function AiModelsPage() {
  const { t } = useTranslation(["platform_admin", "common"]);

  // Filtros de búsqueda y estado
  const [tierFilter, setTierFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const {
    models,
    rawModels,
    isLoading,
    refetch,
    createModel,
    updateModel,
    deleteModel,
    isCreating,
    isUpdating,
    isDeleting,
  } = useAiModels({
    tier: tierFilter,
    status: statusFilter,
    search: searchQuery,
  });

  // Estados de Modales
  const [isFormModalOpen, setIsFormModalOpen] = useState<boolean>(false);
  const [editingModel, setEditingModel] = useState<AiModelItem | null>(null);

  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState<boolean>(false);
  const [selectedDetailsModel, setSelectedDetailsModel] = useState<AiModelItem | null>(null);

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [modelToDelete, setModelToDelete] = useState<AiModelItem | null>(null);

  // Estados de Formulario (Creación / Edición)
  const [formSlug, setFormSlug] = useState<string>("");
  const [formDisplayName, setFormDisplayName] = useState<string>("");
  const [formProvider, setFormProvider] = useState<AiModelProvider>("google");
  const [formEngineTier, setFormEngineTier] = useState<AiModelEngineTier>("SYSTEM_2_LLM");
  const [formInputCost, setFormInputCost] = useState<string>("0.15");
  const [formOutputCost, setFormOutputCost] = useState<string>("0.60");
  const [formCachedCost, setFormCachedCost] = useState<string>("0.0375");
  const [formEmbeddingCost, setFormEmbeddingCost] = useState<string>("0.00");
  const [formLatency, setFormLatency] = useState<string>("450");
  const [formMinConfidence, setFormMinConfidence] = useState<string>("0.85");
  const [formMaxContext, setFormMaxContext] = useState<string>("128000");
  const [formIsEnabled, setFormIsEnabled] = useState<boolean>(true);
  const [formIsDefault, setFormIsDefault] = useState<boolean>(false);
  const [formIsFallback, setFormIsFallback] = useState<boolean>(false);
  const [formDescription, setFormDescription] = useState<string>("");
  const [errors, setErrors] = useState<FormErrors>({});

  // KPIs
  const activeCount = useMemo(() => rawModels.filter((m) => m.is_enabled && !m.is_deleted).length, [rawModels]);
  const jevCount = useMemo(() => rawModels.filter((m) => m.engine_tier === "SYSTEM_1_JEV" && !m.is_deleted).length, [rawModels]);
  const defaultModel = useMemo(() => rawModels.find((m) => m.is_default && !m.is_deleted), [rawModels]);
  const fallbackModel = useMemo(() => rawModels.find((m) => m.is_fallback && !m.is_deleted), [rawModels]);

  const handleOpenCreate = () => {
    setEditingModel(null);
    setFormSlug("");
    setFormDisplayName("");
    setFormProvider("google");
    setFormEngineTier("SYSTEM_2_LLM");
    setFormInputCost("0.15");
    setFormOutputCost("0.60");
    setFormCachedCost("0.0375");
    setFormEmbeddingCost("0.00");
    setFormLatency("450");
    setFormMinConfidence("0.85");
    setFormMaxContext("128000");
    setFormIsEnabled(true);
    setFormIsDefault(false);
    setFormIsFallback(false);
    setFormDescription("");
    setErrors({});
    setIsFormModalOpen(true);
  };

  const handleOpenEdit = (model: AiModelItem) => {
    setEditingModel(model);
    setFormSlug(model.model_slug);
    setFormDisplayName(model.display_name);
    setFormProvider(model.provider);
    setFormEngineTier(model.engine_tier);
    setFormInputCost(String(model.input_cost_per_1m_usd));
    setFormOutputCost(String(model.output_cost_per_1m_usd));
    setFormCachedCost(String(model.cached_cost_per_1m_usd));
    setFormEmbeddingCost(String(model.embedding_cost_per_1m_usd));
    setFormLatency(String(model.latency_p95_ms));
    setFormMinConfidence(model.min_confidence_score !== null ? String(model.min_confidence_score) : "0.85");
    setFormMaxContext(String(model.max_context_tokens));
    setFormIsEnabled(model.is_enabled);
    setFormIsDefault(model.is_default);
    setFormIsFallback(model.is_fallback);
    setFormDescription(model.description || "");
    setErrors({});
    setIsFormModalOpen(true);
  };

  const handleOpenDetails = (model: AiModelItem) => {
    setSelectedDetailsModel(model);
    setIsDetailsModalOpen(true);
  };

  const handleOpenDelete = (model: AiModelItem) => {
    setModelToDelete(model);
    setIsDeleteModalOpen(true);
  };

  const validateForm = (): boolean => {
    const errs: FormErrors = {};

    if (!formSlug.trim()) {
      errs.model_slug = t("ai_models.validation.slug_required", "El slug del modelo es obligatorio (ej: gemini-3.8-flash)");
    } else if (!/^[a-z0-9_.-]+$/i.test(formSlug.trim())) {
      errs.model_slug = t("ai_models.validation.slug_format", "El slug solo puede contener letras, números, puntos y guiones");
    }

    if (!formDisplayName.trim()) {
      errs.display_name = t("ai_models.validation.display_name_required", "El nombre descriptivo es obligatorio");
    }

    const inputCostNum = parseFloat(formInputCost);
    if (isNaN(inputCostNum) || inputCostNum < 0) {
      errs.input_cost_per_1m_usd = t("ai_models.validation.input_cost_positive", "El costo de entrada debe ser un número >= 0");
    }

    const outputCostNum = parseFloat(formOutputCost);
    if (isNaN(outputCostNum) || outputCostNum < 0) {
      errs.output_cost_per_1m_usd = t("ai_models.validation.output_cost_positive", "El costo de salida debe ser un número >= 0");
    }

    const cachedCostNum = parseFloat(formCachedCost);
    if (isNaN(cachedCostNum) || cachedCostNum < 0) {
      errs.cached_cost_per_1m_usd = t("ai_models.validation.cached_cost_positive", "El costo de caché debe ser un número >= 0");
    }

    const embeddingCostNum = parseFloat(formEmbeddingCost);
    if (isNaN(embeddingCostNum) || embeddingCostNum < 0) {
      errs.embedding_cost_per_1m_usd = t("ai_models.validation.embedding_cost_positive", "El costo de embeddings debe ser un número >= 0");
    }

    const latencyNum = parseInt(formLatency, 10);
    if (isNaN(latencyNum) || latencyNum <= 0) {
      errs.latency_p95_ms = t("ai_models.validation.latency_positive", "La latencia P95 debe ser un entero positivo en milisegundos");
    }

    const maxContextNum = parseInt(formMaxContext, 10);
    if (isNaN(maxContextNum) || maxContextNum <= 0) {
      errs.max_context_tokens = t("ai_models.validation.max_context_positive", "El contexto máximo debe ser un entero positivo");
    }

    if (formEngineTier === "SYSTEM_1_JEV") {
      const minConf = parseFloat(formMinConfidence);
      if (isNaN(minConf) || minConf < 0 || minConf > 1) {
        errs.min_confidence_score = t("ai_models.validation.min_confidence_range", "La confianza mínima JEV debe estar entre 0.00 y 1.00");
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSaveForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      if (editingModel) {
        const updatePayload: AiModelUpdatePayload = {
          display_name: formDisplayName.trim(),
          provider: formProvider,
          engine_tier: formEngineTier,
          input_cost_per_1m_usd: parseFloat(formInputCost),
          cached_cost_per_1m_usd: parseFloat(formCachedCost),
          output_cost_per_1m_usd: parseFloat(formOutputCost),
          embedding_cost_per_1m_usd: parseFloat(formEmbeddingCost),
          latency_p95_ms: parseInt(formLatency, 10),
          min_confidence_score: formEngineTier === "SYSTEM_1_JEV" ? parseFloat(formMinConfidence) : null,
          max_context_tokens: parseInt(formMaxContext, 10),
          is_default: formIsDefault,
          is_fallback: formIsFallback,
          description: formDescription.trim() || null,
          is_enabled: formIsEnabled,
        };
        await updateModel(editingModel.model_slug, updatePayload);
      } else {
        const createPayload: AiModelCreatePayload = {
          model_slug: formSlug.trim().toLowerCase(),
          display_name: formDisplayName.trim(),
          provider: formProvider,
          engine_tier: formEngineTier,
          input_cost_per_1m_usd: parseFloat(formInputCost),
          cached_cost_per_1m_usd: parseFloat(formCachedCost),
          output_cost_per_1m_usd: parseFloat(formOutputCost),
          embedding_cost_per_1m_usd: parseFloat(formEmbeddingCost),
          latency_p95_ms: parseInt(formLatency, 10),
          min_confidence_score: formEngineTier === "SYSTEM_1_JEV" ? parseFloat(formMinConfidence) : null,
          max_context_tokens: parseInt(formMaxContext, 10),
          is_default: formIsDefault,
          is_fallback: formIsFallback,
          description: formDescription.trim() || null,
          is_enabled: formIsEnabled,
        };
        await createModel(createPayload);
      }
      setIsFormModalOpen(false);
    } catch {
      // toast ya notifica en api.ts
    }
  };

  const handleConfirmDelete = async () => {
    if (!modelToDelete) return;
    try {
      await deleteModel(modelToDelete.model_slug);
      setIsDeleteModalOpen(false);
      setModelToDelete(null);
    } catch {
      // toast ya notifica en api.ts
    }
  };

  const getProviderBadge = (provider: string) => {
    const provLower = provider.toLowerCase();
    if (provLower.includes("google")) {
      return (
        <span
          data-testid={`badge-provider-${provider}`}
          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-500 dark:bg-sky-500/20 dark:text-sky-400 border border-sky-500/30"
        >
          <Sparkles className="w-3 h-3" />
          Google
        </span>
      );
    }
    if (provLower.includes("anthropic")) {
      return (
        <span
          data-testid={`badge-provider-${provider}`}
          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400 border border-amber-500/30"
        >
          <Brain className="w-3 h-3" />
          Anthropic
        </span>
      );
    }
    if (provLower.includes("openai")) {
      return (
        <span
          data-testid={`badge-provider-${provider}`}
          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 border border-emerald-500/30"
        >
          <Bot className="w-3 h-3" />
          OpenAI
        </span>
      );
    }
    if (provLower.includes("oppytec")) {
      return (
        <span
          data-testid={`badge-provider-${provider}`}
          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400 border border-purple-500/30"
        >
          <Zap className="w-3 h-3" />
          JEV OppyTec
        </span>
      );
    }
    return (
      <span
        data-testid={`badge-provider-${provider}`}
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-foreground border border-border"
      >
        <Cpu className="w-3 h-3" />
        {provider}
      </span>
    );
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case "SYSTEM_1_JEV":
        return (
          <span
            data-testid="badge-tier-system-1"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30"
          >
            <Zap className="w-3 h-3" />
            System 1 (JEV)
          </span>
        );
      case "SYSTEM_2_LLM":
        return (
          <span
            data-testid="badge-tier-system-2"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-violet-500/15 text-violet-600 dark:text-violet-400 border border-violet-500/30"
          >
            <Brain className="w-3 h-3" />
            System 2 (LLM)
          </span>
        );
      case "EMBEDDING":
        return (
          <span
            data-testid="badge-tier-embedding"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30"
          >
            <Layers className="w-3 h-3" />
            Embedding
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-muted text-foreground">
            {tier}
          </span>
        );
    }
  };

  const getLatencyBadge = (latency: number) => {
    let colorClass = "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
    if (latency > 1000) {
      colorClass = "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30";
    } else if (latency > 400) {
      colorClass = "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30";
    }

    return (
      <span
        data-testid={`badge-latency-${latency}`}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium border ${colorClass}`}
      >
        <Clock className="w-3 h-3" />
        {latency} ms
      </span>
    );
  };

  return (
    <div
      data-testid="page-ai-models"
      className="space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto transition-colors"
    >
      {/* Encabezado Principal */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground flex items-center gap-2">
              <Cpu className="w-7 h-7 text-primary" />
              <span>
                {t("ai_models.title", "Modelos LLM y Motores JEV")}
              </span>
            </h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/25">
              {t("ai_models.header_tag", "FinOps AI & Router")}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("ai_models.subtitle", "Catálogo unificado de modelos de lenguaje (System 2), motores locales deterministas JEV (System 1) y embeddings vectoriales.")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="btn-refresh-ai-models"
            onClick={() => void refetch()}
            disabled={isLoading}
            className="touch-target inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold shadow-sm transition-colors"
            title={t("ai_models.tooltips.refresh", "Refrescar catálogo de modelos")}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-primary" : ""}`} />
            <span className="hidden sm:inline">{t("ai_models.actions.refresh", "Actualizar")}</span>
          </button>

          {/* Botón Nuevo Modelo protegido con RBAC */}
          <Can perform="platform_admin.ai_models.create">
            <button
              type="button"
              data-testid="btn-new-ai-model"
              onClick={handleOpenCreate}
              className="touch-target inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs sm:text-sm shadow-md hover:bg-primary/90 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>{t("ai_models.actions.new_model", "Nuevo Modelo")}</span>
            </button>
          </Can>
        </div>
      </div>

      {/* Tarjetas KPI Resumen */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">{t("ai_models.kpi.total_models", "Modelos Totales")}</span>
            <Layers className="w-4 h-4 text-primary" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">
            {rawModels.filter((m) => !m.is_deleted).length}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{t("ai_models.kpi_subs.total_models", "Catálogo activo y configurado")}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">{t("ai_models.kpi.active_models", "Modelos Habilitados")}</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {activeCount}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{t("ai_models.kpi_subs.active_models", "Disponibles para inferencia")}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">{t("ai_models.kpi.jev_engines", "Motores JEV (System 1)")}</span>
            <Zap className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-cyan-600 dark:text-cyan-400">
            {jevCount}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{t("ai_models.kpi_subs.jev_engines", "Cero costo de proveedor")}</p>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">{t("ai_models.kpi_subs.router", "Enrutador Primario")}</span>
            <Star className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-sm font-bold text-foreground truncate" title={defaultModel?.display_name || t("ai_models.kpi_subs.none", "Ninguno")}>
            {defaultModel?.display_name || t("ai_models.kpi_subs.no_default", "Sin Default")}
          </div>
          <div className="text-xs text-muted-foreground truncate mt-0.5" title={fallbackModel?.display_name || t("ai_models.kpi_subs.no_fallback", "Sin Fallback")}>
            {t("ai_models.kpi_subs.fallback_prefix", "Fallback")}: {fallbackModel?.display_name || t("ai_models.kpi_subs.none", "Ninguno")}
          </div>
        </div>
      </div>

      {/* Barra de Filtros y Búsqueda */}
      <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Buscador */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              data-testid="input-search-ai-models"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("ai_models.filter.search_placeholder", "Buscar por slug, nombre o proveedor...")}
              className="w-full pl-9 pr-4 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Filtro Tier */}
          <div className="w-full sm:w-auto">
            <select
              aria-label="Filtro por Tier"
              data-testid="select-filter-tier"
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="w-full sm:w-48 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="ALL">{t("ai_models.filter.tier_all", "Todos los Tiers")}</option>
              <option value="SYSTEM_1_JEV">{t("ai_models.filter.tier_system_1_jev", "System 1 (JEV Local)")}</option>
              <option value="SYSTEM_2_LLM">{t("ai_models.filter.tier_system_2_llm", "System 2 (LLM Comercial)")}</option>
              <option value="EMBEDDING">{t("ai_models.filter.tier_embedding", "Embeddings Vectoriales")}</option>
            </select>
          </div>

          {/* Filtro Estado */}
          <div className="w-full sm:w-auto">
            <select
              aria-label="Filtro por Estado"
              data-testid="select-filter-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="w-full sm:w-40 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="all">{t("ai_models.filter.status_all", "Todos los Estados")}</option>
              <option value="active">{t("ai_models.filter.status_active", "Solo Activos")}</option>
              <option value="inactive">{t("ai_models.filter.status_inactive", "Solo Inactivos")}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Lista de Modelos: Tabla Desktop + Cards Mobile */}
      {isLoading ? (
        <div data-testid="loading-ai-models" className="py-16 flex flex-col items-center justify-center text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-2" />
          <p className="text-sm">{t("ai_models.loading", "Cargando catálogo de modelos de inferencia...")}</p>
        </div>
      ) : models.length === 0 ? (
        <div data-testid="empty-ai-models" className="py-16 text-center border border-dashed border-border rounded-xl bg-card/50">
          <Cpu className="w-12 h-12 mx-auto text-muted-foreground/60 mb-3" />
          <h3 className="text-base font-semibold text-foreground">{t("ai_models.empty.title", "No se encontraron modelos configurados")}</h3>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
            {t("ai_models.empty.subtitle", "Ajusta los filtros de búsqueda o agrega un nuevo modelo al enrutador.")}
          </p>
        </div>
      ) : (
        <>
          {/* Vista Tabla Desktop (md en adelante) */}
          <div className="hidden md:block overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold">
                  <th className="py-3 px-4">{t("ai_models.table_headers.model", "Modelo / Identificador")}</th>
                  <th className="py-3 px-4">{t("ai_models.table_headers.provider", "Proveedor")}</th>
                  <th className="py-3 px-4">{t("ai_models.table_headers.tier", "Tier")}</th>
                  <th className="py-3 px-4">{t("ai_models.table_headers.tariffs", "Tarifas USD / 1M")}</th>
                  <th className="py-3 px-4">{t("ai_models.table_headers.latency", "Latencia P95")}</th>
                  <th className="py-3 px-4">{t("ai_models.table_headers.router", "Enrutador")}</th>
                  <th className="py-3 px-4">{t("ai_models.table_headers.status", "Estado")}</th>
                  <th className="py-3 px-4 text-right">{t("ai_models.table_headers.actions", "Acciones")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {models.map((model) => (
                  <tr
                    key={model.model_slug}
                    data-testid={`row-ai-model-${model.model_slug}`}
                    className="hover:bg-muted/30 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground">{model.display_name}</div>
                      <div className="font-mono text-xs text-muted-foreground">{model.model_slug}</div>
                    </td>

                    <td className="py-3 px-4">
                      {getProviderBadge(model.provider)}
                    </td>

                    <td className="py-3 px-4">
                      {getTierBadge(model.engine_tier)}
                    </td>

                    <td className="py-3 px-4">
                      {model.engine_tier === "EMBEDDING" ? (
                        <div className="text-xs">
                          <span className="text-muted-foreground">Embed: </span>
                          <span className="font-mono font-semibold text-foreground">
                            ${Number(model.embedding_cost_per_1m_usd).toFixed(4)}
                          </span>
                        </div>
                      ) : (
                        <div className="text-xs space-y-0.5">
                          <div>
                            <span className="text-muted-foreground">In: </span>
                            <span className="font-mono font-semibold text-foreground">
                              ${Number(model.input_cost_per_1m_usd).toFixed(3)}
                            </span>
                            <span className="text-muted-foreground"> / Out: </span>
                            <span className="font-mono font-semibold text-foreground">
                              ${Number(model.output_cost_per_1m_usd).toFixed(3)}
                            </span>
                          </div>
                          {Number(model.cached_cost_per_1m_usd) > 0 && (
                            <div className="text-[11px] text-muted-foreground">
                              Caché: ${Number(model.cached_cost_per_1m_usd).toFixed(4)}
                            </div>
                          )}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      {getLatencyBadge(model.latency_p95_ms)}
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {model.is_default && (
                          <span
                            data-testid={`badge-default-${model.model_slug}`}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                            title={t("ai_models.tooltips.default_model", "Modelo primario por defecto")}
                          >
                            <Star className="w-3 h-3 fill-current" />
                            {t("ai_models.badges.default", "Default")}
                          </span>
                        )}
                        {model.is_fallback && (
                          <span
                            data-testid={`badge-fallback-${model.model_slug}`}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30"
                            title={t("ai_models.tooltips.fallback_model", "Modelo de contingencia y respaldo")}
                          >
                            <Shield className="w-3 h-3" />
                            {t("ai_models.badges.fallback", "Fallback")}
                          </span>
                        )}
                        {!model.is_default && !model.is_fallback && (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      {model.is_enabled ? (
                        <span
                          data-testid={`badge-status-active-${model.model_slug}`}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                        >
                          <Check className="w-3 h-3" />
                          {t("ai_models.badges.active", "Activo")}
                        </span>
                      ) : (
                        <span
                          data-testid={`badge-status-inactive-${model.model_slug}`}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border"
                        >
                          <X className="w-3 h-3" />
                          {t("ai_models.badges.inactive", "Inactivo")}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center justify-end gap-1">
                        {/* Ver Detalles */}
                        <button
                          type="button"
                          data-testid={`btn-view-details-${model.model_slug}`}
                          onClick={() => handleOpenDetails(model)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                          title={t("ai_models.tooltips.view_details", "Ver especificación técnica")}
                        >
                          <Eye className="w-4 h-4" />
                        </button>

                        {/* Editar */}
                        <Can perform="platform_admin.ai_models.update">
                          <button
                            type="button"
                            data-testid={`btn-edit-${model.model_slug}`}
                            onClick={() => handleOpenEdit(model)}
                            className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-muted transition-colors"
                            title={t("ai_models.tooltips.edit", "Editar parámetros y tarifas")}
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                        </Can>

                        {/* Desactivar / Eliminar */}
                        <Can perform="platform_admin.ai_models.delete">
                          <button
                            type="button"
                            data-testid={`btn-delete-${model.model_slug}`}
                            onClick={() => handleOpenDelete(model)}
                            className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-muted transition-colors"
                            title={t("ai_models.tooltips.delete", "Baja lógica (Soft-Delete)")}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </Can>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Vista Cards Mobile (menor a md) */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {models.map((model) => (
              <div
                key={model.model_slug}
                data-testid={`card-ai-model-${model.model_slug}`}
                className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-foreground text-sm">{model.display_name}</h4>
                    <p className="font-mono text-xs text-muted-foreground">{model.model_slug}</p>
                  </div>
                  {getProviderBadge(model.provider)}
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {getTierBadge(model.engine_tier)}
                  {getLatencyBadge(model.latency_p95_ms)}
                  {model.is_default && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/15 text-amber-600 border border-amber-500/30">
                      <Star className="w-3 h-3 fill-current" /> {t("ai_models.badges.default", "Default")}
                    </span>
                  )}
                  {model.is_fallback && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/15 text-blue-600 border border-blue-500/30">
                      <Shield className="w-3 h-3" /> {t("ai_models.badges.fallback", "Fallback")}
                    </span>
                  )}
                </div>

                <div className="text-xs p-2 rounded-lg bg-muted/40 border border-border">
                  {model.engine_tier === "EMBEDDING" ? (
                    <div>
                      Embeddings: <span className="font-mono font-bold">${Number(model.embedding_cost_per_1m_usd).toFixed(4)}</span> / 1M
                    </div>
                  ) : (
                    <div>
                      In: <span className="font-mono font-bold">${Number(model.input_cost_per_1m_usd).toFixed(3)}</span> | Out:{" "}
                      <span className="font-mono font-bold">${Number(model.output_cost_per_1m_usd).toFixed(3)}</span> / 1M
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-border">
                  <div>
                    {model.is_enabled ? (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        <Check className="w-3.5 h-3.5" /> {t("ai_models.badges.active", "Activo")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground">
                        <X className="w-3.5 h-3.5" /> {t("ai_models.badges.inactive", "Inactivo")}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      data-testid={`btn-mobile-details-${model.model_slug}`}
                      onClick={() => handleOpenDetails(model)}
                      className="px-2.5 py-1 rounded-md text-xs font-medium border border-border bg-card text-foreground"
                    >
                      {t("ai_models.modal_extra.close", "Detalles")}
                    </button>
                    <Can perform="platform_admin.ai_models.update">
                      <button
                        type="button"
                        data-testid={`btn-mobile-edit-${model.model_slug}`}
                        onClick={() => handleOpenEdit(model)}
                        className="px-2.5 py-1 rounded-md text-xs font-medium border border-primary/30 text-primary bg-primary/5"
                      >
                        {t("ai_models.actions.edit", "Editar")}
                      </button>
                    </Can>
                    <Can perform="platform_admin.ai_models.delete">
                      <button
                        type="button"
                        data-testid={`btn-mobile-delete-${model.model_slug}`}
                        onClick={() => handleOpenDelete(model)}
                        className="px-2 py-1 rounded-md text-xs font-medium border border-destructive/30 text-destructive bg-destructive/5"
                        title={t("ai_models.tooltips.delete", "Baja lógica (Soft-Delete)")}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </Can>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Modal de Creación / Edición */}
      <AnimatePresence>
        {isFormModalOpen && (
          <div
            data-testid="modal-ai-model-form"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm overflow-y-auto"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-2xl rounded-2xl border border-border bg-card p-5 sm:p-6 shadow-2xl space-y-4 my-8"
            >
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-foreground">
                      {editingModel
                        ? t("ai_models.modal.edit_title", "Editar Parámetros y Tarifas de Modelo")
                        : t("ai_models.modal.create_title", "Registrar Nuevo Modelo de Inferencia")}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {t("ai_models.modal_extra.form_subtitle", "Configuración de tarifas por millón de tokens y enrutamiento inteligente.")}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  data-testid="btn-close-form-modal"
                  onClick={() => setIsFormModalOpen(false)}
                  className="p-1 rounded-lg text-muted-foreground hover:text-foreground"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveForm} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Slug */}
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      {t("ai_models.modal_extra.slug_label_required", "Identificador Canónico (Slug) *")}
                    </label>
                    <input
                      type="text"
                      data-testid="form-input-slug"
                      disabled={!!editingModel}
                      value={formSlug}
                      onChange={(e) => setFormSlug(e.target.value)}
                      placeholder={t("ai_models.modal.slug_placeholder", "ej: gemini-3.8-flash, claude-3-7-sonnet")}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-60"
                    />
                    {errors.model_slug && (
                      <p className="text-xs text-destructive mt-1">{errors.model_slug}</p>
                    )}
                  </div>

                  {/* Display Name */}
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      {t("ai_models.modal_extra.display_name_label_required", "Nombre Visible (Display Name) *")}
                    </label>
                    <input
                      type="text"
                      data-testid="form-input-display-name"
                      value={formDisplayName}
                      onChange={(e) => setFormDisplayName(e.target.value)}
                      placeholder={t("ai_models.modal.display_name_placeholder", "ej: Gemini 3.8 Flash")}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                    {errors.display_name && (
                      <p className="text-xs text-destructive mt-1">{errors.display_name}</p>
                    )}
                  </div>

                  {/* Proveedor */}
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      {t("ai_models.modal_extra.provider_label_required", "Proveedor Tecnológico *")}
                    </label>
                    <select
                      data-testid="form-select-provider"
                      value={formProvider}
                      onChange={(e) => setFormProvider(e.target.value as any)}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    >
                      <option value="google">Google Cloud (Gemini / Embeddings)</option>
                      <option value="anthropic">Anthropic (Claude Sonnet / Haiku)</option>
                      <option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</option>
                      <option value="oppytec">OppyTec (Motor JEV Sub-Simbólico Local)</option>
                      <option value="otro">Otro Proveedor S3/Ollama</option>
                    </select>
                  </div>

                  {/* Engine Tier */}
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      {t("ai_models.modal_extra.engine_tier_label_required", "Tier de Inferencia *")}
                    </label>
                    <select
                      data-testid="form-select-engine-tier"
                      value={formEngineTier}
                      onChange={(e) => setFormEngineTier(e.target.value as any)}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    >
                      <option value="SYSTEM_2_LLM">{t("ai_models.filter.tier_system_2_llm", "System 2 - LLM Comercial")}</option>
                      <option value="SYSTEM_1_JEV">{t("ai_models.filter.tier_system_1_jev", "System 1 - JEV Local (0 Costo)")}</option>
                      <option value="EMBEDDING">{t("ai_models.filter.tier_embedding", "Embeddings Vectoriales")}</option>
                    </select>
                  </div>
                </div>

                {/* Tarifas y Costos USD por 1M de tokens */}
                <div className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-3">
                  <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                    {t("ai_models.modal_extra.finops_tariffs_title", "Tarifas FinOps (USD / 1 Millón de Tokens)")}
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                        {t("ai_models.modal_extra.input_usd", "Input USD")}
                      </label>
                      <input
                        type="number"
                        step="0.0001"
                        data-testid="form-input-input-cost"
                        value={formInputCost}
                        onChange={(e) => setFormInputCost(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs font-mono"
                      />
                      {errors.input_cost_per_1m_usd && (
                        <p className="text-[11px] text-destructive mt-0.5">{errors.input_cost_per_1m_usd}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                        {t("ai_models.modal_extra.output_usd", "Output USD")}
                      </label>
                      <input
                        type="number"
                        step="0.0001"
                        data-testid="form-input-output-cost"
                        value={formOutputCost}
                        onChange={(e) => setFormOutputCost(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs font-mono"
                      />
                      {errors.output_cost_per_1m_usd && (
                        <p className="text-[11px] text-destructive mt-0.5">{errors.output_cost_per_1m_usd}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                        {t("ai_models.modal_extra.cached_usd", "Caché USD")}
                      </label>
                      <input
                        type="number"
                        step="0.0001"
                        data-testid="form-input-cached-cost"
                        value={formCachedCost}
                        onChange={(e) => setFormCachedCost(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs font-mono"
                      />
                      {errors.cached_cost_per_1m_usd && (
                        <p className="text-[11px] text-destructive mt-0.5">{errors.cached_cost_per_1m_usd}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                        {t("ai_models.modal_extra.embed_usd", "Embed USD")}
                      </label>
                      <input
                        type="number"
                        step="0.0001"
                        data-testid="form-input-embedding-cost"
                        value={formEmbeddingCost}
                        onChange={(e) => setFormEmbeddingCost(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs font-mono"
                      />
                      {errors.embedding_cost_per_1m_usd && (
                        <p className="text-[11px] text-destructive mt-0.5">{errors.embedding_cost_per_1m_usd}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Parámetros Operativos */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t("ai_models.modal_extra.latency_p95_required", "Latencia P95 (ms) *")}
                    </label>
                    <input
                      type="number"
                      data-testid="form-input-latency"
                      value={formLatency}
                      onChange={(e) => setFormLatency(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm font-mono"
                    />
                    {errors.latency_p95_ms && (
                      <p className="text-xs text-destructive mt-1">{errors.latency_p95_ms}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t("ai_models.modal_extra.max_context_required", "Max Context Tokens *")}
                    </label>
                    <input
                      type="number"
                      data-testid="form-input-max-context"
                      value={formMaxContext}
                      onChange={(e) => setFormMaxContext(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm font-mono"
                    />
                    {errors.max_context_tokens && (
                      <p className="text-xs text-destructive mt-1">{errors.max_context_tokens}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t("ai_models.modal_extra.min_confidence_jev", "Min Confianza JEV (0-1)")}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      disabled={formEngineTier !== "SYSTEM_1_JEV"}
                      data-testid="form-input-min-confidence"
                      value={formMinConfidence}
                      onChange={(e) => setFormMinConfidence(e.target.value)}
                      placeholder="ej: 0.85"
                      className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm font-mono disabled:opacity-40"
                    />
                    {errors.min_confidence_score && (
                      <p className="text-xs text-destructive mt-1">{errors.min_confidence_score}</p>
                    )}
                  </div>
                </div>

                {/* Flags booleanos */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                  <label className="flex items-center gap-2 p-2.5 rounded-lg border border-border bg-card cursor-pointer hover:bg-muted/40 transition-colors">
                    <input
                      type="checkbox"
                      data-testid="form-checkbox-is-enabled"
                      checked={formIsEnabled}
                      onChange={(e) => setFormIsEnabled(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary w-4 h-4"
                    />
                    <span className="text-xs font-medium text-foreground">{t("ai_models.modal_extra.enabled", "Habilitado")}</span>
                  </label>

                  <label className="flex items-center gap-2 p-2.5 rounded-lg border border-border bg-card cursor-pointer hover:bg-muted/40 transition-colors">
                    <input
                      type="checkbox"
                      data-testid="form-checkbox-is-default"
                      checked={formIsDefault}
                      onChange={(e) => setFormIsDefault(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary w-4 h-4"
                    />
                    <span className="text-xs font-medium text-foreground">{t("ai_models.modal_extra.default_model", "Modelo Default")}</span>
                  </label>

                  <label className="flex items-center gap-2 p-2.5 rounded-lg border border-border bg-card cursor-pointer hover:bg-muted/40 transition-colors">
                    <input
                      type="checkbox"
                      data-testid="form-checkbox-is-fallback"
                      checked={formIsFallback}
                      onChange={(e) => setFormIsFallback(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary w-4 h-4"
                    />
                    <span className="text-xs font-medium text-foreground">{t("ai_models.modal_extra.fallback_model", "Modelo Fallback")}</span>
                  </label>
                </div>

                {/* Descripción */}
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">
                    {t("ai_models.modal_extra.description_role", "Descripción & Rol Operativo")}
                  </label>
                  <textarea
                    rows={2}
                    data-testid="form-textarea-description"
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    placeholder={t("ai_models.modal_extra.description_placeholder", "Detalles sobre capacidades, límites de tasa y casos de uso recomendados...")}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>

                {/* Acciones Modal */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                  <button
                    type="button"
                    data-testid="btn-cancel-form"
                    onClick={() => setIsFormModalOpen(false)}
                    className="px-4 py-2 rounded-lg border border-border bg-card text-foreground font-semibold text-xs sm:text-sm hover:bg-secondary transition-colors"
                  >
                    {t("ai_models.actions.cancel", "Cancelar")}
                  </button>
                  <button
                    type="submit"
                    data-testid="btn-submit-form"
                    disabled={isCreating || isUpdating}
                    className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs sm:text-sm shadow-md hover:bg-primary/90 transition-all disabled:opacity-50"
                  >
                    {(isCreating || isUpdating) && <Loader2 className="w-4 h-4 animate-spin" />}
                    <span>{editingModel ? t("ai_models.modal_extra.update_button", "Actualizar Modelo") : t("ai_models.actions.save", "Guardar Modelo")}</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal de Detalles / Inspección */}
      <AnimatePresence>
        {isDetailsModalOpen && selectedDetailsModel && (
          <div
            data-testid="modal-ai-model-details"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-lg rounded-2xl border border-border bg-card p-5 sm:p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <Info className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-foreground">
                      {selectedDetailsModel.display_name}
                    </h3>
                    <p className="font-mono text-xs text-muted-foreground">
                      {selectedDetailsModel.model_slug}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  data-testid="btn-close-details-modal"
                  onClick={() => setIsDetailsModalOpen(false)}
                  className="p-1 rounded-lg text-muted-foreground hover:text-foreground"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3 text-xs sm:text-sm">
                <div className="flex items-center justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">{t("ai_models.modal_extra.provider_label_sub", "Proveedor:")}</span>
                  <div>{getProviderBadge(selectedDetailsModel.provider)}</div>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">{t("ai_models.modal_extra.tier_label_sub", "Tier de Inferencia:")}</span>
                  <div>{getTierBadge(selectedDetailsModel.engine_tier)}</div>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">{t("ai_models.modal_extra.latency_label_sub", "Latencia P95 Esperada:")}</span>
                  <div>{getLatencyBadge(selectedDetailsModel.latency_p95_ms)}</div>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-border">
                  <span className="text-muted-foreground">{t("ai_models.modal_extra.max_context_label_sub", "Ventana Máxima Contexto:")}</span>
                  <span className="font-mono font-semibold text-foreground">
                    {selectedDetailsModel.max_context_tokens.toLocaleString()} tokens
                  </span>
                </div>
                {selectedDetailsModel.min_confidence_score !== null && (
                  <div className="flex items-center justify-between py-1.5 border-b border-border">
                    <span className="text-muted-foreground">{t("ai_models.modal_extra.confidence_label_sub", "Umbral Confianza JEV:")}</span>
                    <span className="font-mono font-semibold text-cyan-600 dark:text-cyan-400">
                      {(Number(selectedDetailsModel.min_confidence_score) * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                <div className="py-1.5 border-b border-border">
                  <span className="text-muted-foreground block mb-1">{t("ai_models.modal_extra.tariffs_label_sub", "Tarifas por Millón de Tokens:")}</span>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-muted/30 p-2.5 rounded-lg border border-border">
                    <div>Input: ${Number(selectedDetailsModel.input_cost_per_1m_usd).toFixed(4)}</div>
                    <div>Output: ${Number(selectedDetailsModel.output_cost_per_1m_usd).toFixed(4)}</div>
                    <div>Caché: ${Number(selectedDetailsModel.cached_cost_per_1m_usd).toFixed(4)}</div>
                    <div>Embed: ${Number(selectedDetailsModel.embedding_cost_per_1m_usd).toFixed(4)}</div>
                  </div>
                </div>
                <div className="py-1.5">
                  <span className="text-muted-foreground block mb-1">{t("ai_models.modal_extra.description_label_sub", "Descripción:")}</span>
                  <p className="text-foreground text-xs leading-relaxed bg-muted/20 p-2.5 rounded-lg border border-border">
                    {selectedDetailsModel.description || t("ai_models.modal_extra.no_description", "Sin descripción proporcionada.")}
                  </p>
                </div>
              </div>

              <div className="flex justify-end pt-2 border-t border-border">
                <button
                  type="button"
                  data-testid="btn-close-details"
                  onClick={() => setIsDetailsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs sm:text-sm"
                >
                  {t("ai_models.modal_extra.close", "Cerrar")}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal de Confirmación de Eliminación (Soft-Delete) */}
      <AnimatePresence>
        {isDeleteModalOpen && modelToDelete && (
          <div
            data-testid="modal-ai-model-delete-confirm"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-2xl border border-destructive/40 bg-card p-5 sm:p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3 text-destructive">
                <div className="p-2.5 rounded-xl bg-destructive/10 border border-destructive/20">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">
                    {t("ai_models.modal_extra.soft_delete_title", "Desactivar Modelo de Inferencia")}
                  </h3>
                  <p className="font-mono text-xs text-muted-foreground">
                    {modelToDelete.model_slug}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-xs text-foreground space-y-2">
                <p className="font-semibold text-destructive flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  {t("ai_models.modal_extra.soft_delete_audit_header", "Preservación de Auditoría FinOps (Soft-Delete)")}
                </p>
                <p className="text-muted-foreground leading-relaxed">
                  {t("ai_models.modal_extra.soft_delete_audit_text", "Esta acción marcará el modelo como eliminado lógicamente (is_deleted: true). Los registros históricos de consumo de tokens y telemetría FinOps se preservarán intactos para cumplimiento regulatorio.")}
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  data-testid="btn-cancel-delete"
                  onClick={() => setIsDeleteModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-border bg-card text-foreground font-semibold text-xs sm:text-sm hover:bg-secondary transition-colors"
                >
                  {t("ai_models.actions.cancel", "Cancelar")}
                </button>
                <button
                  type="button"
                  data-testid="btn-confirm-delete"
                  disabled={isDeleting}
                  onClick={handleConfirmDelete}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-destructive text-destructive-foreground font-semibold text-xs sm:text-sm shadow-md hover:bg-destructive/90 transition-all disabled:opacity-50"
                >
                  {isDeleting && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>{t("ai_models.actions.confirm_delete", "Confirmar Baja Lógica")}</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
