/**
 * oppytec-frontend/src/features/oppyfy/__tests__/OppyfyGovernance.test.tsx
 * Pruebas unitarias completas de la Fase 5:
 * "Frontend Panel RBAC Exclusivo y Billetera de Créditos de OppyFy"
 *
 * Casos cubiertos:
 * 1. Renderizado del panel de gobernanza y navegación fluida entre pestañas.
 * 2. Renderizado jerárquico y edición del árbol de dominios/subdominios (con modal de creación).
 * 3. Apertura, triple control de caducidad y otorgamiento de permisos temporales (con revocación).
 * 4. Gestión de billetera global del tenant, ajuste de cupos por trabajador y modal de compra Add-On.
 * 5. Visor y filtrado interactivo de eventos de auditoría de prompts (Allowed vs Blocked).
 */

import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import {
  OppyFyFeatureView,
  OppyfyGovernancePanel,
} from "../index";

const mockAdminPolicy: RbacPolicyState = {
  roleName: "Propietario / Administrador",
  planModules: ["oppyfy", "inventory", "recipes", "procurement", "finance"],
  rolePermissions: [
    "oppyfy.workspace.query",
    "oppyfy.governance.manage",
    "oppyfy.rbac.configure",
  ],
  temporaryGrants: [],
  deniedPermissions: [],
  isSuperUser: true,
};

function renderGovernanceWithProviders(ui: React.ReactElement, policy = mockAdminPolicy) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <CurrencyProvider initialCurrency="CLP">
        <PermissionsProvider initialPolicy={policy}>
          {ui}
        </PermissionsProvider>
      </CurrencyProvider>
    </QueryClientProvider>
  );
}

describe("OppyFy v2.0 - Fase 5: Gobernanza, RBAC Exclusivo & Billetera de Créditos", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 1. RENDERIZADO DEL PANEL DE GOBERNANZA Y NAVEGACIÓN POR TABS
  // ==========================================================================
  describe("Navegación e Integración de Pestañas", () => {
    it("renderiza el selector superior y conmuta fluidamente entre Workspace IA y Gobernanza & RBAC", async () => {
      renderGovernanceWithProviders(<OppyFyFeatureView />);

      // Por defecto carga en Workspace IA
      expect(screen.getByTestId("tab-main-workspace")).toHaveAttribute("aria-selected", "true");
      expect(screen.getByTestId("oppyfy-chat-pane")).toBeInTheDocument();

      // Conmutar a Gobernanza & RBAC
      const govTabBtn = screen.getByTestId("tab-main-governance");
      fireEvent.click(govTabBtn);

      expect(govTabBtn).toHaveAttribute("aria-selected", "true");
      expect(await screen.findByTestId("oppyfy-governance-panel")).toBeInTheDocument();
    });

    it("navega entre las 4 pestañas internas del panel de gobernanza", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel />);

      // Pestaña 1: Árbol de Dominios por defecto
      expect(screen.getByTestId("oppyfy-domain-tree-editor")).toBeInTheDocument();

      // Pestaña 2: Permisos Temporales
      fireEvent.click(screen.getByTestId("tab-gov-grants"));
      expect(await screen.findByTestId("oppyfy-temporary-grants-manager")).toBeInTheDocument();

      // Pestaña 3: Billeteras & Cupos
      fireEvent.click(screen.getByTestId("tab-gov-wallets"));
      expect(await screen.findByTestId("oppyfy-worker-wallets-manager")).toBeInTheDocument();

      // Pestaña 4: Auditoría de Prompts
      fireEvent.click(screen.getByTestId("tab-gov-audit"));
      expect(await screen.findByTestId("oppyfy-prompt-audit-log-viewer")).toBeInTheDocument();
    });

    it("muestra pantalla de acceso denegado si el usuario carece de permisos de gobernanza", async () => {
      const restrictedPolicy: RbacPolicyState = {
        roleName: "Ayudante de Cocina",
        planModules: ["oppyfy"],
        rolePermissions: ["oppyfy.workspace.query"], // Carece de oppyfy.governance.manage
        temporaryGrants: [],
        deniedPermissions: [],
        isSuperUser: false,
      };

      renderGovernanceWithProviders(
        <OppyFyFeatureView initialTab="governance" />,
        restrictedPolicy
      );

      expect(await screen.findByTestId("governance-access-denied")).toBeInTheDocument();
      expect(screen.queryByTestId("oppyfy-governance-panel")).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 2. ÁRBOL DE DOMINIOS Y SUBDOMINIOS
  // ==========================================================================
  describe("Árbol Jerárquico de Dominios & Capacidades", () => {
    it("despliega los dominios de negocio con badges de módulos contratados y herramientas", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="domains" />);

      expect(await screen.findByTestId("domain-card-recipes")).toBeInTheDocument();
      expect(screen.getByTestId("domain-card-inventory")).toBeInTheDocument();
      expect(screen.getByTestId("domain-card-procurement")).toBeInTheDocument();
      expect(screen.getByTestId("domain-card-finance")).toBeInTheDocument();

      // Badge de módulo contratado
      expect(screen.getByTestId("domain-contracted-badge-recipes")).toHaveTextContent("recipes");

      // Fila de subdominio
      expect(screen.getByTestId("subdomain-row-recipes_kitchen")).toBeInTheDocument();
    });

    it("permite conmutar la visibilidad de costos y el estado activo del subdominio", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="domains" />);

      const costToggle = await screen.findByTestId("subdomain-toggle-costs-recipes_kitchen");
      expect(costToggle).toHaveTextContent("Costos: Visibles");

      // Conmutar a enmascarado
      fireEvent.click(costToggle);
      expect(costToggle).toHaveTextContent("Costos: Enmascarados");

      // Conmutar estado activo
      const activeToggle = screen.getByTestId("subdomain-toggle-active-recipes_kitchen");
      expect(activeToggle).toHaveTextContent("Activo");
      fireEvent.click(activeToggle);
      expect(activeToggle).toHaveTextContent("Desactivado");
    });

    it("abre modal y crea un nuevo dominio personalizado de OppyFy", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="domains" />);

      // Abrir modal
      const openBtn = await screen.findByTestId("btn-open-create-domain");
      fireEvent.click(openBtn);

      expect(screen.getByTestId("modal-create-domain")).toBeInTheDocument();

      // Completar campos del formulario
      fireEvent.change(screen.getByTestId("input-domain-key"), {
        target: { value: "eventos_especiales" },
      });
      fireEvent.change(screen.getByTestId("input-domain-name-es"), {
        target: { value: "Eventos Especiales Pollo King" },
      });
      fireEvent.change(screen.getByTestId("input-domain-name-en"), {
        target: { value: "Special Events Pollo King" },
      });
      fireEvent.change(screen.getByTestId("input-subdomain-key"), {
        target: { value: "banquetes_vip" },
      });
      fireEvent.change(screen.getByTestId("input-subdomain-name"), {
        target: { value: "Banquetes VIP y Producción" },
      });

      // Enviar
      const submitBtn = screen.getByTestId("btn-submit-create-domain");
      fireEvent.click(submitBtn);

      // El modal debe cerrarse y el nuevo dominio debe mostrarse
      await waitFor(() => {
        expect(screen.queryByTestId("modal-create-domain")).not.toBeInTheDocument();
      });

      expect(await screen.findByTestId("domain-card-eventos_especiales")).toBeInTheDocument();
      expect(screen.getByText("Eventos Especiales Pollo King")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. PERMISOS TEMPORALES CON TRIPLE CADUCIDAD
  // ==========================================================================
  describe("Gestión de Permisos Temporales Exclusivos", () => {
    it("despliega la lista de permisos activos con detalles de caducidad", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="grants" />);

      expect(await screen.findByTestId("grant-row-grant-uuid-1")).toBeInTheDocument();
      expect(screen.getByTestId("grant-cost-badge-grant-uuid-1")).toHaveTextContent("Desbloqueado");
      expect(screen.getByTestId("grant-status-grant-uuid-1")).toHaveTextContent("Activo");
    });

    it("abre modal y otorga un permiso temporal con triple control de caducidad validado", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="grants" />);

      fireEvent.click(await screen.findByTestId("btn-open-grant-modal"));
      expect(screen.getByTestId("modal-grant-permission")).toBeInTheDocument();

      // Configurar usuario, subdominio y costos
      fireEvent.change(screen.getByTestId("select-grant-user"), { target: { value: "3" } });
      fireEvent.change(screen.getByTestId("select-grant-subdomain"), {
        target: { value: "recipes_kitchen" },
      });
      fireEvent.click(screen.getByTestId("check-grant-can-view-costs"));

      // Configurar triple caducidad
      fireEvent.change(screen.getByTestId("input-grant-expires-at"), {
        target: { value: "2026-11-20T12:00" },
      });
      fireEvent.change(screen.getByTestId("input-grant-max-prompts"), {
        target: { value: "15" },
      });
      fireEvent.change(screen.getByTestId("input-grant-temp-ceiling"), {
        target: { value: "40.00" },
      });

      // Confirmar
      fireEvent.click(screen.getByTestId("btn-submit-grant"));

      await waitFor(() => {
        expect(screen.queryByTestId("modal-grant-permission")).not.toBeInTheDocument();
      });

      // El nuevo permiso debe aparecer en la tabla
      expect(screen.getByText("Carlos Mendoza (Encargado de Compras)")).toBeInTheDocument();
    });

    it("permite revocar un permiso temporal activo", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="grants" />);

      const revokeBtn = await screen.findByTestId("btn-revoke-grant-grant-uuid-2");
      fireEvent.click(revokeBtn);

      // Ahora debe mostrarse como Inactivo
      expect(screen.getByTestId("grant-status-grant-uuid-2")).toHaveTextContent("Inactivo");
    });
  });

  // ==========================================================================
  // 4. BILLETERA DE CRÉDITOS & CUPOS POR TRABAJADOR
  // ==========================================================================
  describe("Billetera de Créditos & Asignación de Cupos", () => {
    it("muestra la bolsa global del tenant sin caducidad y tabla de trabajadores", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="wallets" />);

      expect(await screen.findByTestId("tenant-global-credit-bag")).toBeInTheDocument();
      expect(screen.getByTestId("worker-wallet-row-1")).toBeInTheDocument();
      expect(screen.getByTestId("worker-wallet-row-2")).toBeInTheDocument();
      expect(screen.getByText("Juan Pérez")).toBeInTheDocument();
    });

    it("permite activar o desactivar OppyFy para un trabajador directamente", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="wallets" />);

      const toggleWorker3 = await screen.findByTestId("toggle-worker-oppyfy-3");
      expect(toggleWorker3).toHaveTextContent("Inhabilitado");

      fireEvent.click(toggleWorker3);
      expect(toggleWorker3).toHaveTextContent("Habilitado");
    });

    it("abre modal para editar el cupo asignado de un trabajador y actualiza su saldo", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="wallets" />);

      const editBtn = await screen.findByTestId("btn-edit-worker-wallet-1");
      fireEvent.click(editBtn);

      expect(screen.getByTestId("modal-edit-worker-wallet")).toBeInTheDocument();

      const ceilingInput = screen.getByTestId("input-worker-ceiling");
      fireEvent.change(ceilingInput, { target: { value: "250.00" } });

      fireEvent.click(screen.getByTestId("btn-submit-edit-wallet"));

      await waitFor(() => {
        expect(screen.queryByTestId("modal-edit-worker-wallet")).not.toBeInTheDocument();
      });

      // El cupo en la fila debe haberse actualizado
      expect(screen.getByTestId("worker-wallet-row-1")).toHaveTextContent("250.00 cr.");
    });

    it("abre el modal de compra de paquetes Add-On y calcula cotización bonificada", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="wallets" />);

      fireEvent.click(await screen.findByTestId("btn-open-buy-pack"));
      expect(screen.getByTestId("modal-buy-credit-pack")).toBeInTheDocument();

      // Seleccionar el Pack Enterprise Pollo King
      const packCard = screen.getByTestId("credit-pack-card-2");
      fireEvent.click(packCard);

      // Debe calcular cotización con descuento SaaS
      expect(await screen.findByTestId("active-quote-box")).toBeInTheDocument();

      // Confirmar compra simulada
      fireEvent.click(screen.getByTestId("btn-confirm-buy-pack"));
      expect(await screen.findByTestId("buy-pack-success")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 5. VISOR DE AUDITORÍA DE PROMPTS
  // ==========================================================================
  describe("Visor de Auditoría de Prompts (oppyfy_prompt_audit_log)", () => {
    it("despliega eventos de auditoría y permite filtrar por estado (Blocked vs Allowed)", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="audit" />);

      // Debe contener logs iniciales
      expect(await screen.findByTestId("audit-row-1001")).toBeInTheDocument();
      expect(screen.getByTestId("audit-row-1002")).toBeInTheDocument();

      // Filtrar por 'Solo Bloqueados'
      fireEvent.click(screen.getByTestId("filter-audit-blocked"));

      expect(screen.queryByTestId("audit-row-1001")).not.toBeInTheDocument(); // 1001 era ALLOWED
      expect(screen.getByTestId("audit-row-1002")).toBeInTheDocument(); // 1002 es BLOCKED
      expect(screen.getByTestId("audit-badge-status-1002")).toHaveTextContent("BLOCKED");

      // Filtrar por 'Solo Permitidos'
      fireEvent.click(screen.getByTestId("filter-audit-allowed"));

      expect(screen.getByTestId("audit-row-1001")).toBeInTheDocument();
      expect(screen.queryByTestId("audit-row-1002")).not.toBeInTheDocument();

      // Restaurar 'Todos'
      fireEvent.click(screen.getByTestId("filter-audit-all"));
      expect(screen.getByTestId("audit-row-1001")).toBeInTheDocument();
      expect(screen.getByTestId("audit-row-1002")).toBeInTheDocument();
    });

    it("filtra registros mediante búsqueda de texto en tiempo real", async () => {
      renderGovernanceWithProviders(<OppyfyGovernancePanel initialTab="audit" />);

      const searchInput = await screen.findByTestId("input-audit-search");

      // Buscar texto específico de Pollo King
      fireEvent.change(searchInput, { target: { value: "FEFO" } });

      expect(screen.getByTestId("audit-row-1001")).toBeInTheDocument();
      expect(screen.queryByTestId("audit-row-1002")).not.toBeInTheDocument();

      // Buscar por trabajador
      fireEvent.change(searchInput, { target: { value: "Carlos Mendoza" } });
      expect(screen.getByTestId("audit-row-1004")).toBeInTheDocument();
      expect(screen.queryByTestId("audit-row-1001")).not.toBeInTheDocument();
    });
  });
});
