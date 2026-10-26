// oppytec-frontend/src/features/historial/exportCSV.ts
import { toast } from "sonner";
import i18next from "i18next";
import type { RegistroMovimiento } from "./types";

/**
 * Columnas canónicas exactas del informe de auditoría e historial de inventario Kardex.
 */
export const CANONICAL_AUDIT_CSV_COLUMNS = [
  "Fecha y Hora",
  "Bodega",
  "Producto",
  "Tipo de Movimiento",
  "Cantidad",
  "Unidad",
  "Usuario",
  "Motivo / Notas",
  "Saldo Resultante",
] as const;

export type CanonicalAuditCsvColumn = (typeof CANONICAL_AUDIT_CSV_COLUMNS)[number];

/**
 * Sanitiza valores para exportación CSV neutralizando vectores de Formula Injection (CWE-1236).
 * Si el texto o valor despojado de espacios iniciales comienza con '=', '+', '-', '@', '\t', '\r',
 * se antepone una comilla simple `'` para obligar a los motores de planilla a tratarlo como texto plano.
 */
export function sanitizeCsvField(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (!str) return "";
  const stripped = str.trimStart();
  if (/^[=+\-@\t\r]/.test(str) || /^[=+\-@\t\r]/.test(stripped)) {
    return `'${str}`;
  }
  return str;
}

/**
 * Formatea una fila de valores a formato estándar CSV con comillas escapadas (RFC 4180).
 */
export function formatCsvRow(fields: unknown[]): string {
  return fields
    .map((field) => {
      const sanitized = sanitizeCsvField(field);
      return `"${sanitized.replace(/"/g, '""')}"`;
    })
    .join(",");
}

/**
 * Retorna la fecha local en formato ISO YYYY-MM-DD según la zona horaria chilena (America/Santiago).
 */
export function getChileanDateIsoString(date: Date = new Date()): string {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Santiago",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  } catch {
    return date.toISOString().split("T")[0] ?? "";
  }
}

export interface CsvExportOptions {
  computeBeforeAfter?: (r: RegistroMovimiento) => { before: number; after: number } | null;
  prodName?: (id: string | number) => string;
  prodUnit?: (id: string | number) => string;
}

/**
 * Genera el contenido completo del archivo CSV con codificación UTF-8 BOM (\uFEFF)
 * y columnas canónicas de auditoría.
 */
export function generateAuditoriaCsvContent(
  registros: RegistroMovimiento[],
  options?: CsvExportOptions
): string {
  const bom = "\uFEFF";
  const computeBeforeAfter =
    options?.computeBeforeAfter ??
    ((r: RegistroMovimiento) => {
      if (
        r.delta_before !== null &&
        r.delta_before !== undefined &&
        r.delta_after !== null &&
        r.delta_after !== undefined
      ) {
        return { before: r.delta_before, after: r.delta_after };
      }
      if (
        r.saldo_resultante !== undefined &&
        r.saldo_resultante !== null &&
        r.cantidad !== undefined
      ) {
        return { before: r.saldo_resultante - r.cantidad, after: r.saldo_resultante };
      }
      return null;
    });

  const rows = registros.map((r) => {
    const pName =
      r.nombre_producto ||
      (options?.prodName ? options.prodName(r.producto_id) : `Insumo #${r.producto_id}`);
    const bName = r.nombre_bodega || (r.bodega_id ? `Bodega #${r.bodega_id}` : "—");
    const uName = r.user_display_name || "Sistema";
    const unit =
      r.unidad_medida || (options?.prodUnit ? options.prodUnit(r.producto_id) : "");

    let cantidadStr = String(r.cantidad);
    const tipoLower = r.tipo_movimiento?.toLowerCase() || "";
    if (tipoLower === "conteo" || tipoLower === "ajuste_auditoria") {
      const ba = computeBeforeAfter(r);
      if (ba) {
        cantidadStr = `${ba.before} -> ${ba.after}`;
      }
    }

    const motivoClean = r.motivo_merma ? sanitizeCsvField(r.motivo_merma) : null;
    const descClean = r.descripcion_merma ? sanitizeCsvField(r.descripcion_merma) : null;
    const motivoNotas = [motivoClean, descClean].filter(Boolean).join(" - ");

    const saldoStr =
      r.saldo_resultante !== undefined && r.saldo_resultante !== null
        ? String(r.saldo_resultante)
        : "";

    return [
      r.created_at || r.fecha_recuento,
      bName,
      pName,
      r.tipo_movimiento,
      cantidadStr,
      unit,
      uName,
      motivoNotas,
      saldoStr,
    ];
  });

  return (
    bom +
    [formatCsvRow([...CANONICAL_AUDIT_CSV_COLUMNS]), ...rows.map((row) => formatCsvRow(row))].join(
      "\r\n"
    )
  );
}

/**
 * Ejecuta la descarga segura en el cliente del informe CSV de auditoría de inventario.
 * Gestiona el ciclo de vida del Blob, DOM anchor, limpieza de memoria (URL.revokeObjectURL)
 * y feedback mediante Sonner toast.
 */
export function downloadHistorialCSV(
  registros: RegistroMovimiento[],
  options?: CsvExportOptions
): boolean {
  if (!registros || registros.length === 0) {
    return false;
  }

  const csvContent = generateAuditoriaCsvContent(registros, options);
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const dateStr = getChileanDateIsoString();
  const filename = `auditoria_inventario_${dateStr}.csv`;

  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  toast.success(
    i18next.t("export.toast_success", {
      ns: "history",
      defaultValue: "Auditoría exportada exitosamente",
    })
  );
  return true;
}
