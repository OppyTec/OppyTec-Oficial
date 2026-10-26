// oppytec-frontend/src/features/inventory/alerts/dateUtils.ts
/**
 * Lightweight, zero-dependency date formatting utility compatible with date-fns API.
 * Provides localized date string formatting and relative distance calculations in Spanish.
 */

export const es = { code: "es" };
export const en = { code: "en" };

export function parseISO(dateInput: string | Date): Date {
  if (dateInput instanceof Date) return dateInput;
  if (!dateInput || typeof dateInput !== "string") return new Date(NaN);

  // If input is YYYY-MM-DD, parse explicitly to avoid UTC midnight shifts
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateInput.trim())) {
    const parts = dateInput.trim().split("-").map(Number);
    const year = parts[0] ?? 0;
    const month = parts[1] ?? 1;
    const day = parts[2] ?? 1;
    return new Date(year, month - 1, day);
  }

  return new Date(dateInput);
}

export function isPast(dateInput: Date | string): boolean {
  const d = parseISO(dateInput);
  if (isNaN(d.getTime())) return false;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const compareDate = new Date(d);
  compareDate.setHours(23, 59, 59, 999);

  return compareDate.getTime() < today.getTime();
}

export function format(
  dateInput: Date | string | null | undefined,
  pattern: string = "dd-MM-yyyy"
): string {
  if (!dateInput) return "—";
  const d = parseISO(dateInput);
  if (isNaN(d.getTime())) return "—";

  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = String(d.getFullYear());

  if (pattern === "dd-MM-yyyy") {
    return `${day}-${month}-${year}`;
  }

  if (pattern === "yyyy-MM-dd") {
    return `${year}-${month}-${day}`;
  }

  return `${day}/${month}/${year}`;
}

export interface FormatDistanceOptions {
  readonly addSuffix?: boolean;
  readonly locale?: unknown;
}

export function formatDistanceToNow(
  dateInput: Date | string | null | undefined,
  options?: FormatDistanceOptions
): string {
  if (!dateInput) return "—";
  const targetDate = parseISO(dateInput);
  if (isNaN(targetDate.getTime())) return "—";

  const now = new Date();
  const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const targetMidnight = new Date(
    targetDate.getFullYear(),
    targetDate.getMonth(),
    targetDate.getDate()
  ).getTime();

  const diffMs = targetMidnight - todayMidnight;
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  const addSuffix = options?.addSuffix ?? true;
  const isEn =
    options?.locale === en ||
    (typeof options?.locale === "object" &&
      options?.locale !== null &&
      "code" in options.locale &&
      (options.locale as { code: string }).code === "en");

  if (diffDays === 0) {
    return isEn ? "today" : "hoy";
  }

  if (diffDays < 0) {
    const absDays = Math.abs(diffDays);
    if (absDays === 1) {
      if (isEn) return addSuffix ? "1 day ago" : "1 day";
      return addSuffix ? "hace 1 día" : "1 día";
    }
    if (absDays < 30) {
      if (isEn) return addSuffix ? `${absDays} days ago` : `${absDays} days`;
      return addSuffix ? `hace ${absDays} días` : `${absDays} días`;
    }
    const months = Math.floor(absDays / 30);
    if (months <= 1) {
      if (isEn) return addSuffix ? "1 month ago" : "1 month";
      return addSuffix ? "hace 1 mes" : "1 mes";
    }
    if (months < 12) {
      if (isEn) return addSuffix ? `${months} months ago` : `${months} months`;
      return addSuffix ? `hace ${months} meses` : `${months} meses`;
    }
    const years = Math.floor(months / 12);
    if (isEn) {
      return addSuffix
        ? `${years} ${years === 1 ? "year" : "years"} ago`
        : `${years} ${years === 1 ? "year" : "years"}`;
    }
    return addSuffix
      ? `hace ${years} ${years === 1 ? "año" : "años"}`
      : `${years} ${years === 1 ? "año" : "años"}`;
  } else {
    if (diffDays === 1) {
      if (isEn) return addSuffix ? "in 1 day" : "1 day";
      return addSuffix ? "en 1 día" : "1 día";
    }
    if (diffDays < 30) {
      if (isEn) return addSuffix ? `in ${diffDays} days` : `${diffDays} days`;
      return addSuffix ? `en ${diffDays} días` : `${diffDays} días`;
    }
    const months = Math.floor(diffDays / 30);
    if (months <= 1) {
      if (isEn) return addSuffix ? "in 1 month" : "1 month";
      return addSuffix ? "en 1 mes" : "1 mes";
    }
    if (months < 12) {
      if (isEn) return addSuffix ? `in ${months} months` : `${months} months`;
      return addSuffix ? `en ${months} meses` : `${months} meses`;
    }
    const years = Math.floor(diffDays / 365);
    if (isEn) {
      return addSuffix
        ? `in ${years} ${years === 1 ? "year" : "years"}`
        : `${years} ${years === 1 ? "year" : "years"}`;
    }
    return addSuffix
      ? `en ${years} ${years === 1 ? "año" : "años"}`
      : `${years} ${years === 1 ? "año" : "años"}`;
  }
}
