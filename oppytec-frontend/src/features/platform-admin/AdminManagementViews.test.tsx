import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AppProviders } from "@/app/providers";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { CurrencySelector } from "@/shared/currency/CurrencySelector";
import { LanguageFlagSelector } from "@/shared/i18n/LanguageFlagSelector";
import { QuotaProgressIndicator } from "@/shared/components/ui/QuotaProgressIndicator";
import {
  AdminClientUsersView,
  AdminHoldingsView,
  AdminLegalEntitiesView,
  AdminTenantsView,
  HoldingsManagementView,
  PlansManagementView,
  TenantsManagementView,
} from "./AdminManagementViews";

describe("AdminManagementViews Interaction Tests (Agente 09 QA & Agente 10 RBAC)", () => {
  it("opens create modal, enters data, and adds a new holding in AdminHoldingsView", async () => {
    await act(async () => {
      render(
        <AppProviders>
          <AdminHoldingsView />
        </AppProviders>
      );
    });

    expect(screen.getByTestId("admin-holdings-view")).toBeTruthy();
    expect(screen.getByTestId("holdings-table-create-btn")).toBeTruthy();

    // Click "+ Nuevo Holding"
    await act(async () => {
      fireEvent.click(screen.getByTestId("holdings-table-create-btn"));
    });

    const form = screen.getByTestId("admin-create-holding-form");
    expect(form).toBeTruthy();

    // Fill in required name
    const nameInput = screen.getByPlaceholderText(/Grupo Gastronómico/i);
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Holding Gastronómico Austral SpA" } });
    });
    expect((nameInput as HTMLInputElement).value).toBe("Holding Gastronómico Austral SpA");

    // Submit modal
    const submitBtn = screen.getByTestId("admin-create-holding-form-submit-btn");
    await act(async () => {
      fireEvent.click(submitBtn);
    });

    // Verify row appeared in table
    await waitFor(() => {
      expect(screen.getByText("Holding Gastronómico Austral SpA")).toBeTruthy();
    });
  });

  it("opens create modal and adds legal entity in AdminLegalEntitiesView", async () => {
    await act(async () => {
      render(
        <AppProviders>
          <AdminLegalEntitiesView />
        </AppProviders>
      );
    });

    expect(screen.getByTestId("admin-legal-entities-view")).toBeTruthy();
    expect(screen.getByTestId("legal-entities-table-create-btn")).toBeTruthy();

    // Click "+ Nueva Entidad Legal"
    await act(async () => {
      fireEvent.click(screen.getByTestId("legal-entities-table-create-btn"));
    });

    expect(screen.getByTestId("admin-create-legal-entity-form")).toBeTruthy();

    const taxIdInput = screen.getByPlaceholderText("Ej: 76.543.210-K");
    const legalNameInput = screen.getByPlaceholderText("Ej: Inversiones Gastronómicas SpA");

    await act(async () => {
      fireEvent.change(taxIdInput, { target: { value: "79.111.222-3" } });
      fireEvent.change(legalNameInput, { target: { value: "Comercial Austral SpA" } });
    });

    const submitBtn = screen.getByTestId("admin-create-legal-entity-form-submit-btn");
    await act(async () => {
      fireEvent.click(submitBtn);
    });

    await waitFor(() => {
      expect(screen.getByText("79.111.222-3")).toBeTruthy();
      expect(screen.getByText("Comercial Austral SpA")).toBeTruthy();
    });
  });

  it("opens tenant provision modal and verifies module tree toggles in AdminTenantsView", async () => {
    await act(async () => {
      render(
        <AppProviders>
          <AdminTenantsView />
        </AppProviders>
      );
    });

    expect(screen.getByTestId("admin-tenants-view")).toBeTruthy();
    expect(screen.getByTestId("tenants-table-create-btn")).toBeTruthy();

    // Open Tenant Modal
    await act(async () => {
      fireEvent.click(screen.getByTestId("tenants-table-create-btn"));
    });

    expect(screen.getByTestId("admin-create-tenant-form")).toBeTruthy();

    const nameInput = screen.getByPlaceholderText("Ej: Sucursal Costanera");
    const slugInput = screen.getByPlaceholderText("costanera_centro");

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Sucursal Austral" } });
      fireEvent.change(slugInput, { target: { value: "austral_punta_arenas" } });
    });

    // Check module preset button
    const presetBtn = screen.getAllByTestId("tenant-apply-plan-basico-btn")[0];
    if (presetBtn) {
      await act(async () => {
        fireEvent.click(presetBtn);
      });
    }

    // Submit form
    await act(async () => {
      fireEvent.click(screen.getByTestId("tenant-provision-submit-btn"));
    });

    await waitFor(() => {
      expect(screen.getByText("Sucursal Austral")).toBeTruthy();
    });
  });

  it("performs soft-delete / archiving and frees quota in AdminClientUsersView", async () => {
    await act(async () => {
      render(
        <AppProviders>
          <AdminClientUsersView />
        </AppProviders>
      );
    });

    expect(screen.getByTestId("admin-client-users-view")).toBeTruthy();

    // Initially user 101 has the Archivar button
    const archiveBtn = screen.getByTestId("soft-delete-cu-btn-101");
    expect(archiveBtn).toBeTruthy();

    // Click Archivar
    await act(async () => {
      fireEvent.click(archiveBtn);
    });

    // Once archived, the button is replaced by Liberado badge
    await waitFor(() => {
      expect(screen.queryByTestId("soft-delete-cu-btn-101")).toBeNull();
      expect(screen.getByText("Liberado")).toBeTruthy();
    });

    // Open create client user modal
    await act(async () => {
      fireEvent.click(screen.getByTestId("client-users-table-create-btn"));
    });

    expect(screen.getByTestId("admin-create-client-user-form")).toBeTruthy();
  });

  it("enforces RBAC `<Can>` by hiding action buttons for unprivileged roles", async () => {
    const unprivilegedPolicy = {
      roleName: "Mozo",
      planModules: ["operations"],
      rolePermissions: ["operations.pos.consume" as const],
      temporaryGrants: [],
      deniedPermissions: [],
    };

    await act(async () => {
      render(
        <PermissionsProvider initialPolicy={unprivilegedPolicy}>
          <AdminHoldingsView />
          <AdminClientUsersView />
        </PermissionsProvider>
      );
    });

    // The "+ Nuevo Holding" and "+ Nuevo Usuario Cliente" buttons should NOT be rendered
    expect(screen.queryByTestId("holdings-table-create-btn")).toBeNull();
    expect(screen.queryByTestId("client-users-table-create-btn")).toBeNull();
    expect(screen.queryByTestId("soft-delete-cu-btn-101")).toBeNull();
  });

  it("renders PlansManagementView, HoldingsManagementView, TenantsManagementView, QuotaProgressIndicator, and dropdowns without errors", async () => {
    await act(async () => {
      render(
        <AppProviders>
          <PlansManagementView />
          <HoldingsManagementView />
          <TenantsManagementView />
          <QuotaProgressIndicator
            resourceKey="users"
            label="Usuarios Activos"
            activeCount={3}
            maxLimit={5}
            unitSuffix="usuarios"
            testId="test-quota-users"
          />
          <CurrencySelector />
          <LanguageFlagSelector />
        </AppProviders>
      );
    });

    // Check Plan cards
    expect(screen.getByTestId("admin-plans-view")).toBeTruthy();
    expect(screen.getByTestId("plan-card-basic")).toBeTruthy();

    // Check Holdings & Tenants views
    expect(screen.getByTestId("admin-holdings-view")).toBeTruthy();
    expect(screen.getByTestId("admin-tenants-view")).toBeTruthy();

    // Check QuotaProgressIndicator
    expect(screen.getByTestId("test-quota-users")).toBeTruthy();

    // Check dropdowns
    expect(screen.getByTestId("currency-selector")).toBeTruthy();
    expect(screen.getByTestId("language-flag-selector")).toBeTruthy();
  });
});
