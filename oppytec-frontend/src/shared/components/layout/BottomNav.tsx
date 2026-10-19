import {
  FEATURE_MODULE_ROUTES,
  type FeatureRouteId,
} from "./Sidebar";

export interface BottomNavProps {
  readonly activeFeature: FeatureRouteId;
  readonly onSelectFeature: (feature: FeatureRouteId) => void;
}

const MOBILE_PRIMARY_FEATURES = FEATURE_MODULE_ROUTES.slice(0, 5);

export function BottomNav({ activeFeature, onSelectFeature }: BottomNavProps) {
  return (
    <nav
      aria-label="Mobile Bottom Navigation"
      data-testid="mobile-bottom-nav"
      className="glass fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-border p-1.5 md:hidden"
    >
      {MOBILE_PRIMARY_FEATURES.map((item) => {
        const isCurrent = activeFeature === item.id;
        return (
          <button
            key={item.id}
            type="button"
            data-testid={`bottom-nav-${item.id}`}
            onClick={() => onSelectFeature(item.id)}
            className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg px-2.5 py-1.5 text-[11px] font-semibold ${
              isCurrent
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground"
            }`}
          >
            {item.labelEs.split(" ")[0]}
          </button>
        );
      })}
    </nav>
  );
}
