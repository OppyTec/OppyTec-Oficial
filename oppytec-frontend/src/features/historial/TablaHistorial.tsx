// oppytec-frontend/src/features/historial/TablaHistorial.tsx
import { useMemo } from "react";
import { ArrowRight, ArrowUpRight, ArrowDownLeft, Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useCurrencyFormatter } from "@/shared/currency";
import { cn } from "@/shared/lib";
import { BodegaBadge } from "@/shared/components/layout/BodegaBadge";
import { useAuth, usePermissions } from "@/shared/auth/usePermissions";
import type { RegistroMovimiento, BeforeAfterDelta } from "./types";

/**
 * Propiedades del componente TablaHistorial.
 */
export interface TablaHistorialProps {
  /**
   * Colección de registros de auditoría y movimientos de Kardex a presentar.
   */
  readonly registros?: RegistroMovimiento[];
  /**
   * Alias de compatibilidad retroactiva con implementaciones previas.
   */
  readonly data?: RegistroMovimiento[];
  /**
   * Indicador de carga activa (renderiza skeleton pulsante).
   */
  readonly loading?: boolean;
  /**
   * Control explícito de visibilidad de la columna de usuario según permisos RBAC.
   * Si no se especifica, se evalúa automáticamente con useAuth y usePermissions.
   */
  readonly canViewUsers?: boolean;
  /**
   * Zona horaria IANA canónica para formateo de fechas y horas.
   * Por defecto: 'America/Santiago'.
   */
  readonly timezone?: string;
  /**
   * Callback invocado al hacer clic en una fila de la tabla.
   */
  readonly onRowClick?: (registro: RegistroMovimiento) => void;
  /**
   * Función opcional para calcular deltas de conciliación Before/After.
   */
  readonly computeBeforeAfter?: (r: RegistroMovimiento) => BeforeAfterDelta | null;
  /**
   * Función opcional para resolver nombres de producto cuando no vengan enriquecidos.
   */
  readonly prodName?: (id: string | number) => string;
  /**
   * Función opcional para resolver unidad de medida de producto.
   */
  readonly prodUnit?: (id: string | number) => string;
  /**
   * Clases CSS opcionales para el contenedor exterior.
   */
  readonly className?: string;
}

/**
 * Zona horaria predeterminada de operaciones en Chile.
 */
export const DEFAULT_CHILE_TIMEZONE = "America/Santiago";

/**
 * Formatea una fecha ISO a la representación visual en fecha (dd/MM/yyyy) en la timezone especificada.
 */
export function formatChileDate(isoDateStr: string, timeZone: string = DEFAULT_CHILE_TIMEZONE): string {
  if (!isoDateStr) return "—";
  try {
    const d = new Date(isoDateStr);
    if (isNaN(d.getTime())) return isoDateStr;
    return d.toLocaleDateString("es-CL", {
      timeZone,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return isoDateStr;
  }
}

/**
 * Formatea la hora en notación de 24 horas (HH:mm:ss) en la timezone especificada.
 */
export function formatChileTime(isoDateStr: string, timeZone: string = DEFAULT_CHILE_TIMEZONE): string {
  if (!isoDateStr) return "";
  try {
    const d = new Date(isoDateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("es-CL", {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "";
  }
}

/**
 * Formatea fecha y hora completa canónica: dd-MM-yyyy HH:mm:ss.
 */
export function formatCanonicalChileDateTime(
  isoDateStr: string,
  timeZone: string = DEFAULT_CHILE_TIMEZONE
): string {
  if (!isoDateStr) return "—";
  try {
    const d = new Date(isoDateStr);
    if (isNaN(d.getTime())) return isoDateStr;
    const datePart = d
      .toLocaleDateString("es-CL", {
        timeZone,
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
      .replace(/\//g, "-");
    const timePart = d.toLocaleTimeString("es-CL", {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    return `${datePart} ${timePart}`;
  } catch {
    return isoDateStr;
  }
}

/**
 * Resuelve las clases de estilo cromático semántico según el tipo de movimiento:
 * - compra / entrada / ajuste_positivo: Verde (emerald/green)
 * - consumo / merma / salida / ajuste_negativo: Rojo (destructive/red)
 * - transferencia: Azul / Cian (#06b6d4)
 * - conteo / ajuste_auditoria: Púrpura / Índigo
 * - reversion / redo: Ámbar / Naranja
 */
export function getTipoBadgeClass(tipo: string): string {
  const t = (tipo || "").toLowerCase();

  switch (t) {
    case "compra":
    case "entrada":
    case "ajuste_positivo":
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border-emerald-300/50 dark:border-emerald-800/40";

    case "consumo":
    case "merma":
    case "salida":
    case "ajuste_negativo":
      return "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-400 border-red-300/50 dark:border-red-800/40";

    case "transferencia":
      return "bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-400 border-cyan-300/50 dark:border-cyan-800/40";

    case "conteo":
    case "ajuste_auditoria":
      return "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-400 border-purple-300/50 dark:border-purple-800/40";

    case "reversion":
    case "redo":
      return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border-amber-300/50 dark:border-amber-800/40";

    case "ajuste":
      return "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-400 border-blue-300/50 dark:border-blue-800/40";

    default:
      return "bg-secondary text-secondary-foreground border-border";
  }
}

/**
 * Traduce el identificador de tipo de movimiento a etiqueta legible en español.
 */
export function formatTipoLabel(
  tipo: string,
  t?: (key: string, opts?: any) => string
): string {
  const map: Record<string, string> = {
    conteo: "Conteo",
    consumo: "Consumo",
    merma: "Merma",
    ajuste: "Ajuste",
    transferencia: "Transferencia",
    compra: "Compra",
    entrada: "Entrada",
    salida: "Salida",
    reversion: "Reversión",
    redo: "Rehacer",
    ajuste_auditoria: "Ajuste Auditoría",
    ajuste_positivo: "Ajuste Positivo",
    ajuste_negativo: "Ajuste Negativo",
  };
  const key = (tipo || "").toLowerCase();
  const fallback = map[key] ?? (tipo ? tipo.charAt(0).toUpperCase() + tipo.slice(1) : "—");
  if (t) {
    return t(`filters.types.${key}`, { defaultValue: fallback });
  }
  return fallback;
}

/**
 * Fallback para cálculo Before/After cuando no se inyecta desde el hook useHistorial.
 */
function defaultComputeBeforeAfter(r: RegistroMovimiento): BeforeAfterDelta | null {
  if (r.delta_before != null && r.delta_after != null) {
    return {
      before: Number(r.delta_before),
      after: Number(r.delta_after),
    };
  }
  const t = (r.tipo_movimiento || "").toLowerCase();
  if (t === "conteo" || t.includes("ajuste")) {
    if (r.saldo_resultante != null) {
      const after = Number(r.saldo_resultante);
      const before = after - Number(r.cantidad || 0);
      return { before, after };
    }
  }
  return null;
}

/**
 * Componente de Tabla Multidimensional de Trazabilidad del Kardex (Fase 6).
 *
 * Características:
 * - Envoltorio responsivo con overflow horizontal y sombreado técnico.
 * - Formateo canónico de fecha y hora en timezone America/Santiago (o configurable).
 * - Badges semánticos cromáticos por tipo de movimiento.
 * - Indicadores visuales de dirección en transferencias (↑ salida, ↓ entrada).
 * - Visualización Before/After en conciliaciones de conteos y ajustes.
 * - Control de visibilidad de usuario gobernado por RBAC.
 * - Estados de carga esqueletizados y estado vacío descriptivo.
 */
export function TablaHistorial({
  registros,
  data,
  loading = false,
  canViewUsers,
  timezone = DEFAULT_CHILE_TIMEZONE,
  onRowClick,
  computeBeforeAfter,
  prodName,
  prodUnit,
  className,
}: TablaHistorialProps) {
  const { t } = useTranslation("history");
  const { format: formatCurrency } = useCurrencyFormatter();
  const auth = useAuth();
  const permissions = usePermissions();

  // Resolución reactiva del permiso de visualización de usuarios
  const effectiveCanViewUsers = useMemo(() => {
    if (canViewUsers !== undefined) {
      return canViewUsers;
    }
    return Boolean(
      auth.isGlobalAdmin ||
      auth.user?.role === "admin" ||
      auth.user?.isSuperuser ||
      permissions.can("rbac_audit.audit.read" as any) ||
      permissions.can("inventory.history.read_users" as any)
    );
  }, [canViewUsers, auth.isGlobalAdmin, auth.user, permissions]);

  const items = registros ?? data ?? [];
  const baCalculator = computeBeforeAfter ?? defaultComputeBeforeAfter;

  const totalCols = effectiveCanViewUsers ? 7 : 6;

  return (
    <div
      data-testid="tabla-historial"
      className={cn(
        "overflow-x-auto rounded-lg border border-border shadow-sm bg-card",
        className
      )}
    >
      <table className="w-full text-left text-xs border-collapse">
        <thead>
          <tr className="border-b border-border bg-secondary/50 text-[10px] uppercase font-bold text-muted-foreground select-none">
            <th scope="col" className="py-2.5 px-3 whitespace-nowrap">
              {t("table.headers.datetime")}
            </th>
            <th scope="col" className="py-2.5 px-3 whitespace-nowrap">
              {t("table.headers.product")}
            </th>
            <th scope="col" className="py-2.5 px-3 whitespace-nowrap">
              {t("table.headers.type")}
            </th>
            <th scope="col" className="py-2.5 px-3 whitespace-nowrap">
              {t("table.headers.warehouse")}
            </th>
            <th scope="col" className="py-2.5 px-3 text-right whitespace-nowrap">
              {t("table.headers.quantity")}
            </th>
            {effectiveCanViewUsers && (
              <th scope="col" className="py-2.5 px-3 whitespace-nowrap">
                {t("table.headers.user")}
              </th>
            )}
            <th scope="col" className="py-2.5 px-3 whitespace-nowrap">
              {t("table.headers.reason")}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {loading ? (
            // Filas esqueleto pulsantes para estado de carga
            Array.from({ length: 5 }).map((_, idx) => (
              <tr
                key={`skeleton-row-${idx}`}
                data-testid="tabla-historial-skeleton"
                className="animate-pulse"
              >
                <td className="py-3 px-3">
                  <div className="h-3 w-20 bg-muted rounded mb-1" />
                  <div className="h-2.5 w-14 bg-muted/60 rounded" />
                </td>
                <td className="py-3 px-3">
                  <div className="h-3 w-28 bg-muted rounded" />
                </td>
                <td className="py-3 px-3">
                  <div className="h-5 w-20 bg-muted rounded-full" />
                </td>
                <td className="py-3 px-3">
                  <div className="h-5 w-16 bg-muted rounded-lg" />
                </td>
                <td className="py-3 px-3 text-right">
                  <div className="h-3 w-16 bg-muted rounded ml-auto" />
                </td>
                {effectiveCanViewUsers && (
                  <td className="py-3 px-3">
                    <div className="h-3 w-20 bg-muted rounded" />
                  </td>
                )}
                <td className="py-3 px-3">
                  <div className="h-3 w-24 bg-muted rounded" />
                </td>
              </tr>
            ))
          ) : items.length === 0 ? (
            // Estado vacío
            <tr>
              <td
                colSpan={totalCols}
                data-testid="historial-empty-state"
                className="py-10 px-4 text-center text-sm text-muted-foreground"
              >
                {t("table.empty_state")}
              </td>
            </tr>
          ) : (
            // Renderizado de registros de auditoría
            items.map((r) => {
              const ba = baCalculator(r);
              const pName = r.nombre_producto || (prodName ? prodName(r.producto_id) : "—");
              const bName =
                r.nombre_bodega ||
                (r.bodega_id ? `Bodega #${r.bodega_id}` : "S/N");
              const unit = r.unidad_medida || (prodUnit ? prodUnit(r.producto_id) : "");
              const uName = r.user_display_name || t("table.user_system");

              // Detección de dirección de transferencia (saliente ↑ vs entrante ↓)
              const isTransferencia =
                (r.tipo_movimiento || "").toLowerCase() === "transferencia";
              const isTransferSaliente =
                isTransferencia &&
                (r.descripcion_merma?.toLowerCase().includes("salida") ||
                  Number(r.cantidad) < 0);
              const isTransferEntrante =
                isTransferencia && !isTransferSaliente;

              const isConteoOrAudit =
                (r.tipo_movimiento || "").toLowerCase() === "conteo" ||
                (r.tipo_movimiento || "").toLowerCase() === "ajuste_auditoria";

              const fullDateTimeCanonical = formatCanonicalChileDateTime(
                r.created_at || r.fecha_recuento,
                timezone
              );

              const isClickable = Boolean(onRowClick);

              return (
                <tr
                  key={r.id}
                  data-testid={`historial-row-${r.id}`}
                  onClick={() => onRowClick?.(r)}
                  onKeyDown={(e) => {
                    if (onRowClick && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault();
                      onRowClick(r);
                    }
                  }}
                  tabIndex={isClickable ? 0 : undefined}
                  role={isClickable ? "button" : undefined}
                  className={cn(
                    "transition-colors hover:bg-muted/40",
                    isClickable && "cursor-pointer focus:bg-muted/50 focus:outline-none"
                  )}
                >
                  {/* Fecha y hora en huso horario America/Santiago */}
                  <td className="py-2.5 px-3 font-mono text-[11px] whitespace-nowrap">
                    <div
                      className="text-foreground font-semibold"
                      title={fullDateTimeCanonical}
                    >
                      {formatChileDate(r.created_at || r.fecha_recuento, timezone)}
                    </div>
                    {r.created_at && (
                      <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-2.5 w-2.5 opacity-60 shrink-0" />
                        <span>{formatChileTime(r.created_at, timezone)}</span>
                      </div>
                    )}
                  </td>

                  {/* Producto */}
                  <td className="py-2.5 px-3 font-medium text-foreground whitespace-nowrap">
                    {pName}
                  </td>

                  {/* Tipo de movimiento con Badges Semánticos Cromáticos */}
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <span
                      data-testid={`badge-tipo-${r.id}`}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wide border shadow-xs transition-colors",
                        getTipoBadgeClass(r.tipo_movimiento)
                      )}
                    >
                      <span>{formatTipoLabel(r.tipo_movimiento, t)}</span>
                      {/* Indicadores de dirección en transferencias */}
                      {isTransferSaliente && (
                        <span
                          data-testid="transfer-direction-out"
                          className="inline-flex items-center font-black"
                          title={t("table.transfer.outbound_tooltip")}
                        >
                          <ArrowUpRight className="h-3 w-3 ml-0.5" />
                          <span>↑</span>
                        </span>
                      )}
                      {isTransferEntrante && (
                        <span
                          data-testid="transfer-direction-in"
                          className="inline-flex items-center font-black"
                          title={t("table.transfer.inbound_tooltip")}
                        >
                          <ArrowDownLeft className="h-3 w-3 ml-0.5" />
                          <span>↓</span>
                        </span>
                      )}
                    </span>
                  </td>

                  {/* Bodega */}
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <BodegaBadge nombre={bName} />
                  </td>

                  {/* Cantidad y Visualización Before/After en Conteos */}
                  <td className="py-2.5 px-3 text-right font-bold whitespace-nowrap">
                    {isConteoOrAudit && ba && ba.before !== ba.after ? (
                      <span
                        data-testid={`before-after-${r.id}`}
                        className="inline-flex items-center justify-end gap-1.5"
                      >
                        <span className="text-muted-foreground font-normal line-through opacity-75">
                          {ba.before} {unit}
                        </span>
                        <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                        <span className="text-foreground font-black text-cyan-600 dark:text-cyan-400">
                          {ba.after} {unit}
                        </span>
                      </span>
                    ) : (
                      <span className="text-foreground">
                        {r.cantidad} {unit}
                      </span>
                    )}
                    {/* Multi-moneda FX: Formateo con useCurrencyFormatter y precisión Decimal */}
                    {r.costo_total_movimiento != null && (
                      <div
                        data-testid={`costo-total-${r.id}`}
                        className="text-[10px] font-normal text-muted-foreground mt-0.5"
                        title={
                          r.costo_unitario_ppp != null
                            ? `${t("table.headers.unit_cost")}: ${formatCurrency(r.costo_unitario_ppp)}`
                            : undefined
                        }
                      >
                        {formatCurrency(r.costo_total_movimiento)}
                      </div>
                    )}
                    {r.costo_unitario_ppp != null && r.costo_total_movimiento == null && (
                      <div
                        data-testid={`costo-unitario-${r.id}`}
                        className="text-[10px] font-normal text-muted-foreground mt-0.5"
                      >
                        {formatCurrency(r.costo_unitario_ppp)}
                      </div>
                    )}
                  </td>

                  {/* Usuario visible según RBAC */}
                  {effectiveCanViewUsers && (
                    <td className="py-2.5 px-3 text-muted-foreground text-xs whitespace-nowrap">
                      {uName}
                    </td>
                  )}

                  {/* Motivo y Notas */}
                  <td className="py-2.5 px-3 text-muted-foreground truncate max-w-xs">
                    {[r.motivo_merma, r.descripcion_merma]
                      .filter(Boolean)
                      .join(" - ") || t("table.no_reason")}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

export default TablaHistorial;
