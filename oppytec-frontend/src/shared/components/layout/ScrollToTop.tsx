import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * Universally scrolls the viewport and any inner scrollable main containers
 * to the very top instantaneously across all browsers and devices.
 */
export function scrollToTopInstant(): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  } catch {
    window.scrollTo(0, 0);
  }

  if (document.documentElement) {
    document.documentElement.scrollTop = 0;
  }
  if (document.body) {
    document.body.scrollTop = 0;
  }

  const mainEl = document.querySelector("main");
  if (mainEl) {
    mainEl.scrollTop = 0;
  }
}

/**
 * Universal ScrollToTop component mounted inside the Router.
 * Automatically executes scrollToTopInstant on every pathname or search change.
 */
export function ScrollToTop(): null {
  const { pathname, search } = useLocation();

  useEffect(() => {
    scrollToTopInstant();
  }, [pathname, search]);

  return null;
}
