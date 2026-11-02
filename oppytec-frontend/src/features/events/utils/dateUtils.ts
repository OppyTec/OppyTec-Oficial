// oppytec-frontend/src/features/events/utils/dateUtils.ts
/**
 * Utilidades de fecha y formateo en español para el módulo de Eventos y Calendario.
 * Cero dependencias externas pesadas, compatible con estándares ISO y zonas horarias locales.
 */

export const DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"] as const;
export const DAY_NAMES_FULL = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
] as const;

export const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

export const PALETA_COLORES_EVENTOS = [
  "#ec4899", // Rosa institucional
  "#f43f5e", // Rose
  "#ef4444", // Rojo
  "#f97316", // Naranja
  "#f59e0b", // Ámbar
  "#eab308", // Amarillo
  "#84cc16", // Lima
  "#22c55e", // Verde
  "#10b981", // Esmeralda
  "#14b8a6", // Teal
  "#06b6d4", // Cian
  "#0ea5e9", // Sky
  "#3b82f6", // Azul
  "#6366f1", // Índigo
  "#8b5cf6", // Violeta
  "#a855f7", // Púrpura
  "#d946ef", // Fucsia
  "#78716c", // Piedra
  "#475569", // Pizarra
  "#1e293b", // Medianoche
];

/**
 * Parsea una fecha en formato YYYY-MM-DD sin desfase UTC de medianoche.
 */
export function parseDateLocal(dateStr: string | Date | null | undefined): Date {
  if (!dateStr) return new Date();
  if (dateStr instanceof Date) return dateStr;

  const trimmed = dateStr.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    const parts = trimmed.split("-").map(Number);
    const y = parts[0] ?? 2026;
    const m = parts[1] ?? 1;
    const d = parts[2] ?? 1;
    return new Date(y, m - 1, d);
  }

  const parsed = new Date(trimmed);
  return isNaN(parsed.getTime()) ? new Date() : parsed;
}

/**
 * Retorna fecha en formato ISO 'YYYY-MM-DD'.
 */
export function formatDateISO(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Formatea una fecha a español completo: 'Lunes 15 de Noviembre, 2026'.
 */
export function formatDateES(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "—";
  const d = parseDateLocal(dateInput);
  if (isNaN(d.getTime())) return "—";

  const dayOfWeekIndex = (d.getDay() + 6) % 7; // 0 = Lunes, 6 = Domingo
  const dayName = DAY_NAMES_FULL[dayOfWeekIndex] || "";
  const day = d.getDate();
  const monthName = MONTH_NAMES[d.getMonth()] || "";
  const year = d.getFullYear();

  return `${dayName} ${day} de ${monthName}, ${year}`;
}

/**
 * Formatea una fecha a español corto: '15 Nov 2026'.
 */
export function formatDateShort(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "—";
  const d = parseDateLocal(dateInput);
  if (isNaN(d.getTime())) return "—";

  const day = d.getDate();
  const monthName = (MONTH_NAMES[d.getMonth()] || "").slice(0, 3);
  const year = d.getFullYear();

  return `${day} ${monthName} ${year}`;
}

/**
 * Retorna el Lunes correspondiente a la semana de la fecha entregada.
 */
export function getMondayOfWeek(date: Date): Date {
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(date);
  monday.setDate(date.getDate() + diff);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

/**
 * Comprueba si dos fechas corresponden al mismo día del calendario.
 */
export function isSameDay(d1: Date, d2: Date): boolean {
  return (
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
  );
}

/**
 * Formatea hora tipo '19:00:00' a '19:00'.
 */
export function formatTimeShort(t?: string | null): string {
  if (!t) return "";
  return t.slice(0, 5);
}

/**
 * Detecta colisión horaria entre dos intervalos 'HH:MM'.
 */
export function areIntervalsColliding(
  startA?: string | null,
  endA?: string | null,
  startB?: string | null,
  endB?: string | null
): boolean {
  if (!startA || !endA || !startB || !endB) return false;

  const toMinutes = (timeStr: string) => {
    const [h, m] = timeStr.split(":").map(Number);
    return (h || 0) * 60 + (m || 0);
  };

  const aStart = toMinutes(startA);
  let aEnd = toMinutes(endA);
  const bStart = toMinutes(startB);
  let bEnd = toMinutes(endB);

  // Si termina después de la medianoche (ej: 19:00 a 02:00)
  if (aEnd <= aStart) aEnd += 24 * 60;
  if (bEnd <= bStart) bEnd += 24 * 60;

  return Math.max(aStart, bStart) < Math.min(aEnd, bEnd);
}
