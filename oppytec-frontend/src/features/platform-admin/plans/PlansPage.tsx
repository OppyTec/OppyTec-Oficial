import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Calculator,
  Edit3,
  Layers,
  Loader2,
  Package,
  Plus,
  RefreshCw,
  Save,
  Search,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  TrendingUp,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  calculateCommercialMargin,
  simulateTokensMonthly,
  useAdminPlans,
  useAiCreditPacks,
  useSaaSQuotaPolicy,
} from "../hooks";
import type {
  AiCreditPackCreatePayload,
  AiCreditPackItem,
  SystemPlan,
  SystemPlanCreateRequest,
  SystemPlanUpdateRequest,
} from "../types";

export function PlansPage() {
  const { t } = useTranslation(["platform_admin", "common"]);
  const {
    plans,
    isLoading: isLoadingPlans,
    refetch: refetchPlans,
    createPlan,
    updatePlan,
    deletePlan,
    isCreating,
    isUpdating: isUpdatingPlan,
    isDeleting,
    moduleCatalog,
  } = useAdminPlans();

  const {
    policy,
    isLoading: isLoadingPolicy,
    refetch: refetchPolicy,
    updatePolicy,
    isUpdating: isSavingPolicy,
  } = useSaaSQuotaPolicy();

  const {
    packs: aiPacks,
    isLoading: isLoadingAiPacks,
    refetch: refetchAiPacks,
    createPack: createAiPack,
    isCreating: isCreatingAiPack,
  } = useAiCreditPacks();

  // Selector de Pestaña Principal (SaaS Plans vs Paquetes de Créditos IA Add-On)
  const [activeTab, setActiveTab] = useState<"saas-plans" | "ai-packs">(() => {
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      if (sp.get("tab") === "ai-packs") return "ai-packs";
    }
    return "saas-plans";
  });

  const handleTabChange = (newTab: "saas-plans" | "ai-packs") => {
    setActiveTab(newTab);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", newTab);
      window.history.replaceState({}, "", url.toString());
    }
  };

  useEffect(() => {
    const handlePop = () => {
      const sp = new URLSearchParams(window.location.search);
      setActiveTab(sp.get("tab") === "ai-packs" ? "ai-packs" : "saas-plans");
    };
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  // Modales de Paquete de Créditos IA
  const [aiPackModalOpen, setAiPackModalOpen] = useState<boolean>(false);
  const [editingAiPack, setEditingAiPack] = useState<AiCreditPackItem | null>(null);
  const [packName, setPackName] = useState<string>("");
  const [creditsAmount, setCreditsAmount] = useState<number>(5000);
  const [bonusCredits, setBonusCredits] = useState<number>(250);
  const [priceClp, setPriceClp] = useState<number>(44990);
  const [priceUsd, setPriceUsd] = useState<number>(49);
  const [sortOrder, setSortOrder] = useState<number>(1);
  const [isPopular, setIsPopular] = useState<boolean>(false);
  const [isActive, setIsActive] = useState<boolean>(true);
  const [discountBasico, setDiscountBasico] = useState<number>(0);
  const [discountPro, setDiscountPro] = useState<number>(10);
  const [discountEnterprise, setDiscountEnterprise] = useState<number>(20);

  const handleOpenCreateAiPack = () => {
    setEditingAiPack(null);
    setPackName("");
    setCreditsAmount(5000);
    setBonusCredits(250);
    setPriceClp(44990);
    setPriceUsd(49);
    setSortOrder((aiPacks?.length || 0) + 1);
    setIsPopular(false);
    setIsActive(true);
    setDiscountBasico(0);
    setDiscountPro(10);
    setDiscountEnterprise(20);
    setAiPackModalOpen(true);
  };

  const handleOpenEditAiPack = (pack: AiCreditPackItem) => {
    setEditingAiPack(pack);
    setPackName(pack.pack_name);
    setCreditsAmount(Number(pack.credits_amount) || 0);
    setBonusCredits(Number(pack.bonus_credits) || 0);
    setPriceClp(Number(pack.price_clp) || 0);
    setPriceUsd(Number(pack.price_usd) || 0);
    setSortOrder(pack.sort_order || 1);
    setIsPopular(pack.is_popular);
    setIsActive(pack.is_active);
    const discounts = pack.plan_tier_discounts || {};
    setDiscountBasico(Number(discounts.plan_basico ?? discounts.basico ?? 0));
    setDiscountPro(Number(discounts.plan_pro ?? discounts.pro ?? 10));
    setDiscountEnterprise(Number(discounts.plan_enterprise ?? discounts.enterprise ?? 20));
    setAiPackModalOpen(true);
  };

  const handleSaveAiPack = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!packName.trim() || creditsAmount <= 0) {
      toast.error(
        t("platform_admin:plans.ai_packs.toasts.error_validation", {
          defaultValue: "Completa el nombre comercial, créditos y precios válidos",
        })
      );
      return;
    }

    try {
      const payload: AiCreditPackCreatePayload = {
        pack_name: packName.trim(),
        credits_amount: Number(creditsAmount),
        bonus_credits: Number(bonusCredits) || 0,
        price_clp: Number(priceClp) || 0,
        price_usd: Number(priceUsd) || 0,
        is_popular: isPopular,
        is_active: isActive,
        sort_order: Number(sortOrder) || 1,
        plan_tier_discounts: {
          plan_basico: Number(discountBasico) || 0,
          plan_pro: Number(discountPro) || 0,
          plan_enterprise: Number(discountEnterprise) || 0,
        },
      };
      await createAiPack(payload);
      setAiPackModalOpen(false);
    } catch {
      // Toast gestionado por el hook
    }
  };

  // Estado del card colapsable de política SaaS
  const [showPolicyCard, setShowPolicyCard] = useState<boolean>(true);

  // Estados locales editables de la Política Global
  const [tokensPerCredit, setTokensPerCredit] = useState<number>(policy.tokens_per_credit || 1000);
  const [defaultMonthlyCredits, setDefaultMonthlyCredits] = useState<number>(
    policy.default_monthly_credits || 2000
  );
  const [creditPriceClp, setCreditPriceClp] = useState<number>(policy.credit_price_clp || 15.0);
  const [creditPriceUsd, setCreditPriceUsd] = useState<number>(policy.credit_price_usd || 0.015);

  // Sincronizar estados locales cuando la política cargue
  useEffect(() => {
    if (policy) {
      setTokensPerCredit(policy.tokens_per_credit);
      setDefaultMonthlyCredits(policy.default_monthly_credits);
      setCreditPriceClp(policy.credit_price_clp);
      setCreditPriceUsd(policy.credit_price_usd);
    }
  }, [policy]);

  // Modales
  const [planModalOpen, setPlanModalOpen] = useState<boolean>(false);
  const [editingPlan, setEditingPlan] = useState<SystemPlan | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState<boolean>(false);
  const [planToDelete, setPlanToDelete] = useState<SystemPlan | null>(null);

  // Form State para Plan
  const [formName, setFormName] = useState<string>("");
  const [formSlug, setFormSlug] = useState<string>("");
  const [formDescription, setFormDescription] = useState<string>("");
  const [formPriceClp, setFormPriceClp] = useState<number>(29990);
  const [formPriceUsd, setFormPriceUsd] = useState<number>(35);
  const [formCredits, setFormCredits] = useState<number>(1000);
  const [formTier, setFormTier] = useState<number>(1);
  const [formMaxUsers, setFormMaxUsers] = useState<number>(5);
  const [formMaxProducts, setFormMaxProducts] = useState<number>(500);
  const [formIsActive, setFormIsActive] = useState<boolean>(true);
  const [formIsPopular, setFormIsPopular] = useState<boolean>(false);
  const [selectedModules, setSelectedModules] = useState<readonly string[]>([]);
  const [moduleSearch, setModuleSearch] = useState<string>("");

  const isLoadingTotal =
    activeTab === "ai-packs"
      ? isLoadingAiPacks
      : isLoadingPlans || isLoadingPolicy;

  // Actualizar todos los datos
  const handleRefresh = async () => {
    if (activeTab === "ai-packs") {
      await refetchAiPacks();
      toast.success(
        t("platform_admin:plans.ai_packs.toasts.refreshed", {
          defaultValue: "Catálogo de paquetes de créditos actualizado",
        })
      );
    } else {
      await Promise.all([refetchPlans(), refetchPolicy()]);
      toast.success(
        t("platform_admin:plans.toasts.refreshed", {
          defaultValue: "Catálogo de planes y política global actualizados",
        })
      );
    }
  };

  // Guardar Política Global de Conversión
  const handleSavePolicy = async () => {
    try {
      await updatePolicy({
        tokens_per_credit: tokensPerCredit,
        default_monthly_credits: defaultMonthlyCredits,
        credit_price_clp: creditPriceClp,
        credit_price_usd: creditPriceUsd,
      });
    } catch {
      // Toast gestionado por onError del hook
    }
  };

  // Apertura modal de creación
  const handleOpenCreate = () => {
    setEditingPlan(null);
    setFormName("");
    setFormSlug("");
    setFormDescription("");
    setFormPriceClp(29990);
    setFormPriceUsd(35);
    setFormCredits(1000);
    setFormTier((plans.length || 0) + 1);
    setFormMaxUsers(5);
    setFormMaxProducts(500);
    setFormIsActive(true);
    setFormIsPopular(false);
    setSelectedModules(["core", "pos", "inventory"]);
    setModuleSearch("");
    setPlanModalOpen(true);
  };

  // Apertura modal de edición
  const handleOpenEdit = (plan: SystemPlan) => {
    setEditingPlan(plan);
    setFormName(plan.name);
    setFormSlug(plan.slug);
    setFormDescription(plan.description || "");
    setFormPriceClp(plan.price_clp);
    setFormPriceUsd(plan.price_usd);
    setFormCredits(plan.monthly_ai_credits);
    setFormTier(plan.tier);
    setFormMaxUsers(plan.max_active_users || 5);
    setFormMaxProducts(plan.max_products || 500);
    setFormIsActive(plan.is_active);
    setFormIsPopular(plan.is_popular);
    setSelectedModules(plan.included_modules || []);
    setModuleSearch("");
    setPlanModalOpen(true);
  };

  // Auto-slug al tipear nombre en modo creación: plan-${slug}
  const handleNameChange = (val: string) => {
    setFormName(val);
    if (!editingPlan) {
      const sanitized = val
        .toLowerCase()
        .trim()
        .replace(/[\s_]+/g, "-")
        .replace(/[^a-z0-9-]/g, "");
      setFormSlug(sanitized ? `plan-${sanitized}`.replace(/^plan-plan-/, "plan-") : "");
    }
  };

  // Toggle de módulos
  const handleToggleModule = (modId: string) => {
    setSelectedModules((prev) =>
      prev.includes(modId) ? prev.filter((m) => m !== modId) : [...prev, modId]
    );
  };

  const handleSelectAllModules = () => {
    setSelectedModules(moduleCatalog.map((m) => m.id));
  };

  const handleDeselectAllModules = () => {
    setSelectedModules([]);
  };

  // Envío del formulario de Plan
  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formSlug.trim()) {
      toast.error(
        t("platform_admin:plans.toasts.validation_error", {
          defaultValue: "El nombre comercial y el slug identificador son obligatorios",
        })
      );
      return;
    }

    try {
      if (editingPlan) {
        const updatePayload: SystemPlanUpdateRequest = {
          name: formName.trim(),
          description: formDescription.trim(),
          tier: Number(formTier) || 1,
          monthly_ai_credits: Number(formCredits) || 0,
          is_popular: formIsPopular,
          is_active: formIsActive,
          max_active_users: Number(formMaxUsers) || 1,
          max_products: Number(formMaxProducts) || 0,
          price_clp: Number(formPriceClp) || 0,
          price_usd: Number(formPriceUsd) || 0,
          included_modules: selectedModules,
        };
        await updatePlan(editingPlan.slug, updatePayload);
      } else {
        const createPayload: SystemPlanCreateRequest = {
          slug: formSlug.trim().toLowerCase(),
          name: formName.trim(),
          tier: Number(formTier) || 1,
          monthly_ai_credits: Number(formCredits) || 0,
          description: formDescription.trim(),
          is_popular: formIsPopular,
          is_active: formIsActive,
          max_active_users: Number(formMaxUsers) || 5,
          max_products: Number(formMaxProducts) || 500,
          max_suppliers: 20,
          max_recipes: 50,
          max_combos: 20,
          max_storage_mb: 1024,
          included_modules: selectedModules,
          anchor_currency: "CLP",
          price_clp: Number(formPriceClp) || 0,
          price_usd: Number(formPriceUsd) || 0,
          auto_convert_fx: true,
        };
        await createPlan(createPayload);
      }
      setPlanModalOpen(false);
    } catch {
      // Toast gestionado por el hook
    }
  };

  // Ejecución de eliminación
  const handleConfirmDelete = async () => {
    if (!planToDelete) return;
    try {
      await deletePlan(planToDelete.slug);
      setDeleteConfirmOpen(false);
      setPlanToDelete(null);
    } catch {
      // Error manejado en hook
    }
  };

  // Módulos filtrados para el selector
  const filteredModules = useMemo(() => {
    const q = moduleSearch.toLowerCase().trim();
    if (!q) return moduleCatalog;
    return moduleCatalog.filter(
      (m) =>
        m.id.toLowerCase().includes(q) ||
        m.label.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q) ||
        m.category.toLowerCase().includes(q)
    );
  }, [moduleCatalog, moduleSearch]);

  // Cálculos reactivos de finanzas y márgenes
  const simulatedTokens = simulateTokensMonthly(defaultMonthlyCredits, tokensPerCredit);
  const costEstimateUsd = (simulatedTokens / 1_000_000) * 0.15; // Estimación base Gemini LLM
  const commercialValueClp = defaultMonthlyCredits * creditPriceClp;
  const marginResult = calculateCommercialMargin(costEstimateUsd, commercialValueClp, 950);

  return (
    <div
      data-testid="plans-page"
      className="p-4 md:p-8 space-y-8 max-w-[1600px] mx-auto animate-in fade-in duration-300"
    >
      {/* 0. SELECTOR DE PESTAÑA PRINCIPAL (SaaS Base vs Paquetes IA Add-On) */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-card/60 p-2 rounded-2xl border border-border/80">
        <div
          role="tablist"
          aria-label="Selector de Planes y Paquetes IA"
          className="flex items-center gap-2"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "saas-plans"}
            data-testid="tab-saas-plans"
            onClick={() => handleTabChange("saas-plans")}
            className={`touch-target min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
              activeTab === "saas-plans"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>
              {t("platform_admin:plans.tabs.saas_plans", {
                defaultValue: "Planes Base del Sistema (SaaS)",
              })}
            </span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "ai-packs"}
            data-testid="tab-ai-packs"
            onClick={() => handleTabChange("ai-packs")}
            className={`touch-target min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
              activeTab === "ai-packs"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>
              {t("platform_admin:plans.tabs.ai_packs", {
                defaultValue: "Paquetes de Créditos IA (Add-On)",
              })}
            </span>
          </button>
        </div>

        <div className="text-xs text-muted-foreground px-2 hidden sm:block">
          {activeTab === "saas-plans"
            ? t("platform_admin:plans.tabs.saas_plans_desc", {
                defaultValue: "Gestión de suscripciones de software mensual/anual de siempre.",
              })
            : t("platform_admin:plans.tabs.ai_packs_desc", {
                defaultValue: "Planes independientes de créditos IA que hacen juego con los planes base.",
              })}
        </div>
      </div>

      {/* 1. CABECERA CANÓNICA Y CONTROLES SUPERIORES */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-2 text-primary font-semibold text-xs uppercase tracking-wider mb-1">
            {activeTab === "saas-plans" ? (
              <Layers className="w-4 h-4" />
            ) : (
              <Sparkles className="w-4 h-4 text-emerald-400" />
            )}
            <span>
              {t("platform_admin:plans.header_pretitle", {
                defaultValue: "Monetización & Suscripciones SaaS",
              })}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            {activeTab === "saas-plans"
              ? t("platform_admin:plans.catalog_title", {
                  defaultValue: "Catálogo de Planes Comerciales & Política SaaS",
                })
              : t("platform_admin:plans.ai_packs.title", {
                  defaultValue: "Paquetes de Créditos IA (Add-Ons Independientes)",
                })}
            <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
              <Sparkles className="w-3 h-3 mr-1" />{" "}
              {t("platform_admin:plans.rate_badge", {
                tokens: tokensPerCredit.toLocaleString("es-CL"),
                defaultValue: `1 Cr = ${tokensPerCredit.toLocaleString("es-CL")} Tokens`,
              })}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {activeTab === "saas-plans"
              ? t("platform_admin:plans.catalog_subtitle", {
                  defaultValue:
                    "Configura los planes de suscripción, módulos incluidos y las cuotas de créditos IA para los clientes de la plataforma",
                })
              : t("platform_admin:plans.ai_packs.subtitle", {
                  defaultValue:
                    "Configura paquetes de recarga acumulables y sin caducidad que ofrecen bonificaciones y descuentos automáticos según el plan base del cliente.",
                })}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {activeTab === "saas-plans" ? (
            <>
              <button
                type="button"
                data-testid="toggle-policy-btn"
                onClick={() => setShowPolicyCard(!showPolicyCard)}
                className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-border bg-secondary/60 hover:bg-secondary px-3.5 py-2 text-xs font-medium text-foreground transition-colors cursor-pointer"
              >
                <Calculator className="w-3.5 h-3.5 text-primary" />
                <span>
                  {showPolicyCard
                    ? t("platform_admin:plans.btn_hide_policy", {
                        defaultValue: "Ocultar Política IA",
                      })
                    : t("platform_admin:plans.btn_show_policy", {
                        defaultValue: "Abrir Política IA",
                      })}
                </span>
              </button>

              <button
                type="button"
                data-testid="refresh-plans-btn"
                onClick={handleRefresh}
                disabled={isLoadingTotal}
                className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-border bg-secondary/60 hover:bg-secondary px-3.5 py-2 text-xs font-medium text-foreground transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 text-primary ${isLoadingTotal ? "animate-spin" : ""}`}
                />
                <span>
                  {t("platform_admin:plans.btn_refresh", {
                    defaultValue: "Actualizar",
                  })}
                </span>
              </button>

              <button
                type="button"
                data-testid="create-plan-btn"
                onClick={handleOpenCreate}
                className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-lg bg-primary hover:bg-primary/90 px-4 py-2 text-xs font-semibold text-primary-foreground shadow-md transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>
                  {t("platform_admin:plans.btn_create_plan", {
                    defaultValue: "Crear Plan",
                  })}
                </span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                data-testid="refresh-plans-btn"
                onClick={handleRefresh}
                disabled={isLoadingTotal}
                className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-border bg-secondary/60 hover:bg-secondary px-3.5 py-2 text-xs font-medium text-foreground transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 text-emerald-400 ${isLoadingTotal ? "animate-spin" : ""}`}
                />
                <span>
                  {t("platform_admin:plans.btn_refresh", {
                    defaultValue: "Actualizar",
                  })}
                </span>
              </button>

              <button
                type="button"
                data-testid="create-ai-pack-btn"
                onClick={handleOpenCreateAiPack}
                className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-lg bg-primary hover:bg-primary/90 px-4 py-2 text-xs font-semibold text-primary-foreground shadow-md transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>
                  {t("platform_admin:plans.ai_packs.btn_create_pack", {
                    defaultValue: "Crear Paquete IA",
                  })}
                </span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* 2. CONTENIDO PESTAÑA: PLANES BASE DEL SISTEMA (SAAS) */}
      {activeTab === "saas-plans" && (
        <>
          {/* CARD COLAPSABLE: CONVERSOR DE CRÉDITOS & POLÍTICA GLOBAL SAAS */}
          <AnimatePresence>
        {showPolicyCard && (
          <motion.div
            data-testid="saas-policy-card"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-5 rounded-2xl bg-gradient-to-r from-card/90 via-card/60 to-primary/5 border border-primary/20 shadow-lg space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/50 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-primary/20 text-primary border border-primary/30 shadow-xs">
                    <Calculator className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">
                      {t("platform_admin:plans.policy.title", {
                        defaultValue: "Conversor de Créditos & Política Global",
                      })}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {t("platform_admin:plans.policy.subtitle", {
                        defaultValue:
                          "Define la equivalencia técnica base y el costo unitario de los créditos para todos los clientes de OppyTec.",
                      })}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  data-testid="save-policy-btn"
                  onClick={handleSavePolicy}
                  disabled={isSavingPolicy}
                  className="touch-target inline-flex min-h-[36px] items-center gap-1.5 rounded-lg bg-primary hover:bg-primary/90 px-3.5 py-1.5 text-xs font-bold text-primary-foreground shadow-md transition-colors cursor-pointer self-start sm:self-auto disabled:opacity-50"
                >
                  {isSavingPolicy ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  <span>
                    {t("platform_admin:plans.policy.btn_save", {
                      defaultValue: "Guardar Política de Conversión",
                    })}
                  </span>
                </button>
              </div>

              {/* Grid de 3 Inputs */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Input 1: Tokens por 1 Crédito */}
                <div className="p-3.5 rounded-xl bg-background/60 border border-border/80 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground flex items-center justify-between">
                    <span>
                      {t("platform_admin:plans.policy.tokens_per_credit_label", {
                        defaultValue: "Tokens por 1 Crédito",
                      })}
                    </span>
                    <span className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono text-emerald-400">
                      {t("platform_admin:plans.policy.base_rate_badge", {
                        defaultValue: "Tasa Base",
                      })}
                    </span>
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      data-testid="input-tokens-per-credit"
                      type="number"
                      min="1"
                      value={tokensPerCredit}
                      onChange={(e) => setTokensPerCredit(Math.max(1, Number(e.target.value)))}
                      className="w-full rounded-md border border-border bg-card px-3 py-1.5 text-sm font-mono font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <span className="text-xs text-muted-foreground font-mono">
                      {t("platform_admin:plans.policy.tokens_unit", {
                        defaultValue: "tokens",
                      })}
                    </span>
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    {t("platform_admin:plans.policy.tokens_desc", {
                      defaultValue: "1.000 tokens ≈ 750 palabras procesadas en español.",
                    })}
                  </p>
                </div>

                {/* Input 2: Créditos Base Mensuales */}
                <div className="p-3.5 rounded-xl bg-background/60 border border-border/80 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground flex items-center justify-between">
                    <span>
                      {t("platform_admin:plans.policy.default_credits_label", {
                        defaultValue: "Créditos Base Mensuales",
                      })}
                    </span>
                    <span className="inline-flex items-center rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-mono text-indigo-400">
                      {t("platform_admin:plans.policy.standard_plan_badge", {
                        defaultValue: "Plan Estándar",
                      })}
                    </span>
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      data-testid="input-default-credits"
                      type="number"
                      min="0"
                      value={defaultMonthlyCredits}
                      onChange={(e) => setDefaultMonthlyCredits(Math.max(0, Number(e.target.value)))}
                      className="w-full rounded-md border border-border bg-card px-3 py-1.5 text-sm font-mono font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <span className="text-xs text-muted-foreground font-mono">
                      {t("platform_admin:plans.policy.credits_unit", {
                        defaultValue: "créditos",
                      })}
                    </span>
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    {t("platform_admin:plans.policy.credits_desc", {
                      tokens: simulatedTokens.toLocaleString("es-CL"),
                      defaultValue: `Equivale a ${simulatedTokens.toLocaleString("es-CL")} tokens mensuales por local.`,
                    })}
                  </p>
                </div>

                {/* Input 3: Precio de Venta (Pack Extra) */}
                <div className="p-3.5 rounded-xl bg-background/60 border border-border/80 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground flex items-center justify-between">
                    <span>
                      {t("platform_admin:plans.policy.price_pack_label", {
                        defaultValue: "Precio Venta (Pack Extra)",
                      })}
                    </span>
                    <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono text-amber-400">
                      {t("platform_admin:plans.policy.monetization_badge", {
                        defaultValue: "Monetización",
                      })}
                    </span>
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      data-testid="input-credit-price-clp"
                      type="number"
                      min="0"
                      step="0.5"
                      value={creditPriceClp}
                      onChange={(e) => setCreditPriceClp(Math.max(0, Number(e.target.value)))}
                      className="w-full rounded-md border border-border bg-card px-3 py-1.5 text-sm font-mono font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <span className="text-xs text-muted-foreground font-mono">
                      {t("platform_admin:plans.policy.clp_per_credit", {
                        defaultValue: "CLP / cr",
                      })}
                    </span>
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    {t("platform_admin:plans.policy.pack_desc", {
                      price: (1000 * creditPriceClp).toLocaleString("es-CL"),
                      defaultValue: `Pack 1.000 créditos = ${(1000 * creditPriceClp).toLocaleString("es-CL")} CLP.`,
                    })}
                  </p>
                </div>
              </div>

              {/* Barra de Rentabilidad & Márgenes */}
              <div className="p-3 rounded-xl bg-secondary/30 border border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <TrendingUp className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    <strong>
                      {t("platform_admin:plans.policy.margin_summary", {
                        defaultValue: "Márgenes del Plan Estándar:",
                      })}
                    </strong>{" "}
                    {t("platform_admin:plans.policy.cost_api_google", {
                      usd: costEstimateUsd.toFixed(3),
                      clp: Math.round(marginResult.costClp),
                      defaultValue: `Costo real API Google: ~$${costEstimateUsd.toFixed(3)} USD (~$${Math.round(marginResult.costClp)} CLP)`,
                    })}{" "}
                    |{" "}
                    {t("platform_admin:plans.policy.commercial_value", {
                      clp: commercialValueClp.toLocaleString("es-CL"),
                      defaultValue: `Valor comercial sugerido: ~$${commercialValueClp.toLocaleString("es-CL")} CLP`,
                    })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-mono font-semibold text-emerald-400">
                    {t("platform_admin:plans.policy.margin_badge", {
                      defaultValue: "Margen Bruto Estimado > 95%",
                    })}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 3. SECCIÓN PRINCIPAL: CATÁLOGO VISUAL DE PLANES */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Package className="w-5 h-5 text-primary" />
              {t("platform_admin:plans.catalog.title", {
                count: plans.length,
                defaultValue: `Planes Comerciales Disponibles (${plans.length})`,
              })}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t("platform_admin:plans.catalog.subtitle", {
                defaultValue:
                  "Configura los niveles de acceso y los módulos que se aprovisionarán automáticamente según el plan contratado.",
              })}
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>
              {t("platform_admin:plans.catalog.modules_count", {
                count: moduleCatalog.length,
                defaultValue: `Módulos del Catálogo: ${moduleCatalog.length} registrados`,
              })}
            </span>
          </div>
        </div>

        {/* Grid Responsive de Planes */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan) => {
            const planTokens = simulateTokensMonthly(plan.monthly_ai_credits, tokensPerCredit);
            const includedCount = plan.included_modules ? plan.included_modules.length : 0;

            return (
              <motion.div
                key={plan.slug}
                data-testid={`plan-card-${plan.slug}`}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`rounded-2xl border transition-all duration-300 flex flex-col justify-between overflow-hidden relative backdrop-blur-md ${
                  plan.is_popular
                    ? "bg-gradient-to-b from-primary/10 via-card to-card border-primary/40 shadow-xl shadow-primary/5 ring-1 ring-primary/30"
                    : "bg-card/80 border-border/80 hover:border-border shadow-md"
                } ${!plan.is_active ? "opacity-60 grayscale-[30%]" : ""}`}
              >
                {/* Banner de Recomendado */}
                {plan.is_popular && (
                  <div className="bg-primary text-primary-foreground text-[10px] font-black uppercase tracking-wider text-center py-1 font-mono">
                    {t("platform_admin:plans.catalog.recommended_banner", {
                      defaultValue: "★ Recomendado para Negocios en Crecimiento",
                    })}
                  </div>
                )}

                <div className="p-6 space-y-5">
                  {/* Encabezado del Plan */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-xl font-bold text-foreground">{plan.name}</h3>
                        <span className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-muted-foreground">
                          {t("platform_admin:plans.catalog.tier", {
                            tier: plan.tier,
                            defaultValue: `Tier ${plan.tier}`,
                          })}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2 min-h-[32px]">
                        {plan.description ||
                          t("platform_admin:plans.catalog.no_description", {
                            defaultValue: "Sin descripción asignada.",
                          })}
                      </p>
                    </div>

                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold shrink-0 ${
                        plan.is_active
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-muted text-muted-foreground border border-border"
                      }`}
                    >
                      {plan.is_active
                        ? t("platform_admin:plans.catalog.status_active", {
                            defaultValue: "Activo",
                          })
                        : t("platform_admin:plans.catalog.status_inactive", {
                            defaultValue: "Inactivo",
                          })}
                    </span>
                  </div>

                  {/* Precios Destacados */}
                  <div className="p-4 rounded-xl bg-background/60 border border-border/60">
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-extrabold text-foreground font-mono">
                        ${plan.price_clp.toLocaleString("es-CL")}
                      </span>
                      <span className="text-xs text-muted-foreground font-medium">
                        {t("platform_admin:plans.catalog.clp_per_month", {
                          defaultValue: "CLP / mes",
                        })}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 font-mono">
                      ≈ ${plan.price_usd.toLocaleString("en-US", { minimumFractionDigits: 1 })} USD
                    </div>
                  </div>

                  {/* Bloque de Créditos de IA */}
                  <div className="p-3.5 rounded-xl bg-primary/5 border border-primary/15 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-foreground flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-primary" />
                        {t("platform_admin:plans.catalog.ai_credits_title", {
                          defaultValue: "Créditos de IA Mensuales",
                        })}
                      </span>
                      <span className="font-mono font-bold text-primary">
                        {plan.monthly_ai_credits.toLocaleString("es-CL")} cr
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground font-mono">
                      {t("platform_admin:plans.catalog.ai_credits_desc", {
                        tokens: planTokens.toLocaleString("es-CL"),
                        defaultValue: `Equivale a ~${planTokens.toLocaleString("es-CL")} tokens procesados al mes.`,
                      })}
                    </p>
                  </div>

                  {/* Lista de Módulos Incluidos */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-muted-foreground">
                        {t("platform_admin:plans.catalog.modules_enabled", {
                          defaultValue: "Módulos Habilitados:",
                        })}
                      </span>
                      <span className="inline-flex items-center rounded-md border border-border px-2 py-0.5 text-[10px] font-mono text-foreground">
                        {t("platform_admin:plans.catalog.modules_ratio", {
                          count: includedCount,
                          total: moduleCatalog.length,
                          defaultValue: `${includedCount} de ${moduleCatalog.length}`,
                        })}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto pr-1">
                      {plan.included_modules && plan.included_modules.length > 0 ? (
                        plan.included_modules.map((modSlug) => {
                          const modInfo = moduleCatalog.find((m) => m.id === modSlug);
                          const label = modInfo ? modInfo.label : modSlug;
                          return (
                            <span
                              key={modSlug}
                              className="inline-flex items-center rounded-md border border-border/50 bg-secondary/60 px-2 py-0.5 text-[10px] text-foreground truncate max-w-[180px]"
                              title={label}
                            >
                              {label}
                            </span>
                          );
                        })
                      ) : (
                        <span className="text-xs text-muted-foreground italic">
                          {t("platform_admin:plans.catalog.no_modules", {
                            defaultValue: "Ningún módulo seleccionado",
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Footer de Tarjeta con Acciones */}
                <div className="p-4 border-t border-border/60 bg-card/40 flex items-center justify-between gap-2">
                  <span className="text-[10px] font-mono text-muted-foreground">
                    slug: <code className="text-foreground">{plan.slug}</code>
                  </span>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      data-testid={`edit-plan-btn-${plan.slug}`}
                      onClick={() => handleOpenEdit(plan)}
                      className="touch-target inline-flex min-h-[32px] items-center gap-1 rounded-md px-2.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>
                        {t("platform_admin:plans.catalog.btn_edit", {
                          defaultValue: "Editar",
                        })}
                      </span>
                    </button>

                    <button
                      type="button"
                      data-testid={`delete-plan-btn-${plan.slug}`}
                      onClick={() => {
                        setPlanToDelete(plan);
                        setDeleteConfirmOpen(true);
                      }}
                      className="touch-target inline-flex min-h-[32px] min-w-[32px] items-center justify-center rounded-md text-xs text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                      title={t("platform_admin:plans.catalog.btn_delete_title", {
                        defaultValue: "Eliminar Plan",
                      })}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
      </>
      )}

      {/* 3. CONTENIDO PESTAÑA: PAQUETES DE CRÉDITOS IA (ADD-ON) */}
      {activeTab === "ai-packs" && (
        <div data-testid="ai-packs-section" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-emerald-400" />
                <span>
                  {t("platform_admin:plans.ai_packs.title", {
                    defaultValue: "Paquetes de Créditos IA (Add-Ons Independientes)",
                  })}
                </span>
                <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 text-xs font-mono font-medium text-emerald-400">
                  {aiPacks?.length || 0} configurados
                </span>
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("platform_admin:plans.ai_packs.subtitle", {
                  defaultValue:
                    "Configura paquetes de recarga acumulables y sin caducidad que ofrecen bonificaciones y descuentos automáticos según el plan base del cliente.",
                })}
              </p>
            </div>
          </div>

          {/* Grid de Paquetes IA */}
          <div
            data-testid="ai-packs-grid"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {aiPacks?.map((pack) => {
              const totalCreds =
                Number(pack.total_credits) ||
                Number(pack.credits_amount) + Number(pack.bonus_credits || 0);
              const unitCostUsd =
                totalCreds > 0 ? (Number(pack.price_usd) / totalCreds).toFixed(4) : "0.0000";
              const unitCostClp =
                totalCreds > 0 ? (Number(pack.price_clp) / totalCreds).toFixed(2) : "0.00";
              const discounts = pack.plan_tier_discounts || {};

              return (
                <div
                  key={pack.id}
                  data-testid={`ai-pack-card-${pack.id}`}
                  className="rounded-2xl border border-border/80 bg-card p-6 shadow-md hover:shadow-lg transition-all space-y-5 flex flex-col justify-between relative overflow-hidden"
                >
                  {/* Popular Banner / Ribbon */}
                  {pack.is_popular && (
                    <div
                      data-testid={`pack-popular-badge-${pack.id}`}
                      className="absolute top-0 right-0 bg-gradient-to-l from-amber-500 to-amber-600 text-amber-950 font-black text-[10px] tracking-wider uppercase px-4 py-1 rounded-bl-xl shadow-xs flex items-center gap-1"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>
                        {t("platform_admin:plans.ai_packs.badge_popular", {
                          defaultValue: "Más Popular",
                        })}
                      </span>
                    </div>
                  )}

                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2 pr-16">
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                              pack.is_active
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : "bg-muted text-muted-foreground border-border"
                            }`}
                          >
                            {pack.is_active
                              ? t("platform_admin:plans.ai_packs.badge_active", {
                                  defaultValue: "Activo",
                                })
                              : t("platform_admin:plans.ai_packs.badge_inactive", {
                                  defaultValue: "Inactivo",
                                })}
                          </span>
                          <span className="text-xs text-muted-foreground font-mono">
                            Orden: #{pack.sort_order}
                          </span>
                        </div>
                        <h3
                          data-testid={`pack-name-${pack.id}`}
                          className="text-lg font-bold text-foreground mt-1.5"
                        >
                          {pack.pack_name}
                        </h3>
                      </div>
                    </div>

                    {/* Créditos */}
                    <div className="p-3.5 rounded-xl bg-secondary/40 border border-border/60 space-y-1">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                          {t("platform_admin:plans.ai_packs.credits_title", {
                            defaultValue: "Créditos IA",
                          })}
                        </span>
                        {Number(pack.bonus_credits) > 0 && (
                          <span className="text-emerald-400 font-semibold font-mono text-[11px]">
                            +{Number(pack.bonus_credits).toLocaleString("es-CL")} bono
                          </span>
                        )}
                      </div>
                      <div
                        data-testid={`pack-total-credits-${pack.id}`}
                        className="text-2xl font-black text-foreground font-mono flex items-baseline gap-2"
                      >
                        <span>{totalCreds.toLocaleString("es-CL")}</span>
                        <span className="text-xs text-muted-foreground font-normal">créditos</span>
                      </div>
                    </div>

                    {/* Precios y Costo Unitario */}
                    <div className="space-y-2">
                      <div className="flex items-baseline justify-between">
                        <span className="text-xs text-muted-foreground">Precio CLP / USD:</span>
                        <div className="text-right">
                          <div className="text-lg font-black text-foreground font-mono">
                            ${Number(pack.price_clp).toLocaleString("es-CL")} CLP
                          </div>
                          <div className="text-xs font-semibold text-muted-foreground font-mono">
                            ${Number(pack.price_usd).toLocaleString("en-US", { minimumFractionDigits: 2 })} USD
                          </div>
                        </div>
                      </div>

                      {/* Costo Unitario */}
                      <div className="flex items-center justify-between text-xs p-2 rounded-lg bg-background/50 border border-border/50">
                        <span className="text-muted-foreground font-medium">
                          {t("platform_admin:plans.ai_packs.cost_unit", {
                            defaultValue: "Costo unitario por crédito:",
                          })}
                        </span>
                        <span className="font-mono font-semibold text-emerald-400">
                          ${unitCostUsd} USD / ${unitCostClp} CLP
                        </span>
                      </div>
                    </div>

                    {/* Reglas de Combinación ("Hacer Juego") */}
                    <div className="p-3.5 rounded-xl bg-primary/5 border border-primary/20 space-y-2">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                        <Layers className="w-3.5 h-3.5" />
                        <span>
                          {t("platform_admin:plans.ai_packs.combination_rules_title", {
                            defaultValue: "Reglas de Combinación con Planes Base:",
                          })}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {t("platform_admin:plans.ai_packs.combination_rules_desc", {
                          defaultValue:
                            "Beneficio en planes base: Descuentos automáticos al adquirir este pack con suscripción activa:",
                        })}
                      </p>
                      <div className="grid grid-cols-3 gap-2 pt-1">
                        <div className="p-2 rounded-lg bg-card border border-border/70 text-center">
                          <div className="text-[10px] text-muted-foreground uppercase font-bold">
                            Básico
                          </div>
                          <div className="text-xs font-mono font-bold text-foreground">
                            {Number(discounts.plan_basico ?? discounts.basico ?? 0)}% desc.
                          </div>
                        </div>
                        <div className="p-2 rounded-lg bg-card border border-border/70 text-center">
                          <div className="text-[10px] text-muted-foreground uppercase font-bold">
                            Pro
                          </div>
                          <div className="text-xs font-mono font-bold text-emerald-400">
                            {Number(discounts.plan_pro ?? discounts.pro ?? 10)}% desc.
                          </div>
                        </div>
                        <div className="p-2 rounded-lg bg-card border border-border/70 text-center">
                          <div className="text-[10px] text-muted-foreground uppercase font-bold">
                            Enterprise
                          </div>
                          <div className="text-xs font-mono font-bold text-emerald-400">
                            {Number(discounts.plan_enterprise ?? discounts.enterprise ?? 20)}% desc.
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Acciones */}
                  <div className="border-t border-border/60 pt-4 flex items-center justify-end">
                    <button
                      type="button"
                      data-testid={`edit-ai-pack-btn-${pack.id}`}
                      onClick={() => handleOpenEditAiPack(pack)}
                      className="touch-target min-h-[38px] inline-flex items-center gap-1.5 rounded-xl border border-border bg-secondary/60 hover:bg-secondary px-3.5 py-1.5 text-xs font-semibold text-foreground transition-colors cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5 text-primary" />
                      <span>
                        {t("platform_admin:plans.ai_packs.btn_edit", {
                          defaultValue: "Editar Paquete",
                        })}
                      </span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. MODAL: CREAR / EDITAR PLAN */}
      {planModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="plan-modal-title"
          data-testid="plan-form-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm overflow-y-auto"
        >
          <div className="w-full max-w-3xl rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto my-auto animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 id="plan-modal-title" className="text-lg font-bold text-foreground flex items-center gap-2">
                  <Package className="w-5 h-5 text-primary" />
                  {editingPlan
                    ? t("platform_admin:plans.modal.edit_title", {
                        name: editingPlan.name,
                        defaultValue: `Editar Plan: ${editingPlan.name}`,
                      })
                    : t("platform_admin:plans.modal.create_title", {
                        defaultValue: "Crear Nuevo Plan SaaS",
                      })}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {t("platform_admin:plans.modal.subtitle", {
                    defaultValue:
                      "Define los precios, cupos de tokens/créditos de IA y activa los módulos que formarán parte de este plan.",
                  })}
                </p>
              </div>
              <button
                type="button"
                data-testid="close-plan-modal-btn"
                onClick={() => setPlanModalOpen(false)}
                className="touch-target inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePlan} className="space-y-5">
              {/* Fila 1: Nombre y Slug */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.modal.field_name", {
                      defaultValue: "Nombre Comercial del Plan *",
                    })}
                  </label>
                  <input
                    required
                    data-testid="plan-form-name-input"
                    type="text"
                    placeholder={t("platform_admin:plans.modal.field_name_placeholder", {
                      defaultValue: "Ej: Plan Pro Plus",
                    })}
                    value={formName}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.modal.field_slug", {
                      defaultValue: "Slug Identificador *",
                    })}
                  </label>
                  <input
                    required
                    data-testid="plan-form-slug-input"
                    type="text"
                    disabled={Boolean(editingPlan)}
                    placeholder={t("platform_admin:plans.modal.field_slug_placeholder", {
                      defaultValue: "Ej: plan-pro-plus",
                    })}
                    value={formSlug}
                    onChange={(e) => setFormSlug(e.target.value.toLowerCase())}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60"
                  />
                </div>
              </div>

              {/* Fila 2: Descripción */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  {t("platform_admin:plans.modal.field_description", {
                    defaultValue: "Descripción Comercial",
                  })}
                </label>
                <textarea
                  data-testid="plan-form-description-input"
                  rows={2}
                  placeholder={t("platform_admin:plans.modal.field_description_placeholder", {
                    defaultValue:
                      "Breve resumen de para quién está pensado este plan y su propuesta de valor...",
                  })}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </div>

              {/* Fila 3: Precios, Créditos y Tier */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.modal.field_price_clp", {
                      defaultValue: "Precio CLP / mes",
                    })}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    data-testid="plan-form-price-clp-input"
                    value={formPriceClp}
                    onChange={(e) => setFormPriceClp(Number(e.target.value))}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.modal.field_price_usd", {
                      defaultValue: "Precio USD / mes",
                    })}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    data-testid="plan-form-price-usd-input"
                    value={formPriceUsd}
                    onChange={(e) => setFormPriceUsd(Number(e.target.value))}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.modal.field_credits", {
                      defaultValue: "Créditos IA / mes",
                    })}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    data-testid="plan-form-credits-input"
                    value={formCredits}
                    onChange={(e) => setFormCredits(Number(e.target.value))}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.modal.field_tier", {
                      defaultValue: "Nivel / Tier",
                    })}
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    data-testid="plan-form-tier-input"
                    value={formTier}
                    onChange={(e) => setFormTier(Number(e.target.value))}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              {/* Fila 4: Flags de Estado y Destacado */}
              <div className="flex flex-wrap items-center gap-6 p-3 rounded-xl bg-secondary/30 border border-border/60">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-foreground select-none">
                  <input
                    type="checkbox"
                    data-testid="plan-form-is-active-checkbox"
                    checked={formIsActive}
                    onChange={(e) => setFormIsActive(e.target.checked)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>
                    {t("platform_admin:plans.modal.is_active_label", {
                      defaultValue: "Plan Activo (Disponible para contratación)",
                    })}
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-foreground select-none">
                  <input
                    type="checkbox"
                    data-testid="plan-form-is-popular-checkbox"
                    checked={formIsPopular}
                    onChange={(e) => setFormIsPopular(e.target.checked)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span className="text-primary font-bold">
                    {t("platform_admin:plans.modal.is_popular_label", {
                      defaultValue: "Marcar como Plan Recomendado / Destacado",
                    })}
                  </span>
                </label>
              </div>

              {/* Fila 5: Selector Jerárquico de Módulos */}
              <div className="space-y-2.5 border-t border-border/60 pt-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <label className="text-xs font-bold text-foreground flex items-center gap-2">
                      <SlidersHorizontal className="w-3.5 h-3.5 text-primary" />
                      {t("platform_admin:plans.modal.modules_label", {
                        count: selectedModules.length,
                        total: moduleCatalog.length,
                        defaultValue: `Módulos del Sistema Incluidos (${selectedModules.length} de ${moduleCatalog.length})`,
                      })}
                    </label>
                    <p className="text-[11px] text-muted-foreground">
                      {t("platform_admin:plans.modal.modules_help", {
                        defaultValue:
                          "Los módulos seleccionados se activarán automáticamente para el local o cliente que elija este plan.",
                      })}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <button
                      type="button"
                      data-testid="select-all-modules-btn"
                      onClick={handleSelectAllModules}
                      className="touch-target inline-flex min-h-[30px] items-center rounded-md border border-border bg-secondary/50 px-2.5 py-1 text-[11px] font-medium text-foreground hover:bg-secondary transition-colors cursor-pointer"
                    >
                      {t("platform_admin:plans.modal.btn_select_all", {
                        defaultValue: "Seleccionar Todos",
                      })}
                    </button>
                    <button
                      type="button"
                      data-testid="deselect-all-modules-btn"
                      onClick={handleDeselectAllModules}
                      className="touch-target inline-flex min-h-[30px] items-center rounded-md border border-border bg-secondary/50 px-2.5 py-1 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer"
                    >
                      {t("platform_admin:plans.modal.btn_deselect_all", {
                        defaultValue: "Deseleccionar Todos",
                      })}
                    </button>
                  </div>
                </div>

                {/* Buscador de Módulos */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    data-testid="module-search-input"
                    placeholder={t("platform_admin:plans.modal.search_modules_placeholder", {
                      defaultValue: "Buscar módulo por nombre o slug...",
                    })}
                    value={moduleSearch}
                    onChange={(e) => setModuleSearch(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background pl-9 pr-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                {/* Grid de Checkboxes de Módulos */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-60 overflow-y-auto p-2 rounded-xl bg-background/50 border border-border/60">
                  {filteredModules.map((mod) => {
                    const isChecked = selectedModules.includes(mod.id);
                    return (
                      <div
                        key={mod.id}
                        data-testid={`module-item-${mod.id}`}
                        onClick={() => handleToggleModule(mod.id)}
                        className={`flex items-start gap-2.5 p-2 rounded-lg border text-left cursor-pointer transition-colors select-none ${
                          isChecked
                            ? "bg-primary/10 border-primary/30 text-foreground"
                            : "bg-card/40 border-border/40 hover:bg-secondary/40 text-muted-foreground"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToggleModule(mod.id)}
                          className="mt-0.5 h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="text-xs font-semibold truncate leading-tight text-foreground">
                            {mod.label}
                          </div>
                          <div className="text-[10px] font-mono text-muted-foreground truncate">
                            {mod.id}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Botones de Acción */}
              <div className="pt-4 border-t border-border/60 flex items-center justify-end gap-2">
                <button
                  type="button"
                  data-testid="cancel-plan-modal-btn"
                  onClick={() => setPlanModalOpen(false)}
                  disabled={isCreating || isUpdatingPlan}
                  className="touch-target inline-flex min-h-[36px] items-center rounded-lg border border-border px-4 py-2 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer disabled:opacity-50"
                >
                  {t("platform_admin:plans.modal.btn_cancel", {
                    defaultValue: "Cancelar",
                  })}
                </button>
                <button
                  type="submit"
                  data-testid="plan-form-submit-btn"
                  onClick={handleSavePlan}
                  disabled={isCreating || isUpdatingPlan}
                  className="touch-target inline-flex min-h-[36px] items-center gap-1.5 rounded-lg bg-primary hover:bg-primary/90 px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-colors cursor-pointer disabled:opacity-50"
                >
                  {(isCreating || isUpdatingPlan) && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>
                    {editingPlan
                      ? t("platform_admin:plans.modal.btn_update_submit", {
                          defaultValue: "Actualizar Plan",
                        })
                      : t("platform_admin:plans.modal.btn_create_submit", {
                          defaultValue: "Crear Plan",
                        })}
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5. MODAL: CONFIRMAR ELIMINACIÓN */}
      {deleteConfirmOpen && planToDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          data-testid="delete-plan-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-4 my-auto animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 text-destructive">
              <div className="p-2 rounded-xl bg-destructive/10 border border-destructive/20">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 id="delete-modal-title" className="text-base font-bold text-foreground">
                  {t("platform_admin:plans.delete_modal.title", {
                    defaultValue: "¿Eliminar Plan Comercial?",
                  })}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {t("platform_admin:plans.delete_modal.subtitle", {
                    defaultValue: "Esta acción dará de baja el plan del catálogo.",
                  })}
                </p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Estás a punto de eliminar el plan <strong>"{planToDelete.name}"</strong> (slug: <code>{planToDelete.slug}</code>).
            </p>

            {planToDelete.active_clients_count > 0 && (
              <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/30 flex items-start gap-2.5 text-xs text-destructive">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>
                  <strong>
                    {t("platform_admin:plans.delete_modal.active_warning_title", {
                      defaultValue: "Atención:",
                    })}
                  </strong>{" "}
                  {t("platform_admin:plans.delete_modal.active_warning_body", {
                    count: planToDelete.active_clients_count,
                    defaultValue: `Este plan cuenta con ${planToDelete.active_clients_count} clientes activos suscritos. La API rechazará la eliminación directa con bloqueo HTTP 409.`,
                  })}
                </span>
              </div>
            )}

            <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
              <button
                type="button"
                data-testid="cancel-delete-plan-btn"
                onClick={() => setDeleteConfirmOpen(false)}
                disabled={isDeleting}
                className="touch-target inline-flex min-h-[36px] items-center rounded-lg border border-border px-3.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer"
              >
                {t("platform_admin:plans.delete_modal.btn_cancel", {
                  defaultValue: "Cancelar",
                })}
              </button>
              <button
                type="button"
                data-testid="confirm-delete-plan-btn"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="touch-target inline-flex min-h-[36px] items-center gap-1.5 rounded-lg bg-destructive hover:bg-destructive/90 px-3.5 py-1.5 text-xs font-bold text-destructive-foreground shadow-sm transition-colors cursor-pointer disabled:opacity-50"
              >
                {isDeleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>
                  {t("platform_admin:plans.delete_modal.btn_confirm", {
                    defaultValue: "Confirmar Eliminación",
                  })}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. MODAL: CREAR / EDITAR PAQUETE DE CRÉDITOS IA */}
      {aiPackModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="ai-pack-modal-title"
          data-testid="ai-credit-pack-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm overflow-y-auto"
        >
          <div className="w-full max-w-2xl rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto my-auto animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3
                  id="ai-pack-modal-title"
                  className="text-lg font-bold text-foreground flex items-center gap-2"
                >
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                  <span>
                    {editingAiPack
                      ? t("platform_admin:plans.ai_packs.modal.edit_title", {
                          name: editingAiPack.pack_name,
                          defaultValue: `Editar Paquete: ${editingAiPack.pack_name}`,
                        })
                      : t("platform_admin:plans.ai_packs.modal.create_title", {
                          defaultValue: "Crear Paquete de Créditos IA (Add-On)",
                        })}
                  </span>
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {t("platform_admin:plans.ai_packs.modal.subtitle", {
                    defaultValue:
                      "Define los créditos, precios multi-moneda y las reglas de combinación con planes base.",
                  })}
                </p>
              </div>
              <button
                type="button"
                data-testid="close-ai-pack-modal-btn"
                onClick={() => setAiPackModalOpen(false)}
                className="touch-target inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveAiPack} className="space-y-4">
              {/* Nombre del Paquete */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  {t("platform_admin:plans.ai_packs.modal.name_label", {
                    defaultValue: "Nombre Comercial del Paquete *",
                  })}
                </label>
                <input
                  data-testid="input-ai-pack-name"
                  type="text"
                  required
                  value={packName}
                  onChange={(e) => setPackName(e.target.value)}
                  placeholder={t("platform_admin:plans.ai_packs.modal.name_placeholder", {
                    defaultValue: "Ej: Growth Pack (5.000 Créditos)",
                  })}
                  className="w-full rounded-xl border border-border bg-background px-3.5 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              {/* Créditos y Bono */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.ai_packs.modal.credits_label", {
                      defaultValue: "Cantidad de Créditos *",
                    })}
                  </label>
                  <input
                    data-testid="input-ai-pack-credits"
                    type="number"
                    min="1"
                    required
                    value={creditsAmount}
                    onChange={(e) => setCreditsAmount(Math.max(1, Number(e.target.value)))}
                    className="w-full rounded-xl border border-border bg-background px-3.5 py-2 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.ai_packs.modal.bonus_label", {
                      defaultValue: "Créditos de Bonificación (Bono)",
                    })}
                  </label>
                  <input
                    data-testid="input-ai-pack-bonus"
                    type="number"
                    min="0"
                    value={bonusCredits}
                    onChange={(e) => setBonusCredits(Math.max(0, Number(e.target.value)))}
                    className="w-full rounded-xl border border-border bg-background px-3.5 py-2 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>

              {/* Precios CLP y USD */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.ai_packs.modal.price_clp_label", {
                      defaultValue: "Precio CLP (IVA incl.) *",
                    })}
                  </label>
                  <input
                    data-testid="input-ai-pack-price-clp"
                    type="number"
                    min="0"
                    required
                    value={priceClp}
                    onChange={(e) => setPriceClp(Math.max(0, Number(e.target.value)))}
                    className="w-full rounded-xl border border-border bg-background px-3.5 py-2 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.ai_packs.modal.price_usd_label", {
                      defaultValue: "Precio USD *",
                    })}
                  </label>
                  <input
                    data-testid="input-ai-pack-price-usd"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    value={priceUsd}
                    onChange={(e) => setPriceUsd(Math.max(0, Number(e.target.value)))}
                    className="w-full rounded-xl border border-border bg-background px-3.5 py-2 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>

              {/* Orden y Checkboxes */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    {t("platform_admin:plans.ai_packs.modal.sort_order_label", {
                      defaultValue: "Orden de Despliegue",
                    })}
                  </label>
                  <input
                    data-testid="input-ai-pack-sort-order"
                    type="number"
                    min="0"
                    value={sortOrder}
                    onChange={(e) => setSortOrder(Math.max(0, Number(e.target.value)))}
                    className="w-full rounded-xl border border-border bg-background px-3.5 py-2 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div className="flex items-center gap-2 pt-4">
                  <input
                    data-testid="checkbox-ai-pack-popular"
                    id="is_popular_ai_pack"
                    type="checkbox"
                    checked={isPopular}
                    onChange={(e) => setIsPopular(e.target.checked)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <label
                    htmlFor="is_popular_ai_pack"
                    className="text-xs font-medium text-foreground cursor-pointer"
                  >
                    {t("platform_admin:plans.ai_packs.modal.is_popular_label", {
                      defaultValue: "Marcar como Más Popular",
                    })}
                  </label>
                </div>

                <div className="flex items-center gap-2 pt-4">
                  <input
                    data-testid="checkbox-ai-pack-active"
                    id="is_active_ai_pack"
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <label
                    htmlFor="is_active_ai_pack"
                    className="text-xs font-medium text-foreground cursor-pointer"
                  >
                    {t("platform_admin:plans.ai_packs.modal.is_active_label", {
                      defaultValue: "Paquete Activo",
                    })}
                  </label>
                </div>
              </div>

              {/* Reglas de Combinación con Planes Base */}
              <div className="p-4 rounded-xl bg-secondary/30 border border-border/80 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                  <Layers className="w-4 h-4 text-primary" />
                  <span>
                    {t("platform_admin:plans.ai_packs.modal.discounts_title", {
                      defaultValue: "Reglas de Combinación con Planes Base (Descuentos)",
                    })}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("platform_admin:plans.ai_packs.modal.discounts_help", {
                    defaultValue:
                      "Define el porcentaje de descuento que reciben los clientes según su plan base contratado:",
                  })}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      {t("platform_admin:plans.ai_packs.modal.discount_basic_label", {
                        defaultValue: "Descuento Plan Básico (%)",
                      })}
                    </label>
                    <input
                      data-testid="input-discount-plan-basico"
                      type="number"
                      min="0"
                      max="100"
                      value={discountBasico}
                      onChange={(e) =>
                        setDiscountBasico(Math.max(0, Math.min(100, Number(e.target.value))))
                      }
                      className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      {t("platform_admin:plans.ai_packs.modal.discount_pro_label", {
                        defaultValue: "Descuento Plan Pro (%)",
                      })}
                    </label>
                    <input
                      data-testid="input-discount-plan-pro"
                      type="number"
                      min="0"
                      max="100"
                      value={discountPro}
                      onChange={(e) =>
                        setDiscountPro(Math.max(0, Math.min(100, Number(e.target.value))))
                      }
                      className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      {t("platform_admin:plans.ai_packs.modal.discount_enterprise_label", {
                        defaultValue: "Descuento Plan Enterprise (%)",
                      })}
                    </label>
                    <input
                      data-testid="input-discount-plan-enterprise"
                      type="number"
                      min="0"
                      max="100"
                      value={discountEnterprise}
                      onChange={(e) =>
                        setDiscountEnterprise(Math.max(0, Math.min(100, Number(e.target.value))))
                      }
                      className="w-full rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>

              {/* Botones */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  data-testid="cancel-ai-pack-btn"
                  onClick={() => setAiPackModalOpen(false)}
                  className="touch-target inline-flex min-h-[40px] items-center rounded-xl border border-border bg-secondary/60 hover:bg-secondary px-4 py-2 text-xs font-medium text-foreground transition-colors cursor-pointer"
                >
                  {t("platform_admin:plans.ai_packs.modal.btn_cancel", {
                    defaultValue: "Cancelar",
                  })}
                </button>

                <button
                  type="submit"
                  data-testid="save-ai-pack-btn"
                  disabled={isCreatingAiPack}
                  className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-xl bg-primary hover:bg-primary/90 px-5 py-2 text-xs font-semibold text-primary-foreground shadow-md transition-colors cursor-pointer disabled:opacity-50"
                >
                  {isCreatingAiPack ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  <span>
                    {t("platform_admin:plans.ai_packs.modal.btn_submit", {
                      defaultValue: "Guardar Paquete IA",
                    })}
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default PlansPage;
