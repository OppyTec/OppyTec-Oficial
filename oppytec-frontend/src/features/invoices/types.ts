/**
 * oppytec-frontend/src/features/invoices/types.ts
 * Contratos TypeScript 5 estrictos para el Módulo de Facturas y Conciliación DTE.
 * Alineado 1:1 con modelos de dominio de backend, RFC 7807 y reglas de paridad Legacy.
 */

export type InvoiceStatus =
  | "UPLOADED"
  | "ANALYZING"
  | "ANALYZED"
  | "READY_FOR_REVIEW"
  | "CONFIRMED_STOCK"
  | "ERROR"
  | "REJECTED";

export type DTEType =
  | "FACTURA_ELECTRONICA_33"
  | "FACTURA_EXENTA_34"
  | "GUIA_DESPACHO_52"
  | "BOLETA_ELECTRONICA_39"
  | "NOTA_CREDITO_61"
  | "NOTA_DEBITO_56";

export type AuditFlagSeverity = "low" | "medium" | "high";

export interface InvoiceAuditFlag {
  readonly code:
    | "TAX_MISMATCH"
    | "RECEIVER_RUT_MISMATCH"
    | "UNKNOWN_SUPPLIER"
    | "PRICE_DRIFT_DETECTED"
    | "DUPLICATE_INVOICE_WARNING"
    | string;
  readonly message: string;
  readonly severity: AuditFlagSeverity;
}

export type LineMatchStatus = "exact_alias" | "suggested" | "unmatched";
export type ProductAction = "use_existing" | "create_new";
export type PriceDriftStatus = "normal" | "warning" | "critical";

export interface InvoiceLineItem {
  id: string;
  line_number: number;
  raw_description: string;
  quantity: number;
  unit_name: string;
  unit_price_net: number;
  tax_rate: number;
  total_net: number;

  // Empaque & Desacoplamiento a Stock de Cocina
  packaging_description?: string;
  factor_empaque: number;
  kitchen_base_unit: string;
  total_stock_fisico: number;
  costo_unitario_inventario: number;

  // Matching semántico y resolución de producto
  match_status: LineMatchStatus;
  matched_product_id: string | null;
  matched_product_name: string | null;
  matched_product_sku: string | null;
  suggested_categoria_id: string | null;

  // Decisiones de operador
  product_action: ProductAction;
  nombre_negocio: string;
  categoria_id: string;
  bodega_id: string;
  remember_alias: boolean;

  // Price drift radar por ítem
  ultimo_costo_referencia?: number | null;
  variacion_pct?: number | null;
  drift_status?: PriceDriftStatus;
}

export interface Invoice {
  id: string;
  filename: string;
  file_url: string;
  file_type: "pdf" | "png" | "jpeg" | string;
  vendor_name: string | null;
  vendor_tax_id: string | null;
  vendor_fiscal_address?: string | null;
  vendor_country?: string;
  invoice_number: string | null;
  dte_type: DTEType;
  invoice_date: string | null;
  due_date: string | null;
  net_amount: number;
  tax_amount: number;
  total_amount: number;
  currency: string;
  transaction_type?: string;
  status: InvoiceStatus;
  confidence_score: number;
  audit_flags: InvoiceAuditFlag[];
  gemini_tokens_used: number;
  gemini_cost_usd: number;
  gemini_model_used?: string | null;
  gemini_processing_time_ms?: number | null;
  is_confirmed_to_inventory: boolean;
  confirmed_at?: string | null;
  confirmed_by_user_id?: number | null;
  confirmed_bodega_id?: string | null;
  items: InvoiceLineItem[];
  created_at: string;
  updated_at?: string;
}

export interface SupplierProductAlias {
  id: string;
  supplier_id: string;
  alias_factura_raw: string;
  alias_factura_normalized: string;
  producto_id: string;
  factor_conversion_default: number;
  unidad_base_default: string;
  times_used: number;
  last_used_at: string;
}

export interface InvoiceStats {
  total_invoices: number;
  pending_review: number;
  confirmed_stock: number;
  total_net_clp: number;
  total_tax_clp: number;
  total_amount_clp: number;
  total_tokens_used: number;
  total_cost_usd: number;
  avg_confidence_score: number;
}

export interface PriceDriftItem {
  id: string;
  producto_id: string;
  producto_nombre: string;
  proveedor_nombre: string;
  costo_anterior: number;
  costo_nuevo: number;
  variacion_pct: number;
  fecha: string;
  severidad: "info" | "warning" | "critical";
}

export interface InvoiceWebhook {
  id: string;
  url: string;
  description: string;
  events: string[];
  is_active: boolean;
  last_sent_at?: string | null;
  last_status_code?: number | null;
  last_response_time_ms?: number | null;
  created_at: string;
}

export type ExportFormat =
  | "csv"
  | "excel"
  | "quickbooks"
  | "xero"
  | "odoo"
  | "sii_compras"
  | "sii_ventas";

export interface InvoiceFilters {
  search?: string;
  status?: InvoiceStatus | "ALL";
  dte_type?: DTEType | "ALL";
  vendor_tax_id?: string;
  date_from?: string | null;
  date_to?: string | null;
  area_id?: string;
  page?: number;
  limit?: number;
}

export interface ConfirmStockPayload {
  bodega_id?: string;
  items: Array<{
    item_id: string;
    product_action: ProductAction;
    product_id?: string | null;
    product_name: string;
    categoria_id: string;
    bodega_id: string;
    factor_empaque: number;
    kitchen_base_unit: string;
    total_stock_fisico: number;
    costo_unitario_inventario: number;
    remember_alias: boolean;
  }>;
}

export interface LearnAliasPayload {
  supplier_tax_id: string;
  supplier_name: string;
  alias_factura_raw: string;
  producto_id: string;
  factor_conversion: number;
  unidad_base: string;
}

export interface CategoryOption {
  id: string;
  nombre: string;
  icono?: string;
  color?: string;
}

export interface WarehouseOption {
  id: string;
  nombre: string;
  icono?: string;
  color?: string;
}

export interface ProductCatalogOption {
  id: string;
  nombre: string;
  sku: string;
  categoria_id: string;
  categoria_nombre?: string;
  unidad_inventario: string;
  costo_unitario_ultimo: number;
}
