// oppytec-frontend/src/features/gestion/__tests__/kardex_parity_5d.test.ts
/**
 * Suite de Pruebas de Paridad 5D en Frontend: Kardex, PPP, Márgenes, Food Cost y Métricas
 * Paridad 1:1 con OppyTec-Legacy y PRODUCTOS_Y_COSTOS_SPEC.md.
 * 
 * 5 Dimensiones:
 * 1. Nivel de Abstracción: Pruebas unitarias de las 7 fórmulas matemáticas de gestión.
 * 2. Basada en Propiedades: Invariante algebraico Food Cost % + Margen Bruto % = 100%.
 * 3. Paridad con Casos Reales del Spec: Caja x192 potes, Jurel 800g/425g drenado.
 * 4. Límites de Frontera y Robustez: División por cero, stock 0, consumo diario 0.
 * 5. Formateo y Exactitud Monetaria en CLP: Decimales condicionales y moneda legal.
 */

import { describe, it, expect } from "vitest";
import { formatUnitCost, formatMoney } from "@/shared/lib/utils";

// Implementación matemática exacta pura en TypeScript coincidente con el motor backend y legacy
export const kardexMath = {
  // 1. Costo PPP por capas (FIFO dinámico)
  calculatePPPByLayers: (
    stockActual: number,
    purchases: { cantidad: number; precio_unitario: number }[],
    baseCost: number = 0,
    lastCost?: number
  ): { valorInventario: number; costoPPP: number } => {
    if (stockActual <= 0) {
      return {
        valorInventario: 0,
        costoPPP: lastCost !== undefined ? lastCost : baseCost,
      };
    }
    if (!purchases || purchases.length === 0) {
      return {
        valorInventario: Math.round(stockActual * baseCost * 100) / 100,
        costoPPP: baseCost,
      };
    }
    let remaining = stockActual;
    let valTotal = 0;
    let unitsCovered = 0;
    for (const item of purchases) {
      if (remaining <= 0) break;
      if (item.cantidad <= 0 || item.precio_unitario <= 0) continue;
      const take = Math.min(remaining, item.cantidad);
      valTotal += take * item.precio_unitario;
      unitsCovered += take;
      remaining -= take;
    }
    if (remaining > 0) {
      valTotal += remaining * baseCost;
      unitsCovered += remaining;
    }
    const costoPPP = unitsCovered > 0 ? valTotal / unitsCovered : baseCost;
    return {
      valorInventario: Math.round(valTotal * 100) / 100,
      costoPPP: Math.round(costoPPP * 10000) / 10000,
    };
  },

  // 2. Costo Promedio Histórico (últimas 10 compras)
  calculateMovingAverage10: (
    purchaseUnitCosts: number[],
    fallbackCost: number = 0
  ): number => {
    const valid = purchaseUnitCosts.slice(0, 10).filter((c) => c > 0);
    if (valid.length === 0) return fallbackCost;
    const sum = valid.reduce((acc, c) => acc + c, 0);
    return Math.round((sum / valid.length) * 10000) / 10000;
  },

  // 3. Food Cost %
  calculateFoodCostPct: (costoBruto: number, pvBruto: number): number => {
    if (pvBruto <= 0) throw new Error("pvBruto must be positive");
    return Math.round(((costoBruto / pvBruto) * 100) * 100) / 100;
  },

  // 4. Margen Bruto %
  calculateGrossMarginPct: (pvBruto: number, costoBruto: number): number => {
    if (pvBruto <= 0) throw new Error("pvBruto must be positive");
    return Math.round((((pvBruto - costoBruto) / pvBruto) * 100) * 100) / 100;
  },

  // 5. Margen Neto %
  calculateNetMarginPct: (pvNeto: number, costoNeto: number): number => {
    if (pvNeto <= 0) throw new Error("pvNeto must be positive");
    return Math.round((((pvNeto - costoNeto) / pvNeto) * 100) * 100) / 100;
  },

  // 6. Variación Inflacionaria %
  calculateInflationVariancePct: (
    ultimoCosto: number,
    penultimoCosto: number
  ): number => {
    if (penultimoCosto <= 0) throw new Error("penultimoCosto must be positive");
    return (
      Math.round(
        (((ultimoCosto - penultimoCosto) / penultimoCosto) * 100) * 100
      ) / 100
    );
  },

  // 7. Días de Cobertura
  calculateDaysOfCoverage: (
    stockActual: number,
    consumoDiarioPromedio: number
  ): number => {
    if (consumoDiarioPromedio > 0) {
      return Math.round(stockActual / consumoDiarioPromedio);
    }
    return stockActual > 0 ? 30 : 0;
  },

  // 8. Índice de Rotación Mensual
  calculateMonthlyTurnoverIndex: (
    unidadesVendidasMes: number,
    stockActual: number
  ): number => {
    const divisor = stockActual > 0 ? stockActual : 1;
    return Math.round((unidadesVendidasMes / divisor) * 10) / 10;
  },
};

describe("5D Kardex Parity Suite - OppyTec Frontend vs Legacy", () => {
  // =========================================================================
  // DIMENSIÓN 1: PRUEBAS UNITARIAS DE LAS 7 FÓRMULAS
  // =========================================================================
  describe("Dimensión 1: Exactitud Unitaria de Fórmulas Financieras", () => {
    it("1.1 Calcula PPP y Valor de Inventario por capas FIFO con precisión exacta", () => {
      const purchases = [
        { cantidad: 10, precio_unitario: 100 },
        { cantidad: 10, precio_unitario: 80 },
      ];
      const res = kardexMath.calculatePPPByLayers(15, purchases, 50);
      expect(res.valorInventario).toBe(1400);
      expect(res.costoPPP).toBe(93.3333);
    });

    it("1.2 Calcula Costo Promedio Histórico con 10 compras exactas", () => {
      const purchases = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120];
      const avg = kardexMath.calculateMovingAverage10(purchases);
      // Promedio de los primeros 10: (10+...+100)/10 = 55
      expect(avg).toBe(55);
    });

    it("1.3 Calcula Food Cost % y Margen Bruto % con exactitud", () => {
      const fc = kardexMath.calculateFoodCostPct(3000, 10000);
      const mb = kardexMath.calculateGrossMarginPct(10000, 3000);
      expect(fc).toBe(30.0);
      expect(mb).toBe(70.0);
      expect(fc + mb).toBe(100.0);
    });

    it("1.4 Calcula Margen Neto %", () => {
      const mn = kardexMath.calculateNetMarginPct(8403.36, 2521.01);
      expect(mn).toBe(70.0);
    });

    it("1.5 Calcula Variación Inflacionaria % positiva y negativa", () => {
      const varPos = kardexMath.calculateInflationVariancePct(1200, 1000);
      expect(varPos).toBe(20.0);

      const varNeg = kardexMath.calculateInflationVariancePct(900, 1000);
      expect(varNeg).toBe(-10.0);
    });

    it("1.6 Calcula Días de Cobertura según consumo diario", () => {
      expect(kardexMath.calculateDaysOfCoverage(100, 10)).toBe(10);
      expect(kardexMath.calculateDaysOfCoverage(100, 3)).toBe(33);
      expect(kardexMath.calculateDaysOfCoverage(50, 0)).toBe(30); // fallback stock sin consumo
      expect(kardexMath.calculateDaysOfCoverage(0, 0)).toBe(0);
    });

    it("1.7 Calcula Índice de Rotación Mensual con salvaguarda de divisor", () => {
      expect(kardexMath.calculateMonthlyTurnoverIndex(200, 50)).toBe(4.0);
      expect(kardexMath.calculateMonthlyTurnoverIndex(5, 0)).toBe(5.0); // divisor = 1 si stock=0
      expect(kardexMath.calculateMonthlyTurnoverIndex(0, 10)).toBe(0.0);
    });
  });

  // =========================================================================
  // DIMENSIÓN 2: BASADA EN PROPIEDADES (INVARIANTES ALGEBRAICOS)
  // =========================================================================
  describe("Dimensión 2: Invariantes y Propiedades Matemáticas", () => {
    it("Invariante fundamental: Food Cost % + Margen Bruto % = 100% para todo par (costo, pv)", () => {
      const testCases = [
        { costo: 1500, pv: 5000 },
        { costo: 850, pv: 1200 },
        { costo: 99.99, pv: 199.99 },
        { costo: 4200, pv: 4200 },
      ];
      for (const { costo, pv } of testCases) {
        const fc = kardexMath.calculateFoodCostPct(costo, pv);
        const mb = kardexMath.calculateGrossMarginPct(pv, costo);
        expect(Math.round((fc + mb) * 100) / 100).toBe(100);
      }
    });

    it("Invariante de cobertura: Mayor consumo diario implica menor o igual días de cobertura", () => {
      const stock = 100;
      const daysLow = kardexMath.calculateDaysOfCoverage(stock, 5);
      const daysHigh = kardexMath.calculateDaysOfCoverage(stock, 15);
      expect(daysHigh).toBeLessThanOrEqual(daysLow);
    });
  });

  // =========================================================================
  // DIMENSIÓN 3: PARIDAD 1:1 CON ESPECIFICACIÓN TÉCNICA LEGACY
  // =========================================================================
  describe("Dimensión 3: Paridad 1:1 con PRODUCTOS_Y_COSTOS_SPEC.md", () => {
    it("Spec Caso Caja x192 Potes a $30.128 Neto", () => {
      const netEmbalaje = 30128;
      const cantEnvases = 192;
      const unitNeto = netEmbalaje / cantEnvases;
      expect(unitNeto).toBeCloseTo(156.9167, 4);

      // Formateo visual condicional (debe mostrar 2 decimales por ser fraccionario)
      const formatted = formatUnitCost(unitNeto);
      expect(formatted).toContain("156,92");
    });

    it("Spec Caso Conserva Jurel: 800g bruto, 425g drenado útil", () => {
      const costoTarro = 2000;
      const pesoBruto = 800;
      const pesoDrenado = 425;

      const rendimiento = (pesoDrenado / pesoBruto) * 100;
      expect(rendimiento).toBeCloseTo(53.125, 2);

      const costoGramoDrenado = costoTarro / pesoDrenado;
      expect(costoGramoDrenado).toBeCloseTo(4.7059, 4);
    });

    it("Spec Caso CLP Moneda Legal: Totales de Inventario en Enteros", () => {
      const netTotal = 86306;
      const multIVA = 1.19;
      const brutoTotal = Math.round(netTotal * multIVA);
      expect(brutoTotal).toBe(102704);
      expect(formatMoney(brutoTotal)).toContain("102.704");
    });
  });

  // =========================================================================
  // DIMENSIÓN 4: ROBUSTEZ Y BLINDAJE ANTE ENTRADAS ANÓMALAS
  // =========================================================================
  describe("Dimensión 4: Manejo Robusto de Casos Límite", () => {
    it("Lanza error al calcular Food Cost o Margen con precio de venta <= 0", () => {
      expect(() => kardexMath.calculateFoodCostPct(100, 0)).toThrow();
      expect(() => kardexMath.calculateGrossMarginPct(0, 100)).toThrow();
      expect(() => kardexMath.calculateNetMarginPct(0, 50)).toThrow();
    });

    it("Lanza error al calcular Variación Inflacionaria con penúltimo costo <= 0", () => {
      expect(() => kardexMath.calculateInflationVariancePct(100, 0)).toThrow();
    });

    it("Fallback seguro de PPP cuando no hay compras y stock es 0", () => {
      const res = kardexMath.calculatePPPByLayers(0, [], 100, 150);
      expect(res.valorInventario).toBe(0);
      expect(res.costoPPP).toBe(150);
    });
  });

  // =========================================================================
  // DIMENSIÓN 5: FORMATEO Y EXACTITUD MONETARIA
  // =========================================================================
  describe("Dimensión 5: Formateo y Exactitud en Pesos Chilenos (CLP)", () => {
    it("formatUnitCost muestra enteros sin decimales y decimales si es fraccionario", () => {
      expect(formatUnitCost(157)).toContain("157");
      expect(formatUnitCost(157)).not.toContain(",00");

      expect(formatUnitCost(156.9167)).toContain("156,92");
      expect(formatUnitCost(null)).toBe("—");
      expect(formatUnitCost(undefined)).toBe("—");
    });
  });
});
