// oppytec-frontend/src/features/inventory/recuentos/RecuentoDetalleModal.tsx
import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Warehouse,
  Calendar,
  User,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  Tag,
  Info,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { useCurrencyFormatter } from "@/shared/currency";
import { toast } from "sonner";
import type { PhysicalCountSession } from "../types";
import { MOCK_STOCK_ITEMS } from "../mockData";

export interface RecuentoDetalleModalProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly session: PhysicalCountSession | null;
  readonly isPropietario?: boolean;
  readonly onSaveSessionItems?: (
    sessionId: number,
    items: Array<{
      producto_id: number;
      cantidad_contada: number;
      fecha_vencimiento?: string | null;
    }>
  ) => Promise<unknown>;
  readonly onApprove?: (sessionId: number) => Promise<unknown>;
  readonly isApproving?: boolean;
}

interface EditableConteoLine {
  localId: string;
  itemId?: number;
  producto_id: number;
  producto_nombre: string;
  unidad_medida: string;
  stock_teorico_sistema: number;
  stock_fisico_contado: number;
  costo_unitario_ppp: number;
  fecha_vencimiento: string;
  lote_codigo: string;
}

export function RecuentoDetalleModal({
  open,
  onClose,
  session,
  isPropietario = false,
  onSaveSessionItems,
  onApprove,
  isApproving = false,
}: RecuentoDetalleModalProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [items, setItems] = useState<EditableConteoLine[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedAddProductId, setSelectedAddProductId] = useState<string>("");

  const isEditable = useMemo(() => {
    if (!session) return false;
    return isPropietario && (session.estado === "EN_PROGRESO" || session.estado === "PENDIENTE_APROBACION");
  }, [session, isPropietario]);

  // Sincronizar items al abrir sesión
  useEffect(() => {
    if (!session) {
      setItems([]);
      return;
    }
    const lines: EditableConteoLine[] = session.items.map((it) => ({
      localId: `it-${it.id || Math.random().toString(36).substring(2, 9)}`,
      itemId: it.id,
      producto_id: it.producto_id,
      producto_nombre: it.producto_nombre,
      unidad_medida: it.unidad_medida,
      stock_teorico_sistema: it.stock_teorico_sistema,
      stock_fisico_contado: it.stock_fisico_contado,
      costo_unitario_ppp: it.costo_unitario_ppp,
      fecha_vencimiento: it.fecha_vencimiento || "",
      lote_codigo: it.lote_codigo || "",
    }));
    setItems(lines);
  }, [session]);

  const handleUpdateLine = (localId: string, field: keyof EditableConteoLine, val: unknown) => {
    setItems((prev) =>
      prev.map((line) => (line.localId === localId ? { ...line, [field]: val } : line))
    );
  };

  const handleRemoveLine = (localId: string) => {
    setItems((prev) => prev.filter((line) => line.localId !== localId));
  };

  const handleAddProduct = (prodIdStr: string) => {
    if (!prodIdStr) return;
    const prodId = Number(prodIdStr);
    const catalogItem = MOCK_STOCK_ITEMS.find((s) => s.producto_id === prodId);
    if (!catalogItem) return;

    // Verificar si ya existe
    const exists = items.some((i) => i.producto_id === prodId);
    if (exists) {
      toast.info(t("recuentos.modal.toast_item_exists", { name: catalogItem.nombre, defaultValue: `El insumo ${catalogItem.nombre} ya está en la lista` }));
      return;
    }

    setItems((prev) => [
      ...prev,
      {
        localId: `add-${Math.random().toString(36).substring(2, 9)}`,
        producto_id: catalogItem.producto_id,
        producto_nombre: catalogItem.nombre,
        unidad_medida: catalogItem.unidad_medida,
        stock_teorico_sistema: catalogItem.stock_actual,
        stock_fisico_contado: 0,
        costo_unitario_ppp: catalogItem.costo_unitario_ppp,
        fecha_vencimiento: "",
        lote_codigo: "",
      },
    ]);
    setSelectedAddProductId("");
  };

  // Cálculos reactivos de discrepancias
  const summary = useMemo(() => {
    let sobrantes = 0;
    let faltantes = 0;
    let valorizacionTotal = 0;

    for (const line of items) {
      const diff = line.stock_fisico_contado - line.stock_teorico_sistema;
      const val = diff * line.costo_unitario_ppp;
      valorizacionTotal += val;
      if (diff > 0) {
        sobrantes += diff;
      } else if (diff < 0) {
        faltantes += Math.abs(diff);
      }
    }

    return {
      sobrantes,
      faltantes,
      valorizacionTotal,
    };
  }, [items]);

  const handleSave = async () => {
    if (!session || !onSaveSessionItems) return;
    setIsSaving(true);
    try {
      const payload = items.map((i) => ({
        producto_id: i.producto_id,
        cantidad_contada: Number(i.stock_fisico_contado),
        fecha_vencimiento: i.fecha_vencimiento ? i.fecha_vencimiento : null,
      }));
      await onSaveSessionItems(session.id, payload);
      toast.success(t("recuentos.modal.toast_update_success", "Recuento actualizado correctamente"));
      onClose();
    } catch {
      toast.error(t("recuentos.modal.toast_update_error", "Error al guardar los cambios del recuento"));
    } finally {
      setIsSaving(false);
    }
  };

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return "—";
    try {
      return new Date(isoStr).toLocaleString("es-CL", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoStr;
    }
  };

  if (!session) return null;

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={t("recuentos.modal.title", { id: session.id, defaultValue: `Acta de Recuento #${session.id}` })}
      description={t("recuentos.modal.description", "Detalle de auditoría, cuadratura de stock físico vs teórico y conciliación")}
      maxWidth="max-w-4xl"
      className="max-h-[92vh]"
    >
      <div className="space-y-4 pt-1">
        {/* Cabecera contextual */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-card/60 p-3 rounded-xl border border-border text-xs">
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
              <Warehouse className="h-3 w-3 text-purple-400" /> {t("recuentos.modal.warehouse", "Bodega")}
            </span>
            <span className="font-extrabold text-foreground truncate block">
              {session.bodega_nombre}
            </span>
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
              <Calendar className="h-3 w-3 text-purple-400" /> {t("recuentos.modal.start_date", "Fecha Inicio")}
            </span>
            <span className="font-semibold text-foreground truncate block">
              {formatDate(session.fecha_inicio)}
            </span>
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
              <User className="h-3 w-3 text-purple-400" /> {t("recuentos.modal.responsible", "Responsable")}
            </span>
            <span className="font-semibold text-foreground truncate block">
              {session.responsable_nombre}
            </span>
          </div>
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
              <Tag className="h-3 w-3 text-purple-400" /> {t("recuentos.modal.status", "Estado")}
            </span>
            <span className="font-extrabold text-purple-400 truncate block">
              {session.estado}
            </span>
          </div>
        </div>

        {/* Resumen de Discrepancias */}
        <div className="grid grid-cols-3 gap-2 p-3 bg-secondary/30 rounded-xl border border-border text-center">
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-bold block">
              {t("recuentos.modal.surplus", "Sobrantes (+)")}
            </span>
            <span className="text-sm font-extrabold text-emerald-500">
              +{summary.sobrantes.toFixed(2)} u.
            </span>
          </div>
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-bold block">
              {t("recuentos.modal.shortage", "Faltantes (-)")}
            </span>
            <span className="text-sm font-extrabold text-rose-500">
              -{summary.faltantes.toFixed(2)} u.
            </span>
          </div>
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-bold block">
              {t("recuentos.modal.net_impact", "Impacto Neto PPP")}
            </span>
            <span
              className={`text-sm font-extrabold ${
                summary.valorizacionTotal >= 0 ? "text-emerald-500" : "text-rose-500"
              }`}
            >
              {summary.valorizacionTotal >= 0 ? "+" : ""}
              {convertAndFormat(summary.valorizacionTotal, "CLP")}
            </span>
          </div>
        </div>

        {/* Tabla de Insumos */}
        <div className="overflow-x-auto rounded-xl border border-border bg-card max-h-[46vh]">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 z-10 bg-muted/90 backdrop-blur-sm border-b border-border text-[10px] uppercase font-bold text-muted-foreground">
              <tr>
                <th className="p-2.5 pl-3">{t("recuentos.modal.col_item", "Insumo / Producto")}</th>
                <th className="p-2.5 text-center">{t("recuentos.modal.col_unit", "Unidad")}</th>
                <th className="p-2.5 text-right">{t("recuentos.modal.col_system_theoretical", "Teórico Sistema")}</th>
                <th className="p-2.5 text-right w-28">{t("recuentos.modal.col_physical_counted", "Físico Contado")}</th>
                <th className="p-2.5 text-right">{t("recuentos.modal.col_difference", "Diferencia")}</th>
                <th className="p-2.5 text-right">{t("recuentos.modal.col_ppp_valuation", "Valorización PPP")}</th>
                {isEditable && <th className="p-2.5 text-center w-10"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((line) => {
                const diff = line.stock_fisico_contado - line.stock_teorico_sistema;
                const val = diff * line.costo_unitario_ppp;
                const isSurplus = diff > 0.0001;
                const isShortage = diff < -0.0001;

                return (
                  <tr
                    key={line.localId}
                    className="hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="p-2.5 pl-3 font-semibold text-foreground">
                      <div className="flex items-center gap-2">
                        <CategoryIcon name="package" className="h-4 w-4 text-purple-400 shrink-0" />
                        <div>
                          <span>{line.producto_nombre}</span>
                          {line.lote_codigo && (
                            <span className="block text-[10px] text-muted-foreground">
                              {t("recuentos.modal.lot_prefix", { code: line.lote_codigo, defaultValue: `Lote: ${line.lote_codigo}` })}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="p-2.5 text-center text-muted-foreground font-mono">
                      {line.unidad_medida}
                    </td>
                    <td className="p-2.5 text-right font-mono text-muted-foreground">
                      {line.stock_teorico_sistema.toFixed(2)}
                    </td>
                    <td className="p-2.5 text-right font-mono">
                      {isEditable ? (
                        <input
                          type="number"
                          step="any"
                          aria-label={t("recuentos.modal.col_physical_counted", "Físico Contado")}
                          value={line.stock_fisico_contado}
                          onChange={(e) =>
                            handleUpdateLine(
                              line.localId,
                              "stock_fisico_contado",
                              parseFloat(e.target.value) || 0
                            )
                          }
                          onFocus={(e) => e.target.select()}
                          className="h-8 w-24 text-right rounded-lg border border-input bg-card px-2 font-black text-foreground focus:ring-1 focus:ring-purple-500"
                        />
                      ) : (
                        <span className="font-extrabold text-foreground">
                          {line.stock_fisico_contado.toFixed(2)}
                        </span>
                      )}
                    </td>
                    <td className="p-2.5 text-right font-mono">
                      <span
                        className={`inline-flex items-center font-black ${
                          isSurplus
                            ? "text-emerald-500"
                            : isShortage
                            ? "text-rose-500"
                            : "text-muted-foreground"
                        }`}
                      >
                        {diff > 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2)}
                      </span>
                    </td>
                    <td className="p-2.5 text-right font-mono font-bold text-foreground">
                      <span
                        className={
                          val > 0
                            ? "text-emerald-500"
                            : val < 0
                            ? "text-rose-500"
                            : "text-muted-foreground"
                        }
                      >
                        {val > 0 ? "+" : ""}
                        {convertAndFormat(val, "CLP")}
                      </span>
                    </td>
                    {isEditable && (
                      <td className="p-2.5 text-center">
                        <button
                          type="button"
                          onClick={() => handleRemoveLine(line.localId)}
                          className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 transition-colors"
                          title={t("recuentos.modal.delete_from_session", "Eliminar de la sesión")}
                          aria-label={t("recuentos.modal.delete_from_session", "Eliminar de la sesión")}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}

              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={isEditable ? 7 : 6}
                    className="p-6 text-center text-muted-foreground italic"
                  >
                    {t("recuentos.modal.empty_session_items", "No hay insumos registrados en esta sesión de conteo.")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Añadir Producto (si está en modo edición) */}
        {isEditable && (
          <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl border border-dashed border-border bg-card/40">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <Plus className="h-3.5 w-3.5 text-purple-400" /> {t("recuentos.modal.add_item_label", "Añadir Insumo:")}
            </span>
            <select
              aria-label={t("recuentos.modal.add_item_label", "Añadir Insumo:")}
              value={selectedAddProductId}
              onChange={(e) => handleAddProduct(e.target.value)}
              className="flex-1 min-w-[200px] h-8 rounded-lg border border-input bg-card px-2 text-xs font-medium text-foreground focus:outline-none"
            >
              <option value="">{t("recuentos.modal.select_item_placeholder", "Seleccione insumo del catálogo...")}</option>
              {MOCK_STOCK_ITEMS.map((st) => (
                <option key={st.producto_id} value={st.producto_id}>
                  {st.nombre} ({st.unidad_medida})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Aviso de impacto en Kardex */}
        {session.estado === "PENDIENTE_APROBACION" && (
          <div className="flex items-center gap-2 p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-300">
            <Info className="h-4 w-4 shrink-0 text-purple-400" />
            <span>
              {t("recuentos.modal.kardex_notice", "Al aprobar esta acta, se generarán automáticamente los asientos de ajuste en el Kardex y se actualizará el stock disponible de la bodega.")}
            </span>
          </div>
        )}

        {/* Footer de botones */}
        <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] items-center rounded-xl border border-border bg-secondary/80 px-4 py-2 text-xs font-bold text-foreground hover:bg-secondary transition-colors"
          >
            {t("recuentos.modal.close", "Cerrar")}
          </button>

          {isEditable && (
            <button
              type="button"
              disabled={isSaving}
              onClick={handleSave}
              className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {isSaving ? t("recuentos.modal.saving", "Guardando...") : t("recuentos.modal.save_changes", "Guardar Cambios")}
            </button>
          )}

          {session.estado === "PENDIENTE_APROBACION" && onApprove && (
            <button
              type="button"
              disabled={isApproving}
              onClick={() => onApprove(session.id)}
              className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 transition-colors shadow-lg shadow-emerald-600/20 disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" />
              {isApproving ? t("recuentos.modal.reconciling", "Conciliando...") : t("recuentos.modal.approve_reconcile", "Aprobar y Conciliar Stock")}
            </button>
          )}
        </div>
      </div>
    </ResponsiveDialog>
  );
}

export default RecuentoDetalleModal;
