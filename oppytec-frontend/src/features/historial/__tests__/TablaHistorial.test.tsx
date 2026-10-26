// oppytec-frontend/src/features/historial/__tests__/TablaHistorial.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  TablaHistorial,
  getTipoBadgeClass,
  formatTipoLabel,
  formatChileDate,
  formatChileTime,
  formatCanonicalChileDateTime,
} from "../TablaHistorial";
import type { RegistroMovimiento } from "../types";

// Mock de useAuth y usePermissions para controlar visibilidad RBAC determinista
const mockAuth = {
  isGlobalAdmin: false,
  user: {
    id: 1,
    username: "testuser",
    role: "operator",
    isSuperuser: false,
    isGlobalAdmin: false,
  },
};

const mockPermissions = {
  can: vi.fn((_perm: string) => false),
};

vi.mock("@/shared/auth/usePermissions", () => ({
  useAuth: () => mockAuth,
  usePermissions: () => mockPermissions,
  AUTH_TOKEN_STORAGE_KEY: "oppytec_access_token",
  AUTH_USER_STORAGE_KEY: "oppytec_auth_user",
}));

const mockRegistros: RegistroMovimiento[] = [
  {
    id: 101,
    producto_id: "prod-1",
    cantidad: 15.5,
    tipo_movimiento: "compra",
    motivo_merma: null,
    usuario_id: 10,
    created_at: "2026-10-25T14:30:00.000Z",
    bodega_id: "bodega-central",
    descripcion_merma: "Factura FC-9812",
    fecha_recuento: "2026-10-25",
    user_display_name: "Ignacio Soto",
    nombre_producto: "Harina de Trigo Premium",
    nombre_bodega: "Bodega Principal",
    unidad_medida: "kg",
    saldo_resultante: 120.0,
  },
  {
    id: 102,
    producto_id: "prod-2",
    cantidad: -4.0,
    tipo_movimiento: "consumo",
    motivo_merma: null,
    usuario_id: 11,
    created_at: "2026-10-25T15:00:00.000Z",
    bodega_id: "bodega-cocina",
    descripcion_merma: "Turno Tarde",
    fecha_recuento: "2026-10-25",
    user_display_name: "Chef Mario",
    nombre_producto: "Aceite de Oliva Extra Virgen",
    nombre_bodega: "Bodega Cocina",
    unidad_medida: "L",
    saldo_resultante: 40.0,
  },
  {
    id: 103,
    producto_id: "prod-3",
    cantidad: -2.0,
    tipo_movimiento: "merma",
    motivo_merma: "Vencimiento",
    usuario_id: 12,
    created_at: "2026-10-25T16:15:00.000Z",
    bodega_id: "bodega-central",
    descripcion_merma: "Lote L-2026-09",
    fecha_recuento: "2026-10-25",
    user_display_name: "Auditor Interno",
    nombre_producto: "Queso Mozzarella",
    nombre_bodega: "Bodega Tránsito",
    unidad_medida: "kg",
    saldo_resultante: 18.0,
  },
  {
    id: 104,
    producto_id: "prod-4",
    cantidad: -10.0,
    tipo_movimiento: "transferencia",
    motivo_merma: null,
    usuario_id: 10,
    created_at: "2026-10-25T17:00:00.000Z",
    bodega_id: "bodega-central",
    descripcion_merma: "salida",
    fecha_recuento: "2026-10-25",
    user_display_name: "Ignacio Soto",
    nombre_producto: "Carne Vacuno Posta",
    nombre_bodega: "Bodega Principal",
    unidad_medida: "kg",
    saldo_resultante: 50.0,
  },
  {
    id: 105,
    producto_id: "prod-4",
    cantidad: 10.0,
    tipo_movimiento: "transferencia",
    motivo_merma: null,
    usuario_id: 10,
    created_at: "2026-10-25T17:05:00.000Z",
    bodega_id: "bodega-bar",
    descripcion_merma: "entrada",
    fecha_recuento: "2026-10-25",
    user_display_name: "Ignacio Soto",
    nombre_producto: "Carne Vacuno Posta",
    nombre_bodega: "Bodega Bar",
    unidad_medida: "kg",
    saldo_resultante: 35.0,
  },
  {
    id: 106,
    producto_id: "prod-5",
    cantidad: 5.0,
    tipo_movimiento: "conteo",
    motivo_merma: null,
    usuario_id: 15,
    created_at: "2026-10-25T18:00:00.000Z",
    bodega_id: "bodega-central",
    descripcion_merma: "Recuento físico semanal",
    fecha_recuento: "2026-10-25",
    user_display_name: "Supervisora Ana",
    nombre_producto: "Levadura Seca",
    nombre_bodega: "Bodega Principal",
    unidad_medida: "paq",
    saldo_resultante: 30.0,
    delta_before: 25.0,
    delta_after: 30.0,
  },
  {
    id: 107,
    producto_id: "prod-6",
    cantidad: 8.0,
    tipo_movimiento: "ajuste_auditoria",
    motivo_merma: null,
    usuario_id: 15,
    created_at: "2026-10-25T19:00:00.000Z",
    bodega_id: "bodega-central",
    descripcion_merma: "Corrección de acta",
    fecha_recuento: "2026-10-25",
    user_display_name: "Supervisora Ana",
    nombre_producto: "Azúcar Flor",
    nombre_bodega: "Bodega Principal",
    unidad_medida: "kg",
    saldo_resultante: 48.0,
    delta_before: 40.0,
    delta_after: 48.0,
  },
  {
    id: 108,
    producto_id: "prod-7",
    cantidad: -3.0,
    tipo_movimiento: "reversion",
    motivo_merma: "Error de digitación",
    usuario_id: 1,
    created_at: "2026-10-25T20:00:00.000Z",
    bodega_id: "bodega-central",
    descripcion_merma: "Reversión de movimiento previo",
    fecha_recuento: "2026-10-25",
    user_display_name: "Admin Sistema",
    nombre_producto: "Mantequilla con Sal",
    nombre_bodega: "Bodega Principal",
    unidad_medida: "kg",
    saldo_resultante: 22.0,
  },
];

describe("Módulo Historial — Tabla Multidimensional de Trazabilidad (TablaHistorial.tsx - Fase 6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.isGlobalAdmin = false;
    mockAuth.user.role = "operator";
    mockAuth.user.isSuperuser = false;
    mockPermissions.can.mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. Renderizado de Columnas y Encabezados
  // ==========================================================================
  describe("Cabecera y Estructura Técnica", () => {
    it("renderiza todos los encabezados técnicos canónicos", () => {
      render(<TablaHistorial registros={mockRegistros} canViewUsers={true} />);

      expect(screen.getByText("Fecha y hora")).toBeInTheDocument();
      expect(screen.getByText("Producto")).toBeInTheDocument();
      expect(screen.getByText("Tipo")).toBeInTheDocument();
      expect(screen.getByText("Bodega")).toBeInTheDocument();
      expect(screen.getByText("Cantidad")).toBeInTheDocument();
      expect(screen.getByText("Usuario")).toBeInTheDocument();
      expect(screen.getByText("Motivo")).toBeInTheDocument();
    });

    it("aplica clases de diseño técnico y overflow horizontal", () => {
      const { container } = render(<TablaHistorial registros={mockRegistros} />);
      const wrapper = container.querySelector('[data-testid="tabla-historial"]');
      expect(wrapper).toHaveClass("overflow-x-auto", "rounded-lg", "border", "shadow-sm");
    });
  });

  // ==========================================================================
  // 2. Badges Semánticos Cromáticos por Tipo de Movimiento
  // ==========================================================================
  describe("Badges Semánticos Cromáticos", () => {
    it("traduce correctamente las etiquetas legibles con formatTipoLabel", () => {
      expect(formatTipoLabel("compra")).toBe("Compra");
      expect(formatTipoLabel("conteo")).toBe("Conteo");
      expect(formatTipoLabel("merma")).toBe("Merma");
      expect(formatTipoLabel("ajuste_auditoria")).toBe("Ajuste Auditoría");
      expect(formatTipoLabel("transferencia")).toBe("Transferencia");
    });

    it("asigna verde (emerald) a compra, entrada y ajuste_positivo", () => {
      const classCompra = getTipoBadgeClass("compra");
      const classEntrada = getTipoBadgeClass("entrada");
      const classAjustePos = getTipoBadgeClass("ajuste_positivo");

      expect(classCompra).toContain("emerald");
      expect(classEntrada).toContain("emerald");
      expect(classAjustePos).toContain("emerald");
    });

    it("asigna rojo (destructive/red) a consumo, merma, salida y ajuste_negativo", () => {
      const classConsumo = getTipoBadgeClass("consumo");
      const classMerma = getTipoBadgeClass("merma");
      const classSalida = getTipoBadgeClass("salida");
      const classAjusteNeg = getTipoBadgeClass("ajuste_negativo");

      expect(classConsumo).toContain("red");
      expect(classMerma).toContain("red");
      expect(classSalida).toContain("red");
      expect(classAjusteNeg).toContain("red");
    });

    it("asigna cian a transferencia", () => {
      const classTransf = getTipoBadgeClass("transferencia");
      expect(classTransf).toContain("cyan");
    });

    it("asigna púrpura/índigo a conteo y ajuste_auditoria", () => {
      const classConteo = getTipoBadgeClass("conteo");
      const classAudit = getTipoBadgeClass("ajuste_auditoria");

      expect(classConteo).toContain("purple");
      expect(classAudit).toContain("purple");
    });

    it("asigna ámbar a reversion y redo", () => {
      const classReversion = getTipoBadgeClass("reversion");
      const classRedo = getTipoBadgeClass("redo");

      expect(classReversion).toContain("amber");
      expect(classRedo).toContain("amber");
    });

    it("renderiza badges visuales en la tabla para cada registro", () => {
      render(<TablaHistorial registros={mockRegistros} />);

      const badgeCompra = screen.getByTestId("badge-tipo-101");
      expect(badgeCompra).toHaveTextContent("Compra");
      expect(badgeCompra).toHaveClass("bg-emerald-100");

      const badgeConsumo = screen.getByTestId("badge-tipo-102");
      expect(badgeConsumo).toHaveTextContent("Consumo");
      expect(badgeConsumo).toHaveClass("bg-red-100");

      const badgeMerma = screen.getByTestId("badge-tipo-103");
      expect(badgeMerma).toHaveTextContent("Merma");
      expect(badgeMerma).toHaveClass("bg-red-100");

      const badgeConteo = screen.getByTestId("badge-tipo-106");
      expect(badgeConteo).toHaveTextContent("Conteo");
      expect(badgeConteo).toHaveClass("bg-purple-100");

      const badgeReversion = screen.getByTestId("badge-tipo-108");
      expect(badgeReversion).toHaveTextContent("Reversión");
      expect(badgeReversion).toHaveClass("bg-amber-100");
    });
  });

  // ==========================================================================
  // 3. Formateo de Fecha y Hora en Timezone America/Santiago
  // ==========================================================================
  describe("Timezone Canónico America/Santiago", () => {
    it("formatea la fecha a representación estándar chilena dd-MM-yyyy o dd/MM/yyyy", () => {
      const formattedDate = formatChileDate("2026-10-25T14:30:00.000Z", "America/Santiago");
      // 2026-10-25 en Santiago de Chile
      expect(formattedDate).toMatch(/^(24|25)[-/]10[-/]2026$/);
    });

    it("formatea la hora a 24 horas HH:mm:ss", () => {
      const formattedTime = formatChileTime("2026-10-25T14:30:00.000Z", "America/Santiago");
      expect(formattedTime).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    });

    it("genera formato canónico completo dd-MM-yyyy HH:mm:ss", () => {
      const canonical = formatCanonicalChileDateTime("2026-10-25T14:30:00.000Z", "America/Santiago");
      expect(canonical).toMatch(/^\d{2}-\d{2}-2026 \d{2}:\d{2}:\d{2}$/);
    });

    it("soporta zonas horarias configurables por prop", () => {
      render(
        <TablaHistorial
          registros={[mockRegistros[0]!]}
          timezone="UTC"
        />
      );

      // En UTC 14:30:00 debe figurar la fecha del día y la hora exacta 14:30:00
      expect(screen.getByText(/25[-/]10[-/]2026/)).toBeInTheDocument();
      expect(screen.getByText("14:30:00")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. Indicadores de Dirección de Transferencias
  // ==========================================================================
  describe("Indicadores de Dirección de Transferencias", () => {
    it("renderiza flecha ↑ para Traspaso Saliente", () => {
      render(<TablaHistorial registros={[mockRegistros[3]!]} />);

      const transferOut = screen.getByTestId("transfer-direction-out");
      expect(transferOut).toBeInTheDocument();
      expect(transferOut).toHaveTextContent("↑");
      expect(transferOut).toHaveAttribute("title", "Traspaso Saliente");
    });

    it("renderiza flecha ↓ para Traspaso Entrante", () => {
      render(<TablaHistorial registros={[mockRegistros[4]!]} />);

      const transferIn = screen.getByTestId("transfer-direction-in");
      expect(transferIn).toBeInTheDocument();
      expect(transferIn).toHaveTextContent("↓");
      expect(transferIn).toHaveAttribute("title", "Traspaso Entrante");
    });
  });

  // ==========================================================================
  // 5. Visualización Before/After en Conteos y Ajustes
  // ==========================================================================
  describe("Visualización Before/After en Conteos", () => {
    it("muestra la transición anterior -> posterior con delta claro", () => {
      render(<TablaHistorial registros={[mockRegistros[5]!]} />);

      const deltaContainer = screen.getByTestId("before-after-106");
      expect(deltaContainer).toBeInTheDocument();
      expect(deltaContainer).toHaveTextContent("25 paq");
      expect(deltaContainer).toHaveTextContent("30 paq");
    });

    it("muestra transición para ajuste_auditoria", () => {
      render(<TablaHistorial registros={[mockRegistros[6]!]} />);

      const deltaContainer = screen.getByTestId("before-after-107");
      expect(deltaContainer).toBeInTheDocument();
      expect(deltaContainer).toHaveTextContent("40 kg");
      expect(deltaContainer).toHaveTextContent("48 kg");
    });

    it("calcula delta con fallback automático cuando no viene delta_before/after explícito", () => {
      const registroConteoSinDelta: RegistroMovimiento = {
        id: 999,
        producto_id: "prod-999",
        cantidad: 4,
        tipo_movimiento: "conteo",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T12:00:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        saldo_resultante: 50,
        unidad_medida: "unidades",
      };

      render(<TablaHistorial registros={[registroConteoSinDelta]} />);

      // before = saldo_resultante (50) - cantidad (4) = 46; after = 50
      const deltaContainer = screen.getByTestId("before-after-999");
      expect(deltaContainer).toHaveTextContent("46 unidades");
      expect(deltaContainer).toHaveTextContent("50 unidades");
    });

    it("muestra cantidad simple para movimientos no-conteo", () => {
      render(<TablaHistorial registros={[mockRegistros[0]!]} />);

      expect(screen.queryByTestId("before-after-101")).not.toBeInTheDocument();
      expect(screen.getByText("15.5 kg")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 6. Control de Visibilidad RBAC (Columna Usuario)
  // ==========================================================================
  describe("Control de Visibilidad RBAC", () => {
    it("oculta columna Usuario cuando canViewUsers es false", () => {
      render(<TablaHistorial registros={mockRegistros} canViewUsers={false} />);

      expect(screen.queryByText("Usuario")).not.toBeInTheDocument();
      expect(screen.queryByText("Ignacio Soto")).not.toBeInTheDocument();
    });

    it("muestra columna Usuario cuando canViewUsers es true", () => {
      render(<TablaHistorial registros={mockRegistros} canViewUsers={true} />);

      expect(screen.getByText("Usuario")).toBeInTheDocument();
      expect(screen.getAllByText("Ignacio Soto").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Chef Mario")).toBeInTheDocument();
    });

    it("muestra columna Usuario automáticamente si el usuario es Admin vía useAuth", () => {
      mockAuth.isGlobalAdmin = true;

      render(<TablaHistorial registros={mockRegistros} />);

      expect(screen.getByText("Usuario")).toBeInTheDocument();
      expect(screen.getAllByText("Ignacio Soto").length).toBeGreaterThanOrEqual(1);
    });

    it("muestra columna Usuario si tiene permiso RBAC rbac_audit.audit.read", () => {
      mockPermissions.can.mockImplementation((perm: string) => perm === "rbac_audit.audit.read");

      render(<TablaHistorial registros={mockRegistros} />);

      expect(screen.getByText("Usuario")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 7. Estados de Carga y Vacío
  // ==========================================================================
  describe("Estados de Carga y Vacío", () => {
    it("muestra skeletons animados durante estado de carga (loading=true)", () => {
      render(<TablaHistorial loading={true} />);

      const skeletons = screen.getAllByTestId("tabla-historial-skeleton");
      expect(skeletons.length).toBe(5);
      expect(skeletons[0]).toHaveClass("animate-pulse");
    });

    it("muestra mensaje descriptivo amigable cuando la lista de registros está vacía", () => {
      render(<TablaHistorial registros={[]} />);

      const emptyState = screen.getByTestId("historial-empty-state");
      expect(emptyState).toBeInTheDocument();
      expect(emptyState).toHaveTextContent(
        "No hay registros que coincidan con los filtros aplicados."
      );
    });
  });

  // ==========================================================================
  // 8. Interacción y Accesibilidad (onRowClick)
  // ==========================================================================
  describe("Interacción y Accesibilidad", () => {
    it("invoca callback onRowClick al hacer clic en una fila", () => {
      const handleRowClick = vi.fn();
      render(<TablaHistorial registros={[mockRegistros[0]!]} onRowClick={handleRowClick} />);

      const row = screen.getByTestId("historial-row-101");
      expect(row).toHaveClass("cursor-pointer");

      fireEvent.click(row);
      expect(handleRowClick).toHaveBeenCalledTimes(1);
      expect(handleRowClick).toHaveBeenCalledWith(mockRegistros[0]!);
    });

    it("permite navegación accesible mediante teclado (Enter y Space)", () => {
      const handleRowClick = vi.fn();
      render(<TablaHistorial registros={[mockRegistros[0]!]} onRowClick={handleRowClick} />);

      const row = screen.getByTestId("historial-row-101");

      fireEvent.keyDown(row, { key: "Enter" });
      expect(handleRowClick).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(row, { key: " " });
      expect(handleRowClick).toHaveBeenCalledTimes(2);
    });
  });

  // ==========================================================================
  // 9. Multi-Moneda FX y Precisión Decimal
  // ==========================================================================
  describe("Multi-Moneda FX y Precisión Decimal", () => {
    it("formatea correctamente los montos monetarios de costo total y unitario", () => {
      const registroConCosto: RegistroMovimiento = {
        ...mockRegistros[0]!,
        costo_unitario_ppp: 14200,
        costo_total_movimiento: 213000,
      };

      render(<TablaHistorial registros={[registroConCosto]} />);

      const costoEl = screen.getByTestId("costo-total-101");
      expect(costoEl).toBeInTheDocument();
      expect(costoEl.textContent).toContain("$213.000");
      expect(costoEl).toHaveAttribute("title", "Costo Unitario: $14.200");
    });
  });

  // ==========================================================================
  // 10. Internacionalización i18n reactiva (es / en)
  // ==========================================================================
  describe("Internacionalización i18n", () => {
    it("renderiza encabezados en inglés cuando se conmuta el idioma", async () => {
      const { i18next } = await import("@/shared/i18n/config");
      await i18next.changeLanguage("en");

      render(<TablaHistorial registros={[]} canViewUsers={true} />);

      expect(screen.getByText("Date and time")).toBeInTheDocument();
      expect(screen.getByText("Product")).toBeInTheDocument();
      expect(screen.getByText("Type")).toBeInTheDocument();
      expect(screen.getByText("Warehouse")).toBeInTheDocument();
      expect(screen.getByText("Quantity")).toBeInTheDocument();
      expect(screen.getByText("User")).toBeInTheDocument();
      expect(screen.getByText("Reason")).toBeInTheDocument();

      expect(
        screen.getByText("No records match the applied filters.")
      ).toBeInTheDocument();

      await i18next.changeLanguage("es");
    });
  });
});
