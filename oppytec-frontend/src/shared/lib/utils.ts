import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatMoney(value: number): string {
  return value.toLocaleString("es-CL", {
    style: "currency",
    currency: "CLP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

export function getImageUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) {
    return path;
  }
  return path;
}

/**
 * Formats unit costs or unit prices in Chilean Pesos (CLP).
 * Shows up to 2 decimals if fractional (e.g. $156,92) or 0 decimals if exact integer.
 */
export function formatUnitCost(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return "—";
  const rounded = Math.round(value * 100) / 100;
  const hasDecimals = !Number.isInteger(rounded);
  return value.toLocaleString("es-CL", {
    style: "currency",
    currency: "CLP",
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 2,
  });
}

export function formatEquivalenciaText(equiv: number, rawUnit?: string): string {
  const u = (rawUnit || "").toLowerCase().trim();

  const isGrams = (u === "g" || u === "gr" || u === "grs" || u.includes("gram")) && !u.includes("kg") && !u.includes("kilo");
  const isKilos = u === "kg" || u === "kgs" || u.includes("kilo");
  const isMilliliters = u === "ml" || u === "cc" || u === "cm3" || u.includes("mili") || u === "mililitro" || u === "mililitros";
  const isLiters = (u === "l" || u === "lt" || u === "lts" || u.includes("litro")) && !isMilliliters;

  if (isGrams) {
    if (equiv >= 1000) {
      const kgVal = equiv / 1000;
      return `${Number.isInteger(kgVal) ? kgVal : parseFloat(kgVal.toFixed(2))} kg`;
    }
    return `${Number.isInteger(equiv) ? equiv : parseFloat(equiv.toFixed(2))} g`;
  }

  if (isKilos) {
    return `${Number.isInteger(equiv) ? equiv : parseFloat(equiv.toFixed(2))} kg`;
  }

  if (isMilliliters) {
    if (equiv >= 1000) {
      const lVal = equiv / 1000;
      return `${Number.isInteger(lVal) ? lVal : parseFloat(lVal.toFixed(2))} L`;
    }
    return `${Number.isInteger(equiv) ? equiv : parseFloat(equiv.toFixed(2))} mL`;
  }

  if (isLiters) {
    return `${Number.isInteger(equiv) ? equiv : parseFloat(equiv.toFixed(2))} L`;
  }

  const isUnits = u === "un" || u === "und" || u === "uni" || u.includes("unidad");
  if (isUnits) {
    return `${Number.isInteger(equiv) ? equiv : parseFloat(equiv.toFixed(2))} un`;
  }

  return `${Number.isInteger(equiv) ? equiv : parseFloat(equiv.toFixed(2))} ${rawUnit || "un"}`;
}

export function formatUnitContent(contenido?: number | null, unidad?: string | null): string {
  if (contenido === undefined || contenido === null) return "";
  const num = Number(contenido);
  if (isNaN(num)) return "";

  const raw = (unidad || "").trim().toLowerCase();

  if (raw.includes("gram") || raw.includes("(g)") || raw === "g" || raw === "gr") {
    return `${num}g`;
  }
  if (raw.includes("mililitro") || raw.includes("(ml)") || raw === "ml") {
    return `${num}ml`;
  }
  if (raw.includes("litro") || raw.includes("(l)") || raw === "l") {
    return `${num}L`;
  }
  if (raw.includes("kilo") || raw.includes("(kg)") || raw === "kg") {
    return `${num}kg`;
  }
  if (raw.includes("cc")) {
    return `${num}cc`;
  }
  if (raw.includes("unidad") || raw.includes("(un)") || raw === "un" || raw === "u") {
    return num === 1 ? `${num} unidad` : `${num} unidades`;
  }

  return `${num} ${unidad}`;
}

function isPureUnitString(str: string): boolean {
  const s = str.trim().toLowerCase();
  return s.includes("gramos") || s.includes("litros") || s.includes("kilos") || s.includes("mililitros") || s.includes("(g)") || s.includes("(ml)") || s.includes("(l)") || s.includes("(kg)") || s.includes("(un)");
}

export function formatProductSubtitle(p: any): string {
  if (!p) return "";

  const marca = p.marca || p.marca_rel?.nombre;
  const envaseNombre = p.tipo_envase_rel?.nombre || (p.unidad_envase && !isPureUnitString(p.unidad_envase) ? p.unidad_envase : "");

  const unitForContent = p.unidad_envase || p.unidad;
  const contenidoFormatted = p.contenido_envase ? formatUnitContent(p.contenido_envase, unitForContent) : "";
  const drenadoFormatted = (p.contenido_drenado && Number(p.contenido_drenado) > 0)
    ? formatUnitContent(p.contenido_drenado, unitForContent)
    : "";

  let envaseConContenido = "";
  const isGranel = envaseNombre.toLowerCase().includes("granel");

  if (isGranel) {
    envaseConContenido = "A Granel";
  } else if (envaseNombre && contenidoFormatted) {
    envaseConContenido = `${envaseNombre} (${contenidoFormatted}${drenadoFormatted ? ` • 💧 Drenado: ${drenadoFormatted}` : ""})`;
  } else if (envaseNombre) {
    envaseConContenido = `${envaseNombre}${drenadoFormatted ? ` (💧 Drenado: ${drenadoFormatted})` : ""}`;
  } else if (contenidoFormatted) {
    envaseConContenido = `(${contenidoFormatted}${drenadoFormatted ? ` • 💧 Drenado: ${drenadoFormatted}` : ""})`;
  } else if (p.unidad) {
    const uClean = p.unidad.trim().toLowerCase();
    envaseConContenido = uClean === "unidad" || uClean === "un" ? "1 unidad" : p.unidad;
  }

  const parts = [];
  if (marca) parts.push(marca);
  if (envaseConContenido) parts.push(envaseConContenido);

  if (parts.length === 0) {
    return p.categoria?.nombre || "Sin Categoría";
  }

  return parts.join(" • ");
}
