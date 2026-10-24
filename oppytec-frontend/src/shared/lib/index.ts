export * from "./utils";

import {
  formatScaledDecimal,
  parseScaledDecimal,
} from "@/shared/currency";

export type UnitLayer = "purchase" | "storage" | "recipe";

export interface ThreeLayerUnitProfile {
  readonly code: string;
  readonly purchaseUnit: string;
  readonly storageUnit: string;
  readonly recipeUnit: string;
  readonly purchaseToStorageFactor: string;
  readonly storageToRecipeFactor: string;
}

const SCALE_FACTOR = 100_000_000n;

/**
 * Exact 3-layer unit conversion (`purchase <-> storage <-> recipe`) using 10^8 fixed-point BigInt math.
 * Returns a 4-decimal string (e.g. `"15000.0000"`).
 */
export function convertThreeLayerQuantity(
  quantity: string | number,
  fromLayer: UnitLayer,
  toLayer: UnitLayer,
  profile: ThreeLayerUnitProfile
): string {
  const qtyScaled = parseScaledDecimal(quantity);
  if (fromLayer === toLayer) {
    return formatScaledDecimal(qtyScaled, 4);
  }

  const p2s = parseScaledDecimal(profile.purchaseToStorageFactor);
  const s2r = parseScaledDecimal(profile.storageToRecipeFactor);

  // Normalize to storage layer first (scaled by 10^8)
  let inStorageScaled: bigint;
  if (fromLayer === "purchase") {
    inStorageScaled = (qtyScaled * p2s) / SCALE_FACTOR;
  } else if (fromLayer === "storage") {
    inStorageScaled = qtyScaled;
  } else {
    inStorageScaled = (qtyScaled * SCALE_FACTOR) / s2r;
  }

  // Convert from storage layer to target layer
  let targetScaled: bigint;
  if (toLayer === "storage") {
    targetScaled = inStorageScaled;
  } else if (toLayer === "recipe") {
    targetScaled = (inStorageScaled * s2r) / SCALE_FACTOR;
  } else {
    targetScaled = (inStorageScaled * SCALE_FACTOR) / p2s;
  }

  return formatScaledDecimal(targetScaled, 4);
}

/**
 * Formats an ISO-8601 timestamp into operational date format (`DD-MM-YYYY` for `es`, `YYYY-MM-DD` for `en`).
 */
export function formatOperationalDate(
  isoDateString: string,
  lang: "es" | "en" = "es"
): string {
  const datePart = isoDateString.split("T")[0] ?? isoDateString;
  const parts = datePart.split("-");
  if (parts.length !== 3) {
    return datePart;
  }
  const [year, month, day] = parts;
  if (lang === "es") {
    return `${day}-${month}-${year}`;
  }
  return `${year}-${month}-${day}`;
}
