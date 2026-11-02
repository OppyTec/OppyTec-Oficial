// oppytec-frontend/src/features/events/dialogs/EventoDialog.tsx
import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Package,
  ChefHat,
  Layers,
  Plus,
  Trash2,
  Check,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn, formatMoney } from "@/shared/lib";
import { useEvents } from "../hooks/useEvents";
import { useSalones } from "../hooks/useSalones";
import type {
  Evento,
  EventoCreatePayload,
  EventoItem,
  EventoReceta,
  EventoCombo,
} from "../types";
import { PALETA_COLORES_EVENTOS, formatDateISO } from "../utils/dateUtils";

export interface EventoDialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly editingEvento?: Evento | null;
  readonly initialDate?: string | null;
  readonly initialSalonId?: string | null;
  readonly initialHoraInicio?: string | null;
  readonly initialHoraFin?: string | null;
}

export function EventoDialog({
  open,
  onClose,
  editingEvento,
  initialDate,
  initialSalonId,
  initialHoraInicio,
  initialHoraFin,
}: EventoDialogProps) {
  const { t } = useTranslation("events");
  const { createEvent, updateEvent, isCreating, isUpdating } = useEvents();
  const { salones } = useSalones();

  const [step, setStep] = useState<1 | 2>(1);

  // Step 1: General Info
  const [nombre, setNombre] = useState("");
  const [titular, setTitular] = useState("");
  const [salonId, setSalonId] = useState<string>("");
  const [lugar, setLugar] = useState("");
  const [fecha, setFecha] = useState<string>(formatDateISO(new Date()));
  const [horaInicio, setHoraInicio] = useState("");
  const [horaFin, setHoraFin] = useState("");
  const [invitados, setInvitados] = useState<number>(0);
  const [color, setColor] = useState<string>(PALETA_COLORES_EVENTOS[0] || "#ec4899");
  const [notas, setNotas] = useState("");

  // Step 2: Supplies
  const [suppliesTab, setSuppliesTab] = useState<"insumos" | "recetas" | "combos">("insumos");
  const [items, setItems] = useState<EventoItem[]>([]);
  const [recetas, setRecetas] = useState<EventoReceta[]>([]);
  const [combos, setCombos] = useState<EventoCombo[]>([]);

  // Draft supply row inputs
  const [draftItemName, setDraftItemName] = useState("");
  const [draftItemQty, setDraftItemQty] = useState<number>(1);
  const [draftItemCost, setDraftItemCost] = useState<number>(0);

  const [draftRecetaName, setDraftRecetaName] = useState("");
  const [draftRecetaPortions, setDraftRecetaPortions] = useState<number>(10);
  const [draftRecetaCost, setDraftRecetaCost] = useState<number>(0);

  const [draftComboName, setDraftComboName] = useState("");
  const [draftComboQty, setDraftComboQty] = useState<number>(1);
  const [draftComboCost, setDraftComboCost] = useState<number>(0);

  const isEditing = Boolean(editingEvento);

  // Initialize or reset form on open/change
  useEffect(() => {
    if (!open) {
      setStep(1);
      setNombre("");
      setTitular("");
      setSalonId("");
      setLugar("");
      setFecha(formatDateISO(new Date()));
      setHoraInicio("");
      setHoraFin("");
      setInvitados(0);
      setColor(PALETA_COLORES_EVENTOS[0] || "#ec4899");
      setNotas("");
      setItems([]);
      setRecetas([]);
      setCombos([]);
      return;
    }

    if (editingEvento) {
      setNombre(editingEvento.nombre);
      setTitular(editingEvento.titular || "");
      setSalonId(editingEvento.salon_id || "");
      setLugar(editingEvento.lugar || "");
      setFecha(editingEvento.fecha);
      setHoraInicio(editingEvento.hora_inicio || "");
      setHoraFin(editingEvento.hora_fin || "");
      setInvitados(editingEvento.cantidad_invitados ?? editingEvento.cantidad_personas ?? 0);
      setColor(editingEvento.color || PALETA_COLORES_EVENTOS[0] || "#ec4899");
      setNotas(editingEvento.notas || editingEvento.nota_equipo || "");
      setItems(editingEvento.items ? [...editingEvento.items] : []);
      setRecetas(editingEvento.recetas ? [...editingEvento.recetas] : []);
      setCombos(editingEvento.combos ? [...editingEvento.combos] : []);
    } else {
      setFecha(initialDate || formatDateISO(new Date()));
      setSalonId(initialSalonId || "");
      setHoraInicio(initialHoraInicio || "");
      setHoraFin(initialHoraFin || "");
    }
  }, [open, editingEvento, initialDate, initialSalonId, initialHoraInicio, initialHoraFin]);

  // Handle supply additions
  const handleAddItem = () => {
    if (!draftItemName.trim() || draftItemQty <= 0) return;
    const newItem: EventoItem = {
      producto_id: Date.now(), // ID temporal
      producto_nombre: draftItemName.trim(),
      bodega_id: 1,
      bodega_nombre: "Bodega Central",
      cantidad: draftItemQty,
      costo_unitario_estimado: draftItemCost,
      costo_total_estimado: draftItemQty * draftItemCost,
      unidad_medida: "u.",
    };
    setItems((prev) => [...prev, newItem]);
    setDraftItemName("");
    setDraftItemQty(1);
    setDraftItemCost(0);
  };

  const handleAddReceta = () => {
    if (!draftRecetaName.trim() || draftRecetaPortions <= 0) return;
    const newReceta: EventoReceta = {
      receta_id: Date.now(),
      receta_nombre: draftRecetaName.trim(),
      porciones: draftRecetaPortions,
      costo_unitario_estimado: draftRecetaCost,
      costo_estimado: draftRecetaPortions * draftRecetaCost,
    };
    setRecetas((prev) => [...prev, newReceta]);
    setDraftRecetaName("");
    setDraftRecetaPortions(10);
    setDraftRecetaCost(0);
  };

  const handleAddCombo = () => {
    if (!draftComboName.trim() || draftComboQty <= 0) return;
    const newCombo: EventoCombo = {
      combo_id: Date.now(),
      combo_nombre: draftComboName.trim(),
      cantidad: draftComboQty,
      costo_unitario_estimado: draftComboCost,
      costo_estimado: draftComboQty * draftComboCost,
    };
    setCombos((prev) => [...prev, newCombo]);
    setDraftComboName("");
    setDraftComboQty(1);
    setDraftComboCost(0);
  };

  // Costo total estimado en tiempo real
  const totalEstimatedCost = useMemo(() => {
    const itemsCost = items.reduce(
      (sum, i) => sum + (i.costo_total_estimado ?? i.cantidad * (i.costo_unitario_estimado ?? 0)),
      0
    );
    const recetasCost = recetas.reduce(
      (sum, r) => sum + (r.costo_estimado ?? r.porciones * (r.costo_unitario_estimado ?? 0)),
      0
    );
    const combosCost = combos.reduce(
      (sum, c) => sum + (c.costo_estimado ?? c.cantidad * (c.costo_unitario_estimado ?? 0)),
      0
    );
    return itemsCost + recetasCost + combosCost;
  }, [items, recetas, combos]);

  // Guardar evento
  const handleSave = async () => {
    if (!nombre.trim()) {
      toast.error(t("dialog.validation_name_required"));
      setStep(1);
      return;
    }
    if (!fecha) {
      toast.error(t("dialog.validation_date_required"));
      setStep(1);
      return;
    }

    const payload: EventoCreatePayload = {
      nombre: nombre.trim(),
      titular: titular.trim() || null,
      salon_id: salonId || null,
      lugar: lugar.trim() || null,
      fecha,
      hora_inicio: horaInicio || null,
      hora_fin: horaFin || null,
      cantidad_personas: Number(invitados) || 0,
      color,
      notas: notas.trim() || null,
      items: items.map((i) => ({
        producto_id: Number(i.producto_id),
        bodega_id: i.bodega_id || 1,
        cantidad: Number(i.cantidad),
        costo_unitario_estimado: i.costo_unitario_estimado,
      })),
      recetas: recetas.map((r) => ({
        receta_id: Number(r.receta_id),
        porciones: Number(r.porciones),
      })),
      combos: combos.map((c) => ({
        combo_id: Number(c.combo_id),
        cantidad: Number(c.cantidad),
      })),
    };

    try {
      if (isEditing && editingEvento) {
        await updateEvent({ id: editingEvento.id, data: payload });
      } else {
        await createEvent(payload);
      }
      onClose();
    } catch {
      // Manejado en hook
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      title={
        isEditing
          ? t("dialog.title_edit", { name: editingEvento?.nombre })
          : t("dialog.title_create")
      }
      description={t("dialog.description")}
      maxWidth="max-w-3xl"
    >
      <div data-testid="evento-dialog-content" className="space-y-4 py-2">
        {/* Wizard Step Selector */}
        <div className="flex items-center justify-between border-b border-border/60 pb-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="wizard-step-1-btn"
              onClick={() => setStep(1)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all cursor-pointer",
                step === 1
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              )}
            >
              <span>{t("dialog.step1_title")}</span>
            </button>

            <ChevronRight className="h-4 w-4 text-muted-foreground" />

            <button
              type="button"
              data-testid="wizard-step-2-btn"
              onClick={() => setStep(2)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all cursor-pointer",
                step === 2
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              )}
            >
              <span>
                {t("dialog.step2_title", {
                  count: items.length + recetas.length + combos.length,
                })}
              </span>
            </button>
          </div>

          {totalEstimatedCost > 0 && (
            <div className="text-right text-xs">
              <span className="text-muted-foreground">{t("dialog.theoretical_cost")}</span>
              <strong className="font-mono text-foreground font-bold">
                {formatMoney(totalEstimatedCost)}
              </strong>
            </div>
          )}
        </div>

        {/* STEP 1: Datos Generales */}
        {step === 1 && (
          <div data-testid="step-1-content" className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {/* Nombre */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.nombre_label")}
                </label>
                <input
                  type="text"
                  required
                  data-testid="input-evento-nombre"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder={t("dialog.nombre_placeholder")}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              {/* Titular */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.titular_label")}
                </label>
                <input
                  type="text"
                  data-testid="input-evento-titular"
                  value={titular}
                  onChange={(e) => setTitular(e.target.value)}
                  placeholder={t("dialog.titular_placeholder")}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              {/* Salón */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.salon_label")}
                </label>
                <select
                  data-testid="select-evento-salon"
                  value={salonId}
                  onChange={(e) => {
                    setSalonId(e.target.value);
                    const selected = salones.find((s) => s.id === e.target.value);
                    if (selected?.color) setColor(selected.color);
                  }}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  <option value="">{t("dialog.no_salon_option")}</option>
                  {salones.map((s) => (
                    <option key={s.id} value={s.id}>
                      {t("dialog.salon_option", {
                        name: s.nombre,
                        capacity: s.capacidad_personas ?? 0,
                      })}
                    </option>
                  ))}
                </select>
              </div>

              {/* Lugar alternativo */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.lugar_label")}
                </label>
                <input
                  type="text"
                  data-testid="input-evento-lugar"
                  value={lugar}
                  onChange={(e) => setLugar(e.target.value)}
                  placeholder={t("dialog.lugar_placeholder")}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              {/* Fecha */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.fecha_label")}
                </label>
                <input
                  type="date"
                  required
                  data-testid="input-evento-fecha"
                  value={fecha}
                  onChange={(e) => setFecha(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              {/* Cantidad de comensales */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.invitados_label")}
                </label>
                <input
                  type="number"
                  min="0"
                  data-testid="input-evento-invitados"
                  value={invitados}
                  onChange={(e) => setInvitados(Number(e.target.value))}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              {/* Hora Inicio y Fin */}
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">
                    {t("dialog.hora_inicio_label")}
                  </label>
                  <input
                    type="time"
                    data-testid="input-evento-hora-inicio"
                    value={horaInicio}
                    onChange={(e) => setHoraInicio(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold text-foreground">
                    {t("dialog.hora_fin_label")}
                  </label>
                  <input
                    type="time"
                    data-testid="input-evento-hora-fin"
                    value={horaFin}
                    onChange={(e) => setHoraFin(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
              </div>

              {/* Selector Cromático */}
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  {t("dialog.color_label")}
                </label>
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {PALETA_COLORES_EVENTOS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setColor(c)}
                      className={cn(
                        "h-5 w-5 rounded-full transition-all cursor-pointer",
                        color === c ? "ring-2 ring-primary ring-offset-2 scale-110" : "opacity-80"
                      )}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Notas */}
            <div className="space-y-1 text-xs">
              <label className="font-semibold text-foreground">
                {t("dialog.notas_label")}
              </label>
              <textarea
                rows={2}
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder={t("dialog.notas_placeholder")}
                className="w-full rounded-xl border border-border bg-background p-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
          </div>
        )}

        {/* STEP 2: Suministros e Insumos */}
        {step === 2 && (
          <div data-testid="step-2-content" className="space-y-3">
            {/* Pestañas internas */}
            <div className="flex items-center gap-2 border-b border-border/50 pb-2 text-xs">
              <button
                type="button"
                onClick={() => setSuppliesTab("insumos")}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1 font-semibold transition-all cursor-pointer",
                  suppliesTab === "insumos"
                    ? "bg-secondary text-primary font-bold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Package className="h-3.5 w-3.5" />
                <span>{t("dialog.tab_insumos", { count: items.length })}</span>
              </button>

              <button
                type="button"
                onClick={() => setSuppliesTab("recetas")}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1 font-semibold transition-all cursor-pointer",
                  suppliesTab === "recetas"
                    ? "bg-secondary text-primary font-bold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <ChefHat className="h-3.5 w-3.5" />
                <span>{t("dialog.tab_recetas", { count: recetas.length })}</span>
              </button>

              <button
                type="button"
                onClick={() => setSuppliesTab("combos")}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1 font-semibold transition-all cursor-pointer",
                  suppliesTab === "combos"
                    ? "bg-secondary text-primary font-bold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Layers className="h-3.5 w-3.5" />
                <span>{t("dialog.tab_combos", { count: combos.length })}</span>
              </button>
            </div>

            {/* Panel de Insumos */}
            {suppliesTab === "insumos" && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-end gap-2 text-xs">
                  <div className="flex-1 min-w-[150px] space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.item_name_label")}
                    </label>
                    <input
                      type="text"
                      data-testid="input-draft-item-name"
                      value={draftItemName}
                      onChange={(e) => setDraftItemName(e.target.value)}
                      placeholder={t("dialog.item_name_placeholder")}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div className="w-24 space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.item_qty_label")}
                    </label>
                    <input
                      type="number"
                      min="1"
                      data-testid="input-draft-item-qty"
                      value={draftItemQty}
                      onChange={(e) => setDraftItemQty(Number(e.target.value))}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div className="w-28 space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.item_cost_label")}
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={draftItemCost}
                      onChange={(e) => setDraftItemCost(Number(e.target.value))}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <button
                    type="button"
                    data-testid="btn-add-item"
                    onClick={handleAddItem}
                    className="inline-flex h-8 items-center gap-1 rounded-xl bg-primary px-3 text-xs font-bold text-primary-foreground shadow-xs hover:bg-primary/90 active:scale-95 transition-all cursor-pointer"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>{t("dialog.btn_add")}</span>
                  </button>
                </div>

                {/* Lista de Insumos */}
                <div className="space-y-1 max-h-[200px] overflow-y-auto pr-1">
                  {items.map((it, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-border bg-card p-2 text-xs"
                    >
                      <span className="font-medium text-foreground truncate flex-1">
                        {it.producto_nombre || `Producto #${it.producto_id}`}
                      </span>
                      <span className="font-mono text-muted-foreground mx-3">
                        {it.cantidad} {it.unidad_medida || "u."} ×{" "}
                        {formatMoney(it.costo_unitario_estimado || 0)}
                      </span>
                      <button
                        type="button"
                        onClick={() => setItems(items.filter((_, i) => i !== idx))}
                        className="text-destructive hover:bg-destructive/10 rounded-md p-1 cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                  {items.length === 0 && (
                    <p className="py-4 text-center text-xs text-muted-foreground">
                      {t("dialog.no_items")}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Panel de Recetas */}
            {suppliesTab === "recetas" && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-end gap-2 text-xs">
                  <div className="flex-1 min-w-[150px] space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.receta_name_label")}
                    </label>
                    <input
                      type="text"
                      value={draftRecetaName}
                      onChange={(e) => setDraftRecetaName(e.target.value)}
                      placeholder={t("dialog.receta_name_placeholder")}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div className="w-24 space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.receta_portions_label")}
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={draftRecetaPortions}
                      onChange={(e) => setDraftRecetaPortions(Number(e.target.value))}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleAddReceta}
                    className="inline-flex h-8 items-center gap-1 rounded-xl bg-primary px-3 text-xs font-bold text-primary-foreground shadow-xs hover:bg-primary/90 active:scale-95 transition-all cursor-pointer"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>{t("dialog.btn_add")}</span>
                  </button>
                </div>

                <div className="space-y-1 max-h-[200px] overflow-y-auto pr-1">
                  {recetas.map((rc, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-border bg-card p-2 text-xs"
                    >
                      <span className="font-medium text-foreground truncate flex-1">
                        {rc.receta_nombre}
                      </span>
                      <span className="font-mono text-muted-foreground mx-3">
                        {t("dialog.portions_unit", { count: rc.porciones })}
                      </span>
                      <button
                        type="button"
                        onClick={() => setRecetas(recetas.filter((_, i) => i !== idx))}
                        className="text-destructive hover:bg-destructive/10 rounded-md p-1 cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                  {recetas.length === 0 && (
                    <p className="py-4 text-center text-xs text-muted-foreground">
                      {t("dialog.no_recetas")}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Panel de Combos */}
            {suppliesTab === "combos" && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-end gap-2 text-xs">
                  <div className="flex-1 min-w-[150px] space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.combo_name_label")}
                    </label>
                    <input
                      type="text"
                      value={draftComboName}
                      onChange={(e) => setDraftComboName(e.target.value)}
                      placeholder={t("dialog.combo_name_placeholder")}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div className="w-24 space-y-1">
                    <label className="font-semibold text-foreground">
                      {t("dialog.combo_qty_label")}
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={draftComboQty}
                      onChange={(e) => setDraftComboQty(Number(e.target.value))}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleAddCombo}
                    className="inline-flex h-8 items-center gap-1 rounded-xl bg-primary px-3 text-xs font-bold text-primary-foreground shadow-xs hover:bg-primary/90 active:scale-95 transition-all cursor-pointer"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>{t("dialog.btn_add")}</span>
                  </button>
                </div>

                <div className="space-y-1 max-h-[200px] overflow-y-auto pr-1">
                  {combos.map((cb, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-border bg-card p-2 text-xs"
                    >
                      <span className="font-medium text-foreground truncate flex-1">
                        {cb.combo_nombre}
                      </span>
                      <span className="font-mono text-muted-foreground mx-3">
                        {t("dialog.packages_unit", { count: cb.cantidad })}
                      </span>
                      <button
                        type="button"
                        onClick={() => setCombos(combos.filter((_, i) => i !== idx))}
                        className="text-destructive hover:bg-destructive/10 rounded-md p-1 cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                  {combos.length === 0 && (
                    <p className="py-4 text-center text-xs text-muted-foreground">
                      {t("dialog.no_combos")}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer Buttons */}
        <div className="flex items-center justify-between border-t border-border/50 pt-3">
          {step === 2 ? (
            <button
              type="button"
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary cursor-pointer"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              <span>{t("dialog.btn_back")}</span>
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-2">
            {step === 1 && (
              <button
                type="button"
                data-testid="btn-siguiente-step"
                onClick={() => setStep(2)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer"
              >
                <span>{t("dialog.btn_next")}</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            )}

            <button
              type="button"
              data-testid="btn-guardar-evento"
              disabled={isCreating || isUpdating}
              onClick={handleSave}
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-5 py-2 text-xs font-bold text-primary-foreground shadow hover:bg-primary/90 active:scale-95 transition-all cursor-pointer disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" />
              <span>{isEditing ? t("dialog.btn_save_edit") : t("dialog.btn_save_create")}</span>
            </button>
          </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
