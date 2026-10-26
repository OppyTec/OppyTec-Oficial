import { useState } from "react";
import {
  AlertTriangle,
  Boxes,
  Building2,
  Check,
  ClipboardCheck,
  Clock,
  CookingPot,
  Eye,
  Flame,
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

export interface NotificationsCompactTableProps {
  readonly solicitudes: readonly Solicitud[];
  readonly highlightId?: string | null;
  readonly onApprove?: (
    id: string,
    customDetails?: Record<string, any>
  ) => void | Promise<any>;
  readonly onReject?: (id: string, reason: string) => void | Promise<any>;
  readonly onInspect?: (solicitud: Solicitud) => void;
  readonly onRequestReject?: (solicitud: Solicitud) => void;
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

function getTipoIcon(tipo: SolicitudTipo) {
  switch (tipo) {
    case "merma":
    case "merma_receta":
      return AlertTriangle;
    case "consumo":
      return Flame;
    case "consumo_buffet":
      return UtensilsCrossed;
    case "conteo":
      return ClipboardCheck;
    case "producto_borrador_receta":
      return CookingPot;
    case "recibir_pedido":
      return Truck;
    case "solicitud_compra":
      return ShoppingCart;
    case "vinculacion_proveedor":
      return Building2;
    case "perfil":
      return User;
    case "color_turno":
      return Palette;
    default:
      return Boxes;
  }
}

function getResumenContextual(solicitud: Solicitud): string {
  const detalles = solicitud.detalles || {};
  switch (solicitud.tipo) {
    case "merma":
    case "merma_receta":
      return `${detalles.producto_nombre || "Insumo"} • ${detalles.cantidad ?? ""} ${detalles.unidad ?? ""} (${detalles.motivo ?? "merma"})`;
    case "consumo":
      return `${detalles.producto_nombre || "Insumo"} • ${detalles.cantidad ?? ""} ${detalles.unidad ?? ""} (${detalles.motivo ?? "cocina"})`;
    case "consumo_buffet":
      return `${detalles.buffet_nombre || "Buffet"} • ${detalles.pax_atendidos ?? 0} pax`;
    case "conteo":
      return `Acta #${detalles.acta_conteo_id || "S/N"} • ${detalles.discrepancias_count ?? 0} discrepancias`;
    case "recibir_pedido":
    case "solicitud_compra":
      return `${detalles.proveedor_nombre || "Proveedor"} • ${detalles.monto_factura ? formatMoney(Number(detalles.monto_factura)) : "Sin monto"}`;
    case "perfil":
      return "Actualización de datos personales";
    case "color_turno":
      return `Color solicitado: ${detalles.color_solicitado || "Destacado"}`;
    default:
      return "Solicitud operativa";
  }
}

export function NotificationsCompactTable({
  solicitudes,
  highlightId,
  onApprove,
  onReject,
  onInspect,
  onRequestReject,
  isApproving = false,
  isRejecting = false,
  className,
}: NotificationsCompactTableProps) {
  // Estado para la fila actualmente en edición inline
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [editTipo, setEditTipo] = useState<SolicitudTipo>("merma");
  const [editCantidad, setEditCantidad] = useState<number>(1);
  const [editLote, setEditLote] = useState<string>("");

  const handleStartEdit = (solicitud: Solicitud) => {
    setEditingRowId(solicitud.id);
    setEditTipo(solicitud.tipo);
    setEditCantidad(Number(solicitud.detalles?.cantidad ?? 1));
    setEditLote(solicitud.detalles?.lote || solicitud.detalles?.lote_codigo || "");
  };

  const handleCancelEdit = () => {
    setEditingRowId(null);
  };

  const handleSaveAndApprove = async (solicitud: Solicitud) => {
    const customDetails = {
      ...(solicitud.detalles || {}),
      tipo: editTipo,
      tipo_reclasificado: editTipo !== solicitud.tipo ? editTipo : undefined,
      cantidad: editCantidad,
      lote: editLote,
      lote_codigo: editLote,
      editado_pre_aprobacion: true,
    };

    await onApprove?.(solicitud.id, customDetails);
    setEditingRowId(null);
  };

  return (
    <div
      data-testid="notifications-compact-table"
      className={cn(
        "w-full rounded-2xl border border-input bg-card shadow-xl overflow-hidden",
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-[10px] font-black uppercase tracking-wider text-muted-foreground">
              <th className="p-3 pl-4">Tipo / Categoría</th>
              <th className="p-3">Detalle Operativo</th>
              <th className="p-3">Solicitante</th>
              <th className="p-3">Área / Bodega</th>
              <th className="p-3">Tiempo</th>
              <th className="p-3">Estado</th>
              <th className="p-3 pr-4 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {solicitudes.map((solicitud) => {
              const isPending = solicitud.estado === "pendiente";
              const isHighlighted = highlightId === solicitud.id;
              const isEditingThisRow = editingRowId === solicitud.id;
              const TipoIcon = getTipoIcon(solicitud.tipo);
              const category = (solicitud.categoria ||
                CATEGORY_MAP[solicitud.tipo] ||
                "operaciones") as CategoryType;

              return (
                <tr
                  key={solicitud.id}
                  id={`notif-compact-${solicitud.id}`}
                  data-testid={`compact-row-${solicitud.id}`}
                  className={cn(
                    "hover:bg-muted/30 transition-colors group",
                    isHighlighted
                      ? "bg-amber-500/10 ring-2 ring-amber-500 font-semibold"
                      : "",
                    !isPending ? "opacity-75" : ""
                  )}
                >
                  {/* Columna 1: Tipo */}
                  <td className="p-3 pl-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-muted text-foreground">
                        <TipoIcon className="h-4 w-4" />
                      </div>
                      <div>
                        <span className="font-bold text-foreground block capitalize">
                          {solicitud.tipo.replace("_", " ")}
                        </span>
                        <span className="text-[9px] uppercase font-mono text-muted-foreground">
                          {category}
                        </span>
                      </div>
                    </div>
                  </td>

                  {/* Columna 2: Detalle Operativo o Editor Inline */}
                  <td className="p-3 max-w-[280px]">
                    {!isEditingThisRow ? (
                      <p className="truncate text-foreground font-medium">
                        {getResumenContextual(solicitud)}
                      </p>
                    ) : (
                      <div className="flex items-center gap-1.5 animate-in fade-in">
                        <select
                          data-testid={`compact-select-tipo-${solicitud.id}`}
                          value={editTipo}
                          onChange={(e) => setEditTipo(e.target.value as SolicitudTipo)}
                          className="h-7 text-[10px] rounded border border-amber-500/40 bg-background text-foreground px-1"
                        >
                          <option value="merma">Merma</option>
                          <option value="consumo">Consumo</option>
                        </select>
                        <input
                          type="number"
                          min="0.1"
                          step="any"
                          data-testid={`compact-input-cantidad-${solicitud.id}`}
                          value={editCantidad}
                          onChange={(e) => setEditCantidad(Math.max(0, Number(e.target.value)))}
                          className="h-7 w-16 text-center text-xs font-mono font-bold rounded border border-amber-500/40 bg-background text-foreground"
                        />
                        <input
                          type="text"
                          data-testid={`compact-input-lote-${solicitud.id}`}
                          value={editLote}
                          onChange={(e) => setEditLote(e.target.value)}
                          placeholder="Lote"
                          className="h-7 w-20 text-xs rounded border border-amber-500/40 bg-background text-foreground px-1"
                        />
                      </div>
                    )}
                  </td>

                  {/* Columna 3: Solicitante */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span className="text-foreground font-semibold">
                        {formatUserDisplayName(solicitud.usuario)}
                      </span>
                      {solicitud.usuario?.role && (
                        <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-muted text-muted-foreground font-mono">
                          {solicitud.usuario.role}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Columna 4: Área / Bodega */}
                  <td className="p-3">
                    {solicitud.detalles?.bodega_nombre ? (
                      <BodegaBadge
                        nombre={solicitud.detalles.bodega_nombre}
                        className="text-[9px]"
                      />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>

                  {/* Columna 5: Tiempo */}
                  <td className="p-3 whitespace-nowrap text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-amber-500" />
                      <span>{formatRelativeTime(solicitud.creado_at)}</span>
                    </div>
                  </td>

                  {/* Columna 6: Estado */}
                  <td className="p-3 whitespace-nowrap">
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider",
                        solicitud.estado === "aprobado"
                          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                          : solicitud.estado === "rechazado"
                          ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                          : "bg-amber-500/15 text-amber-500 border border-amber-500/30"
                      )}
                    >
                      {solicitud.estado}
                    </span>
                  </td>

                  {/* Columna 7: Acciones */}
                  <td className="p-3 pr-4 text-right whitespace-nowrap">
                    {isPending ? (
                      <div className="inline-flex items-center gap-1.5 justify-end">
                        {/* Botón Inspeccionar para buffet o conteo */}
                        {(solicitud.tipo === "conteo" ||
                          solicitud.tipo === "consumo_buffet") && (
                          <button
                            type="button"
                            data-testid={`compact-inspect-${solicitud.id}`}
                            onClick={() => onInspect?.(solicitud)}
                            className="p-1.5 rounded-lg border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 cursor-pointer"
                            title="Inspeccionar"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                        )}

                        {/* Modo Edición Pre-Aprobación */}
                        <Can perform="operations.approvals.approve">
                          {!isEditingThisRow ? (
                            <button
                              type="button"
                              data-testid={`compact-edit-${solicitud.id}`}
                              onClick={() => handleStartEdit(solicitud)}
                              className="p-1.5 rounded-lg border border-amber-500/30 text-amber-500 hover:bg-amber-500/10 cursor-pointer"
                              title="Modificar antes de aprobar"
                            >
                              <SlidersHorizontal className="h-3.5 w-3.5" />
                            </button>
                          ) : (
                            <>
                              <button
                                type="button"
                                data-testid={`compact-cancel-edit-${solicitud.id}`}
                                onClick={handleCancelEdit}
                                className="p-1.5 rounded-lg border border-input text-muted-foreground hover:bg-muted cursor-pointer"
                                title="Cancelar edición"
                              >
                                <X className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                data-testid={`compact-save-edit-${solicitud.id}`}
                                onClick={() => handleSaveAndApprove(solicitud)}
                                className="p-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black shadow-xs cursor-pointer font-bold"
                                title="Guardar y Aprobar"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                            </>
                          )}

                          {!isEditingThisRow && (
                            <>
                              <button
                                type="button"
                                data-testid={`compact-reject-${solicitud.id}`}
                                onClick={() => {
                                  if (onRequestReject) {
                                    onRequestReject(solicitud);
                                  } else {
                                    onReject?.(
                                      solicitud.id,
                                      "Rechazado mediante supervisión rápida"
                                    );
                                  }
                                }}
                                disabled={isRejecting || isApproving}
                                className="p-1.5 rounded-lg border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 cursor-pointer disabled:opacity-50"
                                title="Rechazar"
                              >
                                <X className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                data-testid={`compact-approve-${solicitud.id}`}
                                onClick={() => onApprove?.(solicitud.id)}
                                disabled={isApproving || isRejecting}
                                className="p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm cursor-pointer disabled:opacity-50"
                                title="Aprobar"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                            </>
                          )}
                        </Can>
                      </div>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">
                        {solicitud.resuelto_at
                          ? new Date(solicitud.resuelto_at).toLocaleDateString("es-CL")
                          : "Resuelto"}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default NotificationsCompactTable;
