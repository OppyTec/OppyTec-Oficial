import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/shared/auth/usePermissions";
import { setActiveLanguage } from "@/shared/i18n";
import { ProfilePage } from "./ProfilePage";

describe("ProfilePage Component Suite", () => {
  beforeEach(() => {
    localStorage.clear();
    setActiveLanguage("es");
    vi.clearAllMocks();
  });

  const renderProfilePage = (userRole = "admin") => {
    const mockUser = {
      id: 1,
      username: "oppytec.admin",
      email: "oppytec.admin@gmail.com",
      firstName: "Admin",
      lastName: "Genesis",
      role: userRole,
      isSuperuser: true,
      isGlobalAdmin: true,
      voiceCommand: "admin",
      phone: "+56 9 1234 5678",
      userImage: "",
    };

    return render(
      <MemoryRouter>
        <AuthProvider initialSession={{ accessToken: "mock-token" }} initialUser={mockUser}>
          <ProfilePage />
        </AuthProvider>
      </MemoryRouter>
    );
  };

  it("renders profile header with title and subtitle", () => {
    renderProfilePage();
    expect(screen.getByTestId("profile-page-root")).toBeTruthy();
    expect(screen.getByText("Admin Genesis")).toBeTruthy();
    expect(screen.getByText("@oppytec.admin")).toBeTruthy();
  });

  it("renders role badge matching CARGO_METADATA_MAP", () => {
    renderProfilePage("propietario");
    const elements = screen.getAllByText("Propietario");
    expect(elements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders operational summary with cargo, areas, and template counts", () => {
    renderProfilePage("admin");
    expect(screen.getByText("Resumen Operativo")).toBeTruthy();
    expect(screen.getByText("Cargo Actual")).toBeTruthy();
    expect(screen.getAllByText(/Áreas Operativas/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Plantillas de Tabla")).toBeTruthy();
    expect(screen.getByText("Plantillas Consumo")).toBeTruthy();
  });

  it("renders inputs for personal data and allows updating values", () => {
    renderProfilePage();
    const firstNameInput = screen.getByDisplayValue("Admin") as HTMLInputElement;
    const lastNameInput = screen.getByDisplayValue("Genesis") as HTMLInputElement;
    const emailInput = screen.getByDisplayValue("oppytec.admin@gmail.com") as HTMLInputElement;
    const phoneInput = screen.getByDisplayValue("+56 9 1234 5678") as HTMLInputElement;

    expect(firstNameInput).toBeTruthy();
    expect(lastNameInput).toBeTruthy();
    expect(emailInput).toBeTruthy();
    expect(phoneInput).toBeTruthy();

    fireEvent.change(firstNameInput, { target: { value: "Carlos" } });
    expect(firstNameInput.value).toBe("Carlos");
  });

  it("renders hands-free Oppy voice command section", () => {
    renderProfilePage();
    expect(
      screen.getByText("Comando de Voz Oppy (Modo Manos Libres)")
    ).toBeTruthy();
    const voiceInput = screen.getByDisplayValue("admin");
    expect(voiceInput).toBeTruthy();
  });

  it("switches tabs between Tablas, Consumo, and Emails", () => {
    renderProfilePage();

    // Default tab is Tablas
    expect(screen.getByText("Vista Estándar Operativa")).toBeTruthy();

    // Switch to Consumo Interno
    const consumoTabBtn = screen.getByRole("button", { name: /Consumo Interno/i });
    fireEvent.click(consumoTabBtn);
    expect(screen.getByText("Cierre Diario Cocina Central")).toBeTruthy();

    // Switch to Emails & Mensajes
    const emailsTabBtn = screen.getByRole("button", { name: /Emails & Mensajes/i });
    fireEvent.click(emailsTabBtn);
    expect(screen.getByText("Plantillas de Email & Notificaciones")).toBeTruthy();
  });

  it("opens ResponsiveDialog on clicking '+ Nueva Plantilla' and creates a new preset", async () => {
    renderProfilePage();

    const newBtn = screen.getByRole("button", { name: /\+ Nueva Plantilla/i });
    fireEvent.click(newBtn);

    expect(screen.getByTestId("responsive-dialog")).toBeTruthy();
    expect(screen.getByText("Crear Nueva Plantilla")).toBeTruthy();

    const nameInput = screen.getByPlaceholderText("Ej: Auditoría Cierre Mensual");
    fireEvent.change(nameInput, { target: { value: "Mi Nueva Plantilla Test" } });

    const createBtn = screen.getByRole("button", { name: "Crear Plantilla" });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(screen.queryByTestId("responsive-dialog")).toBeNull();
      expect(screen.getByText("Mi Nueva Plantilla Test")).toBeTruthy();
    });
  });

  it("triggers save changes button successfully", () => {
    renderProfilePage();
    const saveBtn = screen.getByRole("button", { name: "Guardar Cambios" });
    expect(saveBtn).toBeTruthy();
    fireEvent.click(saveBtn);
  });
});
