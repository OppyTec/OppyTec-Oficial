/**
 * oppytec-frontend/src/features/platform-admin/sandbox/__tests__/MockDataMasterSwitchAndPresets.test.tsx
 * Co-creación 1:1 de Tests Unitarios y de Integración para el Sub-Plan 2 / Etapa 2:
 * Switch Maestro Reactivo, Presets Gastronómicos Canónicos, httpClient Filter y Factory Reset.
 */

import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";
import {
  getMockDataMode,
  isMockDataEnabled,
  MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY,
  MOCK_DATA_MODE_EVENT_NAME,
  MOCK_DATA_MODE_STORAGE_KEY,
  MOCK_DATA_RESET_EVENT_NAME,
  selectByMockMode,
  setMockDataMode,
  toggleMockDataMode,
  useMockAwareData,
  useMockDataMode,
} from "@/shared/mock/mockModeStorage";
import {
  executeFactoryReset,
  fetchGastronomicPresets,
} from "../api";
import { MockDataSandboxView } from "../MockDataSandboxView";
import {
  CARNES_ANGUS_CAVA_PRESET,
  CLEAN_SLATE_PRESET,
  FAST_FOOD_POLLO_KING_PRESET,
  GASTRONOMIC_PRESET_METAS,
  GASTRONOMIC_PRESETS,
  getDefaultGastronomicPreset,
  getGastronomicPresetById,
  getGastronomicPresetMetaById,
  HOTEL_DESAYUNO_BUFFET_PRESET,
} from "../presets";

function renderWithProviders(
  ui: React.ReactElement,
  {
    initialRoute = "/admin/sandbox/mock-data",
    permissions = [
      "platform_admin.sandbox.access",
      "platform_admin.sandbox.manage",
    ],
  } = {}
) {
  const rbacState = {
    roleName: "SuperAdmin",
    isSuperUser: true,
    planModules: ["platform_admin"],
    rolePermissions: permissions as any,
    temporaryGrants: [],
    deniedPermissions: [],
  };

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <PermissionsProvider initialPolicy={rbacState as any}>{ui}</PermissionsProvider>
    </MemoryRouter>
  );
}

// Componente auxiliar para probar el hook useMockDataMode de forma aislada
function HookConsumerComponent() {
  const { mode, isDemo, isClean, setMode, toggleMode } = useMockDataMode();
  const awareValue = useMockAwareData("DEMO_DATA", "CLEAN_DATA");
  return (
    <div>
      <span data-testid="hook-mode">{mode}</span>
      <span data-testid="hook-is-demo">{String(isDemo)}</span>
      <span data-testid="hook-is-clean">{String(isClean)}</span>
      <span data-testid="hook-aware-value">{awareValue}</span>
      <button data-testid="btn-hook-set-clean" onClick={() => setMode("clean")}>
        Set Clean
      </button>
      <button data-testid="btn-hook-set-demo" onClick={() => setMode("demo")}>
        Set Demo
      </button>
      <button data-testid="btn-hook-toggle" onClick={toggleMode}>
        Toggle
      </button>
    </div>
  );
}

describe("Sub-Plan 2 / Etapa 2 — Switch Maestro, Presets Gastronómicos y Factory Reset", () => {
  beforeEach(() => {
    localStorage.clear();
    setMockDataMode("demo");
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    setMockDataMode("demo");
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. GESTOR DE ESTADO REACTIVO: mockModeStorage.ts
  // ==========================================================================
  describe("1. mockModeStorage: Persistencia y Reactividad", () => {
    it("debe retornar 'demo' por defecto cuando localStorage está vacío", () => {
      localStorage.removeItem(MOCK_DATA_MODE_STORAGE_KEY);
      expect(getMockDataMode()).toBe("demo");
      expect(isMockDataEnabled()).toBe(true);
    });

    it("debe persistir 'clean' en localStorage al usar setMockDataMode", () => {
      setMockDataMode("clean");
      expect(localStorage.getItem(MOCK_DATA_MODE_STORAGE_KEY)).toBe("clean");
      expect(getMockDataMode()).toBe("clean");
      expect(isMockDataEnabled()).toBe(false);
    });

    it("debe alternar de 'demo' a 'clean' y viceversa con toggleMockDataMode", () => {
      setMockDataMode("demo");
      expect(toggleMockDataMode()).toBe("clean");
      expect(getMockDataMode()).toBe("clean");

      expect(toggleMockDataMode()).toBe("demo");
      expect(getMockDataMode()).toBe("demo");
    });

    it("debe despachar CustomEvent('oppytec_mock_mode_changed') al cambiar el modo", () => {
      const listenerMock = vi.fn();
      window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, listenerMock);

      setMockDataMode("clean");

      expect(listenerMock).toHaveBeenCalledTimes(1);
      const event = listenerMock.mock.calls[0]?.[0] as CustomEvent;
      expect(event.detail?.mode).toBe("clean");

      window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, listenerMock);
    });

    it("useMockDataMode debe reaccionar a cambios locales y multi-pestaña", async () => {
      render(<HookConsumerComponent />);

      expect(screen.getByTestId("hook-mode").textContent).toBe("demo");
      expect(screen.getByTestId("hook-is-demo").textContent).toBe("true");
      expect(screen.getByTestId("hook-is-clean").textContent).toBe("false");

      // Cambio mediante botón del hook
      act(() => {
        screen.getByTestId("btn-hook-set-clean").click();
      });

      expect(screen.getByTestId("hook-mode").textContent).toBe("clean");
      expect(screen.getByTestId("hook-is-demo").textContent).toBe("false");
      expect(screen.getByTestId("hook-is-clean").textContent).toBe("true");

      // Simulación de evento 'storage' desde otra pestaña del navegador
      act(() => {
        window.dispatchEvent(
          new StorageEvent("storage", {
            key: MOCK_DATA_MODE_STORAGE_KEY,
            newValue: "demo",
          })
        );
      });

      expect(screen.getByTestId("hook-mode").textContent).toBe("demo");
      expect(screen.getByTestId("hook-is-demo").textContent).toBe("true");
    });
  });

  // ==========================================================================
  // 2. INTEGRACIÓN CON httpClient.ts (CABECERAS Y COMPORTAMIENTO FALLBACK)
  // ==========================================================================
  describe("2. httpClient: Inyección de Cabecera y Aislamiento Empty State", () => {
    it("buildApiHeaders debe inyectar X-OppyTec-Mock-Mode acorde al modo activo", () => {
      setMockDataMode("demo");
      let headers = httpClient.buildApiHeaders();
      expect(headers["X-OppyTec-Mock-Mode"]).toBe("demo");

      setMockDataMode("clean");
      headers = httpClient.buildApiHeaders();
      expect(headers["X-OppyTec-Mock-Mode"]).toBe("clean");
    });

    it("en modo 'demo', apiRequest debe entregar fallbackData si la llamada HTTP falla", async () => {
      setMockDataMode("demo");

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: new Headers(),
      } as unknown as Response);

      const fallbackList = [{ id: 1, name: "Item Demo" }];
      const res = await httpClient.apiRequest("/test/items", {
        method: "GET",
        fallbackData: fallbackList,
      });

      expect(res.data).toEqual(fallbackList);
    });

    it("en modo 'clean', apiRequest debe retornar [] si falla con 404 y se esperaba un array", async () => {
      setMockDataMode("clean");

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 404,
        headers: new Headers(),
      } as unknown as Response);

      const fallbackList = [{ id: 1, name: "Item Demo Ignorado" }];
      const res = await httpClient.apiRequest("/test/items", {
        method: "GET",
        fallbackData: fallbackList,
      });

      // El fallbackData simulado fue ignorado; se retorna array vacío para forzar Empty State
      expect(res.data).toEqual([]);
    });

    it("en modo 'clean', apiRequest debe propagar el error si ocurre fallo de red y no es array", async () => {
      setMockDataMode("clean");

      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network Error"));

      const fallbackObject = { count: 99 };
      await expect(
        httpClient.apiRequest("/test/stats", {
          method: "GET",
          fallbackData: fallbackObject,
        })
      ).rejects.toThrow("Network Error");
    });
  });

  // ==========================================================================
  // 3. PRESETS GASTRONÓMICOS CANÓNICOS
  // ==========================================================================
  describe("3. Presets Gastronómicos Canónicos: Integridad del Catálogo", () => {
    it("debe contener exactamente los 4 presets canónicos requeridos", () => {
      expect(GASTRONOMIC_PRESETS.length).toBe(4);
      expect(GASTRONOMIC_PRESET_METAS.length).toBe(4);

      const ids = GASTRONOMIC_PRESETS.map((p) => p.meta.id);
      expect(ids).toContain("fast-food-pollo-king");
      expect(ids).toContain("carnes-angus-cava");
      expect(ids).toContain("hotel-desayuno-buffet");
      expect(ids).toContain("clean-slate");
    });

    it("certifica Fast Food & Pollo King: insumos, bodegas, lotes y escandallo", () => {
      const preset = FAST_FOOD_POLLO_KING_PRESET;
      expect(preset.meta.code).toBe("FF-PK-01");
      expect(preset.meta.defaultTenantSchema).toBe("tenant_pollo_king_mall");
      expect(preset.meta.estimatedStockValueClp).toBe(3850000);
      expect(preset.dataset.products.length).toBe(6);
      expect(preset.dataset.warehouses.length).toBe(3);
      expect(preset.dataset.batches.length).toBe(5);
      expect(preset.dataset.recipes.length).toBe(2);

      // Verificación de lote crítico FEFO
      const critical = preset.dataset.batches.find((b) => b.estadoFefo === "CRITICO");
      expect(critical).toBeDefined();
      expect(critical?.productoSku).toBe("AL-POL-001");
    });

    it("certifica Carnes Angus & Cava: cortes dry-aged y cava de vinos", () => {
      const preset = CARNES_ANGUS_CAVA_PRESET;
      expect(preset.meta.code).toBe("STK-AC-02");
      expect(preset.meta.defaultTenantSchema).toBe("tenant_angus_vitacura");
      expect(preset.meta.estimatedStockValueClp).toBe(8940000);
      expect(preset.dataset.warehouses.length).toBe(4);

      const tomahawk = preset.dataset.products.find((p) => p.sku === "CAR-TOM-001");
      expect(tomahawk).toBeDefined();
      expect(tomahawk?.costoUnitarioPpp).toBe(22500);
    });

    it("certifica Hotel & Desayuno Buffet: perecibles de ciclo corto y panadería", () => {
      const preset = HOTEL_DESAYUNO_BUFFET_PRESET;
      expect(preset.meta.code).toBe("HSP-BF-03");
      expect(preset.meta.defaultTenantSchema).toBe("tenant_hotel_andes_central");
      expect(preset.meta.estimatedStockValueClp).toBe(4120000);

      const eggs = preset.dataset.products.find((p) => p.sku === "LAC-HUE-001");
      expect(eggs).toBeDefined();
      expect(eggs?.diasAlertaVencimiento).toBe(7);
    });

    it("certifica Clean Slate: dataset 100% virgen para evaluación de Empty States", () => {
      const preset = CLEAN_SLATE_PRESET;
      expect(preset.meta.code).toBe("CLN-SL-00");
      expect(preset.meta.estimatedStockValueClp).toBe(0);
      expect(preset.dataset.products.length).toBe(0);
      expect(preset.dataset.batches.length).toBe(0);
      expect(preset.dataset.recipes.length).toBe(0);
      expect(preset.meta.kpisSummary.totalSkus).toBe(0);
      expect(preset.meta.kpisSummary.criticalBatches).toBe(0);
    });

    it("funciones selectoras auxiliares de catálogo", () => {
      expect(getGastronomicPresetById("carnes-angus-cava")).toBe(CARNES_ANGUS_CAVA_PRESET);
      expect(getGastronomicPresetMetaById("clean-slate")?.code).toBe("CLN-SL-00");
      expect(getDefaultGastronomicPreset()).toBe(FAST_FOOD_POLLO_KING_PRESET);
      expect(getGastronomicPresetById("non-existent")).toBeUndefined();
    });

    it("certificación Agente 06 (FinOps & AI Governance): aislamiento estricto de créditos y cuotas SaaS", () => {
      // 1. Cada preset gastronómico canónico encapsula sus finops al tenantId correspondiente
      for (const preset of GASTRONOMIC_PRESETS) {
        const declaredTenantIds = new Set(preset.dataset.tenants.map((t) => t.id));
        for (const allocation of preset.dataset.finops) {
          expect(declaredTenantIds.has(allocation.tenantId)).toBe(true);
          expect(allocation.tokensConsumed).toBeLessThanOrEqual(allocation.tokenBudgetMonthly);
          expect(allocation.creditsClpSpent).toBeLessThanOrEqual(allocation.creditsClpBudget);
        }
      }

      // 2. Clean Slate garantiza 0 gasto ficticio para evitar bypass a cuotas reales
      const cleanAllocation = CLEAN_SLATE_PRESET.dataset.finops[0];
      expect(cleanAllocation).toBeDefined();
      expect(cleanAllocation?.tokensConsumed).toBe(0);
      expect(cleanAllocation?.creditsClpSpent).toBe(0);

      // 3. Planes comerciales respetan la jerarquía de límites de tokens
      expect(CLEAN_SLATE_PRESET.dataset.holdings[0]?.planId).toBe("standard_single_store");
      expect(FAST_FOOD_POLLO_KING_PRESET.dataset.holdings[0]?.planId).toBe("enterprise_multi_branch");
      expect(CARNES_ANGUS_CAVA_PRESET.dataset.holdings[0]?.planId).toBe("enterprise_multi_branch");
      expect(HOTEL_DESAYUNO_BUFFET_PRESET.dataset.holdings[0]?.planId).toBe("enterprise_multi_branch");
    });
  });

  // ==========================================================================
  // 4. API DEL SANDBOX: PRESETS Y FACTORY RESET
  // ==========================================================================
  describe("4. api.ts: fetchGastronomicPresets y executeFactoryReset", () => {
    it("fetchGastronomicPresets debe devolver la lista de metadatos de los 4 presets", async () => {
      const presets = await fetchGastronomicPresets();
      expect(presets.length).toBe(4);
      expect(presets[0]?.id).toBe("fast-food-pollo-king");
    });

    it("executeFactoryReset debe restaurar datos y purgar almacenamiento local", async () => {
      localStorage.setItem(MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY, JSON.stringify({ mutated: true }));

      const resetEventSpy = vi.fn();
      window.addEventListener(MOCK_DATA_RESET_EVENT_NAME, resetEventSpy);

      const res = await executeFactoryReset("tenant_qa_lab", "carnes-angus-cava", true);

      expect(res.tenantSchema).toBe("tenant_qa_lab");
      expect(res.presetRestored).toBe("carnes-angus-cava");
      expect(res.tablesTruncated.length).toBeGreaterThanOrEqual(4);
      expect(res.recordsReseeded.products).toBe(6);

      // Limpieza en localStorage
      expect(localStorage.getItem(MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY)).toBeNull();
      expect(resetEventSpy).toHaveBeenCalledTimes(1);

      window.removeEventListener(MOCK_DATA_RESET_EVENT_NAME, resetEventSpy);
    });
  });

  // ==========================================================================
  // 5. COMPONENTE UI: MockDataSandboxView
  // ==========================================================================
  describe("5. MockDataSandboxView: Switch Maestro, Métricas y Factory Reset", () => {
    it("debe renderizar el Switch Maestro y permitir conmutar entre Modo Demo y Clean DB", () => {
      renderWithProviders(<MockDataSandboxView />);

      const masterSwitch = screen.getByTestId("mock-data-master-switch");
      const badge = screen.getByTestId("mock-mode-badge");

      expect(masterSwitch).toBeInTheDocument();
      expect(badge.textContent).toBe("Modo Demo");

      // Clic en Switch Maestro
      fireEvent.click(masterSwitch);
      expect(badge.textContent).toBe("Clean DB");
      expect(getMockDataMode()).toBe("clean");

      // Conmutar de vuelta
      fireEvent.click(masterSwitch);
      expect(badge.textContent).toBe("Modo Demo");
      expect(getMockDataMode()).toBe("demo");
    });

    it("debe permitir seleccionar los 4 presets canónicos y mostrar su banner de métricas KPI", () => {
      renderWithProviders(<MockDataSandboxView />);

      // 1. Clic en Pollo King
      const polloCard = screen.getByTestId("card-preset-fast-food-pollo-king");
      fireEvent.click(polloCard);

      expect(screen.getByTestId("selected-preset-metrics-banner")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-metric-skus").textContent).toBe("6");
      expect(screen.getByTestId("kpi-metric-warehouses").textContent).toBe("3");
      expect(screen.getByTestId("kpi-metric-critical").textContent).toBe("1");

      // 2. Clic en Clean Slate
      const cleanCard = screen.getByTestId("card-preset-clean-slate");
      fireEvent.click(cleanCard);

      expect(screen.getByTestId("kpi-metric-skus").textContent).toBe("0");
      expect(screen.getByTestId("kpi-metric-batches").textContent).toBe("0");
      expect(screen.getByTestId("kpi-metric-critical").textContent).toBe("0");
      expect(screen.getByTestId("kpi-metric-stock-value").textContent).toBe("$0");
    });

    it("debe abrir el modal de Factory Reset y ejecutar la restauración con confirmación", async () => {
      renderWithProviders(<MockDataSandboxView />);

      const resetBtn = screen.getByTestId("btn-factory-reset");
      fireEvent.click(resetBtn);

      // Modal de confirmación abierto
      expect(screen.getByTestId("dialog-factory-reset")).toBeInTheDocument();

      // Cancelar primero
      const cancelBtn = screen.getByTestId("btn-cancel-factory-reset");
      fireEvent.click(cancelBtn);
      expect(screen.queryByTestId("dialog-factory-reset")).not.toBeInTheDocument();

      // Abrir nuevamente y confirmar
      fireEvent.click(resetBtn);
      const confirmBtn = screen.getByTestId("btn-confirm-factory-reset");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("dialog-factory-reset")).not.toBeInTheDocument();
      });

      // Panel de estado actualizado
      expect(screen.getByTestId("mock-data-status-panel")).toBeInTheDocument();
    });

    it("debe activar Clean DB automáticamente cuando se confirma Factory Reset con clean-slate y soportar los 3 botones de Respaldo Maestro JSON", async () => {
      setMockDataMode("demo");
      renderWithProviders(<MockDataSandboxView />);

      // Verificar presencia de la sección de Respaldo Maestro JSON
      expect(screen.getByTestId("mock-data-backup-vault-card")).toBeInTheDocument();
      const downloadBtn = screen.getByTestId("btn-download-mock-backup-json");
      const purgeBtn = screen.getByTestId("btn-purge-all-clean-slate");
      const restoreBtn = screen.getByTestId("btn-restore-mock-backup");

      expect(downloadBtn).toBeInTheDocument();
      expect(purgeBtn).toBeInTheDocument();
      expect(restoreBtn).toBeInTheDocument();

      // Selección de clean-slate y confirmación de Factory Reset cambia a modo clean
      fireEvent.click(screen.getByTestId("card-preset-clean-slate"));
      fireEvent.click(screen.getByTestId("btn-factory-reset"));
      fireEvent.click(screen.getByTestId("btn-confirm-factory-reset"));

      await waitFor(() => {
        expect(getMockDataMode()).toBe("clean");
        expect(restoreBtn).not.toBeDisabled();
      });

      // Botón Restaurar Mock Data desde Respaldo activa modo demo
      fireEvent.click(restoreBtn);
      await waitFor(() => {
        expect(getMockDataMode()).toBe("demo");
        expect(purgeBtn).not.toBeDisabled();
      });

      // Botón Limpiar Todo (Clean Slate 100%) activa modo clean y purga datasets
      fireEvent.click(purgeBtn);
      await waitFor(() => {
        expect(getMockDataMode()).toBe("clean");
        expect(purgeBtn).not.toBeDisabled();
      });

      expect(selectByMockMode(["demo"], [])).toEqual([]);
    });
  });
});
