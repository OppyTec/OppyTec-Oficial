import { formatScaledDecimal, parseScaledDecimal } from "@/shared/currency";

export interface NumericInputProps {
  readonly label: string;
  readonly value: string;
  readonly onChange: (nextValue: string) => void;
  readonly step?: string;
  readonly unitLabel?: string;
  readonly decimals?: number;
  readonly testId?: string;
}

/**
 * Touch-ergonomic numeric input (`>= 44x44px` buttons, `inputMode="decimal"`, exact BigInt step).
 */
export function NumericInput({
  label,
  value,
  onChange,
  step = "1",
  unitLabel,
  decimals = 2,
  testId = "numeric-input",
}: NumericInputProps) {
  const handleStep = (direction: 1n | -1n): void => {
    try {
      const currentScaled = parseScaledDecimal(value || "0");
      const stepScaled = parseScaledDecimal(step);
      const nextScaled = currentScaled + direction * stepScaled;
      const clamped = nextScaled < 0n ? 0n : nextScaled;
      onChange(formatScaledDecimal(clamped, decimals));
    } catch {
      onChange("0");
    }
  };

  return (
    <div data-testid={testId} className="flex flex-col gap-1">
      <label className="text-xs font-medium text-muted-foreground">
        {label}
        {unitLabel ? ` (${unitLabel})` : ""}
      </label>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-label={`${label} -`}
          data-testid={`${testId}-decrement`}
          onClick={() => handleStep(-1n)}
          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-border bg-secondary font-mono text-sm font-bold text-secondary-foreground"
        >
          -
        </button>
        <input
          type="text"
          inputMode="decimal"
          aria-label={label}
          data-testid={`${testId}-field`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="touch-target min-h-[44px] w-28 rounded-md border border-border bg-card px-3 text-center font-mono text-sm font-semibold text-foreground"
        />
        <button
          type="button"
          aria-label={`${label} +`}
          data-testid={`${testId}-increment`}
          onClick={() => handleStep(1n)}
          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-border bg-secondary font-mono text-sm font-bold text-secondary-foreground"
        >
          +
        </button>
      </div>
    </div>
  );
}
