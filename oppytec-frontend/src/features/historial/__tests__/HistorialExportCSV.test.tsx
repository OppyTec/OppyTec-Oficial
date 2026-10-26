// oppytec-frontend/src/features/historial/__tests__/HistorialExportCSV.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { toast } from "sonner";
import * as httpClient from "@/shared/api/httpClient";
import {
  CANONICAL_AUDIT_CSV_COLUMNS,
  sanitizeCsvField,
  formatCsvRow,
  getChileanDateIsoString,
  generateAuditoriaCsvContent,
  downloadHistorialCSV,
} from "../exportCSV";
import { HistorialPage } from "../HistorialPage";
import { HistorialToolbar } from "../HistorialToolbar";
import {
  MOCK_HISTORIAL_PRODUCTS,
  MOCK_HISTORIAL_REGISTROS,
  MOCK_PAGINATED_RESPONSE,
} from "../mockData";
import type { RegistroMovimiento } from "../types";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

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

describe("FASE 7: Motor de Exportación y Descarga Segura CSV — Historial de Auditoría Kardex", () => {
  let createdBlob: Blob | null = null;
  let downloadFilename = "";
  let objectUrlsCreated: string[] = [];
  let objectUrlsRevoked: string[] = [];
  let appendChildSpy: any;
  let removeChildSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    createdBlob = null;
    downloadFilename = "";
    objectUrlsCreated = [];
    objectUrlsRevoked = [];

    // Mock ObjectURL
    window.URL.createObjectURL = vi.fn((blob: Blob) => {
      createdBlob = blob;
      const fakeUrl = `blob:http://localhost/test-blob-${Date.now()}`;
      objectUrlsCreated.push(fakeUrl);
      return fakeUrl;
    });

    window.URL.revokeObjectURL = vi.fn((url: string) => {
      objectUrlsRevoked.push(url);
    });

    // Spies para clic y ciclo de vida de DOM de enlaces <a>
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      downloadFilename = this.getAttribute("download") || "";
    });

    appendChildSpy = vi.spyOn(document.body, "appendChild") as any;
    removeChildSpy = vi.spyOn(document.body, "removeChild") as any;

    // Mock de API exitosa por defecto
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
  // 1. Verificación del botón deshabilitado cuando no hay registros o está cargando
  // ==========================================================================
  describe("1. Control de Habilitación y Deshabilitación del Botón de Exportación", () => {
    it("deshabilita el botón de exportación en Desktop y Mobile cuando recordsCount === 0", () => {
      const mockExport = vi.fn();
      render(
        <HistorialToolbar
          recordsCount={0}
          isExportDisabled={true}
          onExportCSV={mockExport}
        />
      );

      const desktopBtn = screen.getByTestId("export-csv-button");
      const mobileBtn = screen.getByTestId("export-csv-button-mobile");

      expect(desktopBtn).toBeDisabled();
      expect(mobileBtn).toBeDisabled();

      fireEvent.click(desktopBtn);
      fireEvent.click(mobileBtn);

      expect(mockExport).not.toHaveBeenCalled();
    });

    it("deshabilita el botón de exportación cuando isExportDisabled={true} incluso con registros", () => {
      const mockExport = vi.fn();
      render(
        <HistorialToolbar
          recordsCount={10}
          isExportDisabled={true}
          onExportCSV={mockExport}
        />
      );

      expect(screen.getByTestId("export-csv-button")).toBeDisabled();
      expect(screen.getByTestId("export-csv-button-mobile")).toBeDisabled();
    });

    it("habilita el botón cuando existen registros y isExportDisabled={false}", () => {
      const mockExport = vi.fn();
      render(
        <HistorialToolbar
          recordsCount={5}
          isExportDisabled={false}
          onExportCSV={mockExport}
        />
      );

      const desktopBtn = screen.getByTestId("export-csv-button");
      expect(desktopBtn).not.toBeDisabled();

      fireEvent.click(desktopBtn);
      expect(mockExport).toHaveBeenCalledTimes(1);
    });

    it("la función downloadHistorialCSV retorna false y no ejecuta descarga si registros está vacío", () => {
      const result = downloadHistorialCSV([]);
      expect(result).toBe(false);
      expect(window.URL.createObjectURL).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 2. Verificación de la estructura de columnas del CSV generado
  // ==========================================================================
  describe("2. Estructura Canónica de Columnas del Informe de Auditoría", () => {
    it("incluye exactamente las 9 columnas canónicas en la cabecera", () => {
      expect(CANONICAL_AUDIT_CSV_COLUMNS).toEqual([
        "Fecha y Hora",
        "Bodega",
        "Producto",
        "Tipo de Movimiento",
        "Cantidad",
        "Unidad",
        "Usuario",
        "Motivo / Notas",
        "Saldo Resultante",
      ]);
      expect(CANONICAL_AUDIT_CSV_COLUMNS.length).toBe(9);
    });

    it("genera exactamente 9 columnas en cada fila de datos de auditoría", () => {
      const csv = generateAuditoriaCsvContent(MOCK_HISTORIAL_REGISTROS);
      // Remueve el BOM y separa por líneas
      const lines = csv.replace("\uFEFF", "").split("\r\n").filter(Boolean);

      // Línea 0: Cabecera
      const headerCols = (lines[0] ?? "").split('","');
      expect(headerCols.length).toBe(9);

      // Líneas de datos
      for (let i = 1; i < lines.length; i++) {
        // Validación de formato RFC 4180 básico
        const cols = (lines[i] ?? "").split('","');
        expect(cols.length).toBe(9);
      }
    });

    it("aplica fallbacks elegantes cuando faltan nombres de producto, bodega o usuario", () => {
      const registroIncompleto: RegistroMovimiento = {
        id: 999,
        producto_id: 42,
        cantidad: 10,
        tipo_movimiento: "ajuste",
        motivo_merma: null,
        usuario_id: 0,
        created_at: "2026-10-25T10:00:00Z",
        bodega_id: 7,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
      };

      const csv = generateAuditoriaCsvContent([registroIncompleto], {
        prodName: (id) => `Insumo Especial #${id}`,
        prodUnit: () => "unidad",
      });

      expect(csv).toContain("Bodega #7");
      expect(csv).toContain("Insumo Especial #42");
      expect(csv).toContain("Sistema");
      expect(csv).toContain("unidad");
    });

    it("concatena correctamente motivo_merma y descripcion_merma en la columna Motivo / Notas", () => {
      const registroConNotas: RegistroMovimiento = {
        id: 1001,
        producto_id: 1,
        cantidad: -2,
        tipo_movimiento: "merma",
        motivo_merma: "Caducidad",
        usuario_id: 1,
        created_at: "2026-10-25T11:00:00Z",
        bodega_id: 1,
        descripcion_merma: "Lote vencido en refrigerador",
        fecha_recuento: "2026-10-25",
        user_display_name: "Admin Auditor",
        nombre_producto: "Carne Premium",
        nombre_bodega: "Cámara 1",
        unidad_medida: "kg",
        saldo_resultante: 50,
      };

      const csv = generateAuditoriaCsvContent([registroConNotas]);
      expect(csv).toContain("Caducidad - Lote vencido en refrigerador");
    });
  });

  // ==========================================================================
  // 3. Verificación del BOM UTF-8 (\uFEFF) y preservación de caracteres
  // ==========================================================================
  describe("3. Codificación UTF-8 con BOM (\\uFEFF) para Excel", () => {
    it("antepone el caracter BOM exacto \\uFEFF al contenido CSV", () => {
      const csv = generateAuditoriaCsvContent(MOCK_HISTORIAL_REGISTROS);
      expect(csv.startsWith("\uFEFF")).toBe(true);
      expect(csv.charCodeAt(0)).toBe(0xfeff);
    });

    it("el Blob generado incluye los bytes de cabecera UTF-8 BOM 0xEF, 0xBB, 0xBF", async () => {
      downloadHistorialCSV(MOCK_HISTORIAL_REGISTROS);

      expect(createdBlob).not.toBeNull();
      expect(createdBlob?.type).toBe("text/csv;charset=utf-8;");

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
    });

    it("preserva caracteres en español, acentos, tildes y eñes sin alteración", async () => {
      const registrosEspanol: RegistroMovimiento[] = [
        {
          id: 501,
          producto_id: 1,
          cantidad: 12,
          tipo_movimiento: "entrada",
          motivo_merma: null,
          usuario_id: 1,
          created_at: "2026-10-25T12:00:00Z",
          bodega_id: 1,
          descripcion_merma: "Recepción de piña y ñandú en cámara de frío",
          fecha_recuento: "2026-10-25",
          user_display_name: "Gonzalo Ñáñez",
          nombre_producto: "Salmón Atlántico & Champiñón",
          nombre_bodega: "Bodega Fría N°2 — Principal",
          unidad_medida: "kg",
          saldo_resultante: 40,
        },
      ];

      downloadHistorialCSV(registrosEspanol);

      const text = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsText(createdBlob as Blob);
      });

      expect(text).toContain("Salmón Atlántico & Champiñón");
      expect(text).toContain("Bodega Fría N°2 — Principal");
      expect(text).toContain("Gonzalo Ñáñez");
      expect(text).toContain("Recepción de piña y ñandú en cámara de frío");
    });
  });

  // ==========================================================================
  // 4. Verificación de Sanitización Anti-Inyección CSV (CWE-1236)
  // ==========================================================================
  describe("4. Sanitización Estricta Anti-Inyección CSV (Fórmulas Maliciosas)", () => {
    it("escapa celdas que inician con '=', '+', '-', '@' anteponiendo comilla simple", () => {
      expect(sanitizeCsvField("=SUM(A1:B10)")).toBe("'=SUM(A1:B10)");
      expect(sanitizeCsvField("=cmd|' /C calc'!A0")).toBe("'=cmd|' /C calc'!A0");
      expect(sanitizeCsvField("+123")).toBe("'+123");
      expect(sanitizeCsvField("+cmd|' /C calc'!A0")).toBe("'+cmd|' /C calc'!A0");
      expect(sanitizeCsvField("-DDE(\"cmd\";\"/C calc\";\"__DdeLink__\")")).toBe(
        "'-DDE(\"cmd\";\"/C calc\";\"__DdeLink__\")"
      );
      expect(sanitizeCsvField("@SUM(1,2)")).toBe("'@SUM(1,2)");
      expect(sanitizeCsvField("@CMD")).toBe("'@CMD");
    });

    it("escapa celdas que contienen espacios o caracteres de control iniciales antes de la fórmula", () => {
      expect(sanitizeCsvField("   =1+1")).toBe("'   =1+1");
      expect(sanitizeCsvField("\t+payload")).toBe("'\t+payload");
      expect(sanitizeCsvField("\r@malicious")).toBe("'\r@malicious");
      expect(sanitizeCsvField("  -formula")).toBe("'  -formula");
    });

    it("preserva intactos valores alfanuméricos seguros y maneja nulos", () => {
      expect(sanitizeCsvField("Lomo Vetado Angus")).toBe("Lomo Vetado Angus");
      expect(sanitizeCsvField("12345")).toBe("12345");
      expect(sanitizeCsvField("conteo")).toBe("conteo");
      expect(sanitizeCsvField(null)).toBe("");
      expect(sanitizeCsvField(undefined)).toBe("");
    });

    it("escapa comillas dobles internas según estándar RFC 4180", () => {
      const row = formatCsvRow(['Queso "Chanco" Mantecoso', '=2+2']);
      expect(row).toBe('"Queso ""Chanco"" Mantecoso","\'=2+2"');
    });

    it("sanitiza intentos de inyección en campos de producto, notas y usuario en el CSV final", () => {
      const ataqueCsv: RegistroMovimiento[] = [
        {
          id: 666,
          producto_id: 1,
          cantidad: 1,
          tipo_movimiento: "ajuste",
          motivo_merma: "=1+1",
          usuario_id: 1,
          created_at: "2026-10-25T15:00:00Z",
          bodega_id: 1,
          descripcion_merma: "@SUM(1:100)",
          fecha_recuento: "2026-10-25",
          user_display_name: "+56912345678",
          nombre_producto: "=cmd|' /C calc'!A0",
          nombre_bodega: "-BodegaMaliciosa",
          unidad_medida: "kg",
          saldo_resultante: 10,
        },
      ];

      const csv = generateAuditoriaCsvContent(ataqueCsv);
      expect(csv).toContain("\"'=cmd|' /C calc'!A0\"");
      expect(csv).toContain("'-BodegaMaliciosa");
      expect(csv).toContain("'+56912345678");
      expect(csv).toContain("'=1+1");
      expect(csv).toContain("'@SUM(1:100)");
    });
  });

  // ==========================================================================
  // 5. Verificación de Formato Before/After en Conteos
  // ==========================================================================
  describe("5. Manejo y Formateo Before/After en Conteos y Conciliaciones", () => {
    it("formatea la celda de cantidad como '{before} -> {after}' en movimientos de conteo con deltas", () => {
      const conteoConDeltas: RegistroMovimiento = {
        id: 701,
        producto_id: 1,
        cantidad: 15,
        tipo_movimiento: "conteo",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T14:30:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        user_display_name: "Auditor Conteo",
        nombre_producto: "Lomo Vetado Angus",
        nombre_bodega: "Cámara Fría",
        unidad_medida: "kg",
        saldo_resultante: 35,
        delta_before: 20,
        delta_after: 35,
      };

      const csv = generateAuditoriaCsvContent([conteoConDeltas]);
      expect(csv).toContain('"20 -> 35"');
    });

    it("formatea la celda de cantidad como '{before} -> {after}' en ajuste_auditoria con deltas", () => {
      const ajusteAuditoria: RegistroMovimiento = {
        id: 702,
        producto_id: 2,
        cantidad: -5,
        tipo_movimiento: "ajuste_auditoria",
        motivo_merma: "Diferencia física",
        usuario_id: 1,
        created_at: "2026-10-25T14:40:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        saldo_resultante: 45,
        delta_before: 50,
        delta_after: 45,
      };

      const csv = generateAuditoriaCsvContent([ajusteAuditoria]);
      expect(csv).toContain('"50 -> 45"');
    });

    it("utiliza fallback matemático de estimación before = saldo_resultante - cantidad cuando no vienen deltas", () => {
      const conteoSinDeltas: RegistroMovimiento = {
        id: 703,
        producto_id: 3,
        cantidad: 10,
        tipo_movimiento: "conteo",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T14:50:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        saldo_resultante: 30, // before = 30 - 10 = 20
      };

      const csv = generateAuditoriaCsvContent([conteoSinDeltas]);
      expect(csv).toContain('"20 -> 30"');
    });

    it("despliega cantidad numérica simple sin flecha en otros tipos de movimiento (compra, consumo, etc.)", () => {
      const consumoMov: RegistroMovimiento = {
        id: 704,
        producto_id: 4,
        cantidad: -4.5,
        tipo_movimiento: "consumo",
        motivo_merma: null,
        usuario_id: 2,
        created_at: "2026-10-25T13:15:00Z",
        bodega_id: 1,
        descripcion_merma: "Servicio almuerzo",
        fecha_recuento: "2026-10-25",
        saldo_resultante: 12.0,
      };

      const csv = generateAuditoriaCsvContent([consumoMov]);
      expect(csv).toContain('"\'-4.5"'); // Sanitizado con ' por iniciar con -
      expect(csv).not.toContain("->");
    });
  });

  // ==========================================================================
  // 6. Verificación de Nomenclatura del Archivo y Zona Horaria Local Chilena
  // ==========================================================================
  describe("6. Nomenclatura Canónica del Archivo y Zona Horaria Local Chilena", () => {
    it("genera el formato de fecha ISO YYYY-MM-DD en America/Santiago", () => {
      const fechaChilena = getChileanDateIsoString();
      expect(fechaChilena).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it("formatea correctamente fechas arbitrarias en zona horaria America/Santiago", () => {
      // 2026-03-15T02:00:00Z -> En Chile (UTC-3) corresponde a 2026-03-14 23:00
      const utcDate = new Date("2026-03-15T02:00:00Z");
      const localDate = getChileanDateIsoString(utcDate);
      expect(localDate).toBe("2026-03-14");
    });

    it("asigna el nombre exacto auditoria_inventario_YYYY-MM-DD.csv al atributo download", () => {
      downloadHistorialCSV(MOCK_HISTORIAL_REGISTROS);
      const expectedDate = getChileanDateIsoString();
      expect(downloadFilename).toBe(`auditoria_inventario_${expectedDate}.csv`);
    });
  });

  // ==========================================================================
  // 7. Verificación de Limpieza del DOM y Revocación de URL
  // ==========================================================================
  describe("7. Gestión del Ciclo de Vida del DOM y Revocación de ObjectURL", () => {
    it("crea un elemento <a>, lo añade al DOM, simula clic, lo remueve y revoca la URL creada", () => {
      downloadHistorialCSV(MOCK_HISTORIAL_REGISTROS);

      // Verificación de llamadas
      expect(window.URL.createObjectURL).toHaveBeenCalledTimes(1);
      expect(appendChildSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
      expect(window.URL.revokeObjectURL).toHaveBeenCalledTimes(1);

      // El ObjectURL revocado coincide exactamente con el creado
      expect(objectUrlsRevoked[0]).toBe(objectUrlsCreated[0]);

      // No quedan elementos <a> huérfanos con data de descarga en document.body
      const residualLinks = document.querySelectorAll(
        `a[download^="auditoria_inventario_"]`
      );
      expect(residualLinks.length).toBe(0);
    });
  });

  // ==========================================================================
  // 8. Verificación de Feedback de Notificación con Sonner Toast
  // ==========================================================================
  describe("8. Feedback de Notificación con Sonner Toast", () => {
    it("despacha toast.success('Auditoría exportada exitosamente') al completar la descarga", () => {
      downloadHistorialCSV(MOCK_HISTORIAL_REGISTROS);
      expect(toast.success).toHaveBeenCalledWith("Auditoría exportada exitosamente");
    });
  });

  // ==========================================================================
  // 9. Integración End-to-End en HistorialPage
  // ==========================================================================
  describe("9. Integración Completa en HistorialPage", () => {
    it("ejecuta el flujo completo de exportación CSV al hacer clic en el botón de la Toolbar", async () => {
      render(<HistorialPage />, { wrapper: createWrapper() });

      // Espera a que los datos se carguen y el botón esté habilitado
      await waitFor(() => {
        expect(screen.getByTestId("export-csv-button")).not.toBeDisabled();
      });

      const exportBtn = screen.getByTestId("export-csv-button");
      fireEvent.click(exportBtn);

      // Verificaciones consolidadas
      expect(window.URL.createObjectURL).toHaveBeenCalled();
      expect(downloadFilename).toMatch(/^auditoria_inventario_\d{4}-\d{2}-\d{2}\.csv$/);
      expect(window.URL.revokeObjectURL).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith("Auditoría exportada exitosamente");
    });
  });
});
