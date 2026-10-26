// oppytec-frontend/src/features/historial/__tests__/HistorialPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import * as httpClient from "@/shared/api/httpClient";
import { HistorialPage, sanitizeCsvField, formatCsvRow } from "../HistorialPage";
import { HistorialToolbar } from "../HistorialToolbar";
import {
  MOCK_HISTORIAL_PRODUCTS,
  MOCK_PAGINATED_RESPONSE,
} from "../mockData";

// Mock framer-motion para tests estables y deterministas
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

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("Módulo Historial y Auditoría Kardex — HistorialPage & HistorialToolbar (Fase 4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    window.history.pushState({}, "", "/historial");

    // Mock API exitoso por defecto
    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
      if (url.includes("/catalog/products")) {
        return {
          data: MOCK_HISTORIAL_PRODUCTS,
          traceId: "test-trace-products",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_inventory_test",
        };
      }
      return {
        data: MOCK_PAGINATED_RESPONSE,
        traceId: "test-trace-history",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_inventory_test",
      };
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  // ==========================================================================
  // 1. Verificación de SectionHeader (Título, Subtítulo, Color Cian #06b6d4)
  // ==========================================================================
  describe("Cabecera Visual Canónica (SectionHeader)", () => {
    it("renderiza el título 'Historial' y el subtítulo corporativo centrado", async () => {
      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Historial");
      });

      const subtitles = screen.getAllByText("Auditoría y Trazabilidad de Inventario");
      expect(subtitles.length).toBeGreaterThanOrEqual(1);
      expect(subtitles[0]).toBeInTheDocument();
    });

    it("aplica el color cian #06b6d4 corporativo al cursor y al ícono", async () => {
      const { container } = render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Historial");
      });

      const iconOrCursor = container.querySelector(
        'svg[style*="#06b6d4"], svg[style*="rgb(6, 182, 212)"], span[style*="rgb(6, 182, 212)"], span[style*="#06b6d4"]'
      );
      expect(iconOrCursor).not.toBeNull();
    });
  });

  // ==========================================================================
  // 2. Verificación de HistorialToolbar
  // ==========================================================================
  describe("Toolbar Unificado de Gobernanza (HistorialToolbar)", () => {
    it("renderiza la estructura desktop completa: selectores, badge inmutable y botón CSV", async () => {
      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("historial-toolbar")).toBeInTheDocument();
      });

      // Desktop toolbar
      expect(screen.getByTestId("historial-toolbar-desktop")).toBeInTheDocument();

      // Badge de Auditoría Inmutable
      const badge = screen.getByTestId("badge-auditoria-inmutable");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent("Auditoría Inmutable");

      // Botón Exportar CSV
      const exportBtn = screen.getByTestId("export-csv-button");
      expect(exportBtn).toBeInTheDocument();
      expect(exportBtn).toHaveTextContent("Exportar CSV");
    });

    it("renderiza la vista móvil con selectores táctiles, badge INMUTABLE y touch targets >= 44px", () => {
      render(
        <HistorialToolbar
          selectedAreaId="all"
          activeWarehouseId="all"
          isExportDisabled={false}
          recordsCount={5}
        />,
        { wrapper: createWrapper() }
      );

      const mobileToolbar = screen.getByTestId("historial-toolbar-mobile");
      expect(mobileToolbar).toBeInTheDocument();

      const mobileBadge = screen.getByTestId("badge-inmutable-mobile");
      expect(mobileBadge).toHaveTextContent("INMUTABLE");

      const mobileExportBtn = screen.getByTestId("export-csv-button-mobile");
      expect(mobileExportBtn).toHaveTextContent("Exportar CSV");
      expect(mobileExportBtn).toHaveClass("min-h-[44px]");
    });

    it("deshabilita el botón de exportación cuando no hay registros o isExportDisabled es true", () => {
      render(
        <HistorialToolbar
          selectedAreaId="all"
          activeWarehouseId="all"
          isExportDisabled={true}
          recordsCount={0}
        />,
        { wrapper: createWrapper() }
      );

      const exportBtn = screen.getByTestId("export-csv-button");
      expect(exportBtn).toBeDisabled();

      const mobileExportBtn = screen.getByTestId("export-csv-button-mobile");
      expect(mobileExportBtn).toBeDisabled();
    });

    it("habilita el botón de exportación cuando hay registros y no está explícitamente deshabilitado", () => {
      render(
        <HistorialToolbar
          selectedAreaId="all"
          activeWarehouseId="all"
          isExportDisabled={false}
          recordsCount={10}
        />,
        { wrapper: createWrapper() }
      );

      const exportBtn = screen.getByTestId("export-csv-button");
      expect(exportBtn).not.toBeDisabled();
    });
  });

  // ==========================================================================
  // 3. Verificación de Controles de Paginación Server-Side
  // ==========================================================================
  describe("Controles de Paginación Server-Side", () => {
    it("muestra el resumen descriptivo 'Mostrando X registros en esta página (Total en base de datos: Y)'", async () => {
      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("pagination-summary")).toBeInTheDocument();
      });

      const summary = screen.getByTestId("pagination-summary");
      expect(summary.textContent).toMatch(
        /Mostrando \d+ registros en esta página \(Total en base de datos: \d+\)/
      );
    });

    it("mantiene el botón 'Anterior' deshabilitado en la primera página", async () => {
      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("pagination-prev")).toBeInTheDocument();
      });

      const prevBtn = screen.getByTestId("pagination-prev");
      expect(prevBtn).toBeDisabled();
      expect(screen.getByTestId("pagination-page-indicator")).toHaveTextContent("Página 1");
    });

    it("permite avanzar con 'Siguiente' cuando existen páginas posteriores", async () => {
      // Mock con total mayor al limit para permitir avance
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
        if (url.includes("/catalog/products")) {
          return {
            data: MOCK_HISTORIAL_PRODUCTS,
            traceId: "test-trace-products",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_inventory_test",
          };
        }
        return {
          data: {
            ...MOCK_PAGINATED_RESPONSE,
            total: 100,
            limit: 10,
            total_pages: 10,
            page: 1,
          },
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_inventory_test",
        };
      });

      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("pagination-next")).toBeInTheDocument();
      });

      const nextBtn = screen.getByTestId("pagination-next");
      expect(nextBtn).not.toBeDisabled();

      fireEvent.click(nextBtn);

      await waitFor(() => {
        expect(screen.getByTestId("pagination-page-indicator")).toHaveTextContent("Página 2");
      });
    });
  });

  // ==========================================================================
  // 4. Verificación de Exportación CSV (BOM UTF-8, Sanitización Anti-Fórmulas)
  // ==========================================================================
  describe("Exportación CSV Segura y Sanitizada", () => {
    it("sanitiza correctamente valores maliciosos con prefijos =, +, -, @, \\t, \\r", () => {
      expect(sanitizeCsvField("=cmd|' /C calc'!A0")).toBe("'=cmd|' /C calc'!A0");
      expect(sanitizeCsvField("+12345")).toBe("'+12345");
      expect(sanitizeCsvField("-DDE_ATTACK")).toBe("'-DDE_ATTACK");
      expect(sanitizeCsvField("@SUM(A1:B1)")).toBe("'@SUM(A1:B1)");
      expect(sanitizeCsvField("\tTabInjection")).toBe("'\tTabInjection");
      expect(sanitizeCsvField("ValorNormal")).toBe("ValorNormal");
      expect(sanitizeCsvField(null)).toBe("");
      expect(sanitizeCsvField(undefined)).toBe("");
      expect(sanitizeCsvField(123)).toBe("123");
    });

    it("escapa comillas dobles y formatea correctamente la fila CSV", () => {
      const row = formatCsvRow(['Texto con "comillas"', "=fórmula", 45]);
      expect(row).toBe('"Texto con ""comillas""","\'=fórmula","45"');
    });

    it("descarga el archivo auditoria_inventario_YYYY-MM-DD.csv con UTF-8 BOM", async () => {
      let createdBlob: Blob | null = null;
      let downloadFilename = "";

      const mockCreateObjectURL = vi.fn((blob: Blob) => {
        createdBlob = blob;
        return "blob:http://localhost/test-blob-historial";
      });
      const mockRevokeObjectURL = vi.fn();

      window.URL.createObjectURL = mockCreateObjectURL;
      window.URL.revokeObjectURL = mockRevokeObjectURL;

      const clickSpy = vi
        .spyOn(HTMLAnchorElement.prototype, "click")
        .mockImplementation(function (this: HTMLAnchorElement) {
          downloadFilename = this.getAttribute("download") || "";
        });

      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("export-csv-button")).not.toBeDisabled();
      });

      const exportBtn = screen.getByTestId("export-csv-button");
      fireEvent.click(exportBtn);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
      expect(downloadFilename).toMatch(/^auditoria_inventario_\d{4}-\d{2}-\d{2}\.csv$/);

      // Verificamos que el Blob contenga el BOM UTF-8 exacto (\uFEFF -> 0xEF, 0xBB, 0xBF)
      expect(createdBlob).not.toBeNull();
      if (createdBlob) {
        const arrayBuffer = await new Promise<ArrayBuffer>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as ArrayBuffer);
          reader.onerror = reject;
          reader.readAsArrayBuffer(createdBlob as Blob);
        });
        const bytes = new Uint8Array(arrayBuffer);
        expect(bytes[0]).toBe(0xef);
        expect(bytes[1]).toBe(0xbb);
        expect(bytes[2]).toBe(0xbf);

        const text = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = reject;
          reader.readAsText(createdBlob as Blob);
        });
        expect(text).toContain("Fecha y Hora");
        expect(text).toContain("Saldo Resultante");
      }

      expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:http://localhost/test-blob-historial");
    });
  });

  // ==========================================================================
  // 5. Estado Vacío y Carga
  // ==========================================================================
  describe("Estados de Carga y Vacío", () => {
    it("muestra mensaje de estado vacío cuando la lista de registros está vacía", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
        if (url.includes("/catalog/products")) {
          return { data: [], traceId: "t1", timestampIso: "", tenantId: "t" };
        }
        return {
          data: { total: 0, skip: 0, limit: 50, page: 1, total_pages: 1, items: [] },
          traceId: "t2",
          timestampIso: "",
          tenantId: "t",
        };
      });

      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("historial-empty-state")).toBeInTheDocument();
      });

      expect(
        screen.getByText("No hay registros que coincidan con los filtros aplicados.")
      ).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 6. Integración del Panel de Filtros Multi-Criterio (Fase 5)
  // ==========================================================================
  describe("Integración con FiltrosHistorial (Fase 5)", () => {
    it("renderiza el panel de filtros y permite filtrar y limpiar", async () => {
      render(<HistorialPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("filtros-historial")).toBeInTheDocument();
      });

      // El input de usuario y los selectores están montados
      const inputUsuario = screen.getByPlaceholderText("Buscar por usuario...");
      expect(inputUsuario).toBeInTheDocument();

      const selectProducto = screen.getByLabelText("Filtrar por producto");
      expect(selectProducto).toBeInTheDocument();

      const selectTipo = screen.getByLabelText("Filtrar por tipo");
      expect(selectTipo).toBeInTheDocument();

      // Aplicamos un filtro de usuario
      fireEvent.change(inputUsuario, { target: { value: "Chef Mario" } });
      expect(inputUsuario).toHaveValue("Chef Mario");

      // El botón Limpiar filtros debe aparecer
      await waitFor(() => {
        expect(screen.getByTestId("btn-limpiar-filtros")).toBeInTheDocument();
      });

      // Al pulsar Limpiar filtros se restablece
      fireEvent.click(screen.getByTestId("btn-limpiar-filtros"));
      expect(screen.queryByTestId("btn-limpiar-filtros")).not.toBeInTheDocument();
    });
  });
});
