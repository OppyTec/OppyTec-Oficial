import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "./Sidebar";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { setActiveLanguage } from "@/shared/i18n";

describe("Sidebar Component Suite — Panel Unlocking and Accordions", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    localStorage.clear();
    setActiveLanguage("es");
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
      },
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  const basePolicy: RbacPolicyState = {
    roleName: "Administrador",
    isSuperUser: true,
    planModules: ["analytics", "operations", "rbac_audit", "inventory", "catalog"],
    rolePermissions: [],
    temporaryGrants: [],
    deniedPermissions: [],
  };

  const renderSidebar = (policy: RbacPolicyState = basePolicy, props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <PermissionsProvider initialPolicy={policy}>
            <Sidebar isOpen={true} {...props} />
          </PermissionsProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it("unlocks all modules and panels immediately when policy.isSuperUser is true", () => {
    renderSidebar({
      ...basePolicy,
      isSuperUser: true,
      planModules: [], // Even with empty planModules, isSuperUser grants access
    });

    // Check panel accordion headers are rendered
    const analiticaHeader = screen.getByTestId("sidebar-accordion-analitica");
    const ejecutivoHeader = screen.getByTestId("sidebar-accordion-ejecutivo");
    const actividadesHeader = screen.getByTestId("sidebar-accordion-actividades");

    expect(analiticaHeader).toBeTruthy();
    expect(ejecutivoHeader).toBeTruthy();
    expect(actividadesHeader).toBeTruthy();

    // Verify they do not have locked styling
    expect(analiticaHeader.className).not.toContain("cursor-not-allowed");
    expect(ejecutivoHeader.className).not.toContain("cursor-not-allowed");
    expect(actividadesHeader.className).not.toContain("cursor-not-allowed");
  });

  it("unlocks Analítica, Ejecutivo, and Actividades based on planModules prefix mapping", () => {
    renderSidebar({
      ...basePolicy,
      isSuperUser: false,
      roleName: "Operador",
      planModules: ["analytics", "operations"],
    });

    const analiticaHeader = screen.getByTestId("sidebar-accordion-analitica");
    const ejecutivoHeader = screen.getByTestId("sidebar-accordion-ejecutivo");
    const actividadesHeader = screen.getByTestId("sidebar-accordion-actividades");

    expect(analiticaHeader.className).not.toContain("cursor-not-allowed");
    expect(ejecutivoHeader.className).not.toContain("cursor-not-allowed");
    expect(actividadesHeader.className).not.toContain("cursor-not-allowed");
  });

  it("expands and collapses Analítica y Rendimiento accordion on click and shows sub-items", () => {
    renderSidebar();

    const analiticaHeader = screen.getByTestId("sidebar-accordion-analitica");

    // Initially closed (unless route matches /reportes)
    expect(screen.queryByText(/Resumen General/i)).toBeNull();

    // Click header to expand
    fireEvent.click(analiticaHeader);
    expect(screen.getByText(/Resumen General/i)).toBeTruthy();
    expect(screen.getByText(/Resumen Ejecutivo/i)).toBeTruthy();
    expect(screen.getByText(/Control de Pérdidas/i)).toBeTruthy();
    expect(screen.getByText(/Eficiencia Operacional/i)).toBeTruthy();
    expect(screen.getByText(/Visión Financiera/i)).toBeTruthy();

    // Click header again to collapse
    fireEvent.click(analiticaHeader);
    expect(screen.queryByText(/Resumen General/i)).toBeNull();
  });

  it("expands and collapses Panel Ejecutivo on click and shows sub-items", () => {
    renderSidebar();

    const ejecutivoHeader = screen.getByTestId("sidebar-accordion-ejecutivo");

    // Initially closed
    expect(screen.queryByText(/Usuarios/i)).toBeNull();

    // Click to expand
    fireEvent.click(ejecutivoHeader);
    expect(screen.getByText(/Usuarios/i)).toBeTruthy();

    // Click to collapse
    fireEvent.click(ejecutivoHeader);
    expect(screen.queryByText(/Usuarios/i)).toBeNull();
  });

  it("expands and collapses Panel de Actividades on click and shows sub-items", () => {
    renderSidebar();

    const actividadesHeader = screen.getByTestId("sidebar-accordion-actividades");

    // Initially closed
    expect(screen.queryByText(/Notas/i)).toBeNull();
    expect(screen.queryByText(/Tareas/i)).toBeNull();
    expect(screen.queryByText(/Horarios/i)).toBeNull();

    // Click to expand
    fireEvent.click(actividadesHeader);
    expect(screen.getByText(/Notas/i)).toBeTruthy();
    expect(screen.getByText(/Tareas/i)).toBeTruthy();
    expect(screen.getByText(/Horarios/i)).toBeTruthy();

    // Click to collapse
    fireEvent.click(actividadesHeader);
    expect(screen.queryByText(/Notas/i)).toBeNull();
  });

  it("allows keyboard interaction (Enter / Space) to expand accordions", () => {
    renderSidebar();

    const analiticaHeader = screen.getByTestId("sidebar-accordion-analitica");
    expect(screen.queryByText(/Resumen General/i)).toBeNull();

    // Press Enter to expand
    fireEvent.keyDown(analiticaHeader, { key: "Enter", code: "Enter" });
    expect(screen.getByText(/Resumen General/i)).toBeTruthy();

    // Press Space to collapse
    fireEvent.keyDown(analiticaHeader, { key: " ", code: "Space" });
    expect(screen.queryByText(/Resumen General/i)).toBeNull();
  });
});
