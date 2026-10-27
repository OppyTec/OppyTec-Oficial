/**
 * oppytec-frontend/src/features/procurement/components/ProveedoresCards.tsx
 * Vista Alternativa Mobile-First en Tarjetas Táctiles para Directorio de Proveedores.
 * ADN Visual Legacy y touch targets >= 44px garantizados.
 */

import { BarChart3, Clock, Mail, Pencil, Phone, Tag, Trash2, Building2, MapPin, AlertCircle } from "lucide-react";
import type { Proveedor } from "../types";

export interface ProveedoresCardsProps {
  readonly proveedores: Proveedor[];
  readonly isLoading?: boolean;
  readonly onOpenDashboard: (proveedor: Proveedor) => void;
  readonly onOpenCatalog: (proveedor: Proveedor) => void;
  readonly onEdit: (proveedor: Proveedor) => void;
  readonly onDelete: (proveedor: Proveedor) => void;
}

export function ProveedoresCards({
  proveedores,
  isLoading = false,
  onOpenDashboard,
  onOpenCatalog,
  onEdit,
  onDelete,
}: ProveedoresCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((idx) => (
          <div
            key={idx}
            className="glass-card flex min-h-[220px] animate-pulse flex-col justify-between rounded-2xl border border-border p-4 shadow-sm"
          >
            <div className="space-y-3">
              <div className="h-5 w-2/3 rounded bg-muted" />
              <div className="h-3 w-1/3 rounded bg-muted" />
              <div className="h-4 w-1/2 rounded bg-muted" />
            </div>
            <div className="h-10 w-full rounded-xl bg-muted/60" />
          </div>
        ))}
      </div>
    );
  }

  if (proveedores.length === 0) {
    return (
      <div
        data-testid="proveedores-cards-empty"
        className="glass-card flex min-h-[260px] flex-col items-center justify-center rounded-2xl border border-dashed border-border p-8 text-center"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h4 className="mt-3 text-sm font-bold text-foreground">
          No se encontraron proveedores
        </h4>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          No hay registros que coincidan con los filtros aplicados o aún no se han registrado proveedores.
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="proveedores-cards-container"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {proveedores.map((prov) => {
        const isActivo = prov.estado === "ACTIVO";
        return (
          <div
            key={prov.id}
            data-testid={`proveedor-card-${prov.id}`}
            className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
          >
            <div>
              {/* Encabezado de la tarjeta */}
              <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3">
                <div className="flex items-start gap-2.5 min-w-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h4
                      data-testid={`card-razon-${prov.id}`}
                      className="font-bold text-foreground text-sm truncate"
                      title={prov.razon_social}
                    >
                      {prov.razon_social}
                    </h4>
                    {prov.nombre_fantasia && (
                      <p
                        data-testid={`card-fantasia-${prov.id}`}
                        className="text-xs text-muted-foreground truncate"
                        title={prov.nombre_fantasia}
                      >
                        {prov.nombre_fantasia}
                      </p>
                    )}
                    <p className="mt-0.5 font-mono text-[11px] font-semibold text-muted-foreground">
                      {prov.rut_tax_id}
                    </p>
                  </div>
                </div>

                {/* Badge de estado */}
                <span
                  data-testid={`card-status-badge-${prov.id}`}
                  className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase ${
                    isActivo
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : "border-zinc-500/30 bg-zinc-500/10 text-zinc-500"
                  }`}
                >
                  {prov.estado}
                </span>
              </div>

              {/* Información y contacto */}
              <div className="my-3 space-y-2 text-xs text-muted-foreground">
                {prov.email_contacto && (
                  <div className="flex items-center gap-2 truncate">
                    <Mail className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                    <span className="truncate">{prov.email_contacto}</span>
                  </div>
                )}
                {prov.telefono && (
                  <div className="flex items-center gap-2">
                    <Phone className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                    <span>{prov.telefono}</span>
                  </div>
                )}
                {prov.direccion && (
                  <div className="flex items-center gap-2 truncate">
                    <MapPin className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                    <span className="truncate">{prov.direccion}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 pt-1 border-t border-border/40 text-foreground font-medium">
                  <Clock className="h-3.5 w-3.5 shrink-0 text-primary" />
                  <span>
                    Lead Time: <strong>{prov.lead_time_dias} {prov.lead_time_dias === 1 ? "día" : "días"}</strong>
                  </span>
                </div>
              </div>
            </div>

            {/* Barra de acciones (touch targets >= 44px) */}
            <div className="grid grid-cols-4 gap-1.5 border-t border-border/70 pt-3">
              <button
                type="button"
                onClick={() => onOpenDashboard(prov)}
                title="Dashboard 360°"
                aria-label={`Dashboard 360 de ${prov.razon_social}`}
                data-testid={`card-btn-dashboard-${prov.id}`}
                className="flex h-11 w-full items-center justify-center rounded-xl bg-muted/40 text-muted-foreground transition-all hover:bg-primary/10 hover:text-primary active:scale-95"
              >
                <BarChart3 className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={() => onOpenCatalog(prov)}
                title="Catálogo pactado"
                aria-label={`Catálogo pactado de ${prov.razon_social}`}
                data-testid={`card-btn-catalog-${prov.id}`}
                className="flex h-11 w-full items-center justify-center rounded-xl bg-muted/40 text-muted-foreground transition-all hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 active:scale-95"
              >
                <Tag className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={() => onEdit(prov)}
                title="Editar proveedor"
                aria-label={`Editar ${prov.razon_social}`}
                data-testid={`card-btn-edit-${prov.id}`}
                className="flex h-11 w-full items-center justify-center rounded-xl bg-muted/40 text-muted-foreground transition-all hover:bg-amber-500/10 hover:text-amber-600 dark:hover:text-amber-400 active:scale-95"
              >
                <Pencil className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={() => onDelete(prov)}
                title="Eliminar proveedor"
                aria-label={`Eliminar ${prov.razon_social}`}
                data-testid={`card-btn-delete-${prov.id}`}
                className="flex h-11 w-full items-center justify-center rounded-xl bg-muted/40 text-muted-foreground transition-all hover:bg-rose-500/10 hover:text-rose-600 dark:hover:text-rose-400 active:scale-95"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
