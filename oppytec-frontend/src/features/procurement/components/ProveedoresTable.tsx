/**
 * oppytec-frontend/src/features/procurement/components/ProveedoresTable.tsx
 * Tabla del Directorio de Proveedores con ADN Visual Legacy y Mobile-First.
 * Touch targets >= 44px, badges temáticos cromáticos y acciones directas.
 */

import { BarChart3, Clock, Mail, Pencil, Phone, Tag, Trash2, Building2, AlertCircle } from "lucide-react";
import type { Proveedor } from "../types";

export interface ProveedoresTableProps {
  readonly proveedores: Proveedor[];
  readonly isLoading?: boolean;
  readonly onOpenDashboard: (proveedor: Proveedor) => void;
  readonly onOpenCatalog: (proveedor: Proveedor) => void;
  readonly onEdit: (proveedor: Proveedor) => void;
  readonly onDelete: (proveedor: Proveedor) => void;
}

export function ProveedoresTable({
  proveedores,
  isLoading = false,
  onOpenDashboard,
  onOpenCatalog,
  onEdit,
  onDelete,
}: ProveedoresTableProps) {
  if (isLoading) {
    return (
      <div className="glass-card rounded-2xl border border-border p-6 shadow-sm">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-1/4 rounded bg-muted" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 w-full rounded-xl bg-muted/60" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (proveedores.length === 0) {
    return (
      <div
        data-testid="proveedores-table-empty"
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
      data-testid="proveedores-table-container"
      className="glass-card overflow-hidden rounded-2xl border border-border shadow-sm"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-border/80 bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              <th className="py-3 px-4">RUT / Tax ID</th>
              <th className="py-3 px-4">Razón Social / Comercial</th>
              <th className="py-3 px-4">Contacto</th>
              <th className="py-3 px-4 text-center">Lead Time</th>
              <th className="py-3 px-4 text-center">Estado</th>
              <th className="py-3 px-4 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 font-medium">
            {proveedores.map((prov) => {
              const isActivo = prov.estado === "ACTIVO";
              return (
                <tr
                  key={prov.id}
                  data-testid={`proveedor-row-${prov.id}`}
                  className="transition-colors hover:bg-muted/30"
                >
                  {/* RUT / Tax ID */}
                  <td
                    data-testid={`supplier-card-${prov.id}`}
                    className="py-3.5 px-4 font-mono text-xs text-foreground font-semibold whitespace-nowrap"
                  >
                    {prov.rut_tax_id}
                  </td>

                  {/* Razón Social & Nombre Comercial */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Building2 className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <div
                          data-testid={`proveedor-razon-${prov.id}`}
                          className="font-bold text-foreground truncate text-xs"
                          title={prov.razon_social}
                        >
                          {prov.razon_social}
                        </div>
                        {prov.nombre_fantasia && (
                          <div
                            data-testid={`proveedor-fantasia-${prov.id}`}
                            className="text-[11px] text-muted-foreground truncate"
                            title={prov.nombre_fantasia}
                          >
                            {prov.nombre_fantasia}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Contacto */}
                  <td className="py-3.5 px-4 text-muted-foreground">
                    <div className="space-y-1">
                      {prov.email_contacto && (
                        <div className="flex items-center gap-1.5 truncate max-w-[200px]" title={prov.email_contacto}>
                          <Mail className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                          <span className="truncate">{prov.email_contacto}</span>
                        </div>
                      )}
                      {prov.telefono && (
                        <div className="flex items-center gap-1.5">
                          <Phone className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                          <span>{prov.telefono}</span>
                        </div>
                      )}
                      {!prov.email_contacto && !prov.telefono && (
                        <span className="text-[11px] text-muted-foreground/60 italic">Sin contacto registrado</span>
                      )}
                    </div>
                  </td>

                  {/* Lead Time */}
                  <td className="py-3.5 px-4 text-center">
                    <div className="inline-flex items-center gap-1 rounded-lg bg-muted/60 px-2 py-1 text-xs font-semibold text-foreground">
                      <Clock className="h-3 w-3 text-primary shrink-0" />
                      <span>{prov.lead_time_dias} {prov.lead_time_dias === 1 ? "día" : "días"}</span>
                    </div>
                  </td>

                  {/* Estado */}
                  <td className="py-3.5 px-4 text-center">
                    <span
                      data-testid={`proveedor-status-badge-${prov.id}`}
                      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase ${
                        isActivo
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : "border-zinc-500/30 bg-zinc-500/10 text-zinc-500"
                      }`}
                    >
                      {prov.estado}
                    </span>
                  </td>

                  {/* Acciones */}
                  <td className="py-3.5 px-4 text-right">
                    <div className="inline-flex items-center gap-1 justify-end">
                      {/* Dashboard 360 */}
                      <button
                        type="button"
                        onClick={() => onOpenDashboard(prov)}
                        title="Dashboard 360° del Proveedor"
                        aria-label={`Dashboard 360 de ${prov.razon_social}`}
                        data-testid={`btn-dashboard-${prov.id}`}
                        className="flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary active:scale-95"
                      >
                        <BarChart3 className="h-4 w-4" />
                      </button>

                      {/* Catálogo pactado */}
                      <button
                        type="button"
                        onClick={() => onOpenCatalog(prov)}
                        title="Catálogo pactado de insumos"
                        aria-label={`Catálogo pactado de ${prov.razon_social}`}
                        data-testid={`btn-catalog-${prov.id}`}
                        className="flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 active:scale-95"
                      >
                        <Tag className="h-4 w-4" />
                      </button>

                      {/* Editar */}
                      <button
                        type="button"
                        onClick={() => onEdit(prov)}
                        title="Editar datos de proveedor"
                        aria-label={`Editar ${prov.razon_social}`}
                        data-testid={`btn-edit-${prov.id}`}
                        className="flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-amber-500/10 hover:text-amber-600 dark:hover:text-amber-400 active:scale-95"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>

                      {/* Eliminar / Desactivar */}
                      <button
                        type="button"
                        onClick={() => onDelete(prov)}
                        title="Eliminar o desactivar proveedor"
                        aria-label={`Eliminar ${prov.razon_social}`}
                        data-testid={`btn-delete-${prov.id}`}
                        className="flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-rose-500/10 hover:text-rose-600 dark:hover:text-rose-400 active:scale-95"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
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
