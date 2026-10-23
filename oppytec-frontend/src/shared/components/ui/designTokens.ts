/**
 * Los 3 Temas Oficiales del ADN Visual de OppyTec-Legacy (Rule 21 & specs/04-DESIGN-SYSTEM.md).
 */
export const OFFICIAL_THEMES = ["light", "dark", "ocean-blue"] as const;
export type OppyTecTheme = (typeof OFFICIAL_THEMES)[number];

/**
 * Paleta Gastronómica Oficial de 42 Colores Predefinidos (Grilla 6 x 7)
 * Rescatada de OppyTec-Legacy (categoriaUI.ts).
 */
export const PRESET_COLORS = [
  // Fila 1: Rojos y Rosados
  "#EF4444", "#DC2626", "#B91C1C", "#F43F5E", "#E11D48", "#EC4899", "#DB2777",
  // Fila 2: Naranjas y Amarillos
  "#F97316", "#EA580C", "#D97706", "#F59E0B", "#EAB308", "#FACC15", "#CA8A04",
  // Fila 3: Verdes y Limas
  "#84CC16", "#65A30D", "#22C55E", "#16A34A", "#15803D", "#10B981", "#059669",
  // Fila 4: Turquesas, Cians y Azules
  "#14B8A6", "#06B6D4", "#0891B2", "#0EA5E9", "#0284C7", "#3B82F6", "#2563EB",
  // Fila 5: Índigos, Púrpuras y Violetas
  "#6366F1", "#4F46E5", "#A855F7", "#9333EA", "#8B5CF6", "#7C3AED", "#C026D3",
  // Fila 6: Grises y Neutros
  "#94A3B8", "#64748B", "#475569", "#78716C", "#57534E", "#525252", "#334155",
] as const;

export type PresetColorHex = (typeof PRESET_COLORS)[number];

/**
 * 49 Íconos Gastronómicos Oficiales organizados en 6 grupos semánticos (categoriaUI.ts).
 */
export const GASTRONOMIC_ICONS = [
  // 1. Alimentos & Platos (14)
  "utensils", "utensils-crossed", "chef-hat", "pizza", "beef", "fish", "drumstick",
  "salad", "soup", "sandwich", "egg", "croissant", "cake-slice", "ice-cream-cone",
  // 2. Frutas & Vegetales (8)
  "apple", "banana", "cherry", "citrus", "grape", "carrot", "wheat", "leaf",
  // 3. Bebidas & Bar (9)
  "coffee", "cup-soda", "wine", "beer", "martini", "glass-water", "milk", "bottle-wine", "sparkles",
  // 4. Cocina, Fuego & Frío (6)
  "flame", "snowflake", "thermometer-snowflake", "cooking-pot", "microwave", "scale",
  // 5. Bodega, Empaque & Logística (7)
  "package", "boxes", "archive", "truck", "clipboard-check", "barcode", "qr-code",
  // 6. Limpieza, Seguridad & Operación (5)
  "spray-can", "shield-alert", "recycle", "trash-2", "wrench",
] as const;

export type GastronomicIconId = (typeof GASTRONOMIC_ICONS)[number];

export type QuotaResourceKey =
  | "users"
  | "products"
  | "suppliers"
  | "recipes"
  | "combos"
  | "storage_mb";

export type QuotaSemaphoreStatus =
  | "NORMAL"
  | "WARNING"
  | "CRITICAL"
  | "OVER_QUOTA";

export function resolveQuotaSemaphoreStatus(
  activeCount: number,
  maxLimit: number
): {
  readonly status: QuotaSemaphoreStatus;
  readonly percentage: number;
} {
  if (maxLimit <= 0 || activeCount >= maxLimit) {
    return { status: "OVER_QUOTA", percentage: 100 };
  }
  const rawPct = Math.min(100, Math.round((activeCount / maxLimit) * 100));
  if (rawPct >= 95) {
    return { status: "CRITICAL", percentage: rawPct };
  }
  if (rawPct >= 80) {
    return { status: "WARNING", percentage: rawPct };
  }
  return { status: "NORMAL", percentage: rawPct };
}
