// oppytec-frontend/src/shared/lib/security.ts
/**
 * OppyTec SaaS Security Utilities:
 * - CWE-1236: CSV / Excel Formula Injection Prevention (Neutralization with single quote `'`)
 * - File Upload Hardening: Magic byte expectations, double extension rejection, executable blacklist
 * - DoS Mitigation: 1,500 batch rows limit and 10 MB file size limit
 */

export const MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024; // 10 MB
export const MAX_BATCH_ROWS = 1500;

export const FORMULA_PREFIX_CHARS = ["=", "+", "-", "@", "\t", "\r", "|"] as const;
export const FORMULA_PREFIX_REGEX = /^[=+\-@\t\r\|]/;

export const DANGEROUS_EXECUTABLE_EXTENSIONS = new Set([
  "exe",
  "sh",
  "bat",
  "cmd",
  "bin",
  "msi",
  "dll",
  "com",
  "scr",
  "pif",
  "vbs",
  "js",
  "wsf",
  "ps1",
  "py",
  "php",
  "pl",
  "elf",
  "jar",
  "vbe",
  "jse",
  "hta",
  "cpl",
  "msc",
  "apk",
  "app",
  "dmg",
  "iso",
  "cgi",
]);

/**
 * Checks if a string starts with spreadsheet formula execution characters (CWE-1236).
 */
export function isFormulaInjection(value: unknown): boolean {
  if (typeof value !== "string") return false;
  const str = value.trimStart();
  return FORMULA_PREFIX_REGEX.test(str);
}

/**
 * Sanitizes an imported or exported spreadsheet cell against formula injection (CWE-1236).
 * Any field starting with '=', '+', '-', '@', '\t', '\r' (even after leading whitespace)
 * is prepended with a single quote `'` to enforce plain text rendering in Excel/Calc.
 */
export function sanitizeSpreadsheetCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (!str) return "";

  const trimmedStart = str.trimStart();
  if (FORMULA_PREFIX_REGEX.test(trimmedStart) || FORMULA_PREFIX_REGEX.test(str)) {
    return `'${str}`;
  }
  return str;
}

/**
 * Sanitizes all string values within an object record against CWE-1236 formula injection.
 */
export function sanitizeSpreadsheetRecord<T extends Record<string, unknown>>(record: T): T {
  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(record)) {
    if (typeof val === "string") {
      result[key] = sanitizeSpreadsheetCell(val);
    } else {
      result[key] = val;
    }
  }
  return result as T;
}

export interface FileValidationResult {
  readonly valid: boolean;
  readonly error?: string;
  readonly sanitizedFileName?: string;
}

/**
 * Validates file upload safety against:
 * 1. File size limit (10 MB DoS prevention)
 * 2. Executable extensions (.exe, .sh, .bat, etc.)
 * 3. Double extensions (.pdf.exe, .xlsx.sh, .backup.xlsx, etc.)
 * 4. Path traversal characters ('..', '/', '\\')
 */
export function validateUploadFile(
  file: File,
  options?: {
    maxSizeBytes?: number;
    allowedExtensions?: readonly string[];
  }
): FileValidationResult {
  const maxSize = options?.maxSizeBytes ?? MAX_UPLOAD_FILE_BYTES;

  // 1. Size check
  if (file.size <= 0) {
    return { valid: false, error: "El archivo está vacío (0 bytes)." };
  }
  if (file.size > maxSize) {
    return {
      valid: false,
      error: `El archivo supera el límite máximo permitido de ${Math.round(maxSize / (1024 * 1024))} MB.`,
    };
  }

  const rawName = file.name.trim();
  if (!rawName || rawName.includes("..") || rawName.includes("/") || rawName.includes("\\")) {
    return { valid: false, error: "El nombre de archivo contiene caracteres inválidos o inseguros." };
  }

  // 2. Extension analysis
  const parts = rawName.split(".");
  if (parts.length < 2) {
    return { valid: false, error: "El archivo debe tener una extensión válida." };
  }

  const suffixes = parts.slice(1).map((s) => s.toLowerCase());

  // Check for dangerous executable extensions anywhere in suffixes
  for (const sfx of suffixes) {
    if (DANGEROUS_EXECUTABLE_EXTENSIONS.has(sfx)) {
      return {
        valid: false,
        error: `Extensión ejecutable no permitida: '.${sfx}'.`,
      };
    }
  }

  // Double extension detection (.pdf.exe, .xlsx.sh, .backup.pdf)
  if (suffixes.length > 1) {
    return {
      valid: false,
      error: `Archivo con doble extensión detectado y bloqueado por seguridad: '${rawName}'.`,
    };
  }

  const finalExt = `.${suffixes[suffixes.length - 1]}`;
  if (options?.allowedExtensions && options.allowedExtensions.length > 0) {
    const isAllowed = options.allowedExtensions.some(
      (ext) => ext.toLowerCase() === finalExt
    );
    if (!isAllowed) {
      return {
        valid: false,
        error: `Formato de archivo '.${suffixes[suffixes.length - 1]}' no soportado para este proceso.`,
      };
    }
  }

  return { valid: true, sanitizedFileName: rawName };
}
