// oppytec-frontend/src/features/consumo/components/BotonesFlotantes.tsx
import { ShoppingCart, History } from "lucide-react";
import { cn } from "@/shared/lib/utils";

export interface BotonesFlotantesProps {
  readonly cartCount: number;
  readonly onOpenCart: () => void;
  readonly onOpenLog: () => void;
  readonly className?: string;
}

export function BotonesFlotantes({
  cartCount,
  onOpenCart,
  onOpenLog,
  className,
}: BotonesFlotantesProps) {
  return (
    <div
      data-testid="floating-buttons-container"
      className={cn(
        "fixed bottom-6 right-6 z-40 flex items-center gap-3 pointer-events-auto select-none",
        className
      )}
    >
      {/* Botón Flotante de Historial (Cian #06b6d4) */}
      <button
        type="button"
        data-testid="floating-history-btn"
        onClick={onOpenLog}
        className="flex items-center justify-center h-12 w-12 rounded-2xl bg-[#06b6d4] text-white shadow-lg shadow-[#06b6d4]/30 hover:bg-[#0891b2] hover:scale-105 active:scale-95 transition-all cursor-pointer border border-[#06b6d4]/40 backdrop-blur-md"
        title="Historial de consumos"
        aria-label="Abrir historial de consumos"
      >
        <History className="h-6 w-6" />
      </button>

      {/* Botón Flotante de Carrito con Badge Dinámico */}
      <button
        type="button"
        data-testid="floating-cart-btn"
        onClick={onOpenCart}
        className={cn(
          "relative flex items-center gap-2.5 h-12 px-4 rounded-2xl bg-yellow-500 text-black font-black uppercase text-xs tracking-wider shadow-xl shadow-yellow-500/25 hover:bg-yellow-400 hover:scale-105 active:scale-95 transition-all cursor-pointer border border-yellow-400",
          cartCount > 0 ? "scale-100" : "scale-95 opacity-90"
        )}
        title="Ver carrito de consumo"
        aria-label={`Ver carrito (${cartCount} ítems)`}
      >
        <div className="relative">
          <ShoppingCart className="h-5 w-5" />
          {cartCount > 0 && (
            <span
              data-testid="floating-cart-badge"
              className="absolute -top-2.5 -right-2.5 flex h-5 min-w-[20px] px-1 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-[10px] font-black shadow-md border-2 border-background animate-pulse"
            >
              {cartCount > 99 ? "99+" : cartCount}
            </span>
          )}
        </div>
        <span className="hidden sm:inline">Carrito</span>
      </button>
    </div>
  );
}

export default BotonesFlotantes;
