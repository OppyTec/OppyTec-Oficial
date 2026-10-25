// oppytec-frontend/src/features/gestion/components/FacturaImportModal/FacturaSupplierBanner.tsx
import React from "react";
import { useTranslation } from "react-i18next";
import { Building2, FileText, UserPlus, CheckCircle2, Calendar, DollarSign } from "lucide-react";
import { cn } from "@/shared/lib/utils";

export interface FacturaSupplierInfo {
  readonly rut: string;
  readonly razonSocial: string;
  readonly giro?: string;
  readonly direccion?: string;
  readonly folio: string;
  readonly fechaEmision: string;
  readonly montoNeto: number;
  readonly montoIva: number;
  readonly montoTotal: number;
}

export interface FacturaSupplierBannerProps {
  readonly supplier: FacturaSupplierInfo;
  readonly isNewSupplier?: boolean;
  readonly onRegisterSupplier?: (supplier: FacturaSupplierInfo) => void;
  readonly className?: string;
}

export const FacturaSupplierBanner: React.FC<FacturaSupplierBannerProps> = ({
  supplier,
  isNewSupplier = false,
  onRegisterSupplier,
  className,
}) => {
  const { t } = useTranslation(["factura_import"]);

  return (
    <div
      data-testid="factura-supplier-banner"
      className={cn(
        "p-4 rounded-2xl border transition-all space-y-3",
        isNewSupplier
          ? "bg-amber-500/10 border-amber-500/30 text-foreground"
          : "bg-card border-border shadow-xs",
        className
      )}
    >
      {/* Top row: Supplier details and folio */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "h-10 w-10 rounded-xl flex items-center justify-center shrink-0 shadow-xs",
              isNewSupplier
                ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                : "bg-primary/10 text-primary"
            )}
          >
            <Building2 className="h-5 w-5" />
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-black text-foreground">
                {supplier.razonSocial || t("supplier.unknown_supplier", "Proveedor Desconocido")}
              </h4>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground border border-border">
                {t("supplier.rut", { rut: supplier.rut, defaultValue: `RUT: ${supplier.rut}` })}
              </span>
              {isNewSupplier ? (
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                  {t("supplier.new_supplier_badge", "Nuevo Proveedor")}
                </span>
              ) : (
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  {t("supplier.registered_badge", "Registrado")}
                </span>
              )}
            </div>

            {supplier.giro && (
              <p className="text-[11px] text-muted-foreground mt-0.5">{supplier.giro}</p>
            )}
          </div>
        </div>

        {/* Quick register action if new */}
        {isNewSupplier && onRegisterSupplier && (
          <button
            type="button"
            onClick={() => onRegisterSupplier(supplier)}
            data-testid="btn-register-supplier"
            className="touch-target inline-flex min-h-[40px] px-3.5 items-center gap-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold uppercase tracking-wider shadow-sm cursor-pointer select-none shrink-0"
          >
            <UserPlus className="h-4 w-4" />
            <span>{t("supplier.quick_register_btn", "Dar de Alta Rápido")}</span>
          </button>
        )}
      </div>

      {/* Bottom row: Document meta & amounts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-border/60 text-xs">
        <div className="flex items-center gap-2 p-2 rounded-lg bg-secondary/30">
          <FileText className="h-4 w-4 text-primary shrink-0" />
          <div>
            <span className="text-[10px] font-bold uppercase text-muted-foreground block">
              {t("supplier.doc_label", "Documento")}
            </span>
            <strong className="text-foreground">
              {t("supplier.folio", { folio: supplier.folio, defaultValue: `Factura N° ${supplier.folio}` })}
            </strong>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-lg bg-secondary/30">
          <Calendar className="h-4 w-4 text-primary shrink-0" />
          <div>
            <span className="text-[10px] font-bold uppercase text-muted-foreground block">
              {t("supplier.emission_label", "Emisión")}
            </span>
            <strong className="text-foreground">
              {supplier.fechaEmision || t("supplier.today", "Hoy")}
            </strong>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-lg bg-secondary/30">
          <DollarSign className="h-4 w-4 text-muted-foreground shrink-0" />
          <div>
            <span className="text-[10px] font-bold uppercase text-muted-foreground block">
              {t("supplier.net_amount", "Monto Neto")}
            </span>
            <strong className="text-foreground font-mono">
              ${supplier.montoNeto.toLocaleString("es-CL")}
            </strong>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <div>
            <span className="text-[10px] font-bold uppercase text-emerald-700 dark:text-emerald-400 block">
              {t("supplier.total_amount", "Total Factura")}
            </span>
            <strong className="text-emerald-600 dark:text-emerald-400 font-mono text-sm">
              ${supplier.montoTotal.toLocaleString("es-CL")}
            </strong>
          </div>
        </div>
      </div>
    </div>
  );
};
