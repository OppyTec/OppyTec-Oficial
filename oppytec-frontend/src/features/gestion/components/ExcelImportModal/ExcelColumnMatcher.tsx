// oppytec-frontend/src/features/gestion/components/ExcelImportModal/ExcelColumnMatcher.tsx
import React from "react";
import { useTranslation } from "react-i18next";
import { Check, Sparkles, AlertCircle, ArrowRight, Table2 } from "lucide-react";
import { cn } from "@/shared/lib/utils";

export interface TargetFieldDef {
  readonly key: string;
  readonly label: string;
  readonly required: boolean;
  readonly description: string;
  readonly synonyms: readonly string[];
}

export const TARGET_CATALOG_FIELDS: readonly TargetFieldDef[] = [
  {
    key: "nombre",
    label: "Nombre Comercial",
    required: true,
    description: "Nombre del producto o insumo",
    synonyms: ["nombre", "producto", "articulo", "item", "descripcion", "detalle"],
  },
  {
    key: "sku",
    label: "Código SKU",
    required: false,
    description: "Identificador interno único",
    synonyms: ["sku", "codigo", "codigo_interno", "cod", "referencia", "id_producto"],
  },
  {
    key: "codigo_barra",
    label: "Código de Barra / PLU",
    required: false,
    description: "EAN-13, UPC o código de balanza",
    synonyms: ["codigo_barra", "barcode", "ean", "ean13", "plu", "upc"],
  },
  {
    key: "categoria",
    label: "Categoría",
    required: true,
    description: "Familia o categoría principal",
    synonyms: ["categoria", "rubro", "linea", "seccion", "familia", "grupo"],
  },
  {
    key: "marca",
    label: "Marca Comercial",
    required: false,
    description: "Fabricante o marca",
    synonyms: ["marca", "brand", "fabricante", "proveedor_marca"],
  },
  {
    key: "unidad_base",
    label: "Unidad Base",
    required: true,
    description: "kg, g, L, mL, unidad, botella",
    synonyms: ["unidad", "unidad_base", "u_medida", "um", "medida", "formato"],
  },
  {
    key: "tipo_envase",
    label: "Tipo de Envase",
    required: false,
    description: "Botella, Caja, Bolsa, Lata, Granel",
    synonyms: ["envase", "tipo_envase", "embalaje", "empaque", "packaging"],
  },
  {
    key: "costo_neto",
    label: "Costo Unitario Neto",
    required: true,
    description: "Costo de compra sin IVA",
    synonyms: ["costo", "costo_neto", "costo_unitario", "precio_compra", "costo_compra", "unit_cost"],
  },
  {
    key: "precio_venta_neto",
    label: "Precio Venta Neto",
    required: false,
    description: "Precio de venta sin IVA",
    synonyms: ["precio", "precio_venta", "precio_neto", "venta", "pvp", "p_venta"],
  },
  {
    key: "stock_actual",
    label: "Stock Inicial",
    required: false,
    description: "Cantidad física disponible",
    synonyms: ["stock", "stock_inicial", "cantidad", "existencias", "saldo", "inventario"],
  },
  {
    key: "stock_minimo",
    label: "Stock Mínimo Alerta",
    required: false,
    description: "Umbral mínimo para alertas",
    synonyms: ["stock_minimo", "minimo", "alerta_stock", "stock_seguridad"],
  },
  {
    key: "bodega",
    label: "Bodega Asignada",
    required: false,
    description: "Bodega de almacenamiento",
    synonyms: ["bodega", "almacen", "sucursal", "ubicacion_bodega"],
  },
];

export type MatchConfidence = "exact" | "suggested" | "manual" | "none";

export function detectColumnMatch(header: string, fieldDef: TargetFieldDef): MatchConfidence {
  const normHeader = header.toLowerCase().replace(/[^a-z0-9]/g, "");
  const normField = fieldDef.key.toLowerCase().replace(/[^a-z0-9]/g, "");
  const normLabel = fieldDef.label.toLowerCase().replace(/[^a-z0-9]/g, "");

  if (normHeader === normField || normHeader === normLabel) {
    return "exact";
  }

  const isExactSynonym = fieldDef.synonyms.some(
    (syn) => normHeader === syn.toLowerCase().replace(/[^a-z0-9]/g, "")
  );
  if (isExactSynonym) return "exact";

  const isPartialSynonym = fieldDef.synonyms.some((syn) => {
    const s = syn.toLowerCase().replace(/[^a-z0-9]/g, "");
    return normHeader.includes(s) || s.includes(normHeader);
  });
  if (isPartialSynonym) return "suggested";

  return "none";
}

/**
 * Returns an automatic mapping dictionary given a list of Excel headers.
 */
export function autoMapExcelHeaders(excelHeaders: readonly string[]): Record<string, string> {
  const mapping: Record<string, string> = {};
  const usedHeaders = new Set<string>();

  // Pass 1: exact matches
  for (const field of TARGET_CATALOG_FIELDS) {
    for (const header of excelHeaders) {
      if (!usedHeaders.has(header)) {
        if (detectColumnMatch(header, field) === "exact") {
          mapping[field.key] = header;
          usedHeaders.add(header);
          break;
        }
      }
    }
  }

  // Pass 2: suggested matches
  for (const field of TARGET_CATALOG_FIELDS) {
    if (!mapping[field.key]) {
      for (const header of excelHeaders) {
        if (!usedHeaders.has(header)) {
          if (detectColumnMatch(header, field) === "suggested") {
            mapping[field.key] = header;
            usedHeaders.add(header);
            break;
          }
        }
      }
    }
  }

  return mapping;
}

export interface ExcelColumnMatcherProps {
  readonly excelHeaders: readonly string[];
  readonly mappings: Record<string, string>;
  readonly onMappingChange: (targetField: string, excelHeader: string) => void;
  readonly previewRows?: readonly Record<string, string>[];
}

export const ExcelColumnMatcher: React.FC<ExcelColumnMatcherProps> = ({
  excelHeaders,
  mappings,
  onMappingChange,
  previewRows = [],
}) => {
  const { t } = useTranslation(["excel_import", "gestion"]);

  // Count required fields mapped
  const requiredCount = TARGET_CATALOG_FIELDS.filter((f) => f.required).length;
  const mappedRequiredCount = TARGET_CATALOG_FIELDS.filter(
    (f) => f.required && Boolean(mappings[f.key])
  ).length;

  const isComplete = mappedRequiredCount === requiredCount;

  return (
    <div className="space-y-4" data-testid="excel-column-matcher">
      {/* Header status bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-secondary/30 border border-border">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-black uppercase text-foreground">
              {t("column_matcher.title", "Mapeo Inteligente de Columnas (IA)")}
            </h4>
            <p className="text-[11px] text-muted-foreground">
              {t(
                "column_matcher.subtitle",
                "Asigna cada columna de tu archivo a los campos del catálogo ERP."
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={cn(
              "text-[11px] font-bold px-3 py-1.5 rounded-lg border",
              isComplete
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                : "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400"
            )}
            data-testid="matcher-required-status"
          >
            {isComplete ? (
              <span className="flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5" />
                {t("column_matcher.required_ready", {
                  mapped: mappedRequiredCount,
                  total: requiredCount,
                  defaultValue: `${mappedRequiredCount}/${requiredCount} Campos requeridos listos`,
                })}
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <AlertCircle className="h-3.5 w-3.5" />
                {t("column_matcher.required_missing", {
                  mapped: mappedRequiredCount,
                  total: requiredCount,
                  missing: requiredCount - mappedRequiredCount,
                  defaultValue: `${mappedRequiredCount}/${requiredCount} Requeridos (Faltan ${requiredCount - mappedRequiredCount})`,
                })}
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Grid of field mappings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[420px] overflow-y-auto pr-1 custom-scrollbar">
        {TARGET_CATALOG_FIELDS.map((field) => {
          const selectedHeader = mappings[field.key] || "";
          const confidence: MatchConfidence = selectedHeader
            ? detectColumnMatch(selectedHeader, field) === "exact"
              ? "exact"
              : detectColumnMatch(selectedHeader, field) === "suggested"
              ? "suggested"
              : "manual"
            : "none";

          const fieldLabel = t(`column_matcher.fields.${field.key}.label`, field.label);
          const fieldDesc = t(`column_matcher.fields.${field.key}.description`, field.description);

          return (
            <div
              key={field.key}
              data-testid={`matcher-card-${field.key}`}
              className={cn(
                "p-3 rounded-xl border transition-all flex flex-col justify-between gap-2.5",
                field.required && !selectedHeader
                  ? "bg-destructive/5 border-destructive/30"
                  : selectedHeader
                  ? "bg-card border-border hover:border-primary/40"
                  : "bg-secondary/10 border-border/60"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-black text-foreground">{fieldLabel}</span>
                    {field.required && (
                      <span className="text-[10px] text-destructive font-bold uppercase">
                        {t("column_matcher.required_tag", "* Requerido")}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground block">{fieldDesc}</span>
                </div>

                {/* Confidence Badge */}
                {confidence === "exact" && (
                  <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shrink-0">
                    {t("column_matcher.confidence.exact", "Exacta")}
                  </span>
                )}
                {confidence === "suggested" && (
                  <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30 shrink-0">
                    {t("column_matcher.confidence.suggested", "Sugerida")}
                  </span>
                )}
                {confidence === "manual" && (
                  <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground border border-border shrink-0">
                    {t("column_matcher.confidence.manual", "Manual")}
                  </span>
                )}
                {confidence === "none" && field.required && (
                  <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-destructive/15 text-destructive border border-destructive/30 shrink-0">
                    {t("column_matcher.confidence.none", "Sin mapear")}
                  </span>
                )}
              </div>

              {/* Selector de columna Excel */}
              <div className="flex items-center gap-2">
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <select
                  value={selectedHeader}
                  onChange={(e) => onMappingChange(field.key, e.target.value)}
                  data-testid={`select-mapping-${field.key}`}
                  className="w-full h-10 px-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer truncate"
                >
                  <option value="">{t("column_matcher.ignore_option", "-- Ignorar / No mapear --")}</option>
                  {excelHeaders.map((hdr) => (
                    <option key={hdr} value={hdr}>
                      {hdr}
                    </option>
                  ))}
                </select>
              </div>

              {/* Vista previa del valor en fila 1 */}
              {selectedHeader && previewRows.length > 0 && (
                <div className="flex items-center gap-1.5 pt-1 text-[10px] text-muted-foreground truncate border-t border-border/40">
                  <Table2 className="h-3 w-3 shrink-0 opacity-60" />
                  <span className="opacity-75">{t("column_matcher.example_prefix", "Ejemplo:")}</span>
                  <strong className="text-foreground truncate">
                    {previewRows[0]?.[selectedHeader] || "—"}
                  </strong>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
