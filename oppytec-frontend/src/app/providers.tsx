import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { ErrorBoundary } from "@/shared/components/feedback/ErrorBoundary";
import { CurrencyProvider } from "@/shared/currency";
import { RealtimeProvider } from "@/shared/realtime/RealtimeProvider";

export interface AppProvidersProps {
  readonly children: ReactNode;
  readonly holdingId?: string;
  readonly tenantId?: string;
}

export function AppProviders({
  children,
  holdingId = "holding-gastro-sur",
  tenantId = "tenant_rest_central",
}: AppProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <CurrencyProvider>
          <PermissionsProvider>
            <RealtimeProvider holdingId={holdingId} tenantId={tenantId}>
              {children}
            </RealtimeProvider>
          </PermissionsProvider>
        </CurrencyProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
