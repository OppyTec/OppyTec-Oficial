import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/shared/auth/usePermissions";
import { setActiveLanguage } from "@/shared/i18n";
import { UsuariosPage } from "./UsuariosPage";

describe("UsuariosPage Component Suite", () => {
  beforeEach(() => {
    localStorage.clear();
    setActiveLanguage("es");
    vi.clearAllMocks();
  });

  const renderUsuariosPage = (userRole = "admin") => {
    const mockUser = {
      id: 1,
      username: "admin",
      email: "admin@oppytec.cl",
      firstName: "Super",
      lastName: "Admin",
      role: userRole,
      isSuperuser: true,
      isGlobalAdmin: true,
    };

    return render(
      <MemoryRouter>
        <AuthProvider initialSession={{ accessToken: "mock-token" }} initialUser={mockUser}>
          <UsuariosPage />
        </AuthProvider>
      </MemoryRouter>
    );
  };

  it("renders SectionHeader with title and subtitle", () => {
    renderUsuariosPage();
    expect(screen.getByRole("heading", { level: 1 })).toBeTruthy();
    expect(screen.getByText(/Administración de accesos, roles y cargos del personal/i)).toBeTruthy();
  });

  it("renders toolbar with search input, area filter, and new user button", () => {
    renderUsuariosPage();
    expect(screen.getByPlaceholderText(/Buscar usuarios por nombre/i)).toBeTruthy();
    expect(screen.getByTestId("btn-nuevo-usuario")).toBeTruthy();
    expect(screen.getByText(/Usuarios y Accesos/i)).toBeTruthy();
    expect(screen.getByText(/Gestión de Cargos/i)).toBeTruthy();
    expect(screen.getByText(/Matriz de Roles/i)).toBeTruthy();
  });

  it("renders list of initial mock users with names, usernames, and roles", () => {
    renderUsuariosPage();
    expect(screen.getByText("Juan Campillay")).toBeTruthy();
    expect(screen.getByText("@jcampillay")).toBeTruthy();
    expect(screen.getByText("Valentina Soto")).toBeTruthy();
    expect(screen.getByText("@vsoto")).toBeTruthy();
    expect(screen.getByText("Carlos Mendoza")).toBeTruthy();
  });

  it("filters users when typing in search input", () => {
    renderUsuariosPage();
    const searchInput = screen.getByPlaceholderText(/Buscar usuarios por nombre/i);
    fireEvent.change(searchInput, { target: { value: "Valentina" } });

    expect(screen.getByText("Valentina Soto")).toBeTruthy();
    expect(screen.queryByText("Juan Campillay")).toBeNull();
  });

  it("opens create user modal with form fields and preset colors when clicking new user button", () => {
    renderUsuariosPage();
    const newBtn = screen.getByTestId("btn-nuevo-usuario");
    fireEvent.click(newBtn);

    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("Crear Nuevo Usuario")).toBeTruthy();
    expect(screen.getByPlaceholderText("Ej: Juan")).toBeTruthy();
    expect(screen.getByPlaceholderText("Ej: Pérez")).toBeTruthy();
    expect(screen.getByPlaceholderText("Ej: juan.perez")).toBeTruthy();
    expect(screen.getByPlaceholderText("juan@restaurante.com")).toBeTruthy();
  });

  it("toggles sub-tabs between usuarios, cargos and roles", () => {
    renderUsuariosPage();
    const cargosTab = screen.getByText(/Gestión de Cargos/i);
    fireEvent.click(cargosTab);
    expect(screen.getByText("dueño")).toBeTruthy();
    expect(screen.getByText("cocinero")).toBeTruthy();

    const rolesTab = screen.getByText(/Matriz de Roles/i);
    fireEvent.click(rolesTab);
    expect(screen.getByText("RBAC v2.0")).toBeTruthy();
    expect(screen.getByText("Ver Productos")).toBeTruthy();
  });

  it("opens change password modal when lock button is clicked", () => {
    renderUsuariosPage();
    const lockButtons = screen.getAllByTitle("Cambiar Contraseña");
    expect(lockButtons.length).toBeGreaterThanOrEqual(1);
    const firstLock = lockButtons[0];
    expect(firstLock).toBeDefined();
    if (firstLock) fireEvent.click(firstLock);

    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByPlaceholderText("Mínimo 6 caracteres")).toBeTruthy();
  });

  it("opens status toggle modal when power button is clicked", () => {
    renderUsuariosPage();
    const powerButtons = screen.getAllByTitle("Activar / Desactivar");
    expect(powerButtons.length).toBeGreaterThanOrEqual(1);
    const firstPower = powerButtons[0];
    expect(firstPower).toBeDefined();
    if (firstPower) fireEvent.click(firstPower);

    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("¿Cambiar estado del usuario?")).toBeTruthy();
  });
});
