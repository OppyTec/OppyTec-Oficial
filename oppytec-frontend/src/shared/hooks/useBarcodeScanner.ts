import { useCallback, useState } from "react";

export interface BarcodeScannerState {
  readonly lastScannedCode: string;
  readonly scannerActive: boolean;
  readonly simulateScan: (code: string) => void;
  readonly toggleScanner: () => void;
}

export function useBarcodeScanner(
  initialCode = "7801234567890"
): BarcodeScannerState {
  const [lastScannedCode, setLastScannedCode] = useState<string>(initialCode);
  const [scannerActive, setScannerActive] = useState<boolean>(false);

  const simulateScan = useCallback((code: string): void => {
    setLastScannedCode(code.trim());
  }, []);

  const toggleScanner = useCallback((): void => {
    setScannerActive((prev) => !prev);
  }, []);

  return {
    lastScannedCode,
    scannerActive,
    simulateScan,
    toggleScanner,
  };
}
