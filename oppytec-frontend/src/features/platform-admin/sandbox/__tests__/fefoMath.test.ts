import { describe, expect, it } from "vitest";
import {
  calculateDaysDifference,
  calculateDaysRemaining,
  calculateEstimatedLoss,
  calculateLossRate,
  classifyFefoStatus,
  evaluateBatchSimulation,
  FEFO_DEMO_SCENARIO_CONFIGS,
  FEFO_LOSS_RATE_CRITICAL,
  FEFO_LOSS_RATE_EXPIRED,
  FEFO_TIME_TRAVEL_RANGE,
  generateScenarioBatches,
  shiftIsoDate,
  summarizeFefoSimulation,
  syncBatchesToToday,
} from "../fefoMath";
import type { BatchEvaluationInput } from "../fefoMath";

describe("Sub-Plan 4 — Etapa 1: Arquitectura Matemática y Contratos FEFO Simulation", () => {
  const TODAY = "2026-11-05";

  describe("1. Modelo Matemático de Fechas Relativas", () => {
    it("debe calcular la diferencia de días exacta entre dos fechas ISO", () => {
      expect(calculateDaysDifference("2026-11-20", "2026-11-05")).toBe(15);
      expect(calculateDaysDifference("2026-11-05", "2026-11-20")).toBe(-15);
      expect(calculateDaysDifference("2026-11-05", "2026-11-05")).toBe(0);
    });

    it("debe desplazar fechas mediante shiftIsoDate con offset positivo y negativo", () => {
      expect(shiftIsoDate("2026-11-05", 15)).toBe("2026-11-20");
      expect(shiftIsoDate("2026-11-05", -10)).toBe("2026-10-26");
      expect(shiftIsoDate("2026-11-05", 0)).toBe("2026-11-05");
    });

    it("debe calcular D_rem incorporando el offset simulado: D_rem = Expiry - (Today + Offset)", () => {
      // Expiración el 20 de noviembre.
      // Offset = 0 -> 15 días restantes
      expect(calculateDaysRemaining("2026-11-20", TODAY, 0)).toBe(15);

      // Offset = +10 días -> Hoy simulado es 15 de noviembre -> 5 días restantes
      expect(calculateDaysRemaining("2026-11-20", TODAY, 10)).toBe(5);

      // Offset = +20 días -> Hoy simulado es 25 de noviembre -> -5 días (caducado)
      expect(calculateDaysRemaining("2026-11-20", TODAY, 20)).toBe(-5);

      // Offset = -5 días (retrospectivo) -> Hoy simulado es 31 de octubre -> 20 días restantes
      expect(calculateDaysRemaining("2026-11-20", TODAY, -5)).toBe(20);
    });
  });

  describe("2. Semáforos Canónicos FEFO (4 Estados)", () => {
    it("debe clasificar OPTIMAL cuando D_rem >= 15 días", () => {
      expect(classifyFefoStatus(15)).toBe("OPTIMAL");
      expect(classifyFefoStatus(30)).toBe("OPTIMAL");
      expect(classifyFefoStatus(180)).toBe("OPTIMAL");
    });

    it("debe clasificar WARNING cuando 7 <= D_rem <= 14 días", () => {
      expect(classifyFefoStatus(14)).toBe("WARNING");
      expect(classifyFefoStatus(10)).toBe("WARNING");
      expect(classifyFefoStatus(7)).toBe("WARNING");
    });

    it("debe clasificar CRITICAL cuando 1 <= D_rem <= 6 días", () => {
      expect(classifyFefoStatus(6)).toBe("CRITICAL");
      expect(classifyFefoStatus(3)).toBe("CRITICAL");
      expect(classifyFefoStatus(1)).toBe("CRITICAL");
    });

    it("debe clasificar EXPIRED cuando D_rem <= 0 días", () => {
      expect(classifyFefoStatus(0)).toBe("EXPIRED");
      expect(classifyFefoStatus(-1)).toBe("EXPIRED");
      expect(classifyFefoStatus(-45)).toBe("EXPIRED");
    });
  });

  describe("3. Valorización Financiera de Merma y Tasas de Riesgo", () => {
    it("debe aplicar tasa 1.0 (100%) para EXPIRED y 0.75 (75%) para CRITICAL", () => {
      expect(calculateLossRate("EXPIRED")).toBe(FEFO_LOSS_RATE_EXPIRED);
      expect(calculateLossRate("expired")).toBe(FEFO_LOSS_RATE_EXPIRED);
      expect(calculateLossRate("CRITICAL")).toBe(FEFO_LOSS_RATE_CRITICAL);
      expect(calculateLossRate("critical")).toBe(FEFO_LOSS_RATE_CRITICAL);
      expect(calculateLossRate("WARNING")).toBe(0.0);
      expect(calculateLossRate("OPTIMAL")).toBe(0.0);
    });

    it("debe calcular el monto estimado de pérdida con precisión decimal", () => {
      // 10 kg a 10.000 CLP:
      // EXPIRED -> 10 * 10000 * 1.0 = 100.000 CLP
      expect(calculateEstimatedLoss(10, 10000, "EXPIRED")).toBe(100000);

      // CRITICAL -> 10 * 10000 * 0.75 = 75.000 CLP
      expect(calculateEstimatedLoss(10, 10000, "CRITICAL")).toBe(75000);

      // WARNING -> 0 CLP
      expect(calculateEstimatedLoss(10, 10000, "WARNING")).toBe(0);

      // OPTIMAL -> 0 CLP
      expect(calculateEstimatedLoss(10, 10000, "OPTIMAL")).toBe(0);
    });

    it("debe soportar conversión FX a divisas secundarias", () => {
      const sampleLot: BatchEvaluationInput = {
        batchId: "LOT-TEST-01",
        productSku: "SKU-CARN-01",
        productName: "Lomo Angus",
        category: "carnes",
        warehouseId: "bod-cocina",
        isBuffetBatch: false,
        originalExpiryDate: "2026-11-04", // 1 día vencido
        stockQuantity: 10,
        unitMeasure: "Kg",
        unitCost: 10000,
      };

      // Tasa FX: 1 USD = 950 CLP
      const evaluation = evaluateBatchSimulation(sampleLot, TODAY, 0, 950);
      expect(evaluation.canonicalStatus).toBe("EXPIRED");
      expect(evaluation.estimatedLossAmount).toBe(100000);
      expect(evaluation.estimatedLossFxAmount).toBeCloseTo(105.26, 1);
    });
  });

  describe("4. Escenarios de Demostración Preconfigurados", () => {
    it("debe contener metadatos canónicos para los 3 escenarios oficiales", () => {
      expect(FEFO_DEMO_SCENARIO_CONFIGS.HEALTHY.title).toBe("Operación Saludable");
      expect(FEFO_DEMO_SCENARIO_CONFIGS.WARNING.title).toBe("Alerta Fin de Semana");
      expect(FEFO_DEMO_SCENARIO_CONFIGS.CRITICAL.title).toBe("Auditoría / Rotura de Frío");
    });

    it("HEALTHY: debe tener 0% vencido, 10% advertencia y 90% óptimo", () => {
      const batches = generateScenarioBatches("HEALTHY", TODAY);
      expect(batches.length).toBe(20);

      const expired = batches.filter((b) => b.canonicalStatus === "EXPIRED");
      const critical = batches.filter((b) => b.canonicalStatus === "CRITICAL");
      const warning = batches.filter((b) => b.canonicalStatus === "WARNING");
      const optimal = batches.filter((b) => b.canonicalStatus === "OPTIMAL");

      expect(expired.length).toBe(0);
      expect(critical.length).toBe(0);
      expect(warning.length).toBe(2); // 10% de 20
      expect(optimal.length).toBe(18); // 90% de 20

      const summary = summarizeFefoSimulation(batches, TODAY, "HEALTHY");
      expect(summary.expiredBatchesCount).toBe(0);
      expect(summary.criticalBatchesCount).toBe(0);
      expect(summary.totalSpoilageRiskAmount).toBe(0);
    });

    it("WARNING: debe tener 20% crítico (venciendo en 48h) y 30% advertencia", () => {
      const batches = generateScenarioBatches("WARNING", TODAY);
      expect(batches.length).toBe(20);

      const expired = batches.filter((b) => b.canonicalStatus === "EXPIRED");
      const critical = batches.filter((b) => b.canonicalStatus === "CRITICAL");
      const warning = batches.filter((b) => b.canonicalStatus === "WARNING");
      const optimal = batches.filter((b) => b.canonicalStatus === "OPTIMAL");

      expect(expired.length).toBe(0);
      expect(critical.length).toBe(4); // 20% de 20
      expect(warning.length).toBe(6); // 30% de 20
      expect(optimal.length).toBe(10); // 50% de 20

      // Todos los críticos deben tener 1 o 2 días (48h)
      for (const b of critical) {
        expect(b.daysToExpiration).toBeLessThanOrEqual(2);
        expect(b.daysToExpiration).toBeGreaterThanOrEqual(1);
      }
    });

    it("CRITICAL: debe tener 15% caducado sanitario y 35% en riesgo crítico", () => {
      const batches = generateScenarioBatches("CRITICAL", TODAY);
      expect(batches.length).toBe(20);

      const expired = batches.filter((b) => b.canonicalStatus === "EXPIRED");
      const critical = batches.filter((b) => b.canonicalStatus === "CRITICAL");
      const warning = batches.filter((b) => b.canonicalStatus === "WARNING");
      const optimal = batches.filter((b) => b.canonicalStatus === "OPTIMAL");

      expect(expired.length).toBe(3); // 15% de 20
      expect(critical.length).toBe(7); // 35% de 20
      expect(warning.length).toBe(5); // 25% de 20
      expect(optimal.length).toBe(5); // 25% de 20

      const summary = summarizeFefoSimulation(batches, TODAY, "CRITICAL");
      expect(summary.expiredBatchesCount).toBe(3);
      expect(summary.criticalBatchesCount).toBe(7);
      expect(summary.totalSpoilageRiskAmount).toBeGreaterThan(0);
      expect(summary.alertsCreated).toBe(10);
    });
  });

  describe("5. Time-Travel Slider Configuration", () => {
    it("debe cumplir con el rango operativo de -30 días a +60 días", () => {
      expect(FEFO_TIME_TRAVEL_RANGE.minDays).toBe(-30);
      expect(FEFO_TIME_TRAVEL_RANGE.maxDays).toBe(60);
      expect(FEFO_TIME_TRAVEL_RANGE.defaultDays).toBe(0);
      expect(FEFO_TIME_TRAVEL_RANGE.stepDays).toBe(1);
      expect(FEFO_TIME_TRAVEL_RANGE.criticalThresholdDays).toBe(6);
      expect(FEFO_TIME_TRAVEL_RANGE.warningThresholdDays).toBe(14);
      expect(FEFO_TIME_TRAVEL_RANGE.optimalThresholdDays).toBe(15);
    });
  });

  describe("6. Acción Quirúrgica: Sincronizar fechas a Hoy", () => {
    it("debe recalcular lotes vencidos para que vuelvan a tener ciclo activo sin vencimiento", () => {
      const initialBatches = generateScenarioBatches("CRITICAL", TODAY);
      const expiredBefore = initialBatches.filter((b) => b.canonicalStatus === "EXPIRED");
      expect(expiredBefore.length).toBe(3);

      const synchronized = syncBatchesToToday(initialBatches, TODAY, true);
      const expiredAfter = synchronized.filter((b) => b.canonicalStatus === "EXPIRED");
      expect(expiredAfter.length).toBe(0);

      // Todos los lotes deben tener al menos 3 días restantes
      for (const b of synchronized) {
        expect(b.daysToExpiration).toBeGreaterThanOrEqual(3);
      }
    });
  });
});
