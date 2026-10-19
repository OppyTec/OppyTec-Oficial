import { useState } from "react";
import { NumericInput } from "@/shared/components/ui/NumericInput";
import {
  formatScaledDecimal,
  MoneyBadge,
  parseScaledDecimal,
} from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

export function RecipesFeatureView() {
  const [yieldPct, setYieldPct] = useState<string>("85.00");
  const [targetSalePriceClp, setTargetSalePriceClp] = useState<string>("12900");
  const baseRecipeCostClp = "3870";

  // Exact BigInt margin calculation
  const saleScaled = parseScaledDecimal(targetSalePriceClp || "12900");
  const costScaled = parseScaledDecimal(baseRecipeCostClp);
  const marginClp = formatScaledDecimal(
    saleScaled > costScaled ? saleScaled - costScaled : 0n,
    0
  );

  return (
    <section
      data-testid="feature-recipes"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("recipes", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("recipes", "bom.recursion_depth", {
              depth: 3,
              maxDepth: 5,
            })}
          </p>
        </div>
        <span className="rounded-lg bg-primary/15 px-3 py-1 font-mono text-xs font-bold text-primary">
          {translateKey("recipes", "costing.food_cost", { foodCostPct: "30.0" })}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid="recipes-escandallo-tree"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            {translateKey("recipes", "bom.ingredients_header", { count: 4 })}
          </h3>
          <ul className="space-y-1.5 text-xs">
            <li className="flex items-center justify-between rounded-md bg-card p-2">
              <span>L1: Pollo King Marinado (Receta Padre)</span>
              <MoneyBadge amount="2150" baseCurrency="CLP" showSource={false} />
            </li>
            <li className="flex items-center justify-between rounded-md bg-card p-2">
              <span>L2: Salsa Reducción Austral (Sub-Receta)</span>
              <MoneyBadge amount="1120" baseCurrency="CLP" showSource={false} />
            </li>
            <li className="flex items-center justify-between rounded-md bg-card p-2">
              <span>L3: Fondo Oscuro Concentrado (Base)</span>
              <MoneyBadge amount="600" baseCurrency="CLP" showSource={false} />
            </li>
          </ul>
        </div>

        <div
          data-testid="recipes-margin-simulator"
          className="space-y-3 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            Simulador de Precio, Rendimiento & Combos
          </h3>
          <div className="flex flex-wrap gap-3">
            <NumericInput
              label={translateKey("recipes", "costing.yield_factor", {
                yieldPct,
              })}
              value={yieldPct}
              onChange={setYieldPct}
              step="1.00"
              unitLabel="%"
              testId="recipes-yield-input"
            />
            <NumericInput
              label="Precio Carta (CLP)"
              value={targetSalePriceClp}
              onChange={setTargetSalePriceClp}
              step="500"
              decimals={0}
              testId="recipes-price-input"
            />
          </div>
          <div className="flex items-center justify-between border-t border-border pt-2 text-xs">
            <span>
              {translateKey("recipes", "costing.margin_contribution", {
                margin: marginClp,
              })}
            </span>
            <MoneyBadge amount={marginClp} baseCurrency="CLP" />
          </div>
        </div>
      </div>
    </section>
  );
}
