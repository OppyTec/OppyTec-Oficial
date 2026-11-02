// oppytec-frontend/src/features/events/dialogs/SalonesDialog.tsx
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Building2,
  Pencil,
  Trash2,
  Check,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn, formatMoney } from "@/shared/lib";
import { useSalones } from "../hooks/useSalones";
import type { Salon, SalonEstado, SalonCreatePayload } from "../types";
import { PALETA_COLORES_EVENTOS } from "../utils/dateUtils";

export interface SalonesDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
}

export function SalonesDialog({ open, onClose }: SalonesDialogProps) {
  const { t } = useTranslation("events");
  const { salones, createSalon, updateSalon, deleteSalon, isCreating, isUpdating, isDeleting } =
    useSalones();

  const [isEditingMode, setIsEditingMode] = useState<boolean>(false);
  const [editingSalonId, setEditingSalonId] = useState<string | null>(null);

  // Form State
  const [nombre, setNombre] = useState("");
  const [capacidad, setCapacidad] = useState<number | "">("");
  const [precioNeto, setPrecioNeto] = useState<number>(0);
  const [ivaPorcentaje, setIvaPorcentaje] = useState<number>(19);
  const [precioBruto, setPrecioBruto] = useState<number>(0);
  const [estado, setEstado] = useState<SalonEstado>("limpio");
  const [color, setColor] = useState<string>(PALETA_COLORES_EVENTOS[0] || "#ec4899");
  const [notas, setNotas] = useState("");

  const resetForm = () => {
    setIsEditingMode(false);
    setEditingSalonId(null);
    setNombre("");
    setCapacidad("");
    setPrecioNeto(0);
    setIvaPorcentaje(19);
    setPrecioBruto(0);
    setEstado("limpio");
    setColor(PALETA_COLORES_EVENTOS[0] || "#ec4899");
    setNotas("");
  };

  useEffect(() => {
    if (!open) {
      resetForm();
    }
  }, [open]);

  // Cálculos bidireccionales Neto <-> Bruto
  const handleNetoChange = (val: number) => {
    const neto = Math.max(0, val);
    const bruto = Math.round(neto * (1 + ivaPorcentaje / 100));
    setPrecioNeto(neto);
    setPrecioBruto(bruto);
  };

  const handleBrutoChange = (val: number) => {
    const bruto = Math.max(0, val);
    const factor = 1 + ivaPorcentaje / 100;
    const neto = factor > 0 ? Math.round(bruto / factor) : bruto;
    setPrecioBruto(bruto);
    setPrecioNeto(neto);
  };

  const handleIvaChange = (val: number) => {
    const iva = Math.max(0, val);
    const bruto = Math.round(precioNeto * (1 + iva / 100));
    setIvaPorcentaje(iva);
    setPrecioBruto(bruto);
  };

  const startEdit = (salon: Salon) => {
    setIsEditingMode(true);
    setEditingSalonId(salon.id);
    setNombre(salon.nombre);
    setCapacidad(salon.capacidad_personas ?? "");
    setPrecioNeto(salon.precio_neto);
    setIvaPorcentaje(salon.iva_porcentaje || 19);
    setPrecioBruto(salon.precio_bruto);
    setEstado(salon.estado || "limpio");
    setColor(salon.color || PALETA_COLORES_EVENTOS[0] || "#ec4899");
    setNotas(salon.notas || "");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) return;

    const payload: SalonCreatePayload = {
      nombre: nombre.trim(),
      capacidad_personas: capacidad === "" ? null : Number(capacidad),
      precio_neto: Number(precioNeto) || 0,
      iva_porcentaje: Number(ivaPorcentaje) || 19,
      precio_bruto: Number(precioBruto) || 0,
      estado,
      color,
      notas: notas.trim() || null,
      areas_operativas_ids: [1],
    };

    try {
      if (isEditingMode && editingSalonId) {
        await updateSalon({ id: editingSalonId, data: payload });
      } else {
        await createSalon(payload);
      }
      resetForm();
    } catch {
      // Error manejado en hook con sonner
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm(t("salones_dialog.confirm_delete"))) {
      await deleteSalon(id);
      if (editingSalonId === id) {
        resetForm();
      }
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("salones_dialog.title")}
      description={t("salones_dialog.description")}
      maxWidth="max-w-3xl"
    >
      <div data-testid="salones-dialog-content" className="space-y-6 py-2">
        {/* Formulario de Alta / Edición */}
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-border bg-card p-4 space-y-4 shadow-sm"
        >
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              <span>
                {isEditingMode
                  ? t("salones_dialog.title_edit")
                  : t("salones_dialog.title_create")}
              </span>
            </h4>
            {isEditingMode && (
              <button
                type="button"
                onClick={resetForm}
                className="text-xs font-semibold text-muted-foreground hover:text-foreground"
              >
                {t("salones_dialog.cancel_edit")}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {/* Nombre */}
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                {t("salones_dialog.nombre_label")}
              </label>
              <input
                type="text"
                required
                data-testid="input-salon-nombre"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder={t("salones_dialog.nombre_placeholder")}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>

            {/* Capacidad */}
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                {t("salones_dialog.capacidad_label")}
              </label>
              <input
                type="number"
                min="1"
                data-testid="input-salon-capacidad"
                value={capacidad}
                onChange={(e) => setCapacidad(e.target.value === "" ? "" : Number(e.target.value))}
                placeholder={t("salones_dialog.capacidad_placeholder")}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>

            {/* Arancel Neto */}
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                {t("salones_dialog.neto_label")}
              </label>
              <input
                type="number"
                min="0"
                step="1000"
                data-testid="input-salon-neto"
                value={precioNeto}
                onChange={(e) => handleNetoChange(Number(e.target.value))}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>

            {/* IVA % y Bruto */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("salones_dialog.iva_label")}
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={ivaPorcentaje}
                  onChange={(e) => handleIvaChange(Number(e.target.value))}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("salones_dialog.bruto_label")}
                </label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  data-testid="input-salon-bruto"
                  value={precioBruto}
                  onChange={(e) => handleBrutoChange(Number(e.target.value))}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground font-mono font-bold text-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>
            </div>

            {/* Estado */}
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                {t("salones_dialog.estado_label")}
              </label>
              <select
                value={estado}
                data-testid="select-salon-estado"
                onChange={(e) => setEstado(e.target.value as SalonEstado)}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="limpio">{t("salones_dialog.estados.limpio")}</option>
                <option value="en_uso">{t("salones_dialog.estados.en_uso")}</option>
                <option value="mantenimiento">{t("salones_dialog.estados.mantenimiento")}</option>
                <option value="sucio">{t("salones_dialog.estados.sucio")}</option>
                <option value="activo">{t("salones_dialog.estados.activo")}</option>
              </select>
            </div>

            {/* Color */}
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                {t("salones_dialog.color_label")}
              </label>
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                {PALETA_COLORES_EVENTOS.slice(0, 10).map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={cn(
                      "h-5 w-5 rounded-full transition-transform active:scale-95 cursor-pointer",
                      color === c ? "ring-2 ring-primary ring-offset-2 scale-110" : ""
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border/40">
            <button
              type="submit"
              data-testid="btn-guardar-salon"
              disabled={isCreating || isUpdating}
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow hover:bg-primary/90 active:scale-95 transition-all cursor-pointer disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" />
              <span>
                {isEditingMode
                  ? t("salones_dialog.btn_update")
                  : t("salones_dialog.btn_create")}
              </span>
            </button>
          </div>
        </form>

        {/* Listado de Salones Existentes */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            {t("salones_dialog.registered_salones", { count: salones.length })}
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-1">
            {salones.map((s) => (
              <div
                key={s.id}
                data-testid={`salon-row-${s.id}`}
                className="flex items-center justify-between rounded-xl border border-border bg-card p-3 shadow-xs hover:border-primary/40 transition-colors"
                style={{ borderLeftWidth: "4px", borderLeftColor: s.color }}
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-foreground text-xs truncate">{s.nombre}</span>
                    <span className="rounded-md bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-secondary-foreground">
                      {t(`salones_dialog.estados.${s.estado}`, { defaultValue: s.estado })}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground font-mono">
                    <span>
                      {t("salones_dialog.capacity_pers", { count: s.capacidad_personas ?? 0 })}
                    </span>
                    <span>
                      {t("salones_dialog.gross_price", { price: formatMoney(s.precio_bruto) })}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0 ml-2">
                  <button
                    type="button"
                    title={t("salones_dialog.btn_edit_tooltip")}
                    onClick={() => startEdit(s)}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-border text-foreground hover:bg-secondary transition-all cursor-pointer"
                  >
                    <Pencil className="h-3 w-3" />
                  </button>
                  <button
                    type="button"
                    title={t("salones_dialog.btn_delete_tooltip")}
                    disabled={isDeleting}
                    onClick={() => handleDelete(s.id)}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 transition-all cursor-pointer"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
