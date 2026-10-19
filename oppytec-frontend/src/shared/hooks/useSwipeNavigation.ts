import { useCallback, useRef, useState } from "react";

export interface SwipeDirectionResult {
  readonly lastSwipeDirection: "left" | "right" | "none";
  readonly onTouchStartX: (clientX: number) => void;
  readonly onTouchEndX: (clientX: number) => "left" | "right" | "none";
}

export function useSwipeNavigation(thresholdPx = 48): SwipeDirectionResult {
  const startXRef = useRef<number>(0);
  const [lastSwipeDirection, setLastSwipeDirection] = useState<
    "left" | "right" | "none"
  >("none");

  const onTouchStartX = useCallback((clientX: number): void => {
    startXRef.current = clientX;
  }, []);

  const onTouchEndX = useCallback(
    (clientX: number): "left" | "right" | "none" => {
      const delta = clientX - startXRef.current;
      if (Math.abs(delta) < thresholdPx) {
        setLastSwipeDirection("none");
        return "none";
      }
      const dir = delta < 0 ? "left" : "right";
      setLastSwipeDirection(dir);
      return dir;
    },
    [thresholdPx]
  );

  return {
    lastSwipeDirection,
    onTouchStartX,
    onTouchEndX,
  };
}
