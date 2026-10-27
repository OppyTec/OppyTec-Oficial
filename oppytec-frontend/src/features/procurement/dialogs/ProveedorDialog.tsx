/**
 * oppytec-frontend/src/features/procurement/dialogs/ProveedorDialog.tsx
 * Modal de Creación y Edición de Proveedor con ResponsiveDialog.
 * Validación de RUT/Tax ID, plazo de entrega (lead time) y estado operativo.
 */

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type {
  CreateProveedorPayload,
  Proveedor,
  ProveedorEstado,
  UpdateProveedorPayload,
} from "../types";

export interface ProveedorDialogProps {
  readonly open: boolean;
  readonly proveedor: Proveedor | null;
  readonly onClose: () => void;
  readonly onSave: (
    payload: CreateProveedorPayload | UpdateProveedorPayload,
    id?: number
  ) => Promise<void> | void;
  readonly isSubmitting?: boolean;
}

export function ProveedorDialog({
  open,
  proveedor,
  onClose,
  onSave,
  isSubmitting = false,
}: ProveedorDialogProps) {
  const isMobile = useIsMobile();
  const isEditing = Boolean(proveedor);

  const [rutTaxId, setRutTaxId] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [nombreFantasia, setNombreFantasia] = useState("");
  const [emailContacto, setEmailContacto] = useState("");
  const [telefono, setTelefono] = useState("");
  const [direccion, setDireccion] = useState("");
  const [leadTimeDias, setLeadTimeDias] = useState<number>(2);
  const [estado, setEstado] = useState<ProveedorEstado>("ACTIVO");
  const [notas, setNotas] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Inicializar formulario al abrir o cambiar de proveedor
  useEffect(() => {
    if (proveedor) {
      setRutTaxId(proveedor.rut_tax_id || "");
      setRazonSocial(proveedor.razon_social || "");
      setNombreFantasia(proveedor.nombre_fantasia || "");
      setEmailContacto(proveedor.email_contacto || "");
      setTelefono(proveedor.telefono || "");
      setDireccion(proveedor.direccion || "");
      setLeadTimeDias(proveedor.lead_time_dias ?? 2);
      setEstado(proveedor.estado || "ACTIVO");
      setNotas(proveedor.notas || "");
    } else {
      setRutTaxId("");
      setRazonSocial("");
      setNombreFantasia("");
      setEmailContacto("");
      setTelefono("");
      setDireccion("");
      setLeadTimeDias(2);
      setEstado("ACTIVO");
      setNotas("");
    }
    setErrorMessage(null);
  }, [proveedor, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedRut = rutTaxId.trim();
    const trimmedRazon = razonSocial.trim();

    if (!isEditing && !trimmedRut) {
      setErrorMessage("El RUT o Tax ID es obligatorio.");
      return;
    }

    if (!trimmedRazon) {
      setErrorMessage("La Razón Social es obligatoria.");
      return;
    }

    if (leadTimeDias < 0) {
      setErrorMessage("El plazo de entrega (lead time) no puede ser negativo.");
      return;
    }

    try {
      if (isEditing && proveedor) {
        const payload: UpdateProveedorPayload = {
          razon_social: trimmedRazon,
          nombre_fantasia: nombreFantasia.trim() || null,
          email_contacto: emailContacto.trim() || null,
          telefono: telefono.trim() || null,
          direccion: direccion.trim() || null,
          lead_time_dias: Number(leadTimeDias),
          estado,
          notas: notas.trim() || null,
        };
        await onSave(payload, proveedor.id);
      } else {
        const payload: CreateProveedorPayload = {
          rut_tax_id: trimmedRut,
          razon_social: trimmedRazon,
          nombre_fantasia: nombreFantasia.trim() || null,
          email_contacto: emailContacto.trim() || null,
          telefono: telefono.trim() || null,
          direccion: direccion.trim() || null,
          lead_time_dias: Number(leadTimeDias),
          estado,
          notas: notas.trim() || null,
        };
        await onSave(payload);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al procesar el proveedor.";
      setErrorMessage(msg);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      isMobile={isMobile}
      maxWidth="max-w-2xl"
      title={isEditing ? `Editar Proveedor: ${proveedor?.razon_social}` : "Nuevo Proveedor"}
      description={
        isEditing
          ? "Modifica los datos comerciales, tiempos de entrega o estado operativo."
          : "Registra una nueva alianza comercial o distribuidor en el sistema."
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-2">
        {errorMessage && (
          <div
            data-testid="proveedor-dialog-error"
            className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400 font-medium"
          >
            {errorMessage}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
          {/* RUT / Tax ID */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              RUT / Tax ID <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              name="rut_tax_id"
              data-testid="input-rut-tax-id"
              value={rutTaxId}
              onChange={(e) => setRutTaxId(e.target.value)}
              disabled={isEditing}
              placeholder="76.321.400-8"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60 disabled:bg-muted/40"
              required={!isEditing}
            />
          </div>

          {/* Razón Social */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Razón Social <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              name="razon_social"
              data-testid="input-razon-social"
              value={razonSocial}
              onChange={(e) => setRazonSocial(e.target.value)}
              placeholder="Distribuidora de Alimentos SpA"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>

          {/* Nombre de Fantasía */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Nombre de Fantasía / Comercial
            </label>
            <input
              type="text"
              name="nombre_fantasia"
              data-testid="input-nombre-fantasia"
              value={nombreFantasia}
              onChange={(e) => setNombreFantasia(e.target.value)}
              placeholder="Alimentos Central"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Estado */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Estado Operativo
            </label>
            <select
              name="estado"
              data-testid="select-estado"
              value={estado}
              onChange={(e) => setEstado(e.target.value as ProveedorEstado)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="ACTIVO">ACTIVO (Habilitado para compras)</option>
              <option value="INACTIVO">INACTIVO (Suspendido)</option>
            </select>
          </div>

          {/* Email de Contacto */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Email de Contacto
            </label>
            <input
              type="email"
              name="email_contacto"
              data-testid="input-email-contacto"
              value={emailContacto}
              onChange={(e) => setEmailContacto(e.target.value)}
              placeholder="contacto@proveedor.cl"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Teléfono */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Teléfono Comercial
            </label>
            <input
              type="tel"
              name="telefono"
              data-testid="input-telefono"
              value={telefono}
              onChange={(e) => setTelefono(e.target.value)}
              placeholder="+56 9 1234 5678"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Lead Time (Plazo de Entrega en Días) */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Plazo de Entrega (Días hábiles)
            </label>
            <input
              type="number"
              name="lead_time_dias"
              data-testid="input-lead-time"
              min="0"
              max="90"
              value={leadTimeDias}
              onChange={(e) => setLeadTimeDias(Number(e.target.value))}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Dirección */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-foreground">
              Dirección Comercial / Despacho
            </label>
            <input
              type="text"
              name="direccion"
              data-testid="input-direccion"
              value={direccion}
              onChange={(e) => setDireccion(e.target.value)}
              placeholder="Av. Industrial 1234, Módulo B"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Notas u Observaciones */}
        <div>
          <label className="mb-1 block text-xs font-semibold text-foreground">
            Notas u Observaciones Comerciales
          </label>
          <textarea
            name="notas"
            data-testid="textarea-notas"
            rows={2}
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            placeholder="Condiciones de pago a 30 días, entregas lunes y jueves..."
            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
          />
        </div>

        {/* Botones de acción */}
        <div className="mt-2 flex items-center justify-end gap-2 border-t border-border/70 pt-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="min-h-[44px] rounded-xl border border-border px-4 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            data-testid="btn-submit-proveedor"
            className="min-h-[44px] flex items-center gap-2 rounded-xl bg-primary px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            <span>{isSubmitting ? "Guardando..." : isEditing ? "Actualizar Proveedor" : "Registrar Proveedor"}</span>
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
