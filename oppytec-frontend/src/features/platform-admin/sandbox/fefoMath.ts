/**
 * oppytec-frontend/src/features/platform-admin/sandbox/fefoMath.ts
 * Motor Algorítmico y Matemático Puro para FEFO y Time-Travel Simulation (Sub-Plan 4).
 *
 * Responsabilidades:
 * - Aritmética determinista de fechas relativas: D_rem = Expiry - (ReferenceDate + OffsetDays).
 * - Clasificación canónica de semáforos FEFO de 4 estados (OPTIMAL, WARNING, CRITICAL, EXPIRED).
 * - Cuantificación de mermas y riesgo financiero con soporte para precisión monetaria (CLP y divisas FX).
 * - Generador sintético determinista para los 3 escenarios canónicos (HEALTHY, WARNING, CRITICAL).
 * - Función quirúrgica de sincronización de fechas a "Hoy" (recalculando lotes de inventario y buffet).
 *
 * Reglas de diseño:
 * - 0 dependencias impuras (cero efectos secundarios, funciones puras).
 * - 0 uso de `any`, 100% tipos estrictos e inmutables (`readonly`).
 */

import type {
  FefoBatchCanonicalStatus,
  FefoBatchSimulationImpact,
  FefoBatchStatus,
  FefoDemoScenarioId,
  FefoSimulationResponse,
  FefoTimeTravelRange,
} from "../sandboxTypes";
import {
  FEFO_DEMO_SCENARIO_CONFIGS,
  FEFO_TIME_TRAVEL_RANGE,
} from "../sandboxTypes";

export { FEFO_DEMO_SCENARIO_CONFIGS, FEFO_TIME_TRAVEL_RANGE };
export type { FefoTimeTravelRange };

// ============================================================================
// 1. CONSTANTES MATEMÁTICAS Y TASAS DE RIESGO
// ============================================================================

export const FEFO_LOSS_RATE_EXPIRED = 1.0; // 100% computable como pérdida directa
export const FEFO_LOSS_RATE_CRITICAL = 0.75; // 75% riesgo financiero si no se acelera consumo
export const FEFO_LOSS_RATE_WARNING = 0.0; // 0% pérdida estimada inmediata
export const FEFO_LOSS_RATE_OPTIMAL = 0.0; // 0% pérdida estimada

export const FEFO_THRESHOLD_OPTIMAL_DAYS = 15;
export const FEFO_THRESHOLD_WARNING_MIN_DAYS = 7;
export const FEFO_THRESHOLD_WARNING_MAX_DAYS = 14;
export const FEFO_THRESHOLD_CRITICAL_MIN_DAYS = 1;
export const FEFO_THRESHOLD_CRITICAL_MAX_DAYS = 6;
export const FEFO_THRESHOLD_EXPIRED_MAX_DAYS = 0;

// ============================================================================
// 2. FUNCIONES MATEMÁTICAS PURAS DE FECHAS Y SEMÁFOROS
// ============================================================================

/**
 * Calcula la diferencia en días exactos entre dos fechas ISO (target - reference).
 */
export function calculateDaysDifference(
  targetDateIso: string,
  referenceDateIso: string
): number {
  const target = new Date(targetDateIso.slice(0, 10));
  const reference = new Date(referenceDateIso.slice(0, 10));
  const diffTime = target.getTime() - reference.getTime();
  return Math.round(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Añade o sustrae días de una fecha ISO-8601 devolviendo la fecha resultante en YYYY-MM-DD.
 */
export function shiftIsoDate(baseDateIso: string, daysOffset: number): string {
  const d = new Date(baseDateIso.slice(0, 10));
  d.setUTCDate(d.getUTCDate() + daysOffset);
  return d.toISOString().slice(0, 10);
}

/**
 * Calcula los días restantes de vida útil proyectada para un lote:
 * D_rem = ExpirationDate - (ReferenceDate + OffsetDays)
 */
export function calculateDaysRemaining(
  expiryDateIso: string,
  referenceDateIso: string,
  offsetDays = 0
): number {
  const simulatedReference = shiftIsoDate(referenceDateIso, offsetDays);
  return calculateDaysDifference(expiryDateIso, simulatedReference);
}

/**
 * Clasifica deterministamente el semáforo FEFO canónico según los días restantes:
 * - OPTIMAL: >= 15 días
 * - WARNING: 7 a 14 días
 * - CRITICAL: 1 a 6 días
 * - EXPIRED: <= 0 días
 */
export function classifyFefoStatus(
  daysRemaining: number
): FefoBatchCanonicalStatus {
  if (daysRemaining >= FEFO_THRESHOLD_OPTIMAL_DAYS) {
    return "OPTIMAL";
  }
  if (daysRemaining >= FEFO_THRESHOLD_WARNING_MIN_DAYS) {
    return "WARNING";
  }
  if (daysRemaining >= FEFO_THRESHOLD_CRITICAL_MIN_DAYS) {
    return "CRITICAL";
  }
  return "EXPIRED";
}

/**
 * Retorna la tasa porcentual de riesgo financiero computable como merma.
 */
export function calculateLossRate(status: FefoBatchStatus): number {
  const normalized = status.toUpperCase();
  if (normalized === "EXPIRED") {
    return FEFO_LOSS_RATE_EXPIRED;
  }
  if (normalized === "CRITICAL") {
    return FEFO_LOSS_RATE_CRITICAL;
  }
  return 0.0;
}

/**
 * Cuantifica la pérdida estimada en valor monetario:
 * Loss = StockQuantity * UnitCost * LossRate
 */
export function calculateEstimatedLoss(
  stockQuantity: number,
  unitCost: number,
  status: FefoBatchStatus
): number {
  const rate = calculateLossRate(status);
  const rawLoss = stockQuantity * unitCost * rate;
  return Math.round(rawLoss * 100) / 100;
}

// ============================================================================
// 3. EVALUACIÓN Y PROYECCIÓN DE LOTES INDIVIDUALES
// ============================================================================

export interface BatchEvaluationInput {
  readonly batchId: string;
  readonly productSku: string;
  readonly productName: string;
  readonly category?: string;
  readonly warehouseId?: string;
  readonly isBuffetBatch?: boolean;
  readonly originalExpiryDate: string;
  readonly stockQuantity: number;
  readonly unitMeasure: string;
  readonly unitCost: number;
}

/**
 * Evalúa el impacto de la proyección temporal sobre un lote específico.
 */
export function evaluateBatchSimulation(
  lot: BatchEvaluationInput,
  referenceDateIso: string,
  offsetDays: number,
  exchangeRate?: number
): FefoBatchSimulationImpact {
  const remainingDays = calculateDaysRemaining(
    lot.originalExpiryDate,
    referenceDateIso,
    offsetDays
  );
  const canonical = classifyFefoStatus(remainingDays);
  const legacyStatus = canonical.toLowerCase() as "optimal" | "warning" | "critical" | "expired";
  const lossAmount = calculateEstimatedLoss(lot.stockQuantity, lot.unitCost, canonical);
  const fxLoss = exchangeRate && exchangeRate > 0
    ? Math.round((lossAmount / exchangeRate) * 100) / 100
    : undefined;

  return {
    batchId: lot.batchId,
    productSku: lot.productSku,
    productName: lot.productName,
    category: lot.category ?? "insumos",
    warehouseId: lot.warehouseId ?? "bod-cocina-central",
    isBuffetBatch: lot.isBuffetBatch ?? false,
    originalExpiryDate: lot.originalExpiryDate,
    simulatedExpiryDate: shiftIsoDate(lot.originalExpiryDate, -offsetDays),
    daysToExpiration: remainingDays,
    status: legacyStatus,
    canonicalStatus: canonical,
    stockQuantity: lot.stockQuantity,
    unitMeasure: lot.unitMeasure,
    unitCost: lot.unitCost,
    estimatedLossAmount: lossAmount,
    estimatedLossFxAmount: fxLoss,
    lossRateApplied: calculateLossRate(canonical),
  };
}

// ============================================================================
// 4. GENERADOR DETERMINISTA DE LOS 3 ESCENARIOS CANÓNICOS
// ============================================================================

/**
 * Dataset semilla para generar lotes de demostración gastronómicos.
 */
interface SeedProductMeta {
  readonly sku: string;
  readonly name: string;
  readonly category: string;
  readonly unit: string;
  readonly cost: number;
  readonly defaultShelfLifeDays: number;
  readonly isBuffet: boolean;
}

const SEED_CATALOG: readonly SeedProductMeta[] = [
  { sku: "INS-CARN-01", name: "Lomo Vetado Angus Premium", category: "carnes", unit: "Kg", cost: 14500, defaultShelfLifeDays: 20, isBuffet: false },
  { sku: "INS-AVE-02", name: "Pechuga de Pollo Fresca Granja", category: "carnes", unit: "Kg", cost: 4200, defaultShelfLifeDays: 8, isBuffet: false },
  { sku: "INS-LACT-03", name: "Queso Mozzarella Barra Fior di Latte", category: "lacteos", unit: "Kg", cost: 8900, defaultShelfLifeDays: 25, isBuffet: false },
  { sku: "INS-LACT-04", name: "Crema de Leche Gastronómica 35%", category: "lacteos", unit: "Lt", cost: 3600, defaultShelfLifeDays: 14, isBuffet: true },
  { sku: "INS-VERD-05", name: "Tomate Chonto de Huerto Seleccionado", category: "verduras", unit: "Kg", cost: 1800, defaultShelfLifeDays: 6, isBuffet: false },
  { sku: "INS-VERD-06", name: "Lechuga Costina Hidropónica", category: "verduras", unit: "Un", cost: 990, defaultShelfLifeDays: 4, isBuffet: true },
  { sku: "INS-ABAR-07", name: "Harina de Trigo Selecta 0000", category: "abarrotes", unit: "Kg", cost: 1250, defaultShelfLifeDays: 180, isBuffet: false },
  { sku: "INS-ABAR-08", name: "Salsa Pomodoro Casera Reducida", category: "abarrotes", unit: "Kg", cost: 2400, defaultShelfLifeDays: 30, isBuffet: true },
  { sku: "INS-BEB-09", name: "Vino Tinto Carménère Reserva Cava", category: "bebidas", unit: "Bot", cost: 6500, defaultShelfLifeDays: 365, isBuffet: false },
  { sku: "INS-PESC-10", name: "Salmón Fresco Chileno Porcionado", category: "pescados", unit: "Kg", cost: 16800, defaultShelfLifeDays: 3, isBuffet: true },
] as const;

/**
 * Genera un conjunto de lotes sintéticos calibrados exactamente para cumplir la distribución
 * porcentual del escenario de demostración solicitado:
 * - HEALTHY: 0% vencido, 10% advertencia, 90% óptimo.
 * - WARNING: 0% vencido, 20% crítico (venciendo en 48h), 30% advertencia, 50% óptimo.
 * - CRITICAL: 15% caducado, 35% riesgo crítico, 25% advertencia, 25% óptimo.
 */
export function generateScenarioBatches(
  scenarioId: FefoDemoScenarioId,
  referenceDateIso: string,
  warehouseId = "bod-cocina-central",
  exchangeRate?: number
): readonly FefoBatchSimulationImpact[] {
  // Cantidad base de lotes: 20 para permitir granularidad entera precisa de porcentajes
  const totalLots = 20;
  const cfg = FEFO_DEMO_SCENARIO_CONFIGS[scenarioId];
  const { warningPct, criticalPct, expiredPct } = cfg.distribution;

  const expiredCount = Math.round((expiredPct / 100) * totalLots);
  const criticalCount = Math.round((criticalPct / 100) * totalLots);
  const warningCount = Math.round((warningPct / 100) * totalLots);
  const optimalCount = totalLots - (expiredCount + criticalCount + warningCount);

  const targets: Array<{ days: number; isBuffet: boolean }> = [];

  // 1. Expired (<= 0 días)
  for (let i = 0; i < expiredCount; i++) {
    // -1 a -5 días
    targets.push({ days: -(1 + (i % 5)), isBuffet: i % 2 === 0 });
  }

  // 2. Critical (1 a 6 días, priorizando <= 2 días para WARNING scenario)
  for (let i = 0; i < criticalCount; i++) {
    const days = scenarioId === "WARNING"
      ? (i % 2 === 0 ? 1 : 2) // 48h
      : 1 + (i % 6);
    targets.push({ days, isBuffet: i % 2 === 1 });
  }

  // 3. Warning (7 a 14 días)
  for (let i = 0; i < warningCount; i++) {
    targets.push({ days: 7 + (i % 8), isBuffet: false });
  }

  // 4. Optimal (>= 15 días)
  for (let i = 0; i < optimalCount; i++) {
    targets.push({ days: 15 + (i * 7), isBuffet: false });
  }

  // Construir lotes evaluados
  return targets.map((t, idx) => {
    const seed = SEED_CATALOG[idx % SEED_CATALOG.length] ?? SEED_CATALOG[0]!;
    const batchId = `LOT-${scenarioId.slice(0, 3)}-${String(idx + 1).padStart(3, "0")}`;
    const expiryIso = shiftIsoDate(referenceDateIso, t.days);
    const stockQty = 10 + (idx * 2.5);

    const input: BatchEvaluationInput = {
      batchId,
      productSku: seed.sku,
      productName: seed.name,
      category: seed.category,
      warehouseId,
      isBuffetBatch: t.isBuffet,
      originalExpiryDate: expiryIso,
      stockQuantity: stockQty,
      unitMeasure: seed.unit,
      unitCost: seed.cost,
    };

    return evaluateBatchSimulation(input, referenceDateIso, 0, exchangeRate);
  });
}

/**
 * Calcula el resumen consolidado de simulación FEFO a partir de una lista de lotes evaluados.
 */
export function summarizeFefoSimulation(
  batches: readonly FefoBatchSimulationImpact[],
  simulatedDateIso: string,
  scenarioId?: FefoDemoScenarioId | null,
  currency = "CLP",
  targetFxCurrency = "USD"
): FefoSimulationResponse {
  let optimalCount = 0;
  let warningCount = 0;
  let criticalCount = 0;
  let expiredCount = 0;
  let totalRiskClp = 0;
  let totalRiskFx = 0;

  for (const b of batches) {
    const canonical = b.canonicalStatus ?? classifyFefoStatus(b.daysToExpiration);
    if (canonical === "OPTIMAL") optimalCount++;
    else if (canonical === "WARNING") warningCount++;
    else if (canonical === "CRITICAL") criticalCount++;
    else if (canonical === "EXPIRED") expiredCount++;

    totalRiskClp += b.estimatedLossAmount;
    if (b.estimatedLossFxAmount) {
      totalRiskFx += b.estimatedLossFxAmount;
    }
  }

  return {
    simulationId: `sim-${Date.now().toString(36)}`,
    executedAt: new Date().toISOString(),
    simulatedSystemDate: simulatedDateIso,
    totalBatchesEvaluated: batches.length,
    optimalBatchesCount: optimalCount,
    warningBatchesCount: warningCount,
    criticalBatchesCount: criticalCount,
    expiredBatchesCount: expiredCount,
    totalSpoilageRiskAmount: Math.round(totalRiskClp * 100) / 100,
    totalSpoilageRiskFxAmount: Math.round(totalRiskFx * 100) / 100,
    currency,
    targetFxCurrency,
    alertsCreated: criticalCount + expiredCount,
    scenarioApplied: scenarioId ?? null,
    batches,
  };
}

// ============================================================================
// 5. ACCIÓN QUIRÚRGICA: SINCRONIZAR FECHAS A HOY
// ============================================================================

/**
 * Recalcula deterministamente la fecha de vencimiento de una colección de lotes para que
 * tomen como punto cero la fecha actual ("Hoy"), manteniendo la vida útil proporcional.
 * Restaura lotes vencidos para que vuelvan a tener un ciclo de rotación activo.
 */
export function syncBatchesToToday(
  batches: readonly FefoBatchSimulationImpact[],
  todayIso: string,
  recalculateBuffetLots = true
): readonly FefoBatchSimulationImpact[] {
  return batches.map((batch, idx) => {
    // Si el lote estaba vencido o en estado crítico, le otorgamos una vida útil fresca según su tipo
    let freshDaysRemaining: number;
    if (batch.daysToExpiration <= 0) {
      // Si era buffet, 4 días; si era bodega general, 20 a 29 días
      freshDaysRemaining = batch.isBuffetBatch ? 4 : 20 + (idx % 10);
    } else {
      // Al sincronizar fechas a hoy para demo quirúrgica, se restaura frescura base garantizando ciclo activo (mínimo 5 días)
      freshDaysRemaining = Math.max(batch.daysToExpiration, batch.isBuffetBatch ? 4 : 5);
    }

    if (recalculateBuffetLots && batch.isBuffetBatch) {
      // Para porciones de buffet se recalibra la ventana a un ciclo óptimo de 48h-72h (3 a 5 días)
      freshDaysRemaining = Math.max(freshDaysRemaining, 4);
    }

    const newExpiryIso = shiftIsoDate(todayIso, freshDaysRemaining);

    const input: BatchEvaluationInput = {
      batchId: batch.batchId,
      productSku: batch.productSku,
      productName: batch.productName,
      category: batch.category,
      warehouseId: batch.warehouseId,
      isBuffetBatch: batch.isBuffetBatch,
      originalExpiryDate: newExpiryIso,
      stockQuantity: batch.stockQuantity,
      unitMeasure: batch.unitMeasure,
      unitCost: batch.unitCost,
    };

    return evaluateBatchSimulation(input, todayIso, 0);
  });
}
