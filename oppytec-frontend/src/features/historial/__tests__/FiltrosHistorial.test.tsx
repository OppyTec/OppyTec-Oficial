// oppytec-frontend/src/features/historial/__tests__/FiltrosHistorial.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  FiltrosHistorial,
  formatChileDate,
  toDateInputValue,
  parseLocalDate,
} from "../FiltrosHistorial";
import type { HistorialCatalogProduct } from "../types";

const MOCK_PRODUCTOS: HistorialCatalogProduct[] = [
  { id: "prod-3", nombre: "Zanahoria Fresca", unidad: "kg" },
  { id: "prod-1", nombre: "Aceite de Oliva", unidad: "L" },
  { id: "prod-2", nombre: "Carne Vacuno", unidad: "kg" },
];

describe("Módulo Historial — FiltrosHistorial (Fase 5)", () => {
  const mockSetFiltroProducto = vi.fn();
  const mockSetFiltroTipo = vi.fn();
  const mockSetFechaDesde = vi.fn();
  const mockSetFechaHasta = vi.fn();
  const mockSetFiltroUsuario = vi.fn();
  const mockClearFilters = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. Renderizado de Controles de Filtro
  // ==========================================================================
  describe("Renderizado de Controles", () => {
    it("renderiza todos los controles de filtro con atributos accesibles y estilos", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
          clearFilters={mockClearFilters}
        />
      );

      // 1. Input usuario
      const inputUsuario = screen.getByPlaceholderText("Buscar por usuario...");
      expect(inputUsuario).toBeInTheDocument();
      expect(inputUsuario).toHaveAttribute("aria-label", "Buscar por usuario");

      // 2. Selector producto
      const selectProducto = screen.getByLabelText("Filtrar por producto");
      expect(selectProducto).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Todos los productos" })).toBeInTheDocument();

      // 3. Selector tipo
      const selectTipo = screen.getByLabelText("Filtrar por tipo");
      expect(selectTipo).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Todos" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Conteo" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Merma" })).toBeInTheDocument();

      // 4. Selector fecha Desde y Hasta
      const inputDesde = screen.getByLabelText("Desde");
      expect(inputDesde).toBeInTheDocument();
      expect(screen.getByTestId("fecha-desde-display")).toHaveTextContent("Desde");

      const inputHasta = screen.getByLabelText("Hasta");
      expect(inputHasta).toBeInTheDocument();
      expect(screen.getByTestId("fecha-hasta-display")).toHaveTextContent("Hasta");

      // Botón Limpiar filtros no debe estar visible si no hay filtros activos
      expect(screen.queryByTestId("btn-limpiar-filtros")).not.toBeInTheDocument();
    });

    it("ordena alfabéticamente la lista de productos en el selector", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const selectProducto = screen.getByLabelText("Filtrar por producto");
      const options = Array.from(selectProducto.querySelectorAll("option")).map(
        (o) => o.textContent?.trim()
      );

      expect(options[0]).toBe("Todos los productos");
      expect(options[1]).toContain("Aceite de Oliva");
      expect(options[2]).toContain("Carne Vacuno");
      expect(options[3]).toContain("Zanahoria Fresca");
    });
  });

  // ==========================================================================
  // 2. Búsqueda Predictiva por Usuario
  // ==========================================================================
  describe("Búsqueda Predictiva por Usuario", () => {
    it("permite escribir en el input y llama a setFiltroUsuario", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const input = screen.getByPlaceholderText("Buscar por usuario...");
      fireEvent.change(input, { target: { value: "Carlos" } });

      expect(mockSetFiltroUsuario).toHaveBeenCalledTimes(1);
      expect(mockSetFiltroUsuario).toHaveBeenCalledWith("Carlos");
    });

    it("muestra botón de limpieza X cuando hay texto y permite limpiarlo al click", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario="Administrador"
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const clearBtn = screen.getByTestId("filtro-usuario-clear");
      expect(clearBtn).toBeInTheDocument();

      fireEvent.click(clearBtn);
      expect(mockSetFiltroUsuario).toHaveBeenCalledWith("");
    });
  });

  // ==========================================================================
  // 3. Cambio de Producto y Tipo de Movimiento
  // ==========================================================================
  describe("Selector de Producto y Tipo de Movimiento", () => {
    it("llama a setFiltroProducto al seleccionar un producto específico", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const selectProducto = screen.getByLabelText("Filtrar por producto");
      fireEvent.change(selectProducto, { target: { value: "prod-2" } });

      expect(mockSetFiltroProducto).toHaveBeenCalledWith("prod-2");
    });

    it("llama a setFiltroTipo al cambiar el tipo de movimiento", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const selectTipo = screen.getByLabelText("Filtrar por tipo");
      fireEvent.change(selectTipo, { target: { value: "merma" } });

      expect(mockSetFiltroTipo).toHaveBeenCalledWith("merma");
    });
  });

  // ==========================================================================
  // 4. Selección de Fechas y Botón Limpiar Filtros
  // ==========================================================================
  describe("Selector de Rango de Fechas y Botón Limpiar", () => {
    it("muestra fechas formateadas en formato chileno dd/MM/yyyy", () => {
      const fecha1 = new Date(2026, 9, 25); // 25 de Octubre 2026
      const fecha2 = new Date(2026, 9, 31); // 31 de Octubre 2026

      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={fecha1}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={fecha2}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      expect(screen.getByTestId("fecha-desde-display")).toHaveTextContent("25/10/2026");
      expect(screen.getByTestId("fecha-hasta-display")).toHaveTextContent("31/10/2026");
    });

    it("llama a setFechaDesde al modificar el input fecha Desde", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const inputDesde = screen.getByLabelText("Desde");
      fireEvent.change(inputDesde, { target: { value: "2026-10-15" } });

      expect(mockSetFechaDesde).toHaveBeenCalledTimes(1);
      const call = mockSetFechaDesde.mock.calls[0];
      expect(call).toBeDefined();
      const callArg = call ? (call[0] as Date) : null;
      expect(callArg).toBeInstanceOf(Date);
      expect(callArg?.getFullYear()).toBe(2026);
      expect(callArg?.getMonth()).toBe(9); // Octubre (0-indexed)
      expect(callArg?.getDate()).toBe(15);
    });

    it("llama a setFechaHasta al modificar el input fecha Hasta", () => {
      render(
        <FiltrosHistorial
          filtroProducto="all"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const inputHasta = screen.getByLabelText("Hasta");
      fireEvent.change(inputHasta, { target: { value: "2026-10-20" } });

      expect(mockSetFechaHasta).toHaveBeenCalledTimes(1);
      const call = mockSetFechaHasta.mock.calls[0];
      expect(call).toBeDefined();
      const callArg = call ? (call[0] as Date) : null;
      expect(callArg).toBeInstanceOf(Date);
      expect(callArg?.getFullYear()).toBe(2026);
      expect(callArg?.getMonth()).toBe(9);
      expect(callArg?.getDate()).toBe(20);
    });

    it("muestra el botón Limpiar filtros cuando hasFilters es true y ejecuta clearFilters", () => {
      render(
        <FiltrosHistorial
          filtroProducto="prod-1"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="all"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={undefined}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={undefined}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario=""
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
          clearFilters={mockClearFilters}
        />
      );

      const btnLimpiar = screen.getByTestId("btn-limpiar-filtros");
      expect(btnLimpiar).toBeInTheDocument();
      expect(btnLimpiar).toHaveTextContent("Limpiar filtros");

      fireEvent.click(btnLimpiar);
      expect(mockClearFilters).toHaveBeenCalledTimes(1);
    });

    it("ejecuta fallback de reseteo si no se provee clearFilters", () => {
      render(
        <FiltrosHistorial
          filtroProducto="prod-1"
          setFiltroProducto={mockSetFiltroProducto}
          filtroTipo="merma"
          setFiltroTipo={mockSetFiltroTipo}
          fechaDesde={new Date(2026, 9, 10)}
          setFechaDesde={mockSetFechaDesde}
          fechaHasta={new Date(2026, 9, 20)}
          setFechaHasta={mockSetFechaHasta}
          filtroUsuario="Chef"
          setFiltroUsuario={mockSetFiltroUsuario}
          productos={MOCK_PRODUCTOS}
        />
      );

      const btnLimpiar = screen.getByTestId("btn-limpiar-filtros");
      fireEvent.click(btnLimpiar);

      expect(mockSetFiltroProducto).toHaveBeenCalledWith("all");
      expect(mockSetFiltroTipo).toHaveBeenCalledWith("all");
      expect(mockSetFechaDesde).toHaveBeenCalledWith(undefined);
      expect(mockSetFechaHasta).toHaveBeenCalledWith(undefined);
      expect(mockSetFiltroUsuario).toHaveBeenCalledWith("");
    });
  });

  // ==========================================================================
  // 5. Utilidades Puras de Fecha
  // ==========================================================================
  describe("Utilidades de Fecha (Chile / ISO)", () => {
    it("formatChileDate formatea correctamente y maneja nulos de forma segura", () => {
      expect(formatChileDate(undefined)).toBe("");
      expect(formatChileDate(new Date(NaN))).toBe("");
      expect(formatChileDate(new Date(2026, 0, 5))).toBe("05/01/2026");
      expect(formatChileDate(new Date(2026, 11, 31))).toBe("31/12/2026");
    });

    it("toDateInputValue convierte Date a YYYY-MM-DD", () => {
      expect(toDateInputValue(undefined)).toBe("");
      expect(toDateInputValue(new Date(NaN))).toBe("");
      expect(toDateInputValue(new Date(2026, 4, 9))).toBe("2026-05-09");
    });

    it("parseLocalDate crea fechas locales sin desfase UTC", () => {
      expect(parseLocalDate("")).toBeUndefined();
      const parsed = parseLocalDate("2026-10-25");
      expect(parsed).toBeDefined();
      expect(parsed?.getFullYear()).toBe(2026);
      expect(parsed?.getMonth()).toBe(9);
      expect(parsed?.getDate()).toBe(25);
    });
  });
});
