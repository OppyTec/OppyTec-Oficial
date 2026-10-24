import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import {
  type AuthenticatedUser,
  AuthProvider,
  type AuthSession,
  PermissionsProvider,
} from "@/shared/auth/usePermissions";
import { ErrorBoundary } from "@/shared/components/feedback/ErrorBoundary";
import { Toaster } from "@/shared/components/ui/sonner";
import { CurrencyProvider } from "@/shared/currency";
import { LanguageProvider } from "@/shared/i18n";
import { RealtimeProvider } from "@/shared/realtime/RealtimeProvider";

export interface AppProvidersProps {
  readonly children: ReactNode;
  readonly holdingId?: string;
  readonly tenantId?: string;
  readonly initialSession?: AuthSession | null;
  readonly initialUser?: AuthenticatedUser | null;
}

export function AppProviders({
  children,
  holdingId = "holding-gastro-sur",
  tenantId = "tenant_rest_central",
  initialSession,
  initialUser,
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
        <LanguageProvider>
          <CurrencyProvider>
            <AuthProvider
              initialSession={initialSession}
              initialUser={initialUser}
            >
              <PermissionsProvider>
                <RealtimeProvider holdingId={holdingId} tenantId={tenantId}>
                  {children}
                  <Toaster />
                </RealtimeProvider>
              </PermissionsProvider>
            </AuthProvider>
          </CurrencyProvider>
        </LanguageProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
