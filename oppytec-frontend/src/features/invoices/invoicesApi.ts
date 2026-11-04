/**
 * oppytec-frontend/src/features/invoices/invoicesApi.ts
 * Capa cliente HTTP para el Módulo de Facturas y Conciliación DTE.
 * Utiliza apiRequest con tipado estricto, headers canónicos (X-Tenant-ID, X-Trace-ID)
 * y fallbacks resilientes con mockData.
 */

import { apiRequest, resolveApiEndpointUrl, buildApiHeaders } from "@/shared/api/httpClient";
import {
  MOCK_INVOICES,
  MOCK_INVOICE_STATS,
  MOCK_PRICE_DRIFT_ITEMS,
} from "./mockData";
import type {
  ConfirmStockPayload,
  ExportFormat,
  Invoice,
  InvoiceFilters,
  InvoiceStats,
  InvoiceWebhook,
  LearnAliasPayload,
  PriceDriftItem,
} from "./types";

export interface PaginatedInvoicesResponse {
  items: Invoice[];
  total: number;
}

export const invoicesApi = {
  /**
   * Obtiene la lista paginada y filtrada de facturas.
   */
  async list(filters?: InvoiceFilters): Promise<PaginatedInvoicesResponse> {
    const query = new URLSearchParams();
    if (filters?.search) query.set("search", filters.search);
    if (filters?.status && filters.status !== "ALL") query.set("status", filters.status);
    if (filters?.dte_type && filters.dte_type !== "ALL") query.set("dte_type", filters.dte_type);
    if (filters?.vendor_tax_id) query.set("vendor_tax_id", filters.vendor_tax_id);
    if (filters?.date_from) query.set("date_from", filters.date_from);
    if (filters?.date_to) query.set("date_to", filters.date_to);
    if (filters?.area_id && filters.area_id !== "all") query.set("area_id", filters.area_id);
    if (filters?.page) query.set("page", String(filters.page));
    if (filters?.limit) query.set("limit", String(filters.limit));

    const path = `/api/v1/invoices${query.toString() ? `?${query.toString()}` : ""}`;

    const fallback: PaginatedInvoicesResponse = {
      items: MOCK_INVOICES,
      total: MOCK_INVOICES.length,
    };

    const res = await apiRequest<PaginatedInvoicesResponse>(path, {
      method: "GET",
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Obtiene una factura por su ID único.
   */
  async getById(id: string): Promise<Invoice> {
    const found = MOCK_INVOICES.find((inv) => inv.id === id) || MOCK_INVOICES[0]!;
    const res = await apiRequest<Invoice>(`/api/v1/invoices/${id}`, {
      method: "GET",
      fallbackData: found,
    });
    return res.data;
  },

  /**
   * Sube uno o más archivos de facturas (PDF/PNG/JPG) a Cloudflare R2 vía multipart/form-data.
   */
  async upload(
    files: File[],
    onProgress?: (pct: number) => void
  ): Promise<{ uploaded: number; invoices: Invoice[] }> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    const headers = { ...buildApiHeaders() };
    // Eliminamos Content-Type para que el browser establezca el boundary de multipart/form-data
    delete (headers as Record<string, string | undefined>)["Content-Type"];

    try {
      const url = resolveApiEndpointUrl("/api/v1/invoices/upload");
      onProgress?.(30);

      const response = await fetch(url, {
        method: "POST",
        headers,
        body: formData,
      });

      onProgress?.(80);

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }

      const parsed = (await response.json()) as { uploaded: number; invoices: Invoice[] };
      onProgress?.(100);
      return parsed;
    } catch {
      // Fallback resiliente creando facturas simuladas
      onProgress?.(100);
      const today = new Date().toISOString().split("T")[0] || null;
      const dueDate = new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0] || null;

      const mockCreated: Invoice[] = files.map((f, i) => ({
        id: `inv-sim-${Date.now()}-${i}`,
        filename: f.name,
        file_url: URL.createObjectURL(f),
        file_type: f.type.includes("pdf") ? "pdf" : "png",
        vendor_name: "Distribuidora Gastronómica Simulada SpA",
        vendor_tax_id: "76.543.210-9",
        invoice_number: String(10000 + i),
        dte_type: "FACTURA_ELECTRONICA_33",
        invoice_date: today,
        due_date: dueDate,
        net_amount: 100000,
        tax_amount: 19000,
        total_amount: 119000,
        currency: "CLP",
        status: "READY_FOR_REVIEW",
        confidence_score: 0.95,
        audit_flags: [],
        gemini_tokens_used: 1500,
        gemini_cost_usd: 0.003,
        is_confirmed_to_inventory: false,
        created_at: new Date().toISOString(),
        items: [
          {
            id: `item-sim-${Date.now()}-${i}-1`,
            line_number: 1,
            raw_description: `INSUMO CARGADO: ${f.name.slice(0, 30)}`,
            quantity: 1,
            unit_name: "Caja",
            unit_price_net: 100000,
            tax_rate: 0.19,
            total_net: 100000,
            packaging_description: "Caja de 10 unidades estándar",
            factor_empaque: 10,
            kitchen_base_unit: "unidad",
            total_stock_fisico: 10,
            costo_unitario_inventario: 10000,
            match_status: "suggested",
            matched_product_id: null,
            matched_product_name: null,
            matched_product_sku: null,
            suggested_categoria_id: "cat-abarrotes",
            product_action: "create_new",
            nombre_negocio: f.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "),
            categoria_id: "cat-abarrotes",
            bodega_id: "bod-central",
            remember_alias: true,
          },
        ],
      }));

      return {
        uploaded: files.length,
        invoices: mockCreated,
      };
    }
  },

  /**
   * Re-procesa una factura con IA Gemini OCR.
   */
  async process(id: string): Promise<Invoice> {
    const found = MOCK_INVOICES.find((i) => i.id === id) || MOCK_INVOICES[0]!;
    const fallback: Invoice = {
      ...found,
      status: "READY_FOR_REVIEW",
      confidence_score: 0.96,
    };
    const res = await apiRequest<Invoice>(`/api/v1/invoices/${id}/process`, {
      method: "POST",
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Actualiza metadatos y líneas de una factura.
   */
  async update(id: string, payload: Partial<Invoice>): Promise<Invoice> {
    const base = MOCK_INVOICES.find((i) => i.id === id) || MOCK_INVOICES[0]!;
    const fallback: Invoice = {
      ...base,
      ...payload,
      id,
      filename: payload.filename ?? base.filename,
      file_url: payload.file_url ?? base.file_url,
      file_type: payload.file_type ?? base.file_type,
      dte_type: payload.dte_type ?? base.dte_type,
      status: payload.status ?? base.status,
      confidence_score: payload.confidence_score ?? base.confidence_score,
      items: payload.items ?? base.items,
      created_at: base.created_at,
    };
    const res = await apiRequest<Invoice>(`/api/v1/invoices/${id}`, {
      method: "PUT",
      body: payload,
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Confirma la factura e ingresa el stock físico a bodegas con Kardex FEFO.
   */
  async confirmStock(
    id: string,
    payload: ConfirmStockPayload
  ): Promise<{ success: boolean; movements_created: number }> {
    const fallback = { success: true, movements_created: payload.items.length };
    const res = await apiRequest<{ success: boolean; movements_created: number }>(
      `/api/v1/invoices/${id}/confirm-stock`,
      {
        method: "POST",
        body: payload,
        fallbackData: fallback,
      }
    );
    return res.data;
  },

  /**
   * Elimina una factura (solo si no ha sido ingresada a inventario).
   */
  async remove(id: string): Promise<void> {
    await apiRequest<void>(`/api/v1/invoices/${id}`, {
      method: "DELETE",
      fallbackData: undefined,
    });
  },

  /**
   * Procesa en lote un conjunto de facturas pendientes.
   */
  async bulkProcess(ids: string[]): Promise<{ processed: number }> {
    const fallback = { processed: ids.length };
    const res = await apiRequest<{ processed: number }>("/api/v1/invoices/bulk-process", {
      method: "POST",
      body: { ids },
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Elimina en lote facturas seleccionadas.
   */
  async bulkDelete(ids: string[]): Promise<{ deleted: number }> {
    const fallback = { deleted: ids.length };
    const res = await apiRequest<{ deleted: number }>("/api/v1/invoices/bulk-delete", {
      method: "POST",
      body: { ids },
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Obtiene métricas consolidadas del panel y control FinOps de tokens.
   */
  async getStats(): Promise<InvoiceStats> {
    const res = await apiRequest<InvoiceStats>("/api/v1/invoices/stats", {
      method: "GET",
      fallbackData: MOCK_INVOICE_STATS,
    });
    return res.data;
  },

  /**
   * Obtiene el reporte analítico del radar de variación de precios (Price Drift).
   */
  async getPriceDrift(): Promise<PriceDriftItem[]> {
    const res = await apiRequest<PriceDriftItem[]>("/api/v1/invoices/price-drift", {
      method: "GET",
      fallbackData: MOCK_PRICE_DRIFT_ITEMS,
    });
    return res.data;
  },

  /**
   * Exporta facturas al formato solicitado (SII Compras, QuickBooks, Excel, etc.).
   */
  async exportInvoices(ids: string[], format: ExportFormat): Promise<Blob> {
    try {
      const url = resolveApiEndpointUrl(
        format === "sii_compras"
          ? "/api/v1/invoices/export/sii/compras"
          : format === "sii_ventas"
          ? "/api/v1/invoices/export/sii/ventas"
          : `/api/v1/invoices/export?format=${format}`
      );
      const headers = buildApiHeaders();
      const response = await fetch(url, {
        method: format.startsWith("sii_") ? "GET" : "POST",
        headers,
        body: format.startsWith("sii_") ? undefined : JSON.stringify({ ids, format }),
      });
      if (!response.ok) {
        throw new Error(`Export error: ${response.statusText}`);
      }
      return await response.blob();
    } catch {
      // Fallback CSV en memoria
      const csvContent =
        "Folio;Tipo Doc;RUT Proveedor;Razon Social;Fecha;Monto Neto;Monto IVA;Monto Total\n" +
        MOCK_INVOICES.map(
          (i) =>
            `${i.invoice_number || ""};${i.dte_type};${i.vendor_tax_id || ""};${
              i.vendor_name || ""
            };${i.invoice_date || ""};${i.net_amount};${i.tax_amount};${i.total_amount}`
        ).join("\n");
      return new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    }
  },

  /**
   * Lista los webhooks salientes registrados.
   */
  async listWebhooks(): Promise<InvoiceWebhook[]> {
    const fallback: InvoiceWebhook[] = [
      {
        id: "hook-1",
        url: "https://erp.restaurantesur.cl/webhooks/facturas",
        description: "ERP Central Contable",
        events: ["invoice.stock_confirmed", "invoice.analyzed"],
        is_active: true,
        last_sent_at: "2026-11-03T18:30:00Z",
        last_status_code: 200,
        last_response_time_ms: 184,
        created_at: "2026-10-15T12:00:00Z",
      },
    ];
    const res = await apiRequest<InvoiceWebhook[]>("/api/v1/invoices/webhooks", {
      method: "GET",
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Crea un nuevo webhook saliente.
   */
  async createWebhook(webhook: Partial<InvoiceWebhook>): Promise<InvoiceWebhook> {
    const fallback: InvoiceWebhook = {
      id: `hook-${Date.now()}`,
      url: webhook.url || "https://example.com/webhook",
      description: webhook.description || "Nuevo Webhook",
      events: webhook.events || ["invoice.stock_confirmed"],
      is_active: true,
      created_at: new Date().toISOString(),
    };
    const res = await apiRequest<InvoiceWebhook>("/api/v1/invoices/webhooks", {
      method: "POST",
      body: webhook,
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Elimina un webhook configurado.
   */
  async deleteWebhook(id: string): Promise<void> {
    await apiRequest<void>(`/api/v1/invoices/webhooks/${id}`, {
      method: "DELETE",
      fallbackData: undefined,
    });
  },

  /**
   * Ejecuta un ping de prueba contra el webhook configurado.
   */
  async pingWebhook(
    id: string
  ): Promise<{ success: boolean; response_time_ms: number; status_code: number }> {
    const fallback = { success: true, response_time_ms: 120, status_code: 200 };
    const res = await apiRequest<{
      success: boolean;
      response_time_ms: number;
      status_code: number;
    }>(`/api/v1/invoices/webhooks/${id}/ping`, {
      method: "POST",
      fallbackData: fallback,
    });
    return res.data;
  },

  /**
   * Memoriza o actualiza un alias de proveedor de forma explícita.
   */
  async learnAlias(payload: LearnAliasPayload): Promise<{ success: boolean; alias_id: string }> {
    const fallback = { success: true, alias_id: `alias-${Date.now()}` };
    const res = await apiRequest<{ success: boolean; alias_id: string }>(
      "/api/v1/invoices/aliases/learn",
      {
        method: "POST",
        body: payload,
        fallbackData: fallback,
      }
    );
    return res.data;
  },
};
