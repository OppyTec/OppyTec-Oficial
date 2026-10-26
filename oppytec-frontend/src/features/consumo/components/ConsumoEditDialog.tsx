// oppytec-frontend/src/features/consumo/components/ConsumoEditDialog.tsx
import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { History, Save, X, Loader2 } from "lucide-react";
import type { ConsumptionRecord } from "../types";

export interface ConsumoEditDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly record: ConsumptionRecord | null;
  readonly onSave: (
    id: string,
    data: { cantidad: number; motivo_merma?: string; notas?: string }
  ) => Promise<void>;
}

export function ConsumoEditDialog({
  open,
  onOpenChange,
  record,
  onSave,
}: ConsumoEditDialogProps) {
  const { t } = useTranslation("operations");
  const [cantidad, setCantidad] = useState("");
  const [motivo, setMotivo] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (record) {
      setCantidad(Math.abs(record.cantidad || 1).toString());
      setMotivo(record.motivo_merma || record.notas || "Ajuste de consumo");
    }
  }, [record, open]);

  if (!open || !record) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = parseFloat(cantidad);
    if (isNaN(qty) || qty <= 0) return;

    setIsSaving(true);
    try {
      await onSave(record.id, {
        cantidad: qty,
        motivo_merma: motivo,
        notas: motivo,
      });
      onOpenChange(false);
    } finally {
      setIsSaving(false);
    }
  };

  const titleText =
    record.nombre_producto ||
    record.nombre_receta ||
    record.codigo_folio ||
    `Registro #${record.id}`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="consumo-edit-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-md rounded-3xl bg-card border border-border shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Cabecera */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-2xl bg-primary/15 text-primary border border-primary/30 flex items-center justify-center">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                {t("consumption.modals.edit.title", { defaultValue: "Editar Registro de Consumo" })}
              </h3>
              <p
                data-testid="edit-record-title"
                className="text-xs text-muted-foreground truncate max-w-[240px]"
              >
                {titleText}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="edit-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Cantidad Consumida *
            </label>
            <input
              type="number"
              step="any"
              min="0.01"
              required
              data-testid="edit-quantity-input"
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
              className="w-full h-10 px-3.5 rounded-xl border border-border bg-background text-sm font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Motivo o Justificación del Ajuste *
            </label>
            <textarea
              required
              rows={3}
              data-testid="edit-motivo-input"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Explica la razón de la corrección en Kardex..."
              className="w-full p-3 rounded-xl border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 custom-scrollbar"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="px-4 py-2 rounded-xl border border-border text-xs font-bold hover:bg-muted transition-colors cursor-pointer text-muted-foreground hover:text-foreground"
            >
              Cancelar
            </button>

            <button
              type="submit"
              data-testid="edit-save-btn"
              disabled={isSaving || !cantidad || parseFloat(cantidad) <= 0}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all cursor-pointer shadow-md"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Guardando...</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>Actualizar Kardex</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ConsumoEditDialog;
