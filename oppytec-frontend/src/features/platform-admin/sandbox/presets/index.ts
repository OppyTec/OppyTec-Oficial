/**
 * oppytec-frontend/src/features/platform-admin/sandbox/presets/index.ts
 * Catálogo Canónico de Presets Gastronómicos Multi-Tenant para OppyTec v2.0.
 */

import { FAST_FOOD_POLLO_KING_PRESET } from "./fastFoodPolloKing";
import { CARNES_ANGUS_CAVA_PRESET } from "./carnesAngusCava";
import { HOTEL_DESAYUNO_BUFFET_PRESET } from "./hotelDesayunoBuffet";
import { CLEAN_SLATE_PRESET } from "./cleanSlate";
import type {
  GastronomicPresetDefinition,
  GastronomicPresetMeta,
} from "./types";

export * from "./types";
export { FAST_FOOD_POLLO_KING_PRESET } from "./fastFoodPolloKing";
export { CARNES_ANGUS_CAVA_PRESET } from "./carnesAngusCava";
export { HOTEL_DESAYUNO_BUFFET_PRESET } from "./hotelDesayunoBuffet";
export { CLEAN_SLATE_PRESET } from "./cleanSlate";

export const GASTRONOMIC_PRESETS: readonly GastronomicPresetDefinition[] = [
  FAST_FOOD_POLLO_KING_PRESET,
  CARNES_ANGUS_CAVA_PRESET,
  HOTEL_DESAYUNO_BUFFET_PRESET,
  CLEAN_SLATE_PRESET,
] as const;

export const GASTRONOMIC_PRESET_METAS: readonly GastronomicPresetMeta[] =
  GASTRONOMIC_PRESETS.map((p) => p.meta);

export function getGastronomicPresetById(
  id: string
): GastronomicPresetDefinition | undefined {
  return GASTRONOMIC_PRESETS.find((p) => p.meta.id === id);
}

export function getGastronomicPresetMetaById(
  id: string
): GastronomicPresetMeta | undefined {
  return GASTRONOMIC_PRESET_METAS.find((m) => m.id === id);
}

export function getDefaultGastronomicPreset(): GastronomicPresetDefinition {
  return FAST_FOOD_POLLO_KING_PRESET;
}
