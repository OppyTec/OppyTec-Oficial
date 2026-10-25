// oppytec-frontend/src/features/gestion/components/ExcelImportModal/ExcelImportModal.tsx
import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Upload,
  FileSpreadsheet,
  Check,
  ChevronRight,
  ChevronLeft,
  Download,
  FileCheck2,
  Boxes,
  RotateCcw,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib/utils";
import {
  validateUploadFile,
  sanitizeSpreadsheetCell,
  MAX_BATCH_ROWS,
} from "@/shared/lib/security";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import {
  ExcelColumnMatcher,
  autoMapExcelHeaders,
} from "./ExcelColumnMatcher";
import { ExcelEntityMatcherBanner } from "./ExcelEntityMatcherBanner";
import {
  ExcelImportReviewGrid,
  type ParsedProductRow,
  validateProductRow,
} from "./ExcelImportReviewGrid";
import { downloadExcelTemplate } from "./ExcelTemplateDownloader";
import type { Categoria, Marca, Producto } from "../../types";

export const EXCEL_DRAFT_KEY = "oppytec_excel_draft";

export type ExcelImportStep = 1 | 2 | 3 | 4 | 5;

export interface ExcelImportModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly categorias: readonly Categoria[];
  readonly marcas: readonly Marca[];
  readonly onImportComplete?: (importedProducts: Partial<Producto>[]) => Promise<void> | void;
  readonly initialStep?: ExcelImportStep;
}

interface StoredExcelDraft {
  fileName: string;
  step: ExcelImportStep;
  headers: string[];
  mappings: Record<string, string>;
  rows: ParsedProductRow[];
  timestamp: string;
}

export const ExcelImportModal: React.FC<ExcelImportModalProps> = ({
  open,
  onOpenChange,
  categorias,
  marcas,
  onImportComplete,
  initialStep = 1,
}) => {
  const { t } = useTranslation(["excel_import", "gestion"]);
  const [currentStep, setCurrentStep] = useState<ExcelImportStep>(initialStep);
  const [fileName, setFileName] = useState<string>("");
  const [excelHeaders, setExcelHeaders] = useState<string[]>([]);
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [parsedRows, setParsedRows] = useState<ParsedProductRow[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);

  // Entity mappings
  const [categoryMappings, setCategoryMappings] = useState<Record<string, string>>({});
  const [brandMappings, setBrandMappings] = useState<Record<string, string>>({});

  // Target warehouse for imported items
  const [selectedBodega, setSelectedBodega] = useState("bod-central");

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Check draft on mount or open
  useEffect(() => {
    if (!open) return;
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const raw = window.localStorage.getItem(EXCEL_DRAFT_KEY);
        if (raw) {
          const parsed: StoredExcelDraft = JSON.parse(raw);
          if (parsed && parsed.rows && parsed.rows.length > 0) {
            setHasDraft(true);
          }
        }
      }
    } catch {
      // ignore
    }
  }, [open]);

  // Continuous auto-save draft
  useEffect(() => {
    if (!open || parsedRows.length === 0) return;
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const draft: StoredExcelDraft = {
          fileName,
          step: currentStep,
          headers: excelHeaders,
          mappings,
          rows: parsedRows,
          timestamp: new Date().toISOString(),
        };
        window.localStorage.setItem(EXCEL_DRAFT_KEY, JSON.stringify(draft));
        setHasDraft(true);
      }
    } catch {
      // ignore
    }
  }, [open, currentStep, fileName, excelHeaders, mappings, parsedRows]);

  // Restore draft
  const handleRestoreDraft = () => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const raw = window.localStorage.getItem(EXCEL_DRAFT_KEY);
        if (raw) {
          const parsed: StoredExcelDraft = JSON.parse(raw);
          setFileName(parsed.fileName || "archivo_recuperado.xlsx");
          setExcelHeaders(parsed.headers || []);
          setMappings(parsed.mappings || {});
          setParsedRows(parsed.rows || []);
          setCurrentStep(parsed.step || 2);
          toast.success(t("draft.restored_success", "Borrador de importación recuperado exitosamente"));
        }
      }
    } catch {
      toast.error(t("draft.restore_error", "Error al restaurar borrador"));
    }
  };

  // Discard draft
  const handleDiscardDraft = () => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(EXCEL_DRAFT_KEY);
      }
      setHasDraft(false);
      setFileName("");
      setExcelHeaders([]);
      setMappings({});
      setParsedRows([]);
      setCurrentStep(1);
      toast.info(t("draft.discarded_info", "Borrador descartado"));
    } catch {
      // ignore
    }
  };

  // Handle uploaded file (CSV/XLSX text parsing with File Upload Hardening and CWE-1236 Sanitization)
  const processUploadedFile = (file: File) => {
    const validation = validateUploadFile(file, {
      allowedExtensions: [".csv", ".xlsx", ".xls"],
    });
    if (!validation.valid) {
      toast.error(validation.error || t("upload.read_error", "Archivo no válido"));
      return;
    }

    setFileName(validation.sanitizedFileName || file.name);
    setIsProcessing(true);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = (e.target?.result as string) || "";
        const lines = content
          .split(/\r?\n/)
          .map((l) => l.trim())
          .filter(Boolean);

        if (lines.length === 0) {
          toast.error(t("upload.empty_file_error", "El archivo está vacío"));
          setIsProcessing(false);
          return;
        }

        // DoS Prevention: Límite estricto de 1.500 filas por lote
        if (lines.length - 1 > MAX_BATCH_ROWS) {
          toast.error(
            t("upload.batch_limit_error", {
              limit: MAX_BATCH_ROWS,
              count: lines.length - 1,
              defaultValue: `El archivo supera el límite máximo de ${MAX_BATCH_ROWS} filas por lote (${lines.length - 1} filas encontradas).`,
            })
          );
          setIsProcessing(false);
          return;
        }

        // Detect delimiter: semicolon or comma or tab
        const firstLine = lines[0] ?? "";
        let delimiter = ";";
        if (firstLine.includes(";") && !firstLine.includes(",")) delimiter = ";";
        else if (firstLine.includes(",")) delimiter = ",";
        else if (firstLine.includes("\t")) delimiter = "\t";

        const headers = firstLine
          .split(delimiter)
          .map((h) => sanitizeSpreadsheetCell(h.replace(/^["'\uFEFF]+|["']+$/g, "").trim()))
          .filter(Boolean);

        setExcelHeaders(headers);

        // Auto map headers with heuristics
        const detectedMappings = autoMapExcelHeaders(headers);
        setMappings(detectedMappings);

        // Parse rows with CWE-1236 sanitization
        const parsed: ParsedProductRow[] = [];
        for (let i = 1; i < lines.length; i++) {
          const line = lines[i];
          if (!line) continue;
          const cols = line
            .split(delimiter)
            .map((c) => sanitizeSpreadsheetCell(c.replace(/^["']+|["']+$/g, "").trim()));

          const rowObj: Record<string, string> = {};
          headers.forEach((h, idx) => {
            rowObj[h] = cols[idx] || "";
          });

          const getMappedVal = (targetKey: string) => {
            const h = detectedMappings[targetKey];
            return h ? rowObj[h] || "" : "";
          };

          const rawNombre = getMappedVal("nombre") || cols[0] || `Producto ${i}`;
          const rawSku = getMappedVal("sku") || `SKU-${Date.now().toString().slice(-4)}-${i}`;
          const rawCategoria = getMappedVal("categoria") || "General";
          const rawMarca = getMappedVal("marca") || "Genérica";
          const costo = Number(getMappedVal("costo_neto")) || 1000;
          const precio = Number(getMappedVal("precio_venta_neto")) || Math.round(costo * 1.4);
          const stock = Number(getMappedVal("stock_actual")) || 10;

          parsed.push({
            id: `row-${i}-${Date.now()}`,
            nombre: sanitizeSpreadsheetCell(rawNombre),
            sku: sanitizeSpreadsheetCell(rawSku),
            codigo_barra: sanitizeSpreadsheetCell(getMappedVal("codigo_barra") || ""),
            categoria: sanitizeSpreadsheetCell(rawCategoria),
            marca: sanitizeSpreadsheetCell(rawMarca),
            unidad_base: sanitizeSpreadsheetCell(getMappedVal("unidad_base") || "unidad"),
            tipo_envase: sanitizeSpreadsheetCell(getMappedVal("tipo_envase") || "Caja"),
            costo_neto: costo,
            precio_venta_neto: precio,
            stock_actual: stock,
            stock_minimo: Number(getMappedVal("stock_minimo")) || 5,
            bodega: sanitizeSpreadsheetCell(getMappedVal("bodega") || "Bodega Central"),
          });
        }

        setParsedRows(parsed);
        setIsProcessing(false);
        setCurrentStep(2);
        toast.success(
          t("upload.processed_success", {
            count: parsed.length,
            defaultValue: `Archivo procesado: ${parsed.length} filas detectadas`,
          })
        );
      } catch {
        toast.error(t("upload.invalid_format_error", "Error al procesar el archivo. Verifica el formato."));
        setIsProcessing(false);
      }
    };

    reader.onerror = () => {
      toast.error(t("upload.read_error", "No se pudo leer el archivo"));
      setIsProcessing(false);
    };

    reader.readAsText(file, "UTF-8");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processUploadedFile(file);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processUploadedFile(file);
    }
  };

  // Entity extraction
  const detectedCategories = useMemo(() => {
    const set = new Set<string>();
    parsedRows.forEach((r) => {
      if (r.categoria?.trim()) set.add(r.categoria.trim());
    });
    return Array.from(set);
  }, [parsedRows]);

  const detectedBrands = useMemo(() => {
    const set = new Set<string>();
    parsedRows.forEach((r) => {
      if (r.marca?.trim()) set.add(r.marca.trim());
    });
    return Array.from(set);
  }, [parsedRows]);

  // Auto create all entities handler
  const handleAutoCreateAllEntities = () => {
    const nextCatMap: Record<string, string> = {};
    detectedCategories.forEach((c) => {
      nextCatMap[c] = "__new__";
    });
    setCategoryMappings(nextCatMap);

    const nextBrandMap: Record<string, string> = {};
    detectedBrands.forEach((b) => {
      nextBrandMap[b] = "__new__";
    });
    setBrandMappings(nextBrandMap);

    toast.success(t("entity_matcher.all_created_toast", "Todas las entidades serán creadas automáticamente"));
  };

  // Review grid updates
  const handleUpdateRow = (id: string, field: keyof ParsedProductRow, value: any) => {
    setParsedRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: value } : r))
    );
  };

  const handleDeleteRow = (id: string) => {
    setParsedRows((prev) => prev.filter((r) => r.id !== id));
  };

  // Confirm import
  const handleFinalConfirmImport = async () => {
    setIsProcessing(true);
    try {
      const validItems = parsedRows.filter(
        (r) => validateProductRow(r).status !== "error"
      );

      const payload: Partial<Producto>[] = validItems.map((r) => ({
        nombre: r.nombre,
        sku: r.sku,
        codigo_barra: r.codigo_barra,
        costo_unitario: r.costo_neto,
        costo_unitario_ultimo: r.costo_neto,
        precio_venta: r.precio_venta_neto,
        stock_actual: r.stock_actual,
        unidad: r.unidad_base || "unidad",
        estado: "activo",
      }));

      if (onImportComplete) {
        await onImportComplete(payload);
      }

      // Clear draft upon successful import
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(EXCEL_DRAFT_KEY);
      }

      toast.success(
        t("confirm.import_success", {
          count: payload.length,
          defaultValue: `¡Éxito! Se han importado ${payload.length} productos al catálogo`,
        })
      );
      onOpenChange(false);
    } catch {
      toast.error(t("confirm.import_error", "Ocurrió un error durante la importación"));
    } finally {
      setIsProcessing(false);
    }
  };

  // Stepper steps definition
  const stepsList = [
    { num: 1, label: t("stepper.step_1", "Carga") },
    { num: 2, label: t("stepper.step_2", "Columnas") },
    { num: 3, label: t("stepper.step_3", "Entidades") },
    { num: 4, label: t("stepper.step_4", "Revisión") },
    { num: 5, label: t("stepper.step_5", "Confirmar") },
  ];

  return (
    <ResponsiveDialog
      open={open}
      onClose={() => onOpenChange(false)}
      title={t("modal.title", "Importador Inteligente de Productos (Excel / CSV IA)")}
      description={t(
        "modal.description",
        "Carga masiva con detección automática de columnas, entidades y validación en vivo."
      )}
      maxWidth="max-w-5xl"
    >
      <div className="space-y-4 py-1 text-foreground" data-testid="excel-import-modal">
        {/* STEPPER HEADER */}
        <div className="flex items-center justify-between border-b border-border pb-3 overflow-x-auto gap-2">
          <div className="flex items-center gap-1.5 sm:gap-2">
            {stepsList.map((step, idx) => {
              const isPast = currentStep > step.num;
              const isCurrent = currentStep === step.num;

              return (
                <React.Fragment key={step.num}>
                  {idx > 0 && (
                    <div
                      className={cn(
                        "h-0.5 w-4 sm:w-6 rounded-full transition-colors",
                        isPast ? "bg-primary" : "bg-border"
                      )}
                    />
                  )}
                  <button
                    type="button"
                    disabled={step.num > currentStep && parsedRows.length === 0}
                    onClick={() => setCurrentStep(step.num as ExcelImportStep)}
                    data-testid={`excel-step-btn-${step.num}`}
                    className={cn(
                      "touch-target flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold transition-all select-none cursor-pointer",
                      isCurrent && "bg-primary text-primary-foreground shadow-xs",
                      isPast && "bg-secondary text-foreground hover:bg-secondary/80",
                      !isCurrent && !isPast && "text-muted-foreground opacity-50 cursor-not-allowed"
                    )}
                  >
                    <span
                      className={cn(
                        "h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-black shrink-0",
                        isCurrent
                          ? "bg-primary-foreground text-primary"
                          : isPast
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {isPast ? <Check className="h-3 w-3 stroke-[3]" /> : step.num}
                    </span>
                    <span className="hidden sm:inline">{step.label}</span>
                  </button>
                </React.Fragment>
              );
            })}
          </div>

          {/* Draft Notification / Action */}
          {hasDraft && currentStep === 1 && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRestoreDraft}
                data-testid="btn-restore-excel-draft"
                className="touch-target inline-flex min-h-[38px] px-3 items-center gap-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs font-bold hover:bg-amber-500/20 cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>{t("draft.restore", "Recuperar Borrador")}</span>
              </button>
              <button
                type="button"
                onClick={handleDiscardDraft}
                data-testid="btn-discard-excel-draft"
                className="text-xs text-muted-foreground hover:text-destructive underline cursor-pointer"
              >
                {t("draft.discard", "Descartar")}
              </button>
            </div>
          )}
        </div>

        {/* STEP 1: CARGA Y DROPZONE */}
        {currentStep === 1 && (
          <div className="space-y-4" data-testid="step-1-upload">
            <div
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              data-testid="excel-dropzone"
              className="border-2 border-dashed border-border hover:border-primary/60 bg-secondary/15 hover:bg-secondary/30 rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileChange}
                data-testid="input-excel-file"
                className="hidden"
              />

              <div className="h-14 w-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-xs">
                <Upload className="h-7 w-7" />
              </div>

              <div>
                <h4 className="text-sm font-black text-foreground uppercase tracking-tight">
                  {t("upload.drag_drop", "Arrastra tu archivo Excel o CSV aquí")}
                </h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                  {t(
                    "upload.supported_formats",
                    "Formatos soportados: .XLSX, .XLS, .CSV (hasta 10 MB y 1.500 productos por lote)."
                  )}
                </p>
              </div>

              <button
                type="button"
                className="touch-target inline-flex min-h-[44px] px-5 items-center gap-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-md hover:bg-primary/90 mt-2 pointer-events-none"
              >
                <FileSpreadsheet className="h-4 w-4" />
                <span>{t("upload.select_file", "Seleccionar Archivo")}</span>
              </button>
            </div>

            {/* Template download banner */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                  <Download className="h-4 w-4" />
                </div>
                <div>
                  <h5 className="text-xs font-black text-foreground">
                    {t("upload.template_title", "¿No tienes el formato estándar?")}
                  </h5>
                  <p className="text-[11px] text-muted-foreground">
                    {t(
                      "upload.template_desc",
                      "Descarga nuestra plantilla oficial con encabezados ERP y ejemplos gastronómicos."
                    )}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => downloadExcelTemplate("csv")}
                data-testid="btn-download-template"
                className="touch-target inline-flex min-h-[44px] px-4 items-center gap-2 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-xs font-bold text-foreground cursor-pointer select-none shrink-0"
              >
                <Download className="h-3.5 w-3.5 text-primary" />
                <span>{t("upload.download_template", "Descargar Plantilla Oficial")}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: ANÁLISIS IA DE COLUMNAS */}
        {currentStep === 2 && (
          <div className="space-y-4" data-testid="step-2-mapping">
            <ExcelColumnMatcher
              excelHeaders={excelHeaders}
              mappings={mappings}
              onMappingChange={(target, hdr) =>
                setMappings((prev) => ({ ...prev, [target]: hdr }))
              }
            />
          </div>
        )}

        {/* STEP 3: DETECCIÓN DE ENTIDADES */}
        {currentStep === 3 && (
          <div className="space-y-4" data-testid="step-3-entities">
            <ExcelEntityMatcherBanner
              detectedCategories={detectedCategories}
              detectedBrands={detectedBrands}
              existingCategories={categorias}
              existingBrands={marcas}
              categoryMappings={categoryMappings}
              brandMappings={brandMappings}
              onCategoryMappingChange={(excelCat, targetId) =>
                setCategoryMappings((prev) => ({ ...prev, [excelCat]: targetId }))
              }
              onBrandMappingChange={(excelBrand, targetId) =>
                setBrandMappings((prev) => ({ ...prev, [excelBrand]: targetId }))
              }
              onAutoCreateAll={handleAutoCreateAllEntities}
            />
          </div>
        )}

        {/* STEP 4: REJILLA DE REVISIÓN */}
        {currentStep === 4 && (
          <div className="space-y-4" data-testid="step-4-review">
            <ExcelImportReviewGrid
              rows={parsedRows}
              onUpdateRow={handleUpdateRow}
              onDeleteRow={handleDeleteRow}
            />
          </div>
        )}

        {/* STEP 5: CONFIRMACIÓN E IMPORTACIÓN FINAL */}
        {currentStep === 5 && (
          <div className="space-y-4" data-testid="step-5-confirm">
            <div className="p-6 rounded-2xl bg-secondary/30 border border-border space-y-4">
              <div className="flex items-center gap-3 pb-3 border-b border-border">
                <div className="h-10 w-10 rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-sm font-black uppercase text-foreground">
                    {t("confirm.title", "Resumen Final de Ingesta Inteligente")}
                  </h4>
                  <p className="text-xs text-muted-foreground">
                    {t(
                      "confirm.subtitle",
                      "Revisa los totales consolidados antes de sincronizar con el catálogo maestro."
                    )}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-xl bg-card border border-border">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground block">
                    {t("confirm.valid_products", "Productos Válidos")}
                  </span>
                  <span className="text-xl font-black text-foreground">
                    {parsedRows.filter((r) => validateProductRow(r).status !== "error").length}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-card border border-border">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground block">
                    {t("confirm.categories_to_create", "Categorías a Crear")}
                  </span>
                  <span className="text-xl font-black text-primary">
                    {detectedCategories.length}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-card border border-border">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground block">
                    {t("confirm.brands_to_create", "Marcas a Crear")}
                  </span>
                  <span className="text-xl font-black text-primary">
                    {detectedBrands.length}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-card border border-border">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground block">
                    {t("confirm.estimated_valuation", "Valorización Estimada")}
                  </span>
                  <span className="text-xl font-black text-emerald-600 dark:text-emerald-400">
                    $
                    {parsedRows
                      .reduce((acc, r) => acc + r.costo_neto * (r.stock_actual || 1), 0)
                      .toLocaleString("es-CL")}
                  </span>
                </div>
              </div>

              {/* Selector de Bodega de Destino para Stock Inicial */}
              <div className="p-3.5 rounded-xl bg-card border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Boxes className="h-4 w-4 text-primary shrink-0" />
                  <span className="text-xs font-bold text-foreground">
                    {t("confirm.target_warehouse_label", "Bodega para asignación de Stock Inicial:")}
                  </span>
                </div>
                <select
                  value={selectedBodega}
                  onChange={(e) => setSelectedBodega(e.target.value)}
                  data-testid="select-import-target-bodega"
                  className="h-10 px-3 rounded-xl bg-background border border-input text-xs font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                >
                  <option value="bod-central">
                    {t("confirm.warehouses.central", "Bodega Principal / Central")}
                  </option>
                  <option value="bod-cocina">
                    {t("confirm.warehouses.kitchen", "Cocina Caliente")}
                  </option>
                  <option value="bod-frio">
                    {t("confirm.warehouses.cold_room", "Cámara Fría -18°C")}
                  </option>
                  <option value="bod-bar">
                    {t("confirm.warehouses.bar", "Barra & Cava")}
                  </option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* PIE DEL MODAL: NAVEGACIÓN Y ACCIÓN */}
        <div className="flex items-center justify-between pt-3 border-t border-border">
          <div>
            {currentStep > 1 && (
              <button
                type="button"
                onClick={() => setCurrentStep((prev) => (prev - 1) as ExcelImportStep)}
                data-testid="btn-prev-excel-step"
                className="touch-target inline-flex min-h-[44px] px-4 items-center gap-1.5 rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer select-none"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>{t("actions.prev", "Anterior")}</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              data-testid="btn-cancel-excel-import"
              className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer select-none"
            >
              {t("actions.cancel", "Cancelar")}
            </button>

            {currentStep < 5 && currentStep > 1 && (
              <button
                type="button"
                onClick={() => setCurrentStep((prev) => (prev + 1) as ExcelImportStep)}
                data-testid="btn-next-excel-step"
                className="touch-target inline-flex min-h-[44px] px-5 items-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-md cursor-pointer select-none"
              >
                <span>{t("actions.next", "Siguiente")}</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            )}

            {currentStep === 5 && (
              <button
                type="button"
                disabled={isProcessing || parsedRows.length === 0}
                onClick={handleFinalConfirmImport}
                data-testid="btn-confirm-import"
                className="touch-target inline-flex min-h-[44px] px-6 items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-black uppercase tracking-wider shadow-lg shadow-emerald-600/20 cursor-pointer select-none disabled:opacity-50"
              >
                <Check className="h-4 w-4 stroke-[3]" />
                <span>
                  {isProcessing
                    ? t("confirm.importing_btn", "Importando...")
                    : t("confirm.confirm_btn", "Confirmar e Importar")}
                </span>
              </button>
            )}
          </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
};
