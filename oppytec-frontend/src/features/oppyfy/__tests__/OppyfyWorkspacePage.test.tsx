/**
 * oppytec-frontend/src/features/oppyfy/__tests__/OppyfyWorkspacePage.test.tsx
 * Pruebas unitarias para OppyfyWorkspacePage (Pantalla Completa OppyFy v2.0):
 * - Renderizado en pantalla completa con layout de 3 columnas
 * - Ticker superior de citas célebres gastronómicas
 * - Navegación al hacer clic en el botón Sparkles del Navbar hacia /oppyfy
 * - Interacción con SmartNavLink (modal para nueva pestaña o ventana actual)
 * - Cambio de especialistas gastronómicos (General, Chef, Stock, Supply, Manager)
 * - Apertura, filtrado y exportación en el Canvas Split-View
 * - Modal de Gobernanza y Ajustes OppyFy
 * - Preservación de la regla comercial "Pollo King"
 */

import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OppyfyWorkspacePage } from "../OppyfyWorkspacePage";
import { Navbar } from "@/shared/components/layout/Navbar";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency/CurrencyContext";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("OppyfyWorkspacePage — Workspace Inmersivo de Pantalla Completa", () => {
  let queryClient: QueryClient;

  const basePolicy: RbacPolicyState = {
    roleName: "Administrador",
    isSuperUser: true,
    planModules: ["inventory", "recipes", "procurement", "oppyfy", "analytics"],
    rolePermissions: [
      "oppyfy.workspace.query",
      "oppyfy.governance.manage",
      "oppyfy.rbac.configure",
    ],
    temporaryGrants: [],
    deniedPermissions: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0, staleTime: 0 },
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  const renderWorkspace = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <CurrencyProvider initialCurrency="CLP">
          <PermissionsProvider initialPolicy={basePolicy}>
            <MemoryRouter initialEntries={["/oppyfy"]}>
              <OppyfyWorkspacePage />
            </MemoryRouter>
          </PermissionsProvider>
        </CurrencyProvider>
      </QueryClientProvider>
    );

  it("1. renderiza OppyfyWorkspacePage ocupando la pantalla completa con 3 columnas", () => {
    renderWorkspace();

    const root = screen.getByTestId("oppyfy-workspace-page");
    expect(root).toBeInTheDocument();
    expect(root.className).toContain("fixed inset-0");

    expect(screen.getByTestId("oppyfy-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("oppyfy-chat-main-pane")).toBeInTheDocument();
    expect(screen.getByTestId("oppyfy-split-canvas")).toBeInTheDocument();
  });

  it("2. renderiza el ticker superior con citas célebres gastronómicas/empresariales", () => {
    renderWorkspace();

    const ticker = screen.getByTestId("quote-ticker-banner");
    expect(ticker).toBeInTheDocument();
    expect(ticker.textContent).toContain("«");
    expect(ticker.textContent).toContain("—");
  });

  it("3. permite alternar la barra lateral izquierda entre colapsada y expandida", () => {
    renderWorkspace();

    const sidebar = screen.getByTestId("oppyfy-sidebar");
    expect(sidebar.className).toContain("w-72");

    const toggleBtn = screen.getByTestId("toggle-sidebar-btn");
    fireEvent.click(toggleBtn);

    expect(sidebar.className).toContain("w-16");

    fireEvent.click(toggleBtn);
    expect(sidebar.className).toContain("w-72");
  });

  it("4. permite cambiar de especialista gastronómico mediante los filtros de la barra lateral", () => {
    renderWorkspace();

    // Cambiar a Oppy Chef
    const chefTab = screen.getByTestId("filter-tab-chef");
    fireEvent.click(chefTab);

    expect(screen.getAllByText(/Oppy Chef/i).length).toBeGreaterThan(0);

    // Cambiar a Oppy Stock
    const stockTab = screen.getByTestId("filter-tab-stock");
    fireEvent.click(stockTab);

    expect(screen.getAllByText(/Oppy Stock/i).length).toBeGreaterThan(0);
  });

  it("5. abre el modal selector de especialista al hacer clic en Nueva Conversación", () => {
    renderWorkspace();

    const newThreadBtn = screen.getByTestId("new-thread-btn");
    fireEvent.click(newThreadBtn);

    expect(screen.getByTestId("new-chat-specialist-modal")).toBeInTheDocument();
    expect(screen.getByText("¿Con quién deseas conversar?")).toBeInTheDocument();

    // Seleccionar especialista Oppy Supply
    const supplyOption = screen.getByTestId("select-specialist-supply");
    fireEvent.click(supplyOption);

    expect(screen.queryByTestId("new-chat-specialist-modal")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Oppy Supply/i).length).toBeGreaterThan(0);
  });

  it("6. interactúa con SmartNavLink abriendo el modal para navegar en nueva pestaña o ventana actual", () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    renderWorkspace();

    // Encontrar enlaces SmartNavLink en el mensaje inicial
    const smartLinks = screen.getAllByTestId("smart-nav-link");
    expect(smartLinks.length).toBeGreaterThan(0);

    // Clic en el primer SmartNavLink
    fireEvent.click(smartLinks[0]!);

    const dialog = screen.getByTestId("smart-nav-dialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByTestId("smart-nav-new-tab")).toBeInTheDocument();
    expect(screen.getByTestId("smart-nav-current-tab")).toBeInTheDocument();

    // Probar abrir en pestaña nueva
    fireEvent.click(screen.getByTestId("smart-nav-new-tab"));
    expect(openSpy).toHaveBeenCalledWith("/recipes", "_blank", "noopener,noreferrer");
    expect(screen.queryByTestId("smart-nav-dialog")).not.toBeInTheDocument();

    // Reabrir y probar navegar en ventana actual
    fireEvent.click(smartLinks[0]!);
    fireEvent.click(screen.getByTestId("smart-nav-current-tab"));
    expect(mockNavigate).toHaveBeenCalledWith("/recipes");
  });

  it("7. permite alternar la visibilidad del Canvas Split-View y filtrar la tabla", () => {
    renderWorkspace();

    expect(screen.getByTestId("oppyfy-split-canvas")).toBeInTheDocument();

    // Filtrar en la tabla del Canvas
    const filterInput = screen.getByTestId("canvas-table-filter");
    fireEvent.change(filterInput, { target: { value: "Pechuga" } });

    expect(screen.getByText("Pechuga de Pollo Fresca")).toBeInTheDocument();
    expect(screen.queryByText("Harina Especial")).not.toBeInTheDocument();

    // Cerrar el Canvas
    const closeCanvasBtn = screen.getByTestId("canvas-close-btn");
    fireEvent.click(closeCanvasBtn);

    expect(screen.queryByTestId("oppyfy-split-canvas")).not.toBeInTheDocument();

    // Volver a abrir el Canvas desde la barra superior
    const toggleCanvasBtn = screen.getByTestId("toggle-split-canvas-btn");
    fireEvent.click(toggleCanvasBtn);

    expect(screen.getByTestId("oppyfy-split-canvas")).toBeInTheDocument();
  });

  it("8. abre y cierra el modal de Gobernanza OppyFy", () => {
    renderWorkspace();

    const settingsBtn = screen.getByTestId("oppyfy-settings-btn");
    fireEvent.click(settingsBtn);

    expect(screen.getByTestId("oppyfy-governance-modal")).toBeInTheDocument();
    expect(screen.getByText("Gobernanza & Ajustes OppyFy")).toBeInTheDocument();

    const closeBtn = screen.getByTestId("close-governance-modal-btn");
    fireEvent.click(closeBtn);

    expect(screen.queryByTestId("oppyfy-governance-modal")).not.toBeInTheDocument();
  });

  it("9. preserva la regla 'Pollo King' en cotizaciones y escandallos", () => {
    renderWorkspace();

    expect(screen.getAllByText(/Escandallo Pollo King/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Pollo King Admin/i)).toBeInTheDocument();
  });

  it("10. botón 'Volver al sistema' ejecuta navegación hacia atrás", () => {
    renderWorkspace();

    const backBtn = screen.getByTestId("workspace-back-btn");
    fireEvent.click(backBtn);

    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });
});

describe("Navbar Sparkles Button — Navegación Directa a /oppyfy", () => {
  let queryClient: QueryClient;

  const basePolicy: RbacPolicyState = {
    roleName: "Administrador",
    isSuperUser: true,
    planModules: ["oppyfy"],
    rolePermissions: [],
    temporaryGrants: [],
    deniedPermissions: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0, staleTime: 0 },
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("al hacer clic en el botón Sparkles del Navbar navega directamente a /oppyfy con el título correcto", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <CurrencyProvider initialCurrency="CLP">
          <PermissionsProvider initialPolicy={basePolicy}>
            <MemoryRouter initialEntries={["/"]}>
              <Navbar />
            </MemoryRouter>
          </PermissionsProvider>
        </CurrencyProvider>
      </QueryClientProvider>
    );

    // Buscar botón Sparkles por título oficial
    const sparklesButtons = screen.getAllByTitle("OppyFy AI Workspace");
    expect(sparklesButtons.length).toBeGreaterThan(0);

    fireEvent.click(sparklesButtons[0]!);
    expect(mockNavigate).toHaveBeenCalledWith("/oppyfy");
  });
});
