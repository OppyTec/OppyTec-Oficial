/**
 * oppytec-frontend/src/features/invoices/components/InvoicePreview.tsx
 * Visor interactivo del documento original de factura (PDF o imagen HD).
 * Incluye controles de Zoom in/out, rotación a 90°, paneo, pantalla completa y descarga.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ZoomIn,
  ZoomOut,
  RotateCw,
  Maximize2,
  Minimize2,
  Download,
  FileText,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/shared/lib";

export interface InvoicePreviewProps {
  fileUrl: string;
  fileType: "pdf" | "png" | "jpeg" | string;
  filename: string;
  className?: string;
}

export function InvoicePreview({
  fileUrl,
  fileType,
  filename,
  className,
}: InvoicePreviewProps) {
  const { t } = useTranslation(["invoices"]);
  const [zoom, setZoom] = useState<number>(1);
  const [rotation, setRotation] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const isPdf = fileType?.toLowerCase() === "pdf" || filename?.toLowerCase().endsWith(".pdf");

  const handleZoomIn = () => setZoom((z) => Math.min(3, Math.round((z + 0.25) * 100) / 100));
  const handleZoomOut = () => setZoom((z) => Math.max(0.5, Math.round((z - 0.25) * 100) / 100));
  const handleRotate = () => setRotation((r) => (r + 90) % 360);
  const handleReset = () => {
    setZoom(1);
    setRotation(0);
  };
  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = fileUrl;
    a.download = filename || t("invoices:preview.default_filename", "factura_documento");
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div
      data-testid="invoice-preview"
      className={cn(
        "glass-card rounded-2xl border border-border flex flex-col overflow-hidden bg-card/60 backdrop-blur-sm shadow-sm transition-all",
        isFullscreen ? "fixed inset-4 z-50 shadow-2xl bg-background" : "h-full min-h-[500px]",
        className
      )}
    >
      {/* Barra de herramientas superior */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted/40">
        <div className="flex items-center gap-2 truncate">
          <FileText className="h-4 w-4 text-primary shrink-0" />
          <span className="text-xs font-semibold text-foreground truncate" title={filename}>
            {filename}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Zoom Controls */}
          <button
            type="button"
            onClick={handleZoomOut}
            title={t("invoices:preview.zoom_out", "Reducir Zoom")}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-[11px] font-mono text-muted-foreground w-11 text-center select-none">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={handleZoomIn}
            title={t("invoices:preview.zoom_in", "Aumentar Zoom")}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <ZoomIn className="h-4 w-4" />
          </button>

          {/* Rotación */}
          <button
            type="button"
            onClick={handleRotate}
            title={t("invoices:preview.rotate", "Rotar 90°")}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors ml-1"
          >
            <RotateCw className="h-4 w-4" />
          </button>

          {/* Reset */}
          {(zoom !== 1 || rotation !== 0) && (
            <button
              type="button"
              onClick={handleReset}
              title={t("invoices:preview.reset", "Restablecer vista")}
              className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Descargar */}
          <button
            type="button"
            onClick={handleDownload}
            title={t("invoices:preview.download", "Descargar documento original")}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors ml-1"
          >
            <Download className="h-4 w-4" />
          </button>

          {/* Pantalla completa */}
          <button
            type="button"
            onClick={() => setIsFullscreen((prev) => !prev)}
            title={
              isFullscreen
                ? t("invoices:preview.exit_fullscreen", "Salir de pantalla completa")
                : t("invoices:preview.fullscreen", "Pantalla completa")
            }
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Área del documento interactivo */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-zinc-900/5 dark:bg-black/30 min-h-[420px]">
        {isPdf ? (
          <div
            className="w-full h-full flex flex-col items-center justify-center transition-transform duration-200"
            style={{
              transform: `scale(${zoom}) rotate(${rotation}deg)`,
              transformOrigin: "center center",
            }}
          >
            <iframe
              src={`${fileUrl}#toolbar=0&navpanes=0`}
              title={filename}
              className="w-full h-[550px] rounded-xl border border-border shadow-md bg-white"
            />
          </div>
        ) : (
          <div className="overflow-auto max-w-full max-h-full flex items-center justify-center">
            <img
              src={fileUrl}
              alt={filename}
              style={{
                transform: `scale(${zoom}) rotate(${rotation}deg)`,
                transformOrigin: "center center",
              }}
              className="max-w-full max-h-[550px] object-contain rounded-xl shadow-md transition-transform duration-200 select-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
