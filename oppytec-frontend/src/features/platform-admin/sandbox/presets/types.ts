/**
 * oppytec-frontend/src/features/platform-admin/sandbox/presets/types.ts
 * Contratos de tipo TypeScript estrictos (0 `any`, `readonly` properties)
 * para los Presets Gastronómicos Canónicos Multi-Tenant de OppyTec v2.0.
 */

export type GastronomicPresetId =
  | "fast-food-pollo-king"
  | "carnes-angus-cava"
  | "hotel-desayuno-buffet"
  | "clean-slate";

export type GastronomicPresetCategory =
  | "fast_food"
  | "steakhouse"
  | "hospitality"
  | "minimal";

export interface GastronomicPresetKpisSummary {
  readonly totalSkus: number;
  readonly totalWarehouses: number;
  readonly totalFefoBatches: number;
  readonly totalRecipes: number;
  readonly criticalBatches: number;
}

export interface GastronomicPresetMeta {
  readonly id: GastronomicPresetId;
  readonly code: string;
  readonly title: string;
  readonly titleKey: string;
  readonly subtitle: string;
  readonly subtitleKey?: string;
  readonly description: string;
  readonly descriptionKey: string;
  readonly category: GastronomicPresetCategory;
  readonly badge: string;
  readonly badgeKey?: string;
  readonly color: string;
  readonly rgb: string;
  readonly iconName: string;
  readonly defaultTenantSchema: string;
  readonly defaultHoldingId: string;
  readonly defaultHoldingName: string;
  readonly estimatedStockValueClp: number;
  readonly kpisSummary: GastronomicPresetKpisSummary;
}

export interface EditableHoldingDto {
  readonly id: string;
  readonly nombre: string;
  readonly rut: string;
  readonly razonSocial: string;
  readonly planId: string;
}

export interface EditableTenantDto {
  readonly id: string;
  readonly holdingId: string;
  readonly schemaName: string;
  readonly nombre: string;
  readonly ciudad: string;
  readonly direccion: string;
  readonly telefono: string;
}

export interface EditableWarehouseDto {
  readonly id: string | number;
  readonly tenantId: string;
  readonly nombre: string;
  readonly tipo: "refrigerado" | "seco" | "cocina" | "barra" | "salon";
  readonly icono: string;
  readonly color: string;
}

export interface EditableProductDto {
  readonly id: number;
  readonly sku: string;
  readonly nombre: string;
  readonly categoria: string;
  readonly categoriaColor: string;
  readonly categoriaIcono: string;
  readonly bodegaId: number | string;
  readonly stockActual: number;
  readonly stockMinimo: number;
  readonly stockMaximo: number;
  readonly puntoReorden: number;
  readonly unidadMedida: string;
  readonly costoUnitarioPpp: number;
  readonly precioVentaSugerido: number;
  readonly semaforo: "OPTIMO" | "MINIMO" | "CRITICO";
  readonly noPerecible: boolean;
  readonly diasAlertaVencimiento: number;
}

export interface EditableFefoBatchDto {
  readonly id: string;
  readonly productoId: number;
  readonly productoSku: string;
  readonly loteCodigo: string;
  readonly bodegaId: number | string;
  readonly fechaElaboracion: string;
  readonly fechaVencimiento: string;
  readonly cantidad: number;
  readonly costoUnitario: number;
  readonly estadoFefo: "OPTIMO" | "PROXIMO" | "CRITICO" | "VENCIDO";
}

export interface EditableRecipeIngredientDto {
  readonly productoId: number;
  readonly nombre: string;
  readonly cantidadRequerida: number;
  readonly unidadMedida: string;
  readonly mermaOperativaPorcentaje: number;
  readonly costoCalculado: number;
}

export interface EditableRecipeDto {
  readonly id: number;
  readonly codigo: string;
  readonly nombre: string;
  readonly categoria: string;
  readonly porciones: number;
  readonly costoTotalEstimado: number;
  readonly precioVentaSugerido: number;
  readonly margenEstimadoPorcentaje: number;
  readonly ingredientes: readonly EditableRecipeIngredientDto[];
}

export interface EditableFinOpsAllocationDto {
  readonly tenantId: string;
  readonly tokenBudgetMonthly: number;
  readonly tokensConsumed: number;
  readonly creditsClpBudget: number;
  readonly creditsClpSpent: number;
}

export interface GastronomicDatasetPayload {
  readonly schemaVersion: "2.0";
  readonly presetId: GastronomicPresetId;
  readonly updatedAtIso: string;
  readonly isCustomized: boolean;
  readonly holdings: readonly EditableHoldingDto[];
  readonly tenants: readonly EditableTenantDto[];
  readonly warehouses: readonly EditableWarehouseDto[];
  readonly products: readonly EditableProductDto[];
  readonly batches: readonly EditableFefoBatchDto[];
  readonly recipes: readonly EditableRecipeDto[];
  readonly finops: readonly EditableFinOpsAllocationDto[];
}

export interface GastronomicPresetDefinition {
  readonly meta: GastronomicPresetMeta;
  readonly dataset: GastronomicDatasetPayload;
}

export interface MockDataResetResponse {
  readonly tenantSchema: string;
  readonly presetRestored: GastronomicPresetId;
  readonly restoredAt: string;
  readonly tablesTruncated: readonly string[];
  readonly recordsReseeded: Readonly<Record<string, number>>;
  readonly durationMs: number;
}
