/**
 * oppytec-frontend/src/features/platform-admin/sandbox/presets/cleanSlate.ts
 * Preset Canónico: Clean Slate (Base Virgen).
 * Entorno estéril y virgen diseñado para evaluar Empty States auténticos, onboarding y testing E2E.
 */

import type { GastronomicPresetDefinition } from "./types";

export const CLEAN_SLATE_PRESET: GastronomicPresetDefinition = {
  meta: {
    id: "clean-slate",
    code: "CLN-SL-00",
    title: "Clean Slate (Base Virgen)",
    titleKey: "platform_admin.sandbox.presets.clean_slate_title",
    subtitle: "Base de datos 100% limpia para verificar Empty States auténticos y onboarding",
    subtitleKey: "platform_admin.sandbox.presets.clean_slate_subtitle",
    description:
      "Dataset virgen para verificar la experiencia de primer uso. Posee estructura básica multi-tenant pero 0 insumos, 0 lotes FEFO, 0 recetas y $0 en inventario, garantizando Empty States puros.",
    descriptionKey: "platform_admin.sandbox.presets.clean_slate_desc",
    category: "minimal",
    badge: "EMPTY STATE",
    badgeKey: "platform_admin.sandbox.presets.clean_slate_badge",
    color: "#3b82f6",
    rgb: "59, 130, 246",
    iconName: "Sparkles",
    defaultTenantSchema: "tenant_clean_slate_01",
    defaultHoldingId: "holding-clean-slate",
    defaultHoldingName: "Holding Base Limpia",
    estimatedStockValueClp: 0,
    kpisSummary: {
      totalSkus: 0,
      totalWarehouses: 1,
      totalFefoBatches: 0,
      totalRecipes: 0,
      criticalBatches: 0,
    },
  },
  dataset: {
    schemaVersion: "2.0",
    presetId: "clean-slate",
    updatedAtIso: "2026-11-05T12:00:00Z",
    isCustomized: false,
    holdings: [
      {
        id: "holding-clean-slate",
        nombre: "Holding Base Limpia",
        rut: "76.000.000-0",
        razonSocial: "Holding Modelo Virgen SpA",
        planId: "standard_single_store",
      },
    ],
    tenants: [
      {
        id: "tenant-clean-01",
        holdingId: "holding-clean-slate",
        schemaName: "tenant_clean_slate_01",
        nombre: "Local Modelo Vacío",
        ciudad: "Santiago",
        direccion: "Av. Providencia 1000",
        telefono: "+56 2 2000 0000",
      },
    ],
    warehouses: [
      {
        id: "bod-clean-principal",
        tenantId: "tenant-clean-01",
        nombre: "Bodega Principal (Vacía)",
        tipo: "seco",
        icono: "Warehouse",
        color: "#3b82f6",
      },
    ],
    products: [],
    batches: [],
    recipes: [],
    finops: [
      {
        tenantId: "tenant-clean-01",
        tokenBudgetMonthly: 100000,
        tokensConsumed: 0,
        creditsClpBudget: 50000,
        creditsClpSpent: 0,
      },
    ],
  },
};
