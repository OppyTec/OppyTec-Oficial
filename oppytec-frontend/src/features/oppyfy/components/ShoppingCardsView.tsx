import { ExternalLink, ShoppingBag, Store, Tag } from "lucide-react";
import { formatCurrencyAmount } from "@/shared/currency/useCurrencyFormatter";

export interface ShoppingProduct {
  title: string;
  price_clp: number;
  price_display?: string;
  vendor: string;
  product_url: string;
  image_url: string;
  unit?: string;
}

export interface ShoppingCardsViewProps {
  readonly products?: readonly ShoppingProduct[];
}

export function ShoppingCardsView({ products }: ShoppingCardsViewProps) {
  if (!products || products.length === 0) return null;

  return (
    <div data-testid="shopping-cards-view" className="my-3 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        <ShoppingBag className="w-3.5 h-3.5 text-primary" />
        <span>Cotizaciones Encontradas en Internet</span>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2 pt-1">
        {products.map((product, idx) => {
          const displayPrice =
            product.price_display ||
            formatCurrencyAmount(product.price_clp, "CLP");

          return (
            <div
              key={`${product.title}-${idx}`}
              data-testid={`shopping-product-card-${idx}`}
              className="flex-shrink-0 w-48 rounded-xl border border-border bg-card/90 hover:bg-card hover:border-primary/40 transition-all duration-200 shadow-sm hover:shadow-md flex flex-col overflow-hidden group text-foreground"
            >
              {/* Imagen del producto */}
              <div className="relative w-full h-28 bg-white/90 flex items-center justify-center p-2 overflow-hidden border-b border-border/50">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.title}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src =
                        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&auto=format&fit=crop&q=80";
                    }}
                  />
                ) : (
                  <Tag className="w-8 h-8 text-muted-foreground/40" />
                )}
              </div>

              {/* Datos del producto */}
              <div className="p-3 flex-1 flex flex-col justify-between space-y-2">
                <div>
                  <h4
                    className="text-xs font-medium text-foreground line-clamp-2 leading-tight"
                    title={product.title}
                  >
                    {product.title}
                  </h4>

                  <p className="text-sm font-bold text-emerald-500 mt-1 font-mono">
                    {displayPrice}
                  </p>
                </div>

                <div className="pt-1.5 border-t border-border/40 flex items-center justify-between text-[11px] text-muted-foreground">
                  <span
                    className="flex items-center gap-1 truncate font-medium max-w-[110px]"
                    title={product.vendor}
                  >
                    <Store className="w-3 h-3 text-muted-foreground/70 shrink-0" />
                    <span className="truncate">{product.vendor}</span>
                  </span>

                  <a
                    href={product.product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded-md text-primary hover:text-primary-foreground hover:bg-primary transition-colors cursor-pointer"
                    title="Abrir cotización en nueva pestaña"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ShoppingCardsView;
