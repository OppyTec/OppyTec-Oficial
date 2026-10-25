// oppytec-frontend/src/features/gestion/useGestion.test.ts
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import * as httpClient from "@/shared/api/httpClient";
import { useGestion } from "./useGestion";
import {
  ALL_COLUMNS,
  COLUMN_WIDTHS,
  getColWidthPx,
  DEFAULT_COLUMNS,
  PRODUCT_SORT_OPTIONS,
  SYSTEM_PRESETS,
} from "./types";

describe("useGestion & Gestion Data Architecture Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // --------------------------------------------------------------------------
  // 1. Columnas analíticas y Presets
  // --------------------------------------------------------------------------
  describe("Tipos, Columnas Analíticas y Presets", () => {
    it("defines all 30 analytical columns classified across the 4 key sections", () => {
      expect(ALL_COLUMNS.length).toBe(30);

      const sections = new Set(ALL_COLUMNS.map((col) => col.section));
      expect(sections.has("📦 Stock y Logística")).toBe(true);
      expect(sections.has("💰 Costos de Compra")).toBe(true);
      expect(sections.has("🏷️ Ventas y Valorización")).toBe(true);
      expect(sections.has("⏳ Rotación y Autonomía")).toBe(true);
    });

    it("verifies column widths map and getColWidthPx helper", () => {
      expect(COLUMN_WIDTHS.bodega).toBe("w-[120px]");
      expect(getColWidthPx("bodega")).toBe(120);
      expect(getColWidthPx("ultimo_costo_unidad_neto")).toBe(160);
      expect(getColWidthPx("costo_prom_inv_embalaje_bruto")).toBe(180);
      expect(getColWidthPx("unknown_col" as any)).toBe(120);
    });

    it("defines default columns for executive overview", () => {
      expect(DEFAULT_COLUMNS).toContain("ultimo_costo_unidad_neto");
      expect(DEFAULT_COLUMNS).toContain("precio_venta_bruto");
      expect(DEFAULT_COLUMNS).toContain("margen_bruto");
      expect(DEFAULT_COLUMNS).toContain("valor_inventario_neto");
    });

    it("includes 6 system presets for operator, manager, audit, finance, warehouse and packaging", () => {
      expect(SYSTEM_PRESETS.length).toBe(6);
      const presetIds = SYSTEM_PRESETS.map((p) => p.id);
      expect(presetIds).toContain("system-operario");
      expect(presetIds).toContain("system-resumen");
      expect(presetIds).toContain("system-costos");
      expect(presetIds).toContain("system-finanzas");
      expect(presetIds).toContain("system-bodega");
      expect(presetIds).toContain("system-embalajes");
    });

    it("defines valid product sort options", () => {
      expect(PRODUCT_SORT_OPTIONS.length).toBeGreaterThanOrEqual(6);
      expect(PRODUCT_SORT_OPTIONS.some((o) => o.key === "nombre" && o.direction === "asc")).toBe(true);
      expect(PRODUCT_SORT_OPTIONS.some((o) => o.key === "stock" && o.direction === "asc")).toBe(true);
      expect(PRODUCT_SORT_OPTIONS.some((o) => o.key === "precio" && o.direction === "desc")).toBe(true);
    });
  });

  // --------------------------------------------------------------------------
  // 2. Resiliencia Total (0 pantallas en blanco) y Carga de Datos
  // --------------------------------------------------------------------------
  describe("Resiliencia Offline y Mock Dataset Gastronómico", () => {
    it("falls back to rich 10-product gastronomy mock when API endpoints fail", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Network Error / Backend Offline"));

      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Validar resiliencia: Cero pantallas en blanco
      expect(result.current.isOffline).toBe(true);
      expect(result.current.productos.length).toBeGreaterThanOrEqual(10);
      expect(result.current.categorias.length).toBeGreaterThanOrEqual(6);
      expect(result.current.marcas.length).toBeGreaterThanOrEqual(6);
      expect(result.current.tiposEnvase.length).toBeGreaterThanOrEqual(5);

      // Validar productos gastronómicos representativos
      const names = result.current.productos.map((p) => p.nombre);
      expect(names).toContain("Lomo Vetado Angus Premium");
      expect(names).toContain("Pechuga de Pollo Deshuesada");
      expect(names).toContain("Salmón Atlántico Fresco");
      expect(names).toContain("Leche Entera Colun 1L");
      expect(names).toContain("Queso Mozzarella Barra 2.5kg");
      expect(names).toContain("Aceite de Oliva Extra Virgen 5L");
      expect(names).toContain("Harina de Trigo Especial 25kg");
      expect(names).toContain("Vino Cabernet Sauvignon Reserva 750ml");
      expect(names).toContain("Cerveza Artesanal IPA 330ml");
      expect(names).toContain("Café de Grano Colombia Supremo 1kg");

      // Validar recetas y combos mock
      expect(result.current.recetas.length).toBeGreaterThanOrEqual(3);
      expect(result.current.combos.length).toBeGreaterThanOrEqual(1);
      expect(result.current.gruposOpciones.length).toBeGreaterThanOrEqual(1);
    });

    it("loads API products and categories when backend responds successfully", async () => {
      const customProducts = [
        {
          id: "prod-api-1",
          nombre: "Corte Tomahawk Wagyu",
          categoria_id: "cat-carnes",
          unidad: "kg",
          costo_unitario: 35000,
          bodegas_config: [],
        },
      ];
      const customCategories = [
        { id: "cat-wagyu", nombre: "Cortes Ultra Premium", color: "#FF0000" },
      ];

      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (path: string) => {
        if (path === "/inventory/products") {
          return { data: customProducts, traceId: "t1", timestampIso: "", tenantId: "tenant-1" } as any;
        }
        if (path === "/inventory/categories") {
          return { data: customCategories, traceId: "t2", timestampIso: "", tenantId: "tenant-1" } as any;
        }
        return { data: [], traceId: "t3", timestampIso: "", tenantId: "tenant-1" } as any;
      });

      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.productos).toEqual(customProducts);
      expect(result.current.categorias).toEqual(customCategories);
      expect(result.current.isOffline).toBe(false);
    });
  });

  // --------------------------------------------------------------------------
  // 3. Filtrado por Bodega y Métricas de Recetas
  // --------------------------------------------------------------------------
  describe("Filtrado por Bodega y Métricas", () => {
    it("filters products correctly by bodegaId", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const coldRoomProducts = result.current.getProductsForBodega("bod-frio");
      expect(coldRoomProducts.length).toBeGreaterThanOrEqual(3);
      const coldNames = coldRoomProducts.map((p) => p.nombre);
      expect(coldNames).toContain("Lomo Vetado Angus Premium");
      expect(coldNames).toContain("Pechuga de Pollo Deshuesada");
      expect(coldNames).toContain("Salmón Atlántico Fresco");

      const barProducts = result.current.getProductsForBodega("bod-bar");
      const barNames = barProducts.map((p) => p.nombre);
      expect(barNames).toContain("Vino Cabernet Sauvignon Reserva 750ml");
      expect(barNames).toContain("Cerveza Artesanal IPA 330ml");
      expect(barNames).toContain("Café de Grano Colombia Supremo 1kg");
    });

    it("calculates recipe cost accurately", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const lomoReceta = result.current.recetas.find((r) => r.id === "rec-1");
      expect(lomoReceta).toBeDefined();
      if (lomoReceta) {
        expect(result.current.getRecetaCosto(lomoReceta)).toBe(6200);
      }
    });
  });

  // --------------------------------------------------------------------------
  // 4. Operaciones CRUD de Productos
  // --------------------------------------------------------------------------
  describe("Product CRUD Operations", () => {
    it("creates a new product successfully with offline resilience", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const initialCount = result.current.productos.length;

      await act(async () => {
        await result.current.createProduct({
          nombre: "Costillar de Cerdo BBQ",
          categoria_id: "cat-carnes",
          unidad: "kg",
          costo_unitario: 8900,
          precio_venta: 16900,
        });
      });

      expect(result.current.productos.length).toBe(initialCount + 1);
      expect(result.current.productos[0]?.nombre).toBe("Costillar de Cerdo BBQ");
      expect(result.current.productos[0]?.costo_unitario).toBe(8900);
    });

    it("updates an existing product properties", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.updateProduct("prod-1", {
          precio_venta: 25900,
          costo_unitario: 15000,
        });
      });

      const updated = result.current.productos.find((p) => p.id === "prod-1");
      expect(updated?.precio_venta).toBe(25900);
      expect(updated?.costo_unitario).toBe(15000);
    });

    it("deletes a product successfully", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const countBefore = result.current.productos.length;

      await act(async () => {
        await result.current.deleteProduct("prod-1");
      });

      expect(result.current.productos.length).toBe(countBefore - 1);
      expect(result.current.productos.find((p) => p.id === "prod-1")).toBeUndefined();
    });
  });

  // --------------------------------------------------------------------------
  // 5. Categorías, Marcas y Tipos de Envase CRUD
  // --------------------------------------------------------------------------
  describe("Categories, Brands & Packaging CRUD", () => {
    it("creates, updates, and deletes categories", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Crear
      await act(async () => {
        await result.current.createCategory("Pastelería y Postres", { color: "#EC4899", icono: "cake" });
      });

      const created = result.current.categorias.find((c) => c.nombre === "Pastelería y Postres");
      expect(created).toBeDefined();
      expect(created?.color).toBe("#EC4899");

      // Actualizar
      if (created) {
        await act(async () => {
          await result.current.updateCategory(created.id, "Pastelería Fina y Postres", { color: "#DB2777" });
        });
        const updated = result.current.categorias.find((c) => c.id === created.id);
        expect(updated?.nombre).toBe("Pastelería Fina y Postres");
        expect(updated?.color).toBe("#DB2777");

        // Eliminar
        await act(async () => {
          await result.current.deleteCategory(created.id);
        });
        expect(result.current.categorias.find((c) => c.id === created.id)).toBeUndefined();
      }
    });

    it("creates a new brand and a new packaging type", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Offline"));
      const { result } = renderHook(() => useGestion());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Brand
      await act(async () => {
        await result.current.createBrand("Viña Montes", "https://example.com/montes.png");
      });
      expect(result.current.marcas.some((m) => m.nombre === "Viña Montes")).toBe(true);

      // Packaging
      await act(async () => {
        await result.current.createTipoEnvase("Frasco de Vidrio", "jar");
      });
      expect(result.current.tiposEnvase.some((e) => e.nombre === "Frasco de Vidrio")).toBe(true);
    });
  });

  // --------------------------------------------------------------------------
  // 6. Sincronización mediante evento 'product_updated'
  // --------------------------------------------------------------------------
  describe("Window Event Synchronization", () => {
    it("listens to 'product_updated' custom event and triggers reload", async () => {
      const apiSpy = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: [],
        traceId: "test",
        timestampIso: "",
        tenantId: "tenant-1",
      } as any);

      renderHook(() => useGestion());

      await waitFor(() => {
        expect(apiSpy).toHaveBeenCalled();
      });

      apiSpy.mockClear();

      // Disparar evento externo
      act(() => {
        window.dispatchEvent(new CustomEvent("product_updated"));
      });

      await waitFor(() => {
        expect(apiSpy).toHaveBeenCalled();
      });
    });
  });
});
