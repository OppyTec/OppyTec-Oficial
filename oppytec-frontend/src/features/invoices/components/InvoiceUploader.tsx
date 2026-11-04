/**
 * oppytec-frontend/src/features/invoices/components/InvoiceUploader.tsx
 * Zona Drag-and-Drop para carga masiva de facturas electrónicas (PDF, PNG, JPG hasta 20 MB).
 */

import { useState, useRef, type DragEvent, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { UploadCloud, FileText, X } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib";

export interface InvoiceUploaderProps {
  onUpload: (files: File[]) => Promise<any>;
  isUploading: boolean;
  uploadProgress: number;
  className?: string;
}

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB
const ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"];

export function InvoiceUploader({
  onUpload,
  isUploading,
  uploadProgress,
  className,
}: InvoiceUploaderProps) {
  const { t } = useTranslation(["invoices"]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFiles = (files: File[]): File[] => {
    const valid: File[] = [];
    for (const f of files) {
      const ext = `.${f.name.split(".").pop()?.toLowerCase()}`;
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        toast.error(
          t("invoices:uploader.invalid_format", {
            name: f.name,
            defaultValue: `Formato no permitido (${f.name}). Solo PDF, PNG o JPG.`,
          })
        );
        continue;
      }
      if (f.size > MAX_FILE_SIZE) {
        toast.error(
          t("invoices:uploader.file_too_large", {
            name: f.name,
            defaultValue: `Archivo excede límite de 20 MB (${f.name}).`,
          })
        );
        continue;
      }
      valid.push(f);
    }
    return valid;
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files);
      const valid = validateFiles(filesArray);
      if (valid.length > 0) {
        setSelectedFiles((prev) => [...prev, ...valid]);
      }
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      const valid = validateFiles(filesArray);
      if (valid.length > 0) {
        setSelectedFiles((prev) => [...prev, ...valid]);
      }
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleStartUpload = async () => {
    if (selectedFiles.length === 0) return;
    try {
      await onUpload(selectedFiles);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch {
      // Error handled by hook
    }
  };

  return (
    <div
      data-testid="invoice-uploader"
      className={cn("glass-card rounded-2xl border border-border p-5 shadow-sm space-y-4", className)}
    >
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center",
          isDragOver
            ? "border-primary bg-primary/10 scale-[1.01]"
            : "border-border/80 hover:border-primary/50 hover:bg-muted/40"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="h-14 w-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3">
          <UploadCloud className="h-7 w-7" />
        </div>

        <h3 className="text-sm font-bold text-foreground">
          {t("invoices:uploader.drag_title", "Arrastra tus facturas electrónicas o haz clic para examinar")}
        </h3>
        <p className="mt-1 text-xs text-muted-foreground max-w-sm">
          {t(
            "invoices:uploader.drag_desc",
            "Formatos compatibles: PDF original, PNG, JPEG. Extracción multimodal con IA Gemini (hasta 20 MB por archivo)."
          )}
        </p>

        <div className="mt-3 flex items-center gap-2">
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
            {t("invoices:uploader.tag_dte", "DTE 33 / DTE 34")}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
            {t("invoices:uploader.tag_dedup", "Deduplicación SHA-256")}
          </span>
        </div>
      </div>

      {/* Lista de archivos en cola */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-border">
          <div className="flex items-center justify-between text-xs font-semibold text-foreground">
            <span>
              {t("invoices:uploader.selected_files", {
                count: selectedFiles.length,
                defaultValue: `${selectedFiles.length} archivo(s) seleccionado(s)`,
              })}
            </span>
            <button
              type="button"
              onClick={() => setSelectedFiles([])}
              className="text-muted-foreground hover:text-foreground text-[11px]"
            >
              {t("invoices:uploader.clear_selection", "Limpiar selección")}
            </button>
          </div>

          <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
            {selectedFiles.map((file, idx) => (
              <div
                key={`${file.name}-${idx}`}
                className="flex items-center justify-between p-2 rounded-xl bg-muted/50 border border-border text-xs"
              >
                <div className="flex items-center gap-2 truncate">
                  <FileText className="h-4 w-4 text-primary shrink-0" />
                  <span className="truncate font-medium text-foreground">{file.name}</span>
                  <span className="text-[10px] text-muted-foreground shrink-0 font-mono">
                    ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile(idx);
                  }}
                  className="p-1 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>

          {/* Barra de Progreso */}
          {isUploading && (
            <div className="space-y-1.5 pt-2">
              <div className="flex justify-between text-[11px] font-medium text-muted-foreground">
                <span>{t("invoices:uploader.uploading_progress", "Subiendo y extrayendo datos con Gemini OCR...")}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="button"
              disabled={isUploading}
              onClick={handleStartUpload}
              className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20 transition-all disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <div className="h-3.5 w-3.5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  {t("invoices:uploader.processing_ai", "Procesando con IA...")}
                </>
              ) : (
                <>
                  <UploadCloud className="h-4 w-4" />
                  {t("invoices:uploader.upload_and_process", "Subir y Procesar con IA")}
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
