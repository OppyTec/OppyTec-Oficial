// oppytec-frontend/src/shared/lib/security.test.ts
import { describe, it, expect } from "vitest";
import {
  isFormulaInjection,
  sanitizeSpreadsheetCell,
  sanitizeSpreadsheetRecord,
  validateUploadFile,
  MAX_UPLOAD_FILE_BYTES,
  MAX_BATCH_ROWS,
} from "./security";

describe("CWE-1236 Formula Injection Prevention", () => {
  it("detects formula injection in strings starting with =, +, -, @, \\t, \\r", () => {
    expect(isFormulaInjection("=cmd|'/c calc'!A0")).toBe(true);
    expect(isFormulaInjection("+SUM(1,2)")).toBe(true);
    expect(isFormulaInjection("-SUM(1,2)")).toBe(true);
    expect(isFormulaInjection("@SUM(1,2)")).toBe(true);
    expect(isFormulaInjection("\t=1+1")).toBe(true);
    expect(isFormulaInjection("\r=1+1")).toBe(true);
    expect(isFormulaInjection("  =SUM(A1:B10)")).toBe(true);
  });

  it("does not flag normal strings or numbers", () => {
    expect(isFormulaInjection("Lomo Vetado Angus")).toBe(false);
    expect(isFormulaInjection("CAR-001")).toBe(false);
    expect(isFormulaInjection("14500")).toBe(false);
    expect(isFormulaInjection("")).toBe(false);
  });

  it("sanitizes cells by prepending single quote", () => {
    expect(sanitizeSpreadsheetCell("=cmd|'/c calc'!A0")).toBe("'=cmd|'/c calc'!A0");
    expect(sanitizeSpreadsheetCell("+100")).toBe("'+100");
    expect(sanitizeSpreadsheetCell("-50")).toBe("'-50");
    expect(sanitizeSpreadsheetCell("@import")).toBe("'@import");
    expect(sanitizeSpreadsheetCell("\tvalue")).toBe("'\tvalue");
    expect(sanitizeSpreadsheetCell("\rvalue")).toBe("'\rvalue");
    expect(sanitizeSpreadsheetCell("  =SUM(1)")).toBe("'  =SUM(1)");
    expect(sanitizeSpreadsheetCell("Harina Flor")).toBe("Harina Flor");
    expect(sanitizeSpreadsheetCell(null)).toBe("");
    expect(sanitizeSpreadsheetCell(undefined)).toBe("");
  });

  it("sanitizes all string fields in a record", () => {
    const raw = {
      nombre: "=cmd|calc",
      sku: "SKU-001",
      costo: 1000,
      categoria: "+Categoría Maliciosa",
    };
    const sanitized = sanitizeSpreadsheetRecord(raw);
    expect(sanitized.nombre).toBe("'=cmd|calc");
    expect(sanitized.sku).toBe("SKU-001");
    expect(sanitized.costo).toBe(1000);
    expect(sanitized.categoria).toBe("'+Categoría Maliciosa");
  });
});

describe("File Upload Hardening & DoS Prevention", () => {
  it("exports batch row limit of 1500 and 10MB limit", () => {
    expect(MAX_BATCH_ROWS).toBe(1500);
    expect(MAX_UPLOAD_FILE_BYTES).toBe(10 * 1024 * 1024);
  });

  it("blocks files exceeding 10MB limit", () => {
    const hugeFile = new File([new Uint8Array(11 * 1024 * 1024)], "archivo_pesado.xlsx");
    const result = validateUploadFile(hugeFile);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("supera el límite máximo permitido");
  });

  it("blocks empty files (0 bytes)", () => {
    const emptyFile = new File([], "vacio.xlsx");
    const result = validateUploadFile(emptyFile);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("está vacío");
  });

  it("blocks executable extensions (.exe, .sh, .bat, etc.)", () => {
    const exeFile = new File([new Uint8Array(100)], "malware.exe");
    expect(validateUploadFile(exeFile).valid).toBe(false);

    const shFile = new File([new Uint8Array(100)], "script.sh");
    expect(validateUploadFile(shFile).valid).toBe(false);
  });

  it("blocks double extensions (.pdf.exe, .xlsx.sh, .backup.pdf)", () => {
    const doubleExt1 = new File([new Uint8Array(100)], "factura.pdf.exe");
    expect(validateUploadFile(doubleExt1).valid).toBe(false);

    const doubleExt2 = new File([new Uint8Array(100)], "catalogo.xlsx.sh");
    expect(validateUploadFile(doubleExt2).valid).toBe(false);

    const doubleExt3 = new File([new Uint8Array(100)], "datos.backup.xlsx");
    expect(validateUploadFile(doubleExt3).valid).toBe(false);
  });

  it("accepts valid safe files with allowed extensions", () => {
    const validFile = new File([new Uint8Array(1024)], "catalogo.xlsx");
    const result = validateUploadFile(validFile, {
      allowedExtensions: [".xlsx", ".xls", ".csv"],
    });
    expect(result.valid).toBe(true);
    expect(result.sanitizedFileName).toBe("catalogo.xlsx");
  });
});
