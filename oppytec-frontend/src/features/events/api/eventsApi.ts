// oppytec-frontend/src/features/events/api/eventsApi.ts
import { apiRequest } from "@/shared/api/httpClient";
import type {
  Salon,
  SalonCreatePayload,
  SalonUpdatePayload,
  Evento,
  EventoListItem,
  EventoCreatePayload,
  EventoUpdatePayload,
  EventFilterParams,
  EventFaltantesResponse,
  EventExecutionResult,
  CommittedStockSummaryResponse,
  EventAlertItem,
} from "../types";
import {
  MOCK_SALONES,
  MOCK_EVENTOS,
  MOCK_EVENTOS_LIST,
  MOCK_FALTANTES_RESPONSE,
  MOCK_COMMITTED_STOCK_RESPONSE,
  MOCK_EVENT_ALERTS,
} from "../mockData";

const BASE_PATH = "/api/v1/events";

/**
 * Cliente API REST tipado para el Módulo de Eventos y Salones de OppyTec v2.0.
 * Conexión resiliente contra backend FastAPI con fallback automático para tests y modo offline.
 */
export const eventsApi = {
  // ==========================================
  // SALONES CRUD
  // ==========================================

  async getSalones(areaId?: number | string): Promise<Salon[]> {
    const query = areaId !== undefined && areaId !== "all" ? `?area_operativa_id=${areaId}` : "";
    const response = await apiRequest<Salon[]>(`${BASE_PATH}/salones${query}`, {
      method: "GET",
      fallbackData: MOCK_SALONES,
    });
    return response.data;
  },

  async getSalonById(id: string): Promise<Salon> {
    const fallback = MOCK_SALONES.find((s) => s.id === id) ?? MOCK_SALONES[0]!;
    const response = await apiRequest<Salon>(`${BASE_PATH}/salones/${id}`, {
      method: "GET",
      fallbackData: fallback,
    });
    return response.data;
  },

  async createSalon(data: SalonCreatePayload): Promise<Salon> {
    const fallback: Salon = {
      id: `sal-${Date.now()}`,
      nombre: data.nombre,
      capacidad_personas: data.capacidad_personas ?? 50,
      precio_neto: data.precio_neto ?? 0,
      iva_porcentaje: data.iva_porcentaje ?? 19,
      precio_bruto: data.precio_bruto ?? (data.precio_neto ? data.precio_neto * 1.19 : 0),
      notas: data.notas ?? null,
      estado: data.estado ?? "limpio",
      color: data.color ?? "#ec4899",
      areas_operativas_ids: data.areas_operativas_ids ?? [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const response = await apiRequest<Salon>(`${BASE_PATH}/salones`, {
      method: "POST",
      body: data,
      fallbackData: fallback,
    });
    return response.data;
  },

  async updateSalon(id: string, data: SalonUpdatePayload): Promise<Salon> {
    const existing = MOCK_SALONES.find((s) => s.id === id) ?? MOCK_SALONES[0]!;
    const fallback: Salon = {
      ...existing,
      ...data,
      id,
      precio_bruto: data.precio_bruto ?? existing.precio_bruto,
      updated_at: new Date().toISOString(),
    };

    const response = await apiRequest<Salon>(`${BASE_PATH}/salones/${id}`, {
      method: "PUT",
      body: data,
      fallbackData: fallback,
    });
    return response.data;
  },

  async deleteSalon(id: string): Promise<void> {
    await apiRequest<void>(`${BASE_PATH}/salones/${id}`, {
      method: "DELETE",
      fallbackData: null as unknown as void,
    });
  },

  // ==========================================
  // EVENTOS CRUD Y CONTROL
  // ==========================================

  async getEvents(filters?: EventFilterParams): Promise<EventoListItem[]> {
    const params = new URLSearchParams();
    if (filters?.estado && filters.estado !== "ALL") {
      params.append("estado", filters.estado);
    }
    if (filters?.fecha_desde) {
      params.append("fecha_desde", filters.fecha_desde);
    }
    if (filters?.fecha_hasta) {
      params.append("fecha_hasta", filters.fecha_hasta);
    }
    if (filters?.salon_id && filters.salon_id !== "all") {
      params.append("salon_id", filters.salon_id);
    }
    if (filters?.area_operativa_id !== undefined) {
      params.append("area_operativa_id", String(filters.area_operativa_id));
    }

    const queryString = params.toString() ? `?${params.toString()}` : "";
    const response = await apiRequest<EventoListItem[]>(`${BASE_PATH}${queryString}`, {
      method: "GET",
      fallbackData: MOCK_EVENTOS_LIST,
    });
    return response.data;
  },

  async getEventById(id: string): Promise<Evento> {
    const fallback = MOCK_EVENTOS.find((e) => e.id === id) ?? MOCK_EVENTOS[0]!;
    const response = await apiRequest<Evento>(`${BASE_PATH}/${id}`, {
      method: "GET",
      fallbackData: fallback,
    });
    return response.data;
  },

  async createEvent(data: EventoCreatePayload): Promise<Evento> {
    const fallback: Evento = {
      id: `evt-${Date.now()}`,
      nombre: data.nombre,
      titular: data.titular ?? null,
      tipo_evento: data.tipo_evento ?? "GENERAL",
      salon_id: data.salon_id ?? null,
      lugar: data.lugar ?? null,
      fecha: data.fecha,
      hora_inicio: data.hora_inicio ?? null,
      hora_fin: data.hora_fin ?? null,
      cantidad_personas: data.cantidad_personas ?? 0,
      cantidad_invitados: data.cantidad_personas ?? 0,
      estado: "agendado",
      color: data.color ?? "#ec4899",
      ejecutado: false,
      cancelado: false,
      encargado_id: data.encargado_id ?? null,
      valor_publico: data.valor_publico ?? 0,
      notas: data.notas ?? null,
      nota_personal: data.nota_personal ?? null,
      nota_equipo: data.nota_equipo ?? null,
      nota_visible: data.nota_visible ?? null,
      items: (data.items ?? []).map((it, idx) => ({
        id: `it-${idx + 1}`,
        producto_id: it.producto_id,
        bodega_id: it.bodega_id,
        cantidad: it.cantidad,
        costo_unitario_estimado: it.costo_unitario_estimado ?? 0,
        notas: it.notas ?? null,
      })),
      recetas: (data.recetas ?? []).map((rc, idx) => ({
        id: `rc-${idx + 1}`,
        receta_id: rc.receta_id,
        bodega_id: rc.bodega_id ?? null,
        porciones: rc.porciones ?? 1,
        notas: rc.notas ?? null,
      })),
      combos: (data.combos ?? []).map((cb, idx) => ({
        id: `cb-${idx + 1}`,
        combo_id: cb.combo_id,
        bodega_id: cb.bodega_id ?? null,
        cantidad: cb.cantidad ?? 1,
        notas: cb.notas ?? null,
      })),
      trabajadores: (data.trabajadores ?? []).map((tb, idx) => ({
        id: `tb-${idx + 1}`,
        usuario_id: tb.usuario_id,
        rol_evento: tb.rol_evento ?? null,
        horas_asignadas: tb.horas_asignadas ?? 0,
      })),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const response = await apiRequest<Evento>(BASE_PATH, {
      method: "POST",
      body: data,
      fallbackData: fallback,
    });
    return response.data;
  },

  async updateEvent(id: string, data: EventoUpdatePayload): Promise<Evento> {
    const existing = MOCK_EVENTOS.find((e) => e.id === id) ?? MOCK_EVENTOS[0]!;
    const fallback: Evento = {
      ...existing,
      ...data,
      id,
      estado: (data.estado ?? existing.estado) as Evento["estado"],
      items:
        data.items !== undefined
          ? data.items.map((it, idx) => ({
              id: `it-${idx + 1}`,
              producto_id: it.producto_id,
              bodega_id: it.bodega_id,
              cantidad: it.cantidad,
              costo_unitario_estimado: it.costo_unitario_estimado ?? 0,
              notas: it.notas ?? null,
            }))
          : existing.items,
      recetas:
        data.recetas !== undefined
          ? data.recetas.map((rc, idx) => ({
              id: `rc-${idx + 1}`,
              receta_id: rc.receta_id,
              bodega_id: rc.bodega_id ?? null,
              porciones: rc.porciones ?? 1,
              notas: rc.notas ?? null,
            }))
          : existing.recetas,
      combos:
        data.combos !== undefined
          ? data.combos.map((cb, idx) => ({
              id: `cb-${idx + 1}`,
              combo_id: cb.combo_id,
              bodega_id: cb.bodega_id ?? null,
              cantidad: cb.cantidad ?? 1,
              notas: cb.notas ?? null,
            }))
          : existing.combos,
      trabajadores:
        data.trabajadores !== undefined
          ? data.trabajadores.map((tb, idx) => ({
              id: `tb-${idx + 1}`,
              usuario_id: tb.usuario_id,
              rol_evento: tb.rol_evento ?? null,
              horas_asignadas: tb.horas_asignadas ?? 0,
            }))
          : existing.trabajadores,
      updated_at: new Date().toISOString(),
    };

    const response = await apiRequest<Evento>(`${BASE_PATH}/${id}`, {
      method: "PUT",
      body: data,
      fallbackData: fallback,
    });
    return response.data;
  },

  async deleteEvent(id: string): Promise<void> {
    await apiRequest<void>(`${BASE_PATH}/${id}`, {
      method: "DELETE",
      fallbackData: null as unknown as void,
    });
  },

  async executeEvent(id: string): Promise<EventExecutionResult> {
    const fallback: EventExecutionResult = {
      evento_id: id,
      ejecutado: true,
      ejecutado_at: new Date().toISOString(),
      total_movimientos_kardex: 2,
      costo_total_consumido: 105000,
      consumos: [],
    };

    const response = await apiRequest<EventExecutionResult>(`${BASE_PATH}/${id}/execute`, {
      method: "POST",
      fallbackData: fallback,
    });
    return response.data;
  },

  async cancelEvent(id: string, motivo?: string): Promise<Evento> {
    const existing = MOCK_EVENTOS.find((e) => e.id === id) ?? MOCK_EVENTOS[0]!;
    const fallback: Evento = {
      ...existing,
      estado: "cancelado",
      cancelado: true,
      cancelado_at: new Date().toISOString(),
      motivo_cancelacion: motivo ?? "Cancelado por el usuario",
      updated_at: new Date().toISOString(),
    };

    const response = await apiRequest<Evento>(`${BASE_PATH}/${id}/cancel`, {
      method: "POST",
      body: motivo ? { motivo } : {},
      fallbackData: fallback,
    });
    return response.data;
  },

  async reactivateEvent(id: string): Promise<Evento> {
    const existing = MOCK_EVENTOS.find((e) => e.id === id) ?? MOCK_EVENTOS[0]!;
    const fallback: Evento = {
      ...existing,
      estado: "agendado",
      cancelado: false,
      cancelado_at: null,
      motivo_cancelacion: null,
      updated_at: new Date().toISOString(),
    };

    const response = await apiRequest<Evento>(`${BASE_PATH}/${id}/reactivate`, {
      method: "POST",
      fallbackData: fallback,
    });
    return response.data;
  },

  async getFaltantesAnalytics(areaId?: number | string): Promise<EventFaltantesResponse> {
    const query = areaId !== undefined && areaId !== "all" ? `?area_operativa_id=${areaId}` : "";
    const response = await apiRequest<EventFaltantesResponse>(`${BASE_PATH}/faltantes${query}`, {
      method: "GET",
      fallbackData: MOCK_FALTANTES_RESPONSE,
    });
    return response.data;
  },

  async getCommittedStock(bodegaId?: string | number): Promise<CommittedStockSummaryResponse> {
    const query = bodegaId !== undefined && bodegaId !== "all" ? `?bodega_id=${bodegaId}` : "";
    let fallback = MOCK_COMMITTED_STOCK_RESPONSE;
    if (bodegaId !== undefined && bodegaId !== "all") {
      const bId = Number(bodegaId);
      const filtered = MOCK_COMMITTED_STOCK_RESPONSE.items.filter((it) => it.bodega_id === bId);
      fallback = {
        total_items: filtered.length,
        items: filtered,
        generado_at: new Date().toISOString(),
      };
    }
    const response = await apiRequest<CommittedStockSummaryResponse>(
      `${BASE_PATH}/analytics/committed-stock${query}`,
      {
        method: "GET",
        fallbackData: fallback,
      }
    );
    return response.data;
  },

  async getEventAlerts(): Promise<EventAlertItem[]> {
    const response = await apiRequest<EventAlertItem[] | { items: EventAlertItem[] }>(
      `${BASE_PATH}/alerts`,
      {
        method: "GET",
        fallbackData: MOCK_EVENT_ALERTS,
      }
    );
    if (Array.isArray(response.data)) {
      return response.data;
    }
    if (response.data && "items" in response.data && Array.isArray((response.data as { items: EventAlertItem[] }).items)) {
      return (response.data as { items: EventAlertItem[] }).items;
    }
    return [];
  },
};
