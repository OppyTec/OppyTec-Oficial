// oppytec-frontend/src/features/gestion/index.ts

export * from "./types";
export * from "./useGestion";

export {
  DraftRecoveryBanner,
  type DraftRecoveryBannerProps,
  type DraftProductData,
  DRAFT_STORAGE_KEY,
} from "./components/DraftRecoveryBanner";

export {
  CategoriaSeccion,
  type CategoriaSeccionProps,
} from "./components/CategoriaSeccion";

export {
  TablePagination,
  type TablePaginationProps,
} from "./components/TablePagination";

export {
  ToolbarGestion,
  type ToolbarGestionProps,
  type TablePreset,
  DEFAULT_PUBLIC_PRESETS,
} from "./components/ToolbarGestion";

export {
  CategoryTableWrapper,
  type CategoryTableWrapperProps,
} from "./components/CategoryTableWrapper";

export {
  ProductMobileCard,
  type ProductMobileCardProps,
  type BodegaInfo,
} from "./components/ProductMobileCard";

export {
  ProductTable,
  type ProductTableProps,
} from "./components/ProductTable";

export {
  TableConfigModal,
  type TableConfigModalProps,
} from "./components/TableConfigModal";

export {
  AdministradorCategoriasDialog,
  type AdministradorCategoriasDialogProps,
} from "./components/AdministradorCategoriasDialog";

export {
  CatalogosManagerDialog,
  type CatalogosManagerDialogProps,
} from "./components/CatalogosManagerDialog";

export {
  TransferDialog,
  type TransferDialogProps,
  type TransferItem,
} from "./components/TransferDialog";

export {
  ProductoWizardDialog,
  type ProductoWizardDialogProps,
  generateFullProductName,
  calculateFinancialKPIs,
} from "./components/ProductoWizardDialog";

export {
  ExcelImportModal,
  type ExcelImportModalProps,
  type ExcelImportStep,
  ExcelColumnMatcher,
  type ExcelColumnMatcherProps,
  ExcelEntityMatcherBanner,
  type ExcelEntityMatcherBannerProps,
  ExcelImportReviewGrid,
  type ExcelImportReviewGridProps,
  type ParsedProductRow,
  downloadExcelTemplate,
  EXCEL_DRAFT_KEY,
} from "./components/ExcelImportModal";

export {
  FacturaImportModal,
  type FacturaImportModalProps,
  FacturaSupplierBanner,
  type FacturaSupplierBannerProps,
  type FacturaSupplierInfo,
  FacturaReviewGrid,
  type FacturaReviewGridProps,
  type FacturaParsedLine,
  UnidadMedidaCombobox,
  type UnidadMedidaComboboxProps,
  FACTURA_DRAFT_KEY,
} from "./components/FacturaImportModal";

export { GestionPage, GestionPage as default } from "./GestionPage";

