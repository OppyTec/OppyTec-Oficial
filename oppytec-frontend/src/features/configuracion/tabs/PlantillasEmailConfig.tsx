import { useState, useRef } from "react";
import {
  Mail,
  Plus,
  Pencil,
  Trash2,
  Sparkles,
  Eye,
  Code,
} from "lucide-react";
import { toast } from "sonner";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib";
import { translateKey, useLanguage } from "@/shared/i18n";

export interface PlantillaEmailItem {
  id: string;
  nombre: string;
  asunto: string;
  cuerpo: string;
  tipo: string;
}

interface VariableChip {
  key: string;
  defaultLabel: string;
  value: string;
  colorClass: string;
}

const VARIABLES_DISPONIBLES: VariableChip[] = [
  { key: "restaurante", defaultLabel: "Restaurante", value: "[Restaurante]", colorClass: "bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-800" },
  { key: "proveedor", defaultLabel: "Proveedor", value: "[Proveedor]", colorClass: "bg-emerald-500/10 text-emerald-600 border-emerald-200 dark:border-emerald-800" },
  { key: "items", defaultLabel: "Items/Productos", value: "[Items]", colorClass: "bg-purple-500/10 text-purple-600 border-purple-200 dark:border-purple-800" },
  { key: "motivo", defaultLabel: "Motivo/Incidencia", value: "[Motivo]", colorClass: "bg-amber-500/10 text-amber-600 border-amber-200 dark:border-amber-800" },
  { key: "fecha", defaultLabel: "Fecha Actual", value: "[Fecha]", colorClass: "bg-slate-500/10 text-slate-600 border-slate-200 dark:border-slate-800" },
  { key: "numero_pedido", defaultLabel: "Número de Pedido", value: "[Numero_Pedido]", colorClass: "bg-red-500/10 text-red-600 border-red-200 dark:border-red-800" },
  { key: "tu_nombre", defaultLabel: "Tu Nombre (Usuario)", value: "[Tu_nombre]", colorClass: "bg-teal-500/10 text-teal-600 border-teal-200 dark:border-teal-800" },
];

const DEFAULT_BODY = `Estimados [Proveedor],

Junto con saludar cordialmente, les escribimos desde [Restaurante] para realizar el siguiente pedido de insumos con fecha [Fecha]:

DETALLES DEL PEDIDO:
------------------------------------------
[Items]
------------------------------------------

Solicitamos confirmar la recepción de este correo e indicarnos el tiempo estimado de entrega y el monto total a cancelar.

Cualquier duda o comentario, favor contactarnos por esta misma vía.

Atentamente,
Administración
[Restaurante]
Sistema de Gestión OppyTec`;

const INITIAL_PLANTILLAS: PlantillaEmailItem[] = [
  {
    id: "tpl-1",
    nombre: "Orden de Compra Estándar",
    asunto: "[Nuevo Pedido # [Numero_Pedido]] Pedido de Insumos - [Restaurante]",
    cuerpo: DEFAULT_BODY,
    tipo: "nuevo_pedido",
  },
  {
    id: "tpl-2",
    nombre: "Modificación de Pedido",
    asunto: "[Pedido Modificado # [Numero_Pedido]] Ajuste de Insumos - [Restaurante]",
    cuerpo: `Estimados [Proveedor],\n\nSolicitamos modificar la orden [Numero_Pedido] con los siguientes cambios:\n\n[Items]\n\nMotivo: [Motivo]\n\nAtentamente,\n[Tu_nombre]\n[Restaurante]`,
    tipo: "modificacion",
  },
  {
    id: "tpl-3",
    nombre: "Solicitud de Cotización",
    asunto: "[Cotización] Requerimiento de Precios - [Restaurante]",
    cuerpo: `Estimados [Proveedor],\n\nFavor cotizar los siguientes insumos requeridos para el local [Restaurante] con fecha [Fecha]:\n\n[Items]\n\nEsperamos su respuesta.\n\nSaludos cordiales,\n[Tu_nombre]`,
    tipo: "cotizacion",
  },
];

export function PlantillasEmailConfig() {
  useLanguage();
  const [plantillas, setPlantillas] = useState<PlantillaEmailItem[]>(INITIAL_PLANTILLAS);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPlantilla, setEditingPlantilla] = useState<PlantillaEmailItem | null>(null);
  const [deletePlantillaId, setDeletePlantillaId] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  const [asunto, setAsunto] = useState("");
  const [cuerpo, setCuerpo] = useState("");
  const [tipo, setTipo] = useState("nuevo_pedido");
  const [activeTab, setActiveTab] = useState<"edit" | "preview">("edit");
  const [lastFocus, setLastFocus] = useState<"asunto" | "cuerpo">("cuerpo");

  const asuntoRef = useRef<HTMLInputElement>(null);
  const cuerpoRef = useRef<HTMLTextAreaElement>(null);

  const openNew = () => {
    setEditingPlantilla(null);
    setNombre("");
    setAsunto("[Nuevo Pedido] Pedido de Insumos - [Restaurante]");
    setCuerpo(DEFAULT_BODY);
    setTipo("nuevo_pedido");
    setActiveTab("edit");
    setDialogOpen(true);
  };

  const openEdit = (p: PlantillaEmailItem) => {
    setEditingPlantilla(p);
    setNombre(p.nombre);
    setAsunto(p.asunto);
    setCuerpo(p.cuerpo);
    setTipo(p.tipo || "nuevo_pedido");
    setActiveTab("edit");
    setDialogOpen(true);
  };

  const insertVariable = (variable: string) => {
    if (lastFocus === "asunto") {
      const el = asuntoRef.current;
      if (!el) return;
      const start = el.selectionStart || 0;
      const end = el.selectionEnd || 0;
      const next = asunto.substring(0, start) + variable + asunto.substring(end);
      setAsunto(next);
      setTimeout(() => {
        el.focus();
        el.setSelectionRange(start + variable.length, start + variable.length);
      }, 0);
    } else {
      const el = cuerpoRef.current;
      if (!el) return;
      const start = el.selectionStart || 0;
      const end = el.selectionEnd || 0;
      const next = cuerpo.substring(0, start) + variable + cuerpo.substring(end);
      setCuerpo(next);
      setTimeout(() => {
        el.focus();
        el.setSelectionRange(start + variable.length, start + variable.length);
      }, 0);
    }
    toast.info(
      translateKey("configuracion", "plantillas_email.toast_variable_insertada", {
        variable,
      })
    );
  };

  const handleTipoChange = (newTipo: string) => {
    setTipo(newTipo);
    let prefix = "";
    if (newTipo === "nuevo_pedido") prefix = "[Nuevo Pedido]";
    else if (newTipo === "modificacion") prefix = "[Pedido Modificado]";
    else if (newTipo === "cancelacion") prefix = "[Pedido Cancelado]";
    else if (newTipo === "cotizacion") prefix = "[Cotización]";

    if (prefix) {
      const regex = /^\[.*?\]\s*/;
      if (regex.test(asunto)) {
        setAsunto(asunto.replace(regex, `${prefix} `));
      } else {
        setAsunto(`${prefix} ${asunto}`);
      }
    }
  };

  const handleSave = () => {
    if (!nombre.trim() || !asunto.trim() || !cuerpo.trim()) {
      toast.error(translateKey("configuracion", "plantillas_email.toast_campos_obligatorios"));
      return;
    }
    if (editingPlantilla) {
      setPlantillas((prev) =>
        prev.map((p) =>
          p.id === editingPlantilla.id
            ? { ...p, nombre: nombre.trim(), asunto: asunto.trim(), cuerpo: cuerpo.trim(), tipo }
            : p
        )
      );
      toast.success(translateKey("configuracion", "plantillas_email.toast_actualizada"));
    } else {
      const newP: PlantillaEmailItem = {
        id: `tpl-${Date.now()}`,
        nombre: nombre.trim(),
        asunto: asunto.trim(),
        cuerpo: cuerpo.trim(),
        tipo,
      };
      setPlantillas((prev) => [...prev, newP]);
      toast.success(translateKey("configuracion", "plantillas_email.toast_creada"));
    }
    setDialogOpen(false);
  };

  const handleDelete = (id: string) => {
    setPlantillas((prev) => prev.filter((p) => p.id !== id));
    toast.success(translateKey("configuracion", "plantillas_email.toast_eliminada"));
    setDeletePlantillaId(null);
  };

  // Preview generator that resolves variables into dummy real data
  const renderResolvedPreview = (template: string) => {
    return template
      .replaceAll("[Restaurante]", "La Fábrica Gastronómica")
      .replaceAll("[Proveedor]", "Distribuidora Alimentos del Sur SpA")
      .replaceAll("[Items]", "• 10 kg Carne Vacuno Lomo Liso\n• 5 cajas Vino Reserva 750cc\n• 20 kg Harina Panadera")
      .replaceAll("[Motivo]", "Falta de stock por evento corporativo de noche")
      .replaceAll("[Fecha]", new Date().toLocaleDateString("es-CL"))
      .replaceAll("[Numero_Pedido]", "OP-2026-0842")
      .replaceAll("[Tu_nombre]", "Juan Campillay");
  };

  return (
    <div className="space-y-4" data-testid="plantillas-email-section">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-sm font-black uppercase tracking-tight">
            {translateKey("configuracion", "plantillas_email.header_title")}
          </h3>
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
            {translateKey("configuracion", "plantillas_email.header_subtitle")}
          </p>
        </div>
        <button
          type="button"
          onClick={openNew}
          className="rounded-xl gap-2 font-black text-[10px] uppercase shadow-lg shadow-primary/20 bg-primary hover:bg-primary/90 text-primary-foreground px-3.5 py-2 inline-flex items-center cursor-pointer min-h-[44px]"
        >
          <Plus className="h-4 w-4" /> {translateKey("configuracion", "plantillas_email.nueva_plantilla")}
        </button>
      </div>

      {/* List of Email Templates */}
      <div className="grid gap-3 sm:grid-cols-2">
        {plantillas.map((p) => (
          <div
            key={p.id}
            className="flex flex-col justify-between p-4 rounded-2xl border border-border bg-card/50 hover:bg-secondary/20 transition-all group"
          >
            <div className="space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                    <Mail className="h-4 w-4" />
                  </div>
                  <h4 className="font-bold text-sm">{p.nombre}</h4>
                </div>
                <div className="flex gap-1 opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    type="button"
                    onClick={() => openEdit(p)}
                    aria-label={translateKey("configuracion", "plantillas_email.editar_aria", {
                      nombre: p.nombre,
                    })}
                    className="h-8 w-8 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeletePlantillaId(p.id)}
                    aria-label={translateKey("configuracion", "plantillas_email.eliminar_aria", {
                      nombre: p.nombre,
                    })}
                    className="h-8 w-8 rounded-lg hover:bg-destructive/10 text-destructive flex items-center justify-center cursor-pointer transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <p className="text-xs font-medium text-foreground/80 truncate">
                <span className="text-[10px] font-bold uppercase text-muted-foreground">
                  {translateKey("configuracion", "plantillas_email.asunto_prefijo")}
                </span>
                {p.asunto}
              </p>
              <p className="text-[11px] text-muted-foreground line-clamp-2 italic">
                {p.cuerpo}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Dialog: Crear / Editar Plantilla */}
      <ResponsiveDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title={
          editingPlantilla
            ? translateKey("configuracion", "plantillas_email.dialog_edit_title")
            : translateKey("configuracion", "plantillas_email.dialog_new_title")
        }
        description={translateKey("configuracion", "plantillas_email.dialog_description")}
      >
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {/* Tipo & Nombre */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
                {translateKey("configuracion", "plantillas_email.tipo_label")}
              </label>
              <select
                value={tipo}
                onChange={(e) => handleTipoChange(e.target.value)}
                className="w-full h-10 rounded-xl border border-border bg-background px-3 text-xs font-bold outline-none cursor-pointer focus:border-primary"
              >
                <option value="nuevo_pedido">
                  {translateKey("configuracion", "plantillas_email.tipos.nuevo_pedido")}
                </option>
                <option value="modificacion">
                  {translateKey("configuracion", "plantillas_email.tipos.modificacion")}
                </option>
                <option value="cancelacion">
                  {translateKey("configuracion", "plantillas_email.tipos.cancelacion")}
                </option>
                <option value="cotizacion">
                  {translateKey("configuracion", "plantillas_email.tipos.cotizacion")}
                </option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
                {translateKey("configuracion", "plantillas_email.nombre_label")}
              </label>
              <input
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder={translateKey("configuracion", "plantillas_email.nombre_placeholder")}
                className="w-full h-10 rounded-xl border border-border bg-background px-3 text-xs font-bold outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* Variables Dinámicas (Chips interactivos) */}
          <div className="space-y-1.5 p-3 rounded-xl border border-border bg-secondary/15">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                {translateKey("configuracion", "plantillas_email.variables_header")}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {VARIABLES_DISPONIBLES.map((v) => {
                const label =
                  translateKey("configuracion", `plantillas_email.variables.${v.key}`) ||
                  v.defaultLabel;
                return (
                  <button
                    key={v.value}
                    type="button"
                    onClick={() => insertVariable(v.value)}
                    className={cn(
                      "px-2.5 py-1 rounded-lg text-[10px] font-bold border transition-transform hover:scale-105 active:scale-95 cursor-pointer shadow-sm",
                      v.colorClass
                    )}
                    title={translateKey(
                      "configuracion",
                      "plantillas_email.insertar_tooltip",
                      { variable: v.value }
                    )}
                  >
                    {label} <code className="font-mono text-[9px] opacity-80">{v.value}</code>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Asunto */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
              {translateKey("configuracion", "plantillas_email.asunto_label")}
            </label>
            <input
              ref={asuntoRef}
              type="text"
              value={asunto}
              onFocus={() => setLastFocus("asunto")}
              onChange={(e) => setAsunto(e.target.value)}
              placeholder={translateKey("configuracion", "plantillas_email.asunto_placeholder")}
              className="w-full h-10 rounded-xl border border-border bg-background px-3 text-xs font-bold outline-none focus:border-primary"
            />
          </div>

          {/* Cuerpo & Toggle Preview */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground block">
                {translateKey("configuracion", "plantillas_email.cuerpo_label")}
              </label>
              <div className="flex rounded-lg border border-border p-0.5 bg-secondary/30">
                <button
                  type="button"
                  onClick={() => setActiveTab("edit")}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer",
                    activeTab === "edit"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Code className="h-3 w-3" /> {translateKey("configuracion", "plantillas_email.tab_editor")}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("preview")}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer",
                    activeTab === "preview"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Eye className="h-3 w-3" /> {translateKey("configuracion", "plantillas_email.tab_preview")}
                </button>
              </div>
            </div>

            {activeTab === "edit" ? (
              <textarea
                ref={cuerpoRef}
                value={cuerpo}
                onFocus={() => setLastFocus("cuerpo")}
                onChange={(e) => setCuerpo(e.target.value)}
                rows={9}
                className="w-full p-3 rounded-xl border border-border bg-background font-mono text-xs outline-none focus:border-primary resize-none leading-relaxed"
                placeholder={translateKey("configuracion", "plantillas_email.cuerpo_placeholder")}
              />
            ) : (
              <div className="p-4 rounded-xl border border-border bg-card/60 min-h-[180px] space-y-3 text-xs">
                <div className="border-b border-border pb-2">
                  <p className="font-bold text-foreground">
                    <span className="text-muted-foreground font-normal">
                      {translateKey("configuracion", "plantillas_email.preview_para")}
                    </span>
                    ventas@proveedor.cl
                  </p>
                  <p className="font-bold text-foreground">
                    <span className="text-muted-foreground font-normal">
                      {translateKey("configuracion", "plantillas_email.preview_asunto")}
                    </span>
                    {renderResolvedPreview(asunto)}
                  </p>
                </div>
                <div className="whitespace-pre-line text-foreground/90 font-sans leading-relaxed">
                  {renderResolvedPreview(cuerpo)}
                </div>
              </div>
            )}
          </div>

          {/* Acciones */}
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setDialogOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-bold text-muted-foreground hover:bg-secondary cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "plantillas_email.boton_cancelar")}
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-primary hover:bg-primary/90 text-primary-foreground shadow-md cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "plantillas_email.boton_confirmar")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      {/* Modal Confirmación de Eliminación */}
      <ResponsiveDialog
        open={!!deletePlantillaId}
        onClose={() => setDeletePlantillaId(null)}
        title={translateKey("configuracion", "plantillas_email.dialog_delete_title")}
        description={translateKey("configuracion", "plantillas_email.dialog_delete_description")}
      >
        <div className="space-y-4 pt-2">
          <p className="text-xs text-muted-foreground">
            {translateKey("configuracion", "plantillas_email.dialog_delete_confirm_text")}
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setDeletePlantillaId(null)}
              className="px-4 py-2 rounded-xl text-xs font-bold hover:bg-secondary text-muted-foreground cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "plantillas_email.boton_cancelar")}
            </button>
            <button
              type="button"
              onClick={() => deletePlantillaId && handleDelete(deletePlantillaId)}
              className="px-4 py-2 rounded-xl text-xs font-black uppercase bg-destructive text-destructive-foreground hover:bg-destructive/90 cursor-pointer min-h-[44px]"
            >
              {translateKey("configuracion", "plantillas_email.boton_eliminar_plantilla")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}

export default PlantillasEmailConfig;
