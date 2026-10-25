// oppytec-frontend/src/features/inventory/__tests__/RecuentosPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup, within } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import * as httpClient from "@/shared/api/httpClient";
import { RecuentosPage } from "../recuentos/RecuentosPage";
import { MOCK_PHYSICAL_COUNT_SESSIONS } from "../mockData";

// Mock de framer-motion
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<any>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      div: ({ children, className, onClick, ...props }: any) => (
        <div className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

function createWrapper(initialEntries = ["/recuentos"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <QueryClientProvider client={queryClient}>
          <CurrencyProvider>
            <PermissionsProvider>
              <Routes>
                <Route path="/recuentos" element={children} />
                <Route path="/contar-inventario" element={<div data-testid="page-contar">Contar Inventario Page</div>} />
                <Route path="/" element={<div data-testid="page-home">Home</div>} />
              </Routes>
            </PermissionsProvider>
          </CurrencyProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("RecuentosPage — Historial de Recuentos y Auditoría (Fase 7)", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url, options) => {
      if (typeof url === "string" && url.includes("/counts")) {
        if (options?.method === "POST" && url.includes("/approve")) {
          return { data: { ...MOCK_PHYSICAL_COUNT_SESSIONS[0], estado: "APROBADO" }, status: 200 } as any;
        }
        if (options?.method === "POST" && url.includes("/reject")) {
          return { data: { ...MOCK_PHYSICAL_COUNT_SESSIONS[0], estado: "RECHAZADO" }, status: 200 } as any;
        }
        if (options?.method === "DELETE") {
          return { data: { success: true }, status: 200 } as any;
        }
        return { data: MOCK_PHYSICAL_COUNT_SESSIONS, status: 200 } as any;
      }
      return { data: [], status: 200 } as any;
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("1. Renderiza el SectionHeader centrado con ADN OppyTec (#8b5cf6)", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    expect(screen.getByTestId("recuentos-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Historial de Recuentos/i })).toBeInTheDocument();
    expect(
      screen.getAllByText(/Consulta y gestiona las sesiones de conteo físico y auditoría/i)[0]
    ).toBeInTheDocument();
  });

  it("2. Renderiza los KPIs de auditoría con totales de actas y montos", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Total Actas")).toBeInTheDocument();
      expect(screen.getByText("Por Aprobar")).toBeInTheDocument();
      expect(screen.getByText("Conciliados")).toBeInTheDocument();
      expect(screen.getByText("Impacto Total PPP")).toBeInTheDocument();
    });
  });

  it("3. Renderiza las tarjetas de sesiones de conteo existentes", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
      expect(screen.getByTestId("recuento-card-102")).toBeInTheDocument();
      expect(screen.getByTestId("recuento-card-103")).toBeInTheDocument();
    });

    const card101 = screen.getByTestId("recuento-card-101");
    const card102 = screen.getByTestId("recuento-card-102");
    const card103 = screen.getByTestId("recuento-card-103");

    expect(within(card101).getByText("Cámara de Frío Principal")).toBeInTheDocument();
    expect(within(card102).getByText("Bodega Seca Central")).toBeInTheDocument();
    expect(within(card103).getByText("Cocina Caliente")).toBeInTheDocument();
  });

  it("4. Filtra sesiones por texto de búsqueda en tiempo real", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Buscar por bodega, responsable/i);
    fireEvent.change(searchInput, { target: { value: "Seca" } });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-102")).toBeInTheDocument();
      expect(screen.queryByTestId("recuento-card-101")).not.toBeInTheDocument();
      expect(screen.queryByTestId("recuento-card-103")).not.toBeInTheDocument();
    });
  });

  it("5. Filtra sesiones por estado (Pendientes de Aprobación)", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
    });

    const estadoSelect = screen.getByLabelText("Filtrar por estado");
    fireEvent.change(estadoSelect, { target: { value: "PENDIENTE_APROBACION" } });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
      expect(screen.queryByTestId("recuento-card-102")).not.toBeInTheDocument();
    });
  });

  it("6. Expande y colapsa el detalle del acta al hacer click en la tarjeta", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
    });

    // Detalle inicialmente cerrado
    expect(screen.queryByTestId("recuento-detail-101")).not.toBeInTheDocument();

    // Click en la tarjeta para expandir
    const cardHeader = screen.getByTestId("recuento-card-101").firstChild as HTMLElement;
    fireEvent.click(cardHeader);

    await waitFor(() => {
      expect(screen.getByTestId("recuento-detail-101")).toBeInTheDocument();
    });

    const detail = screen.getByTestId("recuento-detail-101");
    expect(within(detail).getByText("Lomo Vetado Angus Premium")).toBeInTheDocument();
    expect(within(detail).getByText("Salmón Atlántico Fresco")).toBeInTheDocument();

    // Click de nuevo para colapsar
    fireEvent.click(cardHeader);
    await waitFor(() => {
      expect(screen.queryByTestId("recuento-detail-101")).not.toBeInTheDocument();
    });
  });

  it("7. Aprueba el acta y concilia stock con impacto en Kardex", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
    });

    // Expandir acta 101 que está PENDIENTE_APROBACION
    const cardHeader = screen.getByTestId("recuento-card-101").firstChild as HTMLElement;
    fireEvent.click(cardHeader);

    await waitFor(() => {
      expect(screen.getByTestId("recuento-detail-101")).toBeInTheDocument();
    });

    const approveBtn = within(screen.getByTestId("recuento-detail-101")).getByRole("button", {
      name: /Aprobar y Conciliar Stock/i,
    });
    expect(approveBtn).toBeInTheDocument();

    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(httpClient.apiRequest).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/inventory/counts/101/approve"),
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  it("8. Abre el modal de detalle/edición rápida al presionar el botón de ojo", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recuento-card-101")).toBeInTheDocument();
    });

    const eyeBtn = within(screen.getByTestId("recuento-card-101")).getByLabelText("Ver detalle de recuento");
    fireEvent.click(eyeBtn);

    await waitFor(() => {
      expect(screen.getByText("Acta de Recuento #101")).toBeInTheDocument();
      expect(screen.getByText(/Detalle de auditoría, cuadratura de stock físico vs teórico/i)).toBeInTheDocument();
    });

    // Cerrar modal
    const closeBtn = screen.getByRole("button", { name: "Cerrar" });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText("Acta de Recuento #101")).not.toBeInTheDocument();
    });
  });

  it("9. Navega a /contar-inventario al presionar '+ Nuevo Recuento'", async () => {
    const Wrapper = createWrapper();
    render(<RecuentosPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-nuevo-recuento")).toBeInTheDocument();
    });

    const newBtn = screen.getByTestId("btn-nuevo-recuento");
    fireEvent.click(newBtn);

    await waitFor(() => {
      expect(screen.getByTestId("page-contar")).toBeInTheDocument();
    });
  });
});
