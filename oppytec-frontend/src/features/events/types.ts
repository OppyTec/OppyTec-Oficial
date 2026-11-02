// oppytec-frontend/src/features/events/types.ts
/**
 * Tipos y Contratos TypeScript para el Módulo de Eventos, Salones y Consumo de Inventario.
 * Paridad 1:1 con Backend FastAPI y Modelo de Dominio DDD de OppyTec v2.0.
 */

export type SalonEstado = "limpio" | "en_uso" | "mantenimiento" | "sucio" | "activo";

export interface Salon {
  id: string; // UUID
  nombre: string;
  capacidad_personas: number | null;
  precio_neto: number;
  iva_porcentaje: number;
  precio_bruto: number;
  notas?: string | null;
  estado: SalonEstado;
  color: string;
  areas_operativas_ids: number[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SalonCreatePayload {
  nombre: string;
  capacidad_personas?: number | null;
  precio_neto?: number;
  iva_porcentaje?: number;
  precio_bruto?: number | null;
  notas?: string | null;
  estado?: SalonEstado;
  color?: string;
  areas_operativas_ids?: number[];
}

export type SalonUpdatePayload = Partial<SalonCreatePayload>;

export type EventoEstado =
  | "agendado"
  | "confirmado"
  | "en_curso"
  | "finalizado"
  | "cancelado"
  | "AGENDADO"
  | "CONFIRMADO"
  | "EN_CURSO"
  | "EJECUTADO"
  | "CANCELADO";

export interface EventoItem {
  id?: string;
  evento_id?: string;
  producto_id: number;
  producto_nombre?: string;
  bodega_id: number;
  bodega_nombre?: string;
  cantidad: number;
  costo_unitario_estimado?: number;
  costo_total_estimado?: number;
  unidad_medida?: string;
  notas?: string | null;
}

export interface EventoReceta {
  id?: string;
  evento_id?: string;
  receta_id: number;
  receta_nombre?: string;
  bodega_id?: number | null;
  porciones: number;
  costo_unitario_estimado?: number;
  costo_estimado?: number;
  notas?: string | null;
}

export interface EventoCombo {
  id?: string;
  evento_id?: string;
  combo_id: number;
  combo_nombre?: string;
  bodega_id?: number | null;
  cantidad: number;
  costo_unitario_estimado?: number;
  costo_estimado?: number;
  notas?: string | null;
}

export interface EventoTrabajador {
  id?: string;
  evento_id?: string;
  usuario_id: number;
  usuario?: {
    id: number;
    nombre: string;
    email?: string;
    avatar_url?: string;
  };
  rol_evento?: string | null;
  rol_en_evento?: string | null;
  horas_asignadas?: number;
}

export interface EventoConsumoKardex {
  id: string;
  evento_id: string;
  kardex_movement_id: number;
  producto_id: number;
  producto_nombre?: string;
  bodega_id: number;
  bodega_nombre?: string;
  cantidad_consumida: number;
  costo_unitario_ppp: number;
  origen_tipo: string;
  origen_id?: number | null;
}

export interface Evento {
  id: string; // UUID
  nombre: string;
  titular?: string | null;
  tipo_evento?: string;
  encargado_id?: number | null;
  encargado?: { id: number; nombre: string } | null;
  salon_id?: string | null;
  salon?: Salon | null;
  salon_nombre?: string | null;
  fecha: string; // YYYY-MM-DD
  hora_inicio?: string | null; // HH:MM
  hora_fin?: string | null; // HH:MM
  lugar?: string | null;
  cantidad_personas?: number;
  cantidad_invitados?: number | null;
  estado: EventoEstado;
  color: string;
  ejecutado: boolean;
  cancelado: boolean;
  ejecutado_at?: string | null;
  cancelado_at?: string | null;
  motivo_cancelacion?: string | null;
  valor_publico?: number | null;
  notas?: string | null;
  nota_personal?: string | null;
  nota_equipo?: string | null;
  nota_visible?: string | null;
  items: EventoItem[];
  recetas: EventoReceta[];
  combos: EventoCombo[];
  trabajadores: EventoTrabajador[];
  consumos_kardex?: EventoConsumoKardex[];
  items_count?: number;
  recetas_count?: number;
  combos_count?: number;
  trabajadores_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface EventoListItem {
  id: string;
  nombre: string;
  titular?: string | null;
  tipo_evento: string;
  salon_id?: string | null;
  salon_nombre?: string | null;
  lugar?: string | null;
  fecha: string;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  cantidad_personas: number;
  estado: string;
  color: string;
  ejecutado: boolean;
  cancelado: boolean;
  encargado_id?: number | null;
  valor_publico: number;
  items_count: number;
  recetas_count: number;
  combos_count: number;
  trabajadores_count: number;
}

export interface EventoCreatePayload {
  nombre: string;
  titular?: string | null;
  tipo_evento?: string;
  salon_id?: string | null;
  lugar?: string | null;
  fecha: string;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  cantidad_personas?: number;
  estado?: string;
  color?: string;
  encargado_id?: number | null;
  valor_publico?: number;
  notas?: string | null;
  nota_personal?: string | null;
  nota_equipo?: string | null;
  nota_visible?: string | null;
  items?: Array<{
    producto_id: number;
    bodega_id: number;
    cantidad: number;
    costo_unitario_estimado?: number;
    notas?: string | null;
  }>;
  recetas?: Array<{
    receta_id: number;
    bodega_id?: number | null;
    porciones?: number;
    notas?: string | null;
  }>;
  combos?: Array<{
    combo_id: number;
    bodega_id?: number | null;
    cantidad?: number;
    notas?: string | null;
  }>;
  trabajadores?: Array<{
    usuario_id: number;
    rol_evento?: string | null;
    horas_asignadas?: number;
  }>;
}

export type EventoUpdatePayload = Partial<EventoCreatePayload>;

export interface FaltanteItem {
  producto_id: number | string;
  producto_nombre?: string | null;
  nombre?: string;
  bodega_id?: number | string;
  bodega_nombre?: string | null;
  unidad?: string;
  unidad_medida?: string | null;
  cantidad_requerida: number;
  necesario?: number;
  stock_actual: number;
  disponible?: number;
  deficit: number;
  faltante?: number;
  eventos?: Array<{
    fecha: string;
    cantidad: number;
    nombre_evento: string;
  }>;
}

export interface EventFaltantesResponse {
  total_faltantes: number;
  items: FaltanteItem[];
  eventos_afectados_count: number;
  generado_at: string;
}

export interface EventExecutionResult {
  evento_id: string;
  ejecutado: boolean;
  ejecutado_at: string;
  total_movimientos_kardex: number;
  costo_total_consumido: number;
  consumos: EventoConsumoKardex[];
}

// ============================================================================
// COMMITTED STOCK & EVENT ALERTS TYPES (FASE 7)
// ============================================================================

export interface CommittedStockEventRef {
  evento_id: string;
  evento_nombre: string;
  fecha: string;
  hora_inicio?: string | null;
  cantidad: number;
}

export interface CommittedStockItem {
  producto_id: number;
  producto_nombre?: string | null;
  bodega_id: number;
  bodega_nombre?: string | null;
  stock_actual: number;
  stock_comprometido: number;
  stock_disponible_real: number;
  unidad_medida?: string | null;
  eventos: CommittedStockEventRef[];
}

export type CommittedStockItemOut = CommittedStockItem;

export interface CommittedStockSummaryResponse {
  total_items: number;
  items: CommittedStockItem[];
  generado_at: string;
}

export interface EventAlertInsumoDeficit {
  producto_id: number;
  producto_nombre?: string | null;
  bodega_id: number;
  bodega_nombre?: string | null;
  cantidad_requerida: number;
  stock_actual: number;
  deficit: number;
  unidad_medida?: string | null;
}

export type EventAlertSeverity = "CRITICAL" | "WARNING";

export interface EventAlertItem {
  alerta_id: string;
  evento_id: string;
  evento_nombre: string;
  fecha_evento: string;
  hora_inicio: string;
  severidad: EventAlertSeverity | string;
  horas_restantes: number;
  dias_restantes: number;
  total_insumos_deficit: number;
  insumos_deficit: EventAlertInsumoDeficit[];
  mensaje: string;
  generado_at: string;
}

export type EventAlertOut = EventAlertItem;

export interface EventAlertsResponse {
  total_alertas: number;
  critical_count: number;
  warning_count: number;
  items: EventAlertItem[];
  generado_at: string;
}

export type CalendarViewMode = "month" | "week" | "3days" | "day";

export interface EventFilterParams {
  estado?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  salon_id?: string;
  area_operativa_id?: number;
  search?: string;
}

export type EventoTabType = "proximos" | "historial" | "cancelados";
