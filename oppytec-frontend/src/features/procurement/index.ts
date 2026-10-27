/**
 * oppytec-frontend/src/features/procurement/index.ts
 * Módulo de Abastecimiento, Gestión de Compras, Proveedores y Analítica de Mermas.
 */

export * from "./types";
export * from "./mockData";
export * from "./hooks";
export * from "./ProcurementFeatureView";
export * from "./ProveedoresPage";
export * from "./pages/ProveedoresPage";

// Componentes Principales
export * from "./components/ComprasView";
export * from "./components/ComprasDashboard";
export * from "./components/CompraTable";
export * from "./components/CompraCards";
export * from "./components/CatalogoPrecios";
export * from "./components/ProveedoresTable";
export * from "./components/ProveedoresCards";

// Diálogos Modales
export * from "./dialogs/CompraDialog";
export * from "./dialogs/MercaderiaReceptionDialog";
export * from "./dialogs/IncidenciaDialog";
export * from "./dialogs/CompraDetalleModal";
export * from "./dialogs/ProveedorDialog";
export * from "./dialogs/ProveedorProductosDialog";
export * from "./dialogs/ProveedorDashboardDialog";

// Sub-módulo 3: Gestión Analítica de Mermas (Fase 6)
export * from "./mermas";
