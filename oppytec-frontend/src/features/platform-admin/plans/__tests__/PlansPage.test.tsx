import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import { PlansPage } from "../PlansPage";
import {
  MOCK_AI_CREDIT_PACKS,
  MOCK_SAAS_POLICY,
  MOCK_SYSTEM_PLANS,
  SYSTEM_MODULE_CATALOG,
} from "../../types";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, layout: _l, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-plans-page-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("PlansPage — Catálogo de Planes Comerciales & Política SaaS (Fase 4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
      const method = options?.method ?? "GET";
      if (method === "GET") {
        if (url.includes("/ai-packs")) {
          return createMockEnvelope(MOCK_AI_CREDIT_PACKS);
        }
        if (url.includes("/plans")) {
          return createMockEnvelope(MOCK_SYSTEM_PLANS);
        }
        if (url.includes("/ai-credits/policy")) {
          return createMockEnvelope(MOCK_SAAS_POLICY);
        }
      }
      if (method === "POST" && url.includes("/ai-packs")) {
        return createMockEnvelope({
          id: 99,
          ...options.body,
          total_credits:
            Number(options.body?.credits_amount || 0) + Number(options.body?.bonus_credits || 0),
        });
      }
      return createMockEnvelope({});
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. RENDERIZADO INICIAL Y CABECERA CANÓNICA
  // ==========================================================================
  describe("1. Renderizado Inicial y Cabecera Canónica", () => {
    it("renderiza la cabecera canónica, título, badges y controles superiores", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      expect(
        screen.getByText("Catálogo de Planes Comerciales & Política SaaS")
      ).toBeTruthy();

      expect(
        screen.getByText(/Configura los planes de suscripción, módulos incluidos/i)
      ).toBeTruthy();

      expect(screen.getByTestId("toggle-policy-btn")).toBeTruthy();
      expect(screen.getByText("Ocultar Política IA")).toBeTruthy();
      expect(screen.getByTestId("refresh-plans-btn")).toBeTruthy();
      expect(screen.getByTestId("create-plan-btn")).toBeTruthy();
    });

    it("renderiza el catálogo visual de planes con sus tarjetas, precios y badges", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Planes Comerciales Disponibles/i)).toBeTruthy();
      });

      // Verifica los tres planes por defecto
      expect(screen.getByTestId("plan-card-plan-basico")).toBeTruthy();
      expect(screen.getByTestId("plan-card-plan-pro")).toBeTruthy();
      expect(screen.getByTestId("plan-card-plan-enterprise")).toBeTruthy();

      // Plan Pro tiene el banner de Recomendado
      expect(
        screen.getByText("★ Recomendado para Negocios en Crecimiento")
      ).toBeTruthy();

      // Precios visibles
      expect(screen.getByText("$29.990")).toBeTruthy();
      expect(screen.getByText("$69.990")).toBeTruthy();

      // Botones de acción en tarjetas
      expect(screen.getByTestId("edit-plan-btn-plan-basico")).toBeTruthy();
      expect(screen.getByTestId("delete-plan-btn-plan-basico")).toBeTruthy();
    });
  });

  // ==========================================================================
  // 2. CARD COLAPSABLE: CONVERSOR DE CRÉDITOS & POLÍTICA GLOBAL SAAS
  // ==========================================================================
  describe("2. Card Colapsable: Conversor de Créditos & Política Global", () => {
    it("permite colapsar y expandir el card de política SaaS con el botón toggle", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      // Inicialmente visible
      expect(screen.getByTestId("saas-policy-card")).toBeTruthy();
      const toggleBtn = screen.getByTestId("toggle-policy-btn");
      expect(toggleBtn.textContent).toContain("Ocultar Política IA");

      // Click para ocultar
      await act(async () => {
        fireEvent.click(toggleBtn);
      });

      expect(screen.queryByTestId("saas-policy-card")).toBeNull();
      expect(toggleBtn.textContent).toContain("Abrir Política IA");

      // Click para volver a abrir
      await act(async () => {
        fireEvent.click(toggleBtn);
      });

      expect(screen.getByTestId("saas-policy-card")).toBeTruthy();
      expect(toggleBtn.textContent).toContain("Ocultar Política IA");
    });

    it("permite editar valores de política y guardarlos con mutación PUT", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "PUT" && url.includes("/ai-credits/policy")) {
          return createMockEnvelope({
            tokens_per_credit: 1200,
            default_monthly_credits: 2500,
            credit_price_clp: 18.0,
            credit_price_usd: 0.018,
            updated_at: new Date().toISOString(),
            updated_by: "SuperAdmin",
          });
        }
        if (url.includes("/plans")) return createMockEnvelope(MOCK_SYSTEM_PLANS);
        if (url.includes("/ai-credits/policy")) return createMockEnvelope(MOCK_SAAS_POLICY);
        return createMockEnvelope({});
      });

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("input-tokens-per-credit")).toBeTruthy();
      });

      const inputTokens = screen.getByTestId("input-tokens-per-credit");
      const inputCredits = screen.getByTestId("input-default-credits");
      const inputPrice = screen.getByTestId("input-credit-price-clp");
      const saveBtn = screen.getByTestId("save-policy-btn");

      await act(async () => {
        fireEvent.change(inputTokens, { target: { value: "1200" } });
        fireEvent.change(inputCredits, { target: { value: "2500" } });
        fireEvent.change(inputPrice, { target: { value: "18" } });
      });

      await act(async () => {
        fireEvent.click(saveBtn);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/ai-credits/policy",
        expect.objectContaining({
          method: "PUT",
          body: {
            tokens_per_credit: 1200,
            default_monthly_credits: 2500,
            credit_price_clp: 18,
            credit_price_usd: 0.015,
          },
        })
      );
    });
  });

  // ==========================================================================
  // 3. MODAL CREAR PLAN: FORMULARIO, AUTO-SLUG Y MÓDULOS
  // ==========================================================================
  describe("3. Modal Crear Plan", () => {
    it("abre el modal de creación al hacer click en 'Crear Plan'", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      expect(screen.queryByTestId("plan-form-modal")).toBeNull();

      await act(async () => {
        fireEvent.click(screen.getByTestId("create-plan-btn"));
      });

      expect(screen.getByTestId("plan-form-modal")).toBeTruthy();
      expect(screen.getByText("Crear Nuevo Plan SaaS")).toBeTruthy();
    });

    it("auto-genera el slug 'plan-${slug}' al tipear el nombre comercial en modo creación", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await act(async () => {
        fireEvent.click(screen.getByTestId("create-plan-btn"));
      });

      const nameInput = screen.getByTestId("plan-form-name-input");
      const slugInput = screen.getByTestId("plan-form-slug-input") as HTMLInputElement;

      await act(async () => {
        fireEvent.change(nameInput, { target: { value: "Plan Gourmet Deluxe" } });
      });

      expect(slugInput.value).toBe("plan-gourmet-deluxe");
    });

    it("permite seleccionar todos y deseleccionar todos los módulos del catálogo", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await act(async () => {
        fireEvent.click(screen.getByTestId("create-plan-btn"));
      });

      const selectAllBtn = screen.getByTestId("select-all-modules-btn");
      const deselectAllBtn = screen.getByTestId("deselect-all-modules-btn");

      // Seleccionar todos
      await act(async () => {
        fireEvent.click(selectAllBtn);
      });

      expect(
        screen.getByText(new RegExp(`${SYSTEM_MODULE_CATALOG.length} de ${SYSTEM_MODULE_CATALOG.length}`))
      ).toBeTruthy();

      // Deseleccionar todos
      await act(async () => {
        fireEvent.click(deselectAllBtn);
      });

      expect(
        screen.getByText(new RegExp(`0 de ${SYSTEM_MODULE_CATALOG.length}`))
      ).toBeTruthy();
    });

    it("filtra módulos mediante el buscador en vivo", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await act(async () => {
        fireEvent.click(screen.getByTestId("create-plan-btn"));
      });

      const searchInput = screen.getByTestId("module-search-input");

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: "delivery" } });
      });

      expect(screen.getByTestId("module-item-delivery")).toBeTruthy();
      expect(screen.queryByTestId("module-item-contabilidad")).toBeNull();
    });

    it("envía el formulario y ejecuta createPlan cerrando el modal", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "POST" && url === "/api/v1/platform-admin/plans") {
          return createMockEnvelope({
            slug: "plan-bistro-express",
            name: "Plan Bistro Express",
            tier: 1,
            monthly_ai_credits: 800,
            description: "Para pequeños bistros",
            is_popular: false,
            is_active: true,
            max_active_users: 4,
            max_products: 300,
            max_suppliers: 15,
            max_recipes: 20,
            max_combos: 10,
            max_storage_mb: 1024,
            included_modules: ["core", "pos"],
            anchor_currency: "CLP",
            price_clp: 32990,
            price_usd: 38,
            price_eur: 35,
            price_brl: 190,
            auto_convert_fx: true,
            active_clients_count: 0,
          });
        }
        if (url.includes("/plans")) return createMockEnvelope(MOCK_SYSTEM_PLANS);
        if (url.includes("/ai-credits/policy")) return createMockEnvelope(MOCK_SAAS_POLICY);
        return createMockEnvelope({});
      });

      render(<PlansPage />, { wrapper: createWrapper() });

      await act(async () => {
        fireEvent.click(screen.getByTestId("create-plan-btn"));
      });

      await act(async () => {
        fireEvent.change(screen.getByTestId("plan-form-name-input"), {
          target: { value: "Plan Bistro Express" },
        });
        fireEvent.change(screen.getByTestId("plan-form-description-input"), {
          target: { value: "Para pequeños bistros" },
        });
        fireEvent.change(screen.getByTestId("plan-form-price-clp-input"), {
          target: { value: "32990" },
        });
        fireEvent.change(screen.getByTestId("plan-form-price-usd-input"), {
          target: { value: "38" },
        });
        fireEvent.change(screen.getByTestId("plan-form-credits-input"), {
          target: { value: "800" },
        });
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("plan-form-submit-btn"));
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/plans",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            slug: "plan-bistro-express",
            name: "Plan Bistro Express",
            price_clp: 32990,
            price_usd: 38,
            monthly_ai_credits: 800,
          }),
        })
      );

      await waitFor(() => {
        expect(screen.queryByTestId("plan-form-modal")).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 4. MODAL EDITAR PLAN
  // ==========================================================================
  describe("4. Modal Editar Plan", () => {
    it("abre el modal de edición con los datos precargados del plan seleccionado", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("edit-plan-btn-plan-pro")).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("edit-plan-btn-plan-pro"));
      });

      expect(screen.getByTestId("plan-form-modal")).toBeTruthy();
      expect(screen.getByText("Editar Plan: Plan Pro Gastronómico")).toBeTruthy();

      const nameInput = screen.getByTestId("plan-form-name-input") as HTMLInputElement;
      const slugInput = screen.getByTestId("plan-form-slug-input") as HTMLInputElement;
      const priceInput = screen.getByTestId("plan-form-price-clp-input") as HTMLInputElement;

      expect(nameInput.value).toBe("Plan Pro Gastronómico");
      expect(slugInput.value).toBe("plan-pro");
      expect(slugInput.disabled).toBe(true);
      expect(priceInput.value).toBe("69990");
    });

    it("ejecuta updatePlan al guardar cambios en el modal de edición", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "PUT" && url.includes("/plans/plan-pro")) {
          return createMockEnvelope({
            ...MOCK_SYSTEM_PLANS[1]!,
            price_clp: 74990,
          });
        }
        if (url.includes("/plans")) return createMockEnvelope(MOCK_SYSTEM_PLANS);
        if (url.includes("/ai-credits/policy")) return createMockEnvelope(MOCK_SAAS_POLICY);
        return createMockEnvelope({});
      });

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("edit-plan-btn-plan-pro")).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("edit-plan-btn-plan-pro"));
      });

      await act(async () => {
        fireEvent.change(screen.getByTestId("plan-form-price-clp-input"), {
          target: { value: "74990" },
        });
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("plan-form-submit-btn"));
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/plans/plan-pro",
        expect.objectContaining({
          method: "PUT",
          body: expect.objectContaining({
            price_clp: 74990,
          }),
        })
      );
    });
  });

  // ==========================================================================
  // 5. MODAL DE ELIMINACIÓN
  // ==========================================================================
  describe("5. Modal de Eliminación", () => {
    it("abre el modal de confirmación con advertencia de clientes activos si active_clients_count > 0", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("delete-plan-btn-plan-pro")).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("delete-plan-btn-plan-pro"));
      });

      expect(screen.getByTestId("delete-plan-modal")).toBeTruthy();
      expect(screen.getByText("¿Eliminar Plan Comercial?")).toBeTruthy();

      // MOCK_SYSTEM_PLANS[1] tiene 24 clientes activos
      expect(screen.getByText(/24/)).toBeTruthy();
      expect(screen.getByText(/bloqueo HTTP 409/i)).toBeTruthy();
    });

    it("permite cancelar la eliminación cerrando el modal", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("delete-plan-btn-plan-basico")).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("delete-plan-btn-plan-basico"));
      });

      expect(screen.getByTestId("delete-plan-modal")).toBeTruthy();

      await act(async () => {
        fireEvent.click(screen.getByTestId("cancel-delete-plan-btn"));
      });

      expect(screen.queryByTestId("delete-plan-modal")).toBeNull();
    });

    it("ejecuta deletePlan al confirmar eliminación", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "DELETE" && url.includes("/plans/plan-basico")) {
          return createMockEnvelope(MOCK_SYSTEM_PLANS[0]!);
        }
        if (url.includes("/plans")) return createMockEnvelope(MOCK_SYSTEM_PLANS);
        if (url.includes("/ai-credits/policy")) return createMockEnvelope(MOCK_SAAS_POLICY);
        return createMockEnvelope({});
      });

      render(<PlansPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("delete-plan-btn-plan-basico")).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("delete-plan-btn-plan-basico"));
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("confirm-delete-plan-btn"));
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/plans/plan-basico",
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });
  });

  // ==========================================================================
  // 6. BOTÓN ACTUALIZAR
  // ==========================================================================
  describe("6. Botón Actualizar", () => {
    it("refresca los datos y notifica con toast al hacer click en 'Actualizar'", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      const refreshBtn = screen.getByTestId("refresh-plans-btn");

      await waitFor(() => {
        expect(refreshBtn.getAttribute("disabled")).toBeNull();
      });

      await act(async () => {
        fireEvent.click(refreshBtn);
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringContaining("Catálogo de planes y política global actualizados")
        );
      });
    });
  });

  // ==========================================================================
  // 7. FASE 6 — PESTAÑAS Y PAQUETES DE CRÉDITOS IA (ADD-ON)
  // ==========================================================================
  describe("7. Fase 6 — Pestañas y Paquetes de Créditos IA (Add-On)", () => {
    it("conmuta entre la pestaña de Planes Base y la pestaña de Paquetes de Créditos IA", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      const saasTab = screen.getByTestId("tab-saas-plans");
      const aiTab = screen.getByTestId("tab-ai-packs");

      expect(saasTab).toBeTruthy();
      expect(aiTab).toBeTruthy();
      expect(saasTab.getAttribute("aria-selected")).toBe("true");

      // Conmutar a pestaña de Paquetes IA
      await act(async () => {
        fireEvent.click(aiTab);
      });

      expect(aiTab.getAttribute("aria-selected")).toBe("true");
      expect(screen.getByTestId("ai-packs-section")).toBeTruthy();
      expect(screen.getByTestId("create-ai-pack-btn")).toBeTruthy();

      // Conmutar de vuelta a pestaña SaaS
      await act(async () => {
        fireEvent.click(saasTab);
      });

      expect(saasTab.getAttribute("aria-selected")).toBe("true");
      expect(screen.getByTestId("create-plan-btn")).toBeTruthy();
    });

    it("renderiza el catálogo de paquetes de créditos IA con montos, precios, costos unitarios y reglas para hacer juego", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      // Cambiar a pestaña de Paquetes IA
      await act(async () => {
        fireEvent.click(screen.getByTestId("tab-ai-packs"));
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-packs-grid")).toBeTruthy();
      });

      // Validar los paquetes mockeados
      expect(screen.getByTestId("ai-pack-card-1")).toBeTruthy();
      expect(screen.getByTestId("ai-pack-card-2")).toBeTruthy();
      expect(screen.getByTestId("ai-pack-card-3")).toBeTruthy();

      // Validar paquete 2 (Growth Pack - popular)
      expect(screen.getByTestId("pack-name-2").textContent).toContain("Growth Pack");
      expect(screen.getByTestId("pack-popular-badge-2")).toBeTruthy();
      expect(screen.getByTestId("pack-total-credits-2").textContent).toContain("5.250");

      // Validar regla de combinación ("hacer juego")
      expect(screen.getAllByText(/Reglas de Combinación con Planes Base/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Beneficio en planes base/i).length).toBeGreaterThan(0);
    });

    it("abre el modal para crear un nuevo paquete de créditos IA y ejecuta la mutación POST con reglas de descuento para planes base", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      // Ir a pestaña de paquetes IA
      await act(async () => {
        fireEvent.click(screen.getByTestId("tab-ai-packs"));
      });

      const createBtn = screen.getByTestId("create-ai-pack-btn");
      await act(async () => {
        fireEvent.click(createBtn);
      });

      // Validar modal interactivo
      expect(screen.getByTestId("ai-credit-pack-modal")).toBeTruthy();
      expect(screen.getByText("Crear Paquete de Créditos IA (Add-On)")).toBeTruthy();

      // Completar formulario
      const nameInput = screen.getByTestId("input-ai-pack-name");
      const creditsInput = screen.getByTestId("input-ai-pack-credits");
      const bonusInput = screen.getByTestId("input-ai-pack-bonus");
      const priceClpInput = screen.getByTestId("input-ai-pack-price-clp");
      const priceUsdInput = screen.getByTestId("input-ai-pack-price-usd");
      const popularCheck = screen.getByTestId("checkbox-ai-pack-popular");
      const discountBasico = screen.getByTestId("input-discount-plan-basico");
      const discountPro = screen.getByTestId("input-discount-plan-pro");
      const discountEnterprise = screen.getByTestId("input-discount-plan-enterprise");

      await act(async () => {
        fireEvent.change(nameInput, { target: { value: "Mega Boost Pollo King (25.000)" } });
        fireEvent.change(creditsInput, { target: { value: "25000" } });
        fireEvent.change(bonusInput, { target: { value: "2500" } });
        fireEvent.change(priceClpInput, { target: { value: "189990" } });
        fireEvent.change(priceUsdInput, { target: { value: "210" } });
        fireEvent.click(popularCheck);
        fireEvent.change(discountBasico, { target: { value: "5" } });
        fireEvent.change(discountPro, { target: { value: "15" } });
        fireEvent.change(discountEnterprise, { target: { value: "30" } });
      });

      // Guardar formulario
      const saveBtn = screen.getByTestId("save-ai-pack-btn");
      await act(async () => {
        fireEvent.click(saveBtn);
      });

      await waitFor(() => {
        expect(httpClient.apiRequest).toHaveBeenCalledWith(
          "/api/v1/platform-admin/ai-packs",
          expect.objectContaining({
            method: "POST",
            body: expect.objectContaining({
              pack_name: "Mega Boost Pollo King (25.000)",
              credits_amount: 25000,
              bonus_credits: 2500,
              price_clp: 189990,
              price_usd: 210,
              is_popular: true,
              plan_tier_discounts: {
                plan_basico: 5,
                plan_pro: 15,
                plan_enterprise: 30,
              },
            }),
          })
        );
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringContaining("Mega Boost Pollo King (25.000)")
        );
      });
    });

    it("abre el modal de edición de un paquete IA con los datos precargados", async () => {
      render(<PlansPage />, { wrapper: createWrapper() });

      // Ir a pestaña de paquetes IA
      await act(async () => {
        fireEvent.click(screen.getByTestId("tab-ai-packs"));
      });

      const editBtn = screen.getByTestId("edit-ai-pack-btn-2");
      await act(async () => {
        fireEvent.click(editBtn);
      });

      expect(screen.getByTestId("ai-credit-pack-modal")).toBeTruthy();
      const nameInput = screen.getByTestId("input-ai-pack-name") as HTMLInputElement;
      expect(nameInput.value).toBe("Growth Pack (5.000 Créditos)");
    });
  });
});
