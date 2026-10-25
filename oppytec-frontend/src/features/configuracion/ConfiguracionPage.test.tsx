import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "@/shared/components/layout/Sidebar";
import { ConfiguracionPage } from "./ConfiguracionPage";
import { AparienciaConfig } from "./tabs/AparienciaConfig";
import { PlantillasEmailConfig } from "./tabs/PlantillasEmailConfig";
import { BodegasConfig } from "./tabs/BodegasConfig";
import { RestauranteConfig } from "./tabs/RestauranteConfig";
import { SoporteConfig } from "./tabs/SoporteConfig";
import { AreasOperativasConfig } from "./tabs/AreasOperativasConfig";
import { setActiveLanguage, I18N_RESOURCES } from "@/shared/i18n";

describe("Configuración Feature & Sidebar Gear Popover", () => {
  beforeEach(() => {
    setActiveLanguage("es");
  });
  it("renders Sidebar footer with emerald pulse dot, OPPYTEC label and settings button", () => {
    render(
      <MemoryRouter>
        <Sidebar isCollapsed={false} />
      </MemoryRouter>
    );

    expect(screen.getByText("OPPYTEC")).toBeTruthy();
    const settingsBtn = screen.getByTestId("sidebar-settings-btn");
    expect(settingsBtn).toBeTruthy();
  });

  it("opens the settings popover with 6 configuration links when clicking gear button", async () => {
    render(
      <MemoryRouter>
        <Sidebar isCollapsed={false} />
      </MemoryRouter>
    );

    const settingsBtn = screen.getByTestId("sidebar-settings-btn");
    fireEvent.click(settingsBtn);

    const popover = screen.getByTestId("sidebar-settings-popover");
    expect(popover).toBeTruthy();

    expect(screen.getByText("Negocio")).toBeTruthy();
    expect(screen.getByText("Bodegas")).toBeTruthy();
    expect(screen.getByText("Áreas Operativas")).toBeTruthy();
    expect(screen.getByText("Plantillas de Email")).toBeTruthy();
    expect(screen.getByText("Apariencia")).toBeTruthy();
    expect(screen.getByText("Soporte y Ayuda")).toBeTruthy();
  });

  it("closes settings popover when clicking outside", async () => {
    render(
      <MemoryRouter>
        <div data-testid="outside-area">Outside</div>
        <Sidebar isCollapsed={false} />
      </MemoryRouter>
    );

    const settingsBtn = screen.getByTestId("sidebar-settings-btn");
    fireEvent.click(settingsBtn);
    expect(screen.getByTestId("sidebar-settings-popover")).toBeTruthy();

    fireEvent.mouseDown(screen.getByTestId("outside-area"));
    await waitFor(() => {
      expect(screen.queryByTestId("sidebar-settings-popover")).toBeNull();
    });
  });

  it("renders ConfiguracionPage with SectionHeader and 6 accordion sections", () => {
    render(
      <MemoryRouter initialEntries={["/configuracion"]}>
        <ConfiguracionPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId("configuracion-page")).toBeTruthy();
    expect(screen.getByTestId("config-section-negocio")).toBeTruthy();
    expect(screen.getByTestId("config-section-bodegas")).toBeTruthy();
    expect(screen.getByTestId("config-section-areas")).toBeTruthy();
    expect(screen.getByTestId("config-section-plantillas_email")).toBeTruthy();
    expect(screen.getByTestId("config-section-tema")).toBeTruthy();
    expect(screen.getByTestId("config-section-soporte")).toBeTruthy();
  });

  it("opens the requested section based on ?tab= query parameter", () => {
    render(
      <MemoryRouter initialEntries={["/configuracion?tab=bodegas"]}>
        <ConfiguracionPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId("bodegas-config-section")).toBeTruthy();
  });

  it("renders AparienciaConfig with 3 theme options and NUEVO badge on ocean-blue", () => {
    render(
      <MemoryRouter>
        <AparienciaConfig />
      </MemoryRouter>
    );

    expect(screen.getByText("Modo Claro")).toBeTruthy();
    expect(screen.getByText("Modo Oscuro")).toBeTruthy();
    expect(screen.getByText("Ocean Blue")).toBeTruthy();
    expect(screen.getByText("NUEVO")).toBeTruthy();
  });

  it("inserts variable chips in PlantillasEmailConfig", () => {
    render(
      <MemoryRouter>
        <PlantillasEmailConfig />
      </MemoryRouter>
    );

    const newBtn = screen.getByRole("button", { name: /nueva plantilla/i });
    fireEvent.click(newBtn);

    const chip = screen.getByRole("button", { name: /proveedor/i });
    expect(chip).toBeTruthy();
    fireEvent.click(chip);
  });

  it("opens New Bodega modal with 36 preset colors in BodegasConfig", () => {
    render(
      <MemoryRouter>
        <BodegasConfig />
      </MemoryRouter>
    );

    const newBodegaBtn = screen.getByRole("button", { name: /nueva bodega/i });
    fireEvent.click(newBodegaBtn);

    expect(screen.getByText("Nombre de la Bodega")).toBeTruthy();
    expect(screen.getByText(/36 opciones/i)).toBeTruthy();
  });

  it("renders RestauranteConfig with business types and HTML signature controls", () => {
    render(
      <MemoryRouter>
        <RestauranteConfig />
      </MemoryRouter>
    );

    expect(screen.getByTestId("restaurante-config-form")).toBeTruthy();
    expect(screen.getByText("Tipo de Negocio")).toBeTruthy();
    expect(screen.getByText("Correo de Respuestas (Reply-To)")).toBeTruthy();
    expect(screen.getByText("Firma Corporativa (HTML)")).toBeTruthy();
  });

  it("renders AreasOperativasConfig and allows opening new area modal", () => {
    render(
      <MemoryRouter>
        <AreasOperativasConfig />
      </MemoryRouter>
    );

    expect(screen.getByTestId("areas-operativas-section")).toBeTruthy();
    const newAreaBtn = screen.getByRole("button", { name: /nueva área/i });
    fireEvent.click(newAreaBtn);

    expect(screen.getByText("Nombre del Área")).toBeTruthy();
    expect(screen.getByText("Bodegas Asociadas")).toBeTruthy();
  });

  it("renders SoporteConfig with textarea and official built with passion badge", () => {
    render(
      <MemoryRouter>
        <SoporteConfig />
      </MemoryRouter>
    );

    expect(screen.getByTestId("soporte-config-section")).toBeTruthy();
    expect(screen.getByPlaceholderText(/describe tu consulta/i)).toBeTruthy();
    expect(screen.getByText("Built with passion for OppyTec Team")).toBeTruthy();
  });

  it("verifies 1:1 translation parity between es and en in configuracion namespace", () => {
    const esRes = (I18N_RESOURCES.es as Record<string, unknown>).configuracion;
    const enRes = (I18N_RESOURCES.en as Record<string, unknown>).configuracion;

    expect(esRes).toBeDefined();
    expect(enRes).toBeDefined();

    function getKeys(obj: unknown, prefix = ""): string[] {
      if (!obj || typeof obj !== "object") return [];
      const keys: string[] = [];
      for (const [k, v] of Object.entries(obj)) {
        const full = prefix ? `${prefix}.${k}` : k;
        if (typeof v === "object" && v !== null && !Array.isArray(v)) {
          keys.push(...getKeys(v, full));
        } else {
          keys.push(full);
        }
      }
      return keys;
    }

    const esKeys = getKeys(esRes).sort();
    const enKeys = getKeys(enRes).sort();

    expect(esKeys).toEqual(enKeys);
    expect(esKeys.length).toBeGreaterThan(50);
  });

  it("renders English translations when active language is set to 'en'", () => {
    setActiveLanguage("en");

    render(
      <MemoryRouter>
        <Sidebar isCollapsed={false} />
      </MemoryRouter>
    );

    const settingsBtn = screen.getByTestId("sidebar-settings-btn");
    expect(settingsBtn.getAttribute("title")).toBe("Configuration");
    fireEvent.click(settingsBtn);

    const popover = screen.getByTestId("sidebar-settings-popover");
    expect(popover).toBeTruthy();

    expect(screen.getByText("Business")).toBeTruthy();
    expect(screen.getByText("Warehouses")).toBeTruthy();
    expect(screen.getByText("Operational Areas")).toBeTruthy();
    expect(screen.getByText("Email Templates")).toBeTruthy();
    expect(screen.getByText("Appearance")).toBeTruthy();
    expect(screen.getByText("Support & Help")).toBeTruthy();
  });

  it("renders English ConfiguracionPage header and accordion tabs in 'en' mode", () => {
    setActiveLanguage("en");

    render(
      <MemoryRouter initialEntries={["/configuracion"]}>
        <ConfiguracionPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId("configuracion-page")).toBeTruthy();
    expect(screen.getByText("System Settings and Administration")).toBeTruthy();
    expect(screen.getByText("Business")).toBeTruthy();
    expect(screen.getByText("Warehouses")).toBeTruthy();
    expect(screen.getByText("Operational Areas")).toBeTruthy();
    expect(screen.getByText("Email Templates")).toBeTruthy();
    expect(screen.getByText("Appearance")).toBeTruthy();
    expect(screen.getByText("Support & Help")).toBeTruthy();
  });
});
