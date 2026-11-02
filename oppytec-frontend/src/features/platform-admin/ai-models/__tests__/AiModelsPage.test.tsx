import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { AiModelsPage } from "../AiModelsPage";
import { MOCK_AI_MODELS } from "../types";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, layout: _l, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, layout: _l, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

function createWrapper(permissions?: string[]) {
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

  const rbacState = {
    roleName: "SuperAdmin",
    isSuperUser: true,
    planModules: ["platform_admin"],
    rolePermissions: (permissions ?? [
      "platform_admin.ai_models.read",
      "platform_admin.ai_models.create",
      "platform_admin.ai_models.update",
      "platform_admin.ai_models.delete",
    ]) as any,
    temporaryGrants: [],
    deniedPermissions: [],
  };

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter>
        <PermissionsProvider initialPolicy={rbacState}>
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        </PermissionsProvider>
      </MemoryRouter>
    );
  };
}

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-ai-models-test",
  timestampIso: new Date().toISOString(),
  tenantId: "global",
});

describe("AiModelsPage — Gestión de Modelos LLM y Motores JEV (Fase 2)", () => {
  let apiRequestSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();

    apiRequestSpy = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
      if (url === "/api/v1/platform-admin/ai-models" && (!options || options.method === "GET")) {
        return createMockEnvelope(MOCK_AI_MODELS);
      }
      if (url === "/api/v1/platform-admin/ai-models" && options?.method === "POST") {
        const body = options.body;
        const newModel = {
          ...body,
          id: 99,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_deleted: false,
        };
        return createMockEnvelope(newModel);
      }
      if (url.startsWith("/api/v1/platform-admin/ai-models/") && options?.method === "PUT") {
        const slug = url.split("/").pop();
        const existing = MOCK_AI_MODELS.find((m) => m.model_slug === slug) || MOCK_AI_MODELS[0];
        const updated = {
          ...existing,
          ...options.body,
          updated_at: new Date().toISOString(),
        };
        return createMockEnvelope(updated);
      }
      if (url.startsWith("/api/v1/platform-admin/ai-models/") && options?.method === "DELETE") {
        const slug = url.split("/").pop();
        const existing = MOCK_AI_MODELS.find((m) => m.model_slug === slug) || MOCK_AI_MODELS[0];
        return createMockEnvelope({ ...existing, is_deleted: true, is_enabled: false });
      }
      return createMockEnvelope(null);
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renderiza el título, encabezado, KPIs y la lista completa de modelos", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.queryByTestId("loading-ai-models")).toBeNull();
      expect(screen.getByTestId("page-ai-models")).toBeDefined();
    });

    expect(screen.getByText(/Modelos LLM y Motores JEV/i)).toBeDefined();
    expect(screen.getByText(/FinOps AI & Router/i)).toBeDefined();

    // Verificación de modelos sembrados renderizados
    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-gemini-3.8-flash")).toBeDefined();
    });
    expect(screen.getByTestId("row-ai-model-claude-3-7-sonnet")).toBeDefined();
    expect(screen.getByTestId("row-ai-model-gpt-4o")).toBeDefined();
    expect(screen.getByTestId("row-ai-model-jev-fast-classifier")).toBeDefined();
    expect(screen.getByTestId("row-ai-model-text-embedding-004")).toBeDefined();
  });

  it("renderiza badges de Proveedor, Tier, Default, Fallback y Latencia", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-gemini-3.8-flash")).toBeDefined();
    });

    // Badge Default en gemini-3.8-flash
    expect(screen.getByTestId("badge-default-gemini-3.8-flash")).toBeDefined();

    // Badge Fallback en gpt-4o
    expect(screen.getByTestId("badge-fallback-gpt-4o")).toBeDefined();

    // Badges de Tiers
    expect(screen.getAllByTestId("badge-tier-system-2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("badge-tier-system-1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("badge-tier-embedding").length).toBeGreaterThanOrEqual(1);

    // Latencia P95
    expect(screen.getAllByTestId("badge-latency-450").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("badge-latency-50").length).toBeGreaterThanOrEqual(1);
  });

  it("filtra reactivamente por Tier (SYSTEM_1_JEV vs SYSTEM_2_LLM)", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-gemini-3.8-flash")).toBeDefined();
    });

    const tierSelect = screen.getByTestId("select-filter-tier") as HTMLSelectElement;

    // Filtrar por SYSTEM_1_JEV
    fireEvent.change(tierSelect, { target: { value: "SYSTEM_1_JEV" } });

    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-jev-fast-classifier")).toBeDefined();
      expect(screen.queryByTestId("row-ai-model-gemini-3.8-flash")).toBeNull();
      expect(screen.queryByTestId("row-ai-model-claude-3-7-sonnet")).toBeNull();
    });

    // Cambiar a SYSTEM_2_LLM
    fireEvent.change(tierSelect, { target: { value: "SYSTEM_2_LLM" } });

    await waitFor(() => {
      expect(screen.queryByTestId("row-ai-model-jev-fast-classifier")).toBeNull();
      expect(screen.getByTestId("row-ai-model-gemini-3.8-flash")).toBeDefined();
      expect(screen.getByTestId("row-ai-model-claude-3-7-sonnet")).toBeDefined();
    });
  });

  it("filtra por buscador de texto (slug o display name)", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-gemini-3.8-flash")).toBeDefined();
    });

    const searchInput = screen.getByTestId("input-search-ai-models");

    // Buscar "claude"
    fireEvent.change(searchInput, { target: { value: "claude" } });

    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-claude-3-7-sonnet")).toBeDefined();
      expect(screen.queryByTestId("row-ai-model-gemini-3.8-flash")).toBeNull();
      expect(screen.queryByTestId("row-ai-model-gpt-4o")).toBeNull();
    });

    // Limpiar búsqueda
    fireEvent.change(searchInput, { target: { value: "" } });

    await waitFor(() => {
      expect(screen.getByTestId("row-ai-model-gemini-3.8-flash")).toBeDefined();
      expect(screen.getByTestId("row-ai-model-gpt-4o")).toBeDefined();
    });
  });

  it("abre modal de detalles e inspecciona la configuración técnica del modelo", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-view-details-gemini-3.8-flash")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("btn-view-details-gemini-3.8-flash"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-ai-model-details")).toBeDefined();
    });

    expect(screen.getByText(/Ventana Máxima Contexto:/i)).toBeDefined();
    expect(screen.getByText(/1,048,576 tokens/i)).toBeDefined();

    // Cerrar modal
    fireEvent.click(screen.getByTestId("btn-close-details"));

    await waitFor(() => {
      expect(screen.queryByTestId("modal-ai-model-details")).toBeNull();
    });
  });

  it("abre modal de creación, valida campos obligatorios y envía POST para registrar modelo", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-new-ai-model")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("btn-new-ai-model"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-ai-model-form")).toBeDefined();
    });

    // Llenar formulario
    fireEvent.change(screen.getByTestId("form-input-slug"), { target: { value: "deepseek-v3" } });
    fireEvent.change(screen.getByTestId("form-input-display-name"), { target: { value: "DeepSeek V3" } });
    fireEvent.change(screen.getByTestId("form-select-provider"), { target: { value: "otro" } });
    fireEvent.change(screen.getByTestId("form-select-engine-tier"), {
      target: { value: "SYSTEM_2_LLM" },
    });
    fireEvent.change(screen.getByTestId("form-input-input-cost"), { target: { value: "0.20" } });
    fireEvent.change(screen.getByTestId("form-input-output-cost"), { target: { value: "0.80" } });
    fireEvent.change(screen.getByTestId("form-input-latency"), { target: { value: "600" } });
    fireEvent.change(screen.getByTestId("form-input-max-context"), { target: { value: "64000" } });

    // Enviar
    fireEvent.click(screen.getByTestId("btn-submit-form"));

    await waitFor(() => {
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/ai-models",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            model_slug: "deepseek-v3",
            display_name: "DeepSeek V3",
          }),
        })
      );
    });

    expect(toast.success).toHaveBeenCalled();
  });

  it("abre modal de edición con datos precargados y envía PUT para actualizar modelo", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-edit-gemini-3.8-flash")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("btn-edit-gemini-3.8-flash"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-ai-model-form")).toBeDefined();
    });

    // Slug debe estar deshabilitado en edición
    const slugInput = screen.getByTestId("form-input-slug") as HTMLInputElement;
    expect(slugInput.disabled).toBe(true);
    expect(slugInput.value).toBe("gemini-3.8-flash");

    // Modificar nombre y costo
    fireEvent.change(screen.getByTestId("form-input-display-name"), {
      target: { value: "Gemini 3.8 Flash Turbo" },
    });
    fireEvent.change(screen.getByTestId("form-input-input-cost"), {
      target: { value: "0.12" },
    });

    // Enviar
    fireEvent.click(screen.getByTestId("btn-submit-form"));

    await waitFor(() => {
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        expect.objectContaining({
          method: "PUT",
          body: expect.objectContaining({
            display_name: "Gemini 3.8 Flash Turbo",
            input_cost_per_1m_usd: 0.12,
          }),
        })
      );
    });

    expect(toast.success).toHaveBeenCalled();
  });

  it("abre modal de confirmación con advertencia de Soft-Delete y envía DELETE", async () => {
    const Wrapper = createWrapper();
    render(<AiModelsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-delete-gemini-4-argon")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("btn-delete-gemini-4-argon"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-ai-model-delete-confirm")).toBeDefined();
    });

    // Advertencia de cumplimiento FinOps
    expect(screen.getByText(/Preservación de Auditoría FinOps \(Soft-Delete\)/i)).toBeDefined();

    // Confirmar eliminación
    fireEvent.click(screen.getByTestId("btn-confirm-delete"));

    await waitFor(() => {
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/ai-models/gemini-4-argon",
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });

    expect(toast.success).toHaveBeenCalled();
  });

  it("oculta el botón Nuevo Modelo si el usuario carece de permiso RBAC create", async () => {
    // Wrapper solo con permiso de lectura
    const ReadOnlyWrapper = createWrapper(["platform_admin.ai_models.read"]);
    render(<AiModelsPage />, { wrapper: ReadOnlyWrapper });

    await waitFor(() => {
      expect(screen.getByTestId("page-ai-models")).toBeDefined();
    });

    expect(screen.queryByTestId("btn-new-ai-model")).toBeNull();
  });
});
