/**
 * oppytec-frontend/src/features/invoices/components/PipelineTab.tsx
 * Pestaña Pipeline: Configuración de Webhooks Salientes y Trazas de Integración con ERPs.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Webhook,
  Plus,
  Trash2,
  Send,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useInvoiceWebhooks } from "../useInvoices";

export function PipelineTab() {
  const { t } = useTranslation(["invoices"]);
  const {
    webhooks,
    isLoading,
    createWebhook,
    isCreating,
    deleteWebhook,
    isDeleting,
    pingWebhook,
    isPinging,
  } = useInvoiceWebhooks();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([
    "invoice.stock_confirmed",
    "invoice.analyzed",
  ]);

  const handleCreate = async () => {
    if (!newUrl) return;
    try {
      await createWebhook({
        url: newUrl,
        description: newDescription || "Webhook ERP",
        events: selectedEvents,
      });
      setIsModalOpen(false);
      setNewUrl("");
      setNewDescription("");
    } catch {
      // Handled by hook
    }
  };

  const AVAILABLE_EVENTS = [
    {
      id: "invoice.analyzed",
      label: t("invoices:pipeline.ev_analyzed", "Factura Analizada por IA (OCR Exitoso)"),
    },
    {
      id: "invoice.stock_confirmed",
      label: t("invoices:pipeline.ev_stock_confirmed", "Stock Ingresado a Bodega (Kardex FEFO)"),
    },
    {
      id: "invoice.price_drift_alert",
      label: t("invoices:pipeline.ev_price_drift", "Alerta Crítica de Variación de Precio"),
    },
    {
      id: "invoices.changed",
      label: t("invoices:pipeline.ev_invoices_changed", "Cualquier Cambio en Facturas"),
    },
  ];

  return (
    <div data-testid="pipeline-tab" className="space-y-6">
      {/* Encabezado del Pipeline */}
      <div className="glass-card rounded-2xl border border-border p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Webhook className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold text-foreground">
              {t("invoices:pipeline.header_title", "Webhooks Salientes & ERP Pipeline")}
            </h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {t(
              "invoices:pipeline.header_desc",
              "Transmite eventos de facturas validadas e ingresos de stock a sistemas contables externos (SAP, Odoo, QuickBooks)."
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20 transition-all shrink-0"
        >
          <Plus className="h-4 w-4" />
          {t("invoices:pipeline.new_webhook", "Nuevo Webhook")}
        </button>
      </div>

      {/* Lista de Webhooks */}
      {isLoading ? (
        <div className="glass-card rounded-2xl border border-border p-6 shadow-sm animate-pulse space-y-3">
          <div className="h-16 rounded-xl bg-muted/60" />
          <div className="h-16 rounded-xl bg-muted/60" />
        </div>
      ) : webhooks.length === 0 ? (
        <div className="glass-card rounded-2xl border border-dashed border-border p-8 text-center">
          <Webhook className="h-10 w-10 text-muted-foreground mx-auto mb-2 opacity-50" />
          <h4 className="text-sm font-bold text-foreground">
            {t("invoices:pipeline.empty_title", "No hay webhooks configurados")}
          </h4>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            {t(
              "invoices:pipeline.empty_desc",
              "Registra un endpoint HTTP POST para recibir notificaciones automáticas cuando se confirme stock o se procesen facturas."
            )}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {webhooks.map((hook) => (
            <div
              key={hook.id}
              className="glass-card rounded-2xl border border-border p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-primary/40 transition-colors"
            >
              <div className="space-y-1 truncate pr-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-foreground text-sm">{hook.description}</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    {t("invoices:pipeline.active", "Activo")}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground font-mono truncate max-w-md">
                  {hook.url}
                </div>
                <div className="flex items-center gap-1.5 flex-wrap pt-1">
                  {hook.events.map((ev) => (
                    <span
                      key={ev}
                      className="px-2 py-0.5 rounded-md text-[10px] bg-muted text-muted-foreground font-mono"
                    >
                      {ev}
                    </span>
                  ))}
                </div>
              </div>

              {/* Métricas de entrega & Acciones */}
              <div className="flex items-center gap-3 shrink-0 self-end sm:self-auto">
                {hook.last_sent_at && (
                  <div className="text-right text-[11px] text-muted-foreground font-mono hidden md:block">
                    <div>
                      HTTP {hook.last_status_code} ({hook.last_response_time_ms} ms)
                    </div>
                    <div className="text-[10px] opacity-75">{hook.last_sent_at}</div>
                  </div>
                )}

                <button
                  type="button"
                  disabled={isPinging}
                  onClick={() => pingWebhook(hook.id)}
                  title={t("invoices:pipeline.test_ping", "Test Ping")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl border border-border hover:bg-muted text-foreground transition-colors disabled:opacity-50"
                >
                  <Send className="h-3.5 w-3.5 text-primary" />
                  {t("invoices:pipeline.test_ping", "Test Ping")}
                </button>

                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={() => {
                    if (confirm(t("invoices:pipeline.delete_confirm", "¿Eliminar este webhook?"))) {
                      void deleteWebhook(hook.id);
                    }
                  }}
                  title={t("invoices:pipeline.delete_webhook", "Eliminar Webhook")}
                  className="p-2 rounded-xl hover:bg-rose-500/10 text-muted-foreground hover:text-rose-500 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Crear Webhook */}
      <ResponsiveDialog
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={t("invoices:pipeline.modal_title", "Registrar Nuevo Webhook Saliente")}
        description={t(
          "invoices:pipeline.modal_desc",
          "Ingresa el endpoint seguro HTTPS al que enviaremos las notificaciones de facturas en formato JSON."
        )}
        className="max-w-md"
      >
        <div className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              {t("invoices:pipeline.name_label", "Nombre / Descripción del Servicio")}
            </label>
            <input
              type="text"
              placeholder={t("invoices:pipeline.name_placeholder", "Ej: ERP Contable Odoo Prod")}
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              {t("invoices:pipeline.url_label", "URL Endpoint de Destino (HTTPS)")}
            </label>
            <input
              type="url"
              placeholder="https://api.empresa.cl/webhooks/facturas"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-2">
              {t("invoices:pipeline.events_label", "Eventos a los que suscribirse")}
            </label>
            <div className="space-y-2">
              {AVAILABLE_EVENTS.map((ev) => (
                <label
                  key={ev.id}
                  className="flex items-center gap-2 p-2 rounded-xl border border-border/70 hover:bg-muted/40 cursor-pointer text-xs"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(ev.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedEvents((prev) => [...prev, ev.id]);
                      } else {
                        setSelectedEvents((prev) => prev.filter((id) => id !== ev.id));
                      }
                    }}
                    className="h-4 w-4 rounded text-primary focus:ring-primary border-border cursor-pointer"
                  />
                  <span className="font-medium text-foreground">{ev.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-border hover:bg-muted text-muted-foreground"
            >
              {t("invoices:pipeline.cancel", "Cancelar")}
            </button>
            <button
              type="button"
              disabled={isCreating || !newUrl}
              onClick={handleCreate}
              className="px-5 py-2 text-xs font-bold rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20 disabled:opacity-50"
            >
              {isCreating
                ? t("invoices:pipeline.saving_webhook", "Guardando...")
                : t("invoices:pipeline.create_webhook", "Crear Webhook")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}
