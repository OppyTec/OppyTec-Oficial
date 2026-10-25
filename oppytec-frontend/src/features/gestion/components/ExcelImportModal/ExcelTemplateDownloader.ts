// oppytec-frontend/src/features/gestion/components/ExcelImportModal/ExcelTemplateDownloader.ts
import { sanitizeSpreadsheetCell } from "@/shared/lib/security";

export interface ExcelTemplateColumn {
  readonly key: string;
  readonly label: string;
  readonly required: boolean;
  readonly example: string;
  readonly description: string;
}

export const EXCEL_TEMPLATE_COLUMNS: readonly ExcelTemplateColumn[] = [
  {
    key: "nombre",
    label: "Nombre Comercial",
    required: true,
    example: "Lomo Vetado Angus",
    description: "Nombre base o comercial del producto",
  },
  {
    key: "sku",
    label: "SKU / Código Interno",
    required: false,
    example: "CAR-LOM-001",
    description: "Identificador único de inventario",
  },
  {
    key: "codigo_barra",
    label: "Código de Barra / PLU",
    required: false,
    example: "7801234567890",
    description: "EAN-13, UPC o código de balanza",
  },
  {
    key: "categoria",
    label: "Categoría",
    required: true,
    example: "Carnes y Aves",
    description: "Categoría principal de clasificación",
  },
  {
    key: "marca",
    label: "Marca Comercial",
    required: false,
    example: "Angus Pride",
    description: "Marca del fabricante o productor",
  },
  {
    key: "unidad_base",
    label: "Unidad Base",
    required: true,
    example: "kg",
    description: "kg, g, L, mL, unidad, botella, lata",
  },
  {
    key: "tipo_envase",
    label: "Tipo de Envase",
    required: false,
    example: "Bolsa al Vacío",
    description: "Bolsa, Botella, Caja, Lata, Frasco, Saco, A Granel",
  },
  {
    key: "contenido_envase",
    label: "Contenido Neto",
    required: false,
    example: "1",
    description: "Cantidad numérica del envase primario",
  },
  {
    key: "costo_unitario_neto",
    label: "Costo Unitario Neto",
    required: true,
    example: "14500",
    description: "Costo de compra sin IVA (CLP)",
  },
  {
    key: "iva_porcentaje",
    label: "IVA %",
    required: false,
    example: "19",
    description: "Porcentaje de IVA (normalmente 19)",
  },
  {
    key: "precio_venta_neto",
    label: "Precio Venta Neto",
    required: false,
    example: "22900",
    description: "Precio de venta sin IVA (CLP)",
  },
  {
    key: "stock_inicial",
    label: "Stock Inicial",
    required: false,
    example: "25",
    description: "Cantidad física inicial en existencia",
  },
  {
    key: "stock_minimo",
    label: "Stock Mínimo Alerta",
    required: false,
    example: "10",
    description: "Umbral para alertas de reorden",
  },
  {
    key: "bodega",
    label: "Bodega Asignada",
    required: false,
    example: "Bodega Principal / Central",
    description: "Nombre o ID de bodega física",
  },
  {
    key: "pasillo",
    label: "Pasillo (A-Z)",
    required: false,
    example: "C",
    description: "Coordenada de pasillo en bodega",
  },
  {
    key: "rack",
    label: "Rack / Nivel (1-9)",
    required: false,
    example: "2",
    description: "Nivel de estante físico",
  },
];

export const SAMPLE_TEMPLATE_ROWS = [
  {
    nombre: "Lomo Vetado Angus",
    sku: "CAR-LOM-001",
    codigo_barra: "7801234567890",
    categoria: "Carnes y Aves",
    marca: "Angus Pride",
    unidad_base: "kg",
    tipo_envase: "Bolsa al Vacío",
    contenido_envase: "1",
    costo_unitario_neto: "14500",
    iva_porcentaje: "19",
    precio_venta_neto: "22900",
    stock_inicial: "25",
    stock_minimo: "10",
    bodega: "Bodega Principal / Central",
    pasillo: "C",
    rack: "2",
  },
  {
    nombre: "Vino Cabernet Sauvignon Reserva",
    sku: "BEB-VIN-008",
    codigo_barra: "7808901234567",
    categoria: "Vinos y Licores",
    marca: "Concha y Toro",
    unidad_base: "botella",
    tipo_envase: "Botella",
    contenido_envase: "750",
    costo_unitario_neto: "5200",
    iva_porcentaje: "19",
    precio_venta_neto: "14900",
    stock_inicial: "48",
    stock_minimo: "18",
    bodega: "Bar / Cava",
    pasillo: "A",
    rack: "1",
  },
  {
    nombre: "Aceite de Oliva Extra Virgen",
    sku: "ABA-ACE-006",
    codigo_barra: "7806789012345",
    categoria: "Abarrotes e Insumos Secos",
    marca: "La Finca",
    unidad_base: "L",
    tipo_envase: "Bidón",
    contenido_envase: "5",
    costo_unitario_neto: "32000",
    iva_porcentaje: "19",
    precio_venta_neto: "45000",
    stock_inicial: "15",
    stock_minimo: "6",
    bodega: "Bodega Principal / Central",
    pasillo: "D",
    rack: "3",
  },
];

/**
 * Neutralizes Excel / CSV Formula Injection (CWE-1236) by prepending a single quote.
 */
export function sanitizeSpreadsheetFormula(val: unknown): string {
  return sanitizeSpreadsheetCell(val);
}

/**
 * Generates and downloads the official ERP product catalog import template.
 * Uses CSV format with UTF-8 BOM so Excel automatically recognizes encoding, accents, and delimiters.
 */
export function downloadExcelTemplate(
  format: "csv" | "xlsx" = "csv",
  filename = "plantilla_importacion_productos_oppytec"
): void {
  const headers = EXCEL_TEMPLATE_COLUMNS.map((col) => `"${sanitizeSpreadsheetFormula(col.label)}"`).join(";");
  
  const rows = SAMPLE_TEMPLATE_ROWS.map((row) =>
    EXCEL_TEMPLATE_COLUMNS.map((col) => {
      const val = row[col.key as keyof typeof row] || "";
      const cleanVal = sanitizeSpreadsheetFormula(val);
      return `"${cleanVal.replace(/"/g, '""')}"`;
    }).join(";")
  );

  const csvContent = "\uFEFF" + [headers, ...rows].join("\r\n");

  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const extension = format === "xlsx" ? "csv" : "csv"; // CSV format with Excel BOM is standard for universal opening
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `${filename}.${extension}`);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
