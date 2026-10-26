// oppytec-frontend/src/features/historial/HistorialToolbar.tsx
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Download } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AreaSelector, BodegaSelector } from "@/shared/components/selectors";

const springTransition = {
  type: "spring" as const,
  stiffness: 350,
  damping: 25,
  mass: 1.2,
};

export interface HistorialToolbarProps {
  readonly selectedAreaId?: string;
  readonly onSelectArea?: (areaId: string) => void;
  readonly activeWarehouseId?: string;
  readonly onSelectWarehouse?: (warehouseId: string) => void;
  readonly onExportCSV?: () => void;
  readonly isExportDisabled?: boolean;
  readonly recordsCount?: number;
}

/**
 * Toolbar unificado de gobernanza para el Módulo de Historial y Auditoría de Kardex.
 * Réplica 1:1 con layoutIds de OppyTec-Legacy y optimizaciones Mobile-First (touch targets >= 44px).
 */
export function HistorialToolbar({
  selectedAreaId = "all",
  onSelectArea,
  activeWarehouseId = "all",
  onSelectWarehouse = () => {},
  onExportCSV,
  isExportDisabled,
  recordsCount,
}: HistorialToolbarProps) {
  const { t } = useTranslation("history");
  const disabled =
    isExportDisabled ?? (recordsCount !== undefined ? recordsCount === 0 : false);

  return (
    <motion.div
      layoutId="app-toolbar-outer-card"
      data-testid="historial-toolbar"
      className="bg-card backdrop-blur-md p-4 rounded-2xl border border-input shadow-xl relative z-50"
    >
      {/* =========================================================================
          DESKTOP VIEW (>= 1024px)
          ========================================================================= */}
      <motion.div
        layoutId="app-toolbar-inner-bar"
        data-testid="historial-toolbar-desktop"
        className="hidden lg:block bg-muted/50 p-2.5 px-6 rounded-2xl border border-input shadow-inner w-full"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center w-full">
          {/* Left Column (4 cols): Selectores de Área y Bodega */}
          <motion.div
            layoutId="app-toolbar-left-selectors"
            className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3 w-full lg:col-span-4"
          >
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={onSelectArea}
              className="w-full sm:w-auto"
              buttonClassName="h-10 rounded-xl bg-background border-input shadow-sm text-[9px] min-w-0 w-full sm:w-auto sm:min-w-[150px]"
            />
            <BodegaSelector
              activeWarehouseId={activeWarehouseId}
              onSelectWarehouse={onSelectWarehouse}
              allowAll
              className="w-full sm:w-auto min-w-[160px] h-10 rounded-xl bg-background border-input shadow-sm text-[9px]"
            />
          </motion.div>

          {/* Center Column (5 cols): Badge Inmutable */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full lg:col-span-5">
            <span
              data-testid="badge-auditoria-inmutable"
              className="inline-flex items-center gap-1.5 rounded-xl bg-background border border-border px-4 py-2 text-[10px] font-black uppercase tracking-widest text-muted-foreground shadow-sm h-10 select-none"
            >
              <Lock className="h-3.5 w-3.5 text-cyan-500 shrink-0" />
              <span>{t("toolbar.badge_immutable")}</span>
            </span>
          </div>

          {/* Right Column (3 cols): Botón Exportar CSV */}
          <div className="flex justify-center lg:justify-end w-full lg:col-span-3">
            <AnimatePresence mode="popLayout">
              <motion.div
                key="hist-export-btn"
                layout
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                transition={springTransition}
              >
                <button
                  type="button"
                  data-testid="export-csv-button"
                  className="h-10 px-6 gap-2 rounded-xl border border-input bg-background hover:bg-secondary font-black text-[9px] uppercase tracking-wider transition-all active:scale-95 shadow-sm shrink-0 w-full lg:w-auto inline-flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none touch-target min-h-[44px]"
                  onClick={onExportCSV}
                  disabled={disabled}
                >
                  <Download className="h-4 w-4 text-cyan-500" />
                  <span>{t("toolbar.export_csv")}</span>
                </button>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </motion.div>

      {/* =========================================================================
          MOBILE VIEW (< 1024px)
          ========================================================================= */}
      <div className="block lg:hidden w-full" data-testid="historial-toolbar-mobile">
        <div className="flex flex-col items-center justify-between gap-4 w-full">
          <div className="grid grid-cols-2 gap-2 w-full max-w-md mx-auto bg-muted/50 p-1.5 rounded-xl border border-input shadow-inner">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={onSelectArea}
              buttonClassName="w-full text-center"
            />
            <BodegaSelector
              activeWarehouseId={activeWarehouseId}
              onSelectWarehouse={onSelectWarehouse}
              allowAll
              className="w-full text-center justify-center"
            />
          </div>
          <div className="flex items-center justify-between gap-2 w-full max-w-md mx-auto">
            <span
              data-testid="badge-inmutable-mobile"
              className="inline-flex items-center gap-1 rounded-xl bg-muted border border-border px-3 py-1 text-[9px] font-bold text-muted-foreground h-10 min-h-[44px]"
            >
              <Lock className="h-3.5 w-3.5 text-cyan-500" /> {t("toolbar.badge_immutable_mobile")}
            </span>
            <button
              type="button"
              data-testid="export-csv-button-mobile"
              className="gap-2 rounded-xl h-10 min-h-[44px] px-4 inline-flex items-center justify-center border border-input bg-background hover:bg-secondary text-[9px] font-black uppercase tracking-wider flex-1 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer touch-target"
              onClick={onExportCSV}
              disabled={disabled}
            >
              <Download className="h-3.5 w-3.5 text-cyan-500" /> {t("toolbar.export_csv")}
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default HistorialToolbar;
