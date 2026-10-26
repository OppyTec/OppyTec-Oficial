import { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  Building2,
  Check,
  ClipboardCheck,
  Clock,
  CookingPot,
  Eye,
  Flame,
  Info,
  MessageSquare,
  Palette,
  ShoppingCart,
  SlidersHorizontal,
  Truck,
  User,
  UtensilsCrossed,
  X,
} from "lucide-react";
import { Can } from "@/shared/auth/Can";
import { BodegaBadge } from "@/shared/components/layout";
import { cn, formatMoney } from "@/shared/lib";
import {
  CATEGORY_MAP,
  type CategoryType,
  type Solicitud,
  type SolicitudTipo,
  type UserSimple,
} from "../types";

export interface SolicitudCardProps {
  readonly solicitud: Solicitud;
  readonly isHighlighted?: boolean;
  readonly onApprove?: (
    id: string,
    customDetails?: Record<string, any>
  ) => void | Promise<any>;
  readonly onReject?: (id: string, reason: string) => void | Promise<any>;
  readonly onInspect?: (solicitud: Solicitud) => void;
  readonly isApproving?: boolean;
  readonly isRejecting?: boolean;
  readonly className?: string;
}

function formatUserDisplayName(user?: UserSimple | null): string {
  if (!user) return "Usuario desconocido";
  if (user.first_name || user.last_name) {
    return `${user.first_name || ""} ${user.last_name || ""}`.trim();
  }
  return user.username;
}

function formatRelativeTime(dateString: string): string {
  try {
    const now = Date.now();
    const then = new Date(dateString).getTime();
    if (isNaN(then)) return dateString;
    const diffSec = Math.max(0, Math.floor((now - then) / 1000));
    if (diffSec < 60) return "recién";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `hace ${diffHour} h`;
    const diffDay = Math.floor(diffHour / 24);
    return `hace ${diffDay} d`;
  } catch {
    return dateString;
  }
}

function getTipoConfig(tipo: SolicitudTipo) {
  switch (tipo) {
    case "merma":
    case "merma_receta":
      return {
        label: "Merma",
        icon: AlertTriangle,
        colorClass: "bg-rose-600 text-white shadow-rose-950/20",
        badgeBorder: "border-rose-500/30 text-rose-400 bg-rose-500/10",
      };
    case "consumo":
      return {
        label: "Consumo",
        icon: Flame,
        colorClass: "bg-sky-600 text-white shadow-sky-950/20",
        badgeBorder: "border-sky-500/30 text-sky-400 bg-sky-500/10",
      };
    case "consumo_buffet":
      return {
        label: "Buffet",
        icon: UtensilsCrossed,
        colorClass: "bg-cyan-600 text-white shadow-cyan-950/20",
        badgeBorder: "border-cyan-500/30 text-cyan-400 bg-cyan-500/10",
      };
    case "conteo":
      return {
        label: "Conteo Físico",
        icon: ClipboardCheck,
        colorClass: "bg-emerald-600 text-white shadow-emerald-950/20",
        badgeBorder: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
      };
    case "producto_borrador_receta":
      return {
        label: "Borrador Insumo",
        icon: CookingPot,
        colorClass: "bg-amber-600 text-white shadow-amber-950/20",
        badgeBorder: "border-amber-500/30 text-amber-400 bg-amber-500/10",
      };
    case "recibir_pedido":
      return {
        label: "Recepción Pedido",
        icon: Truck,
        colorClass: "bg-indigo-600 text-white shadow-indigo-950/20",
        badgeBorder: "border-indigo-500/30 text-indigo-400 bg-indigo-500/10",
      };
    case "solicitud_compra":
      return {
        label: "Solicitud Compra",
        icon: ShoppingCart,
        colorClass: "bg-purple-600 text-white shadow-purple-950/20",
        badgeBorder: "border-purple-500/30 text-purple-400 bg-purple-500/10",
      };
    case "vinculacion_proveedor":
      return {
        label: "Vincular Proveedor",
        icon: Building2,
        colorClass: "bg-sky-600 text-white shadow-sky-950/20",
        badgeBorder: "border-sky-500/30 text-sky-400 bg-sky-500/10",
      };
    case "perfil":
      return {
        label: "Perfil Usuario",
        icon: User,
        colorClass: "bg-primary text-primary-foreground shadow-primary/20",
        badgeBorder: "border-primary/30 text-primary bg-primary/10",
      };
    case "color_turno":
      return {
        label: "Color Turno",
        icon: Palette,
        colorClass: "bg-fuchsia-600 text-white shadow-fuchsia-950/20",
        badgeBorder: "border-fuchsia-500/30 text-fuchsia-400 bg-fuchsia-500/10",
      };
    default:
      return {
        label: String(tipo).replace("_", " "),
        icon: Boxes,
        colorClass: "bg-amber-600 text-white shadow-amber-950/20",
        badgeBorder: "border-amber-500/30 text-amber-400 bg-amber-500/10",
      };
  }
}

export function SolicitudCard({
  solicitud,
  isHighlighted = false,
  onApprove,
  onReject,
  onInspect,
  isApproving = false,
  isRejecting = false,
  className,
}: SolicitudCardProps) {
  const [showRejectionForm, setShowRejectionForm] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectError, setRejectError] = useState("");

  // Modo interactivo de edición inline pre-aprobación
  const [isEditingInline, setIsEditingInline] = useState(false);
  const detallesOriginales = solicitud.detalles || {};
  const [editedTipo, setEditedTipo] = useState<SolicitudTipo>(solicitud.tipo);
  const [editedCantidad, setEditedCantidad] = useState<number>(
    Number(detallesOriginales.cantidad ?? 1)
  );
  const [editedLote, setEditedLote] = useState<string>(
    detallesOriginales.lote || detallesOriginales.lote_codigo || ""
  );
  const [editedVencimiento, setEditedVencimiento] = useState<string>(
    detallesOriginales.fecha_vencimiento || detallesOriginales.vencimiento || ""
  );
  const [editedMotivo, setEditedMotivo] = useState<string>(
    detallesOriginales.motivo || ""
  );

  const isPending = solicitud.estado === "pendiente";
  const tipoConfig = getTipoConfig(solicitud.tipo);
  const TipoIcon = tipoConfig.icon;
  const category = (solicitud.categoria || CATEGORY_MAP[solicitud.tipo] || "operaciones") as CategoryType;

  const handleConfirmReject = async () => {
    if (!rejectReason.trim()) {
      setRejectError("El motivo de rechazo es obligatorio");
      return;
    }
    if (rejectReason.trim().length < 5) {
      setRejectError("Ingresa al menos 5 caracteres explicando el motivo");
      return;
    }
    setRejectError("");
    await onReject?.(solicitud.id, rejectReason.trim());
    setShowRejectionForm(false);
    setRejectReason("");
  };

  const handleSaveAndApproveInline = async () => {
    const customDetails = {
      ...detallesOriginales,
      tipo_reclasificado: editedTipo !== solicitud.tipo ? editedTipo : undefined,
      tipo: editedTipo,
      cantidad: editedCantidad,
      lote: editedLote,
      lote_codigo: editedLote,
      fecha_vencimiento: editedVencimiento,
      vencimiento: editedVencimiento,
      motivo: editedMotivo,
      editado_pre_aprobacion: true,
    };

    await onApprove?.(solicitud.id, customDetails);
    setIsEditingInline(false);
  };

  const detalles = solicitud.detalles || {};

  return (
    <div
      id={`notif-${solicitud.id}`}
      data-testid={`solicitud-card-${solicitud.id}`}
      className={cn(
        "rounded-3xl bg-card/60 backdrop-blur-xl border overflow-hidden transition-all duration-300 flex flex-col justify-between p-4 sm:p-5 relative",
        isPending
          ? isHighlighted
            ? "border-amber-500 shadow-[0_0_24px_rgba(245,158,11,0.35)] ring-2 ring-amber-500 animate-pulse"
            : "border-border shadow-lg hover:border-amber-500/40 hover:shadow-xl"
          : "border-border/60 bg-card/30 opacity-90 hover:opacity-100",
        className
      )}
    >
      {/* 1. Cabecera de la Tarjeta */}
      <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "h-10 w-10 rounded-2xl flex items-center justify-center shrink-0 shadow-md",
              tipoConfig.colorClass
            )}
          >
            <TipoIcon className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-black text-sm text-foreground tracking-tight">
                {tipoConfig.label}
              </span>
              <span
                className={cn(
                  "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border",
                  tipoConfig.badgeBorder
                )}
              >
                {category}
              </span>
              {!isPending && (
                <span
                  data-testid={`solicitud-status-${solicitud.id}`}
                  className={cn(
                    "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider",
                    solicitud.estado === "aprobado"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : solicitud.estado === "rechazado"
                      ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                      : "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                  )}
                >
                  {solicitud.estado}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
              <span className="font-semibold text-foreground">
                {formatUserDisplayName(solicitud.usuario)}
              </span>
              {solicitud.usuario?.role && (
                <span className="text-[10px] uppercase font-bold text-muted-foreground/80">
                  • {solicitud.usuario.role}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Metadatos Fecha / Ubicación */}
        <div className="flex flex-col items-end gap-1 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1 font-medium">
            <Clock className="h-3 w-3 text-amber-500" />
            <span>{formatRelativeTime(solicitud.creado_at)}</span>
          </div>
          {detalles.bodega_nombre && (
            <BodegaBadge nombre={detalles.bodega_nombre} className="text-[9px]" />
          )}
        </div>
      </div>

      {/* 2. Cuerpo Contextualizado según tipo */}
      <div className="py-4 space-y-3 flex-1 text-sm">
        {/* Caso Merma */}
        {(solicitud.tipo === "merma" || solicitud.tipo === "merma_receta") && (
          <div className="space-y-2">
            <div className="flex items-baseline justify-between gap-2 flex-wrap">
              <span className="font-bold text-foreground text-base">
                {detalles.producto_nombre || detalles.nombre || "Insumo operativo"}
              </span>
              <span className="font-black text-amber-500 text-sm">
                {detalles.cantidad} {detalles.unidad || "un"}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 p-3 rounded-2xl bg-muted/40 border border-border/50 text-xs">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Motivo
                </span>
                <span className="font-semibold text-foreground capitalize">
                  {detalles.motivo || "Vencimiento"}
                </span>
              </div>
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Lote / Vigencia
                </span>
                <span className="font-semibold text-foreground">
                  {detalles.lote || detalles.lote_codigo || detalles.fecha_vencimiento || "Lote activo"}
                </span>
              </div>
              <div className="col-span-2 sm:col-span-1">
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Pérdida / PPP
                </span>
                <span className="font-black text-rose-500">
                  {detalles.costo_total
                    ? formatMoney(Number(detalles.costo_total))
                    : detalles.impacto_costo
                    ? formatMoney(Number(detalles.impacto_costo))
                    : "—"}
                </span>
              </div>
            </div>
            {detalles.observaciones && (
              <p className="text-xs text-muted-foreground italic px-1">
                &ldquo;{detalles.observaciones}&rdquo;
              </p>
            )}
          </div>
        )}

        {/* Caso Consumo */}
        {solicitud.tipo === "consumo" && (
          <div className="space-y-2">
            <div className="flex items-baseline justify-between gap-2 flex-wrap">
              <span className="font-bold text-foreground text-base">
                {detalles.producto_nombre || detalles.nombre || "Insumo de cocina"}
              </span>
              <span className="font-black text-sky-400 text-sm">
                {detalles.cantidad} {detalles.unidad || "un"}
              </span>
            </div>
            <div className="p-3 rounded-2xl bg-muted/40 border border-border/50 text-xs flex items-center justify-between gap-2">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Destino / Motivo
                </span>
                <span className="font-semibold text-foreground capitalize">
                  {detalles.motivo || "Cocina / Preparación"}
                </span>
              </div>
              {detalles.costo_estimado && (
                <div className="text-right">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                    Costo Estimado
                  </span>
                  <span className="font-bold text-foreground">
                    {formatMoney(Number(detalles.costo_estimado))}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Caso Conteo Físico */}
        {solicitud.tipo === "conteo" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-foreground">
                Acta de Conteo #{detalles.acta_conteo_id || detalles.conteo_id || "S/N"}
              </span>
              <button
                type="button"
                data-testid={`inspect-conteo-${solicitud.id}`}
                onClick={() => onInspect?.(solicitud)}
                className="px-2.5 py-1 rounded-xl bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 text-xs font-bold inline-flex items-center gap-1 transition-colors cursor-pointer"
              >
                <Eye className="h-3.5 w-3.5" />
                <span>Inspeccionar</span>
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2 p-3 rounded-2xl bg-muted/40 border border-border/50 text-xs text-center">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Ítems
                </span>
                <span className="font-bold text-foreground">
                  {detalles.items_contados ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Discrepancias
                </span>
                <span className="font-black text-amber-500">
                  {detalles.discrepancias_count ?? 0}
                </span>
              </div>
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Delta Neto
                </span>
                <span
                  className={cn(
                    "font-black",
                    (detalles.delta_monetario ?? 0) < 0
                      ? "text-rose-500"
                      : "text-emerald-500"
                  )}
                >
                  {detalles.delta_monetario
                    ? formatMoney(Number(detalles.delta_monetario))
                    : "$0"}
                </span>
              </div>
            </div>
            {detalles.observaciones && (
              <p className="text-xs text-muted-foreground italic px-1">
                {detalles.observaciones}
              </p>
            )}
          </div>
        )}

        {/* Caso Compras */}
        {(solicitud.tipo === "recibir_pedido" ||
          solicitud.tipo === "solicitud_compra" ||
          solicitud.tipo === "vinculacion_proveedor") && (
          <div className="space-y-2">
            <div className="flex items-baseline justify-between gap-2 flex-wrap">
              <span className="font-bold text-foreground">
                {detalles.proveedor_nombre || "Proveedor Comercial"}
              </span>
              {detalles.monto_factura && (
                <span className="font-black text-indigo-400">
                  {formatMoney(Number(detalles.monto_factura))}
                </span>
              )}
            </div>
            <div className="p-3 rounded-2xl bg-muted/40 border border-border/50 text-xs grid grid-cols-2 gap-2">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Documento / Guía
                </span>
                <span className="font-semibold text-foreground">
                  {detalles.guia_despacho ||
                    `OC #${detalles.orden_compra_id || detalles.compra_id || "—"}`}
                </span>
              </div>
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Discrepancias
                </span>
                <span
                  className={cn(
                    "font-semibold",
                    detalles.discrepancia_bultos > 0
                      ? "text-amber-500 font-bold"
                      : "text-emerald-400"
                  )}
                >
                  {detalles.discrepancia_bultos > 0
                    ? `${detalles.discrepancia_bultos} bultos en desacuerdo`
                    : "Sin discrepancias"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Caso Consumo Buffet */}
        {solicitud.tipo === "consumo_buffet" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-foreground">
                {detalles.buffet_nombre || "Sesión de Buffet"}
              </span>
              <button
                type="button"
                data-testid={`inspect-buffet-${solicitud.id}`}
                onClick={() => onInspect?.(solicitud)}
                className="px-2.5 py-1 rounded-xl bg-cyan-500 text-black font-black text-xs inline-flex items-center gap-1 shadow-sm transition-all hover:bg-cyan-400 cursor-pointer"
              >
                <Eye className="h-3.5 w-3.5" />
                <span>Auditoría Split-View</span>
              </button>
            </div>
            <div className="p-3 rounded-2xl bg-cyan-950/20 border border-cyan-500/20 text-xs flex items-center justify-between">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                  Asistencia
                </span>
                <span className="font-semibold text-foreground">
                  {detalles.pax_atendidos || 0} comensales (pax)
                </span>
              </div>
              {detalles.costo_estimado && (
                <div className="text-right">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block">
                    Costo Consumo
                  </span>
                  <span className="font-black text-cyan-400">
                    {formatMoney(Number(detalles.costo_estimado))}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Caso Perfil / Equipo */}
        {solicitud.tipo === "perfil" && detalles.profile_updates && (
          <div className="space-y-2">
            <span className="text-[10px] font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              <Info className="h-3.5 w-3.5" /> Cambios de perfil solicitados:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(detalles.profile_updates).map(([k, v]: [string, any]) => (
                <div
                  key={k}
                  className="p-2.5 rounded-xl bg-muted/40 border border-border/40 text-xs space-y-1"
                >
                  <span className="text-[9px] font-black uppercase tracking-widest text-primary block">
                    {k}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="line-through text-destructive/70 text-[11px] truncate">
                      {v?.old || "(vacío)"}
                    </span>
                    <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                    <span className="font-bold text-emerald-400 text-xs truncate">
                      {v?.new || "(nuevo)"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Caso Color Turno */}
        {solicitud.tipo === "color_turno" && (
          <div className="p-3 rounded-2xl bg-muted/40 border border-border/50 text-xs space-y-2">
            <span className="text-[10px] font-black uppercase tracking-wider text-muted-foreground block">
              Cambio de color para turno
            </span>
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-muted-foreground">
                Actual: {detalles.color_actual || "Automático"}
              </span>
              <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-black text-fuchsia-400 uppercase">
                Solicitado: {detalles.color_solicitado || "Destacado"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2.5 Panel Interactivo de Edición Inline Pre-Aprobación */}
      {isPending && isEditingInline && (
        <div
          data-testid={`inline-edit-panel-${solicitud.id}`}
          className="mt-2 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-3 animate-in fade-in"
        >
          <div className="flex items-center justify-between text-xs font-black uppercase text-amber-500 tracking-wider">
            <span className="flex items-center gap-1.5">
              <SlidersHorizontal className="h-4 w-4" /> Edición Supervisada Pre-Aprobación
            </span>
            <button
              type="button"
              onClick={() => setIsEditingInline(false)}
              className="text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {/* Reclasificación merma <-> consumo */}
            <div>
              <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                Reclasificar Naturaleza
              </label>
              <select
                data-testid={`select-inline-tipo-${solicitud.id}`}
                value={editedTipo}
                onChange={(e) => setEditedTipo(e.target.value as SolicitudTipo)}
                className="w-full h-8 rounded-xl border border-input bg-background text-foreground text-xs font-medium px-2"
              >
                <option value="merma">Merma (Descarte operativo)</option>
                <option value="consumo">Consumo (Cocina / Degustación)</option>
                <option value={solicitud.tipo}>{solicitud.tipo}</option>
              </select>
            </div>

            {/* Ajuste de Cantidad Autorizada */}
            <div>
              <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                Cantidad Autorizada ({detalles.unidad || "un"})
              </label>
              <input
                type="number"
                min="0.01"
                step="any"
                data-testid={`input-inline-cantidad-${solicitud.id}`}
                value={editedCantidad}
                onChange={(e) => setEditedCantidad(Math.max(0, Number(e.target.value)))}
                className="w-full h-8 rounded-xl border border-input bg-background text-foreground text-xs font-mono font-bold px-2"
              />
            </div>

            {/* Ajuste de Lote */}
            <div>
              <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                Código de Lote
              </label>
              <input
                type="text"
                data-testid={`input-inline-lote-${solicitud.id}`}
                value={editedLote}
                onChange={(e) => setEditedLote(e.target.value)}
                placeholder="Ej: LOTE-2026-N1"
                className="w-full h-8 rounded-xl border border-input bg-background text-foreground text-xs px-2"
              />
            </div>

            {/* Ajuste de Fecha Vencimiento */}
            <div>
              <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                Fecha Vencimiento
              </label>
              <input
                type="date"
                data-testid={`input-inline-vencimiento-${solicitud.id}`}
                value={editedVencimiento}
                onChange={(e) => setEditedVencimiento(e.target.value)}
                className="w-full h-8 rounded-xl border border-input bg-background text-foreground text-xs px-2"
              />
            </div>

            {/* Ajuste de Motivo */}
            <div className="col-span-1 sm:col-span-2">
              <label className="text-[10px] font-bold uppercase text-muted-foreground block mb-1">
                Motivo / Justificación
              </label>
              <input
                type="text"
                data-testid={`input-inline-motivo-${solicitud.id}`}
                value={editedMotivo}
                onChange={(e) => setEditedMotivo(e.target.value)}
                placeholder="Ej: Ajuste por rotura de envase o reclasificación..."
                className="w-full h-8 rounded-xl border border-input bg-background text-foreground text-xs px-2"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-1 border-t border-amber-500/20">
            <button
              type="button"
              data-testid={`btn-cancel-inline-${solicitud.id}`}
              onClick={() => setIsEditingInline(false)}
              className="px-3 py-1.5 rounded-xl border border-input text-xs font-bold text-muted-foreground hover:bg-muted cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="button"
              data-testid={`btn-save-inline-${solicitud.id}`}
              onClick={handleSaveAndApproveInline}
              disabled={isApproving}
              className="px-3.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-black uppercase tracking-wider inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Guardar y Aprobar</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. Panel de Rechazo Inline */}
      {showRejectionForm && (
        <div
          data-testid={`rejection-panel-${solicitud.id}`}
          className="mt-2 p-3.5 rounded-2xl bg-destructive/10 border border-destructive/20 space-y-2 animate-in fade-in"
        >
          <div className="flex items-center justify-between text-xs font-black uppercase text-destructive tracking-wider">
            <span className="flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" /> Motivo del Rechazo
            </span>
            <button
              type="button"
              onClick={() => {
                setShowRejectionForm(false);
                setRejectError("");
              }}
              className="text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <textarea
            data-testid={`reject-reason-input-${solicitud.id}`}
            rows={2}
            value={rejectReason}
            onChange={(e) => {
              setRejectReason(e.target.value);
              if (rejectError) setRejectError("");
            }}
            placeholder="Especifica detalladamente la razón de rechazo (obligatorio)..."
            className="w-full p-2 rounded-xl bg-background border border-destructive/30 text-xs font-medium text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-destructive"
          />
          {rejectError && (
            <p className="text-[11px] font-bold text-destructive">
              {rejectError}
            </p>
          )}
          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => {
                setShowRejectionForm(false);
                setRejectError("");
              }}
              className="px-3 py-1.5 rounded-xl border border-input bg-background hover:bg-muted text-xs font-bold text-muted-foreground cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="button"
              data-testid={`confirm-reject-btn-${solicitud.id}`}
              onClick={handleConfirmReject}
              disabled={isRejecting}
              className="px-3 py-1.5 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground text-xs font-black uppercase tracking-wider cursor-pointer"
            >
              {isRejecting ? "Rechazando..." : "Confirmar Rechazo"}
            </button>
          </div>
        </div>
      )}

      {/* 4. Metadatos de Resolución Histórica */}
      {!isPending && (
        <div className="pt-3 border-t border-border/50 text-[11px] space-y-1 text-muted-foreground">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>
              Resuelto por:{" "}
              <strong className="text-foreground">
                {formatUserDisplayName(solicitud.resuelto_por_usuario)}
              </strong>
            </span>
            {solicitud.resuelto_at && (
              <span>{new Date(solicitud.resuelto_at).toLocaleDateString("es-CL")}</span>
            )}
          </div>
          {solicitud.estado === "rechazado" && solicitud.motivo_rechazo && (
            <div className="p-2 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive font-medium text-xs mt-1">
              <strong>Motivo:</strong> &ldquo;{solicitud.motivo_rechazo}&rdquo;
            </div>
          )}
        </div>
      )}

      {/* 5. Botones de Acción (Aprobar, Rechazar, Modificar pre-aprobación y RBAC) */}
      {isPending && !showRejectionForm && !isEditingInline && (
        <div className="flex items-center justify-between gap-2 pt-3 border-t border-border/50">
          <div className="flex items-center gap-1.5">
            {/* Botón Inspección si es buffet o conteo */}
            {(solicitud.tipo === "consumo_buffet" || solicitud.tipo === "conteo") && (
              <button
                type="button"
                data-testid={`btn-inspect-${solicitud.id}`}
                onClick={() => onInspect?.(solicitud)}
                className="px-3 py-2 rounded-xl border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 font-bold text-xs inline-flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <Eye className="h-3.5 w-3.5" />
                <span>Inspeccionar</span>
              </button>
            )}

            {/* Botón Modificar pre-aprobación */}
            <Can perform="operations.approvals.approve">
              <button
                type="button"
                data-testid={`btn-edit-inline-${solicitud.id}`}
                onClick={() => setIsEditingInline(true)}
                className="px-3 py-2 rounded-xl border border-amber-500/30 text-amber-500 hover:bg-amber-500/10 font-bold text-xs inline-flex items-center gap-1.5 transition-all cursor-pointer"
                title="Modificar antes de aprobar"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Modificar</span>
              </button>
            </Can>
          </div>

          <div className="flex items-center gap-2">
            <Can perform="operations.approvals.approve">
              <button
                type="button"
                data-testid={`btn-rechazar-${solicitud.id}`}
                onClick={() => setShowRejectionForm(true)}
                disabled={isRejecting || isApproving}
                className="px-3.5 py-2 rounded-xl border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 font-black uppercase text-[10px] tracking-wider inline-flex items-center gap-1.5 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
                <span>Rechazar</span>
              </button>

              <button
                type="button"
                data-testid={`btn-aprobar-${solicitud.id}`}
                onClick={() => onApprove?.(solicitud.id)}
                disabled={isApproving || isRejecting}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black uppercase text-[10px] tracking-widest inline-flex items-center gap-1.5 shadow-md shadow-emerald-950/20 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" />
                <span>{isApproving ? "Aprobando..." : "Aprobar"}</span>
              </button>
            </Can>
          </div>
        </div>
      )}
    </div>
  );
}

export default SolicitudCard;
