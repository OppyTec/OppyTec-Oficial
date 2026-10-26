import type { LucideIcon } from "lucide-react";
import { Boxes, Flame, Truck, Users } from "lucide-react";

// ============================================================================
// 1. Tipos de Dominio y Estados Canónicos
// ============================================================================

export type SolicitudTipo =
  | "merma"
  | "merma_receta"
  | "consumo"
  | "consumo_buffet"
  | "conteo"
  | "producto_borrador_receta"
  | "recibir_pedido"
  | "solicitud_compra"
  | "vinculacion_proveedor"
  | "mencion_nota"
  | "perfil"
  | "color_turno";

export type SolicitudEstado =
  | "pendiente"
  | "aprobado"
  | "rechazado"
  | "aprobado_temporal";

export type CategoryType = "operaciones" | "inventario" | "compras" | "equipo";

export type MainViewType = "bandeja" | "historial" | "configuracion";

// ============================================================================
// 2. Mapeos de Categoría y Configuración Visual Legacy
// ============================================================================

export const CATEGORY_MAP: Record<SolicitudTipo, CategoryType> = {
  merma: "operaciones",
  merma_receta: "operaciones",
  consumo: "operaciones",
  consumo_buffet: "operaciones",
  conteo: "inventario",
  producto_borrador_receta: "inventario",
  recibir_pedido: "compras",
  solicitud_compra: "compras",
  vinculacion_proveedor: "compras",
  mencion_nota: "equipo",
  perfil: "equipo",
  color_turno: "equipo",
};

export interface CategoryConfigItem {
  readonly id: CategoryType;
  readonly label: string;
  readonly color: string;
  readonly icon: LucideIcon;
  readonly activeClass: string;
  readonly badgeClass: string;
}

export const CATEGORIES_CONFIG: readonly CategoryConfigItem[] = [
  {
    id: "operaciones",
    label: "Operaciones",
    color: "#f59e0b",
    icon: Flame,
    activeClass:
      "bg-amber-500/15 text-amber-500 border-amber-500/40 shadow-amber-500/20",
    badgeClass: "bg-amber-500 text-black font-black",
  },
  {
    id: "inventario",
    label: "Inventario",
    color: "#10b981",
    icon: Boxes,
    activeClass:
      "bg-emerald-500/15 text-emerald-500 border-emerald-500/40 shadow-emerald-500/20",
    badgeClass: "bg-emerald-500 text-black font-black",
  },
  {
    id: "compras",
    label: "Compras",
    color: "#6366f1",
    icon: Truck,
    activeClass:
      "bg-indigo-500/15 text-indigo-400 border-indigo-500/40 shadow-indigo-500/20",
    badgeClass: "bg-indigo-500 text-white font-black",
  },
  {
    id: "equipo",
    label: "Equipo",
    color: "#a855f7",
    icon: Users,
    activeClass:
      "bg-purple-500/15 text-purple-400 border-purple-500/40 shadow-purple-500/20",
    badgeClass: "bg-purple-500 text-white font-black",
  },
] as const;

// ============================================================================
// 3. Entidades de Solicitud y Usuarios
// ============================================================================

export interface UserSimple {
  readonly id: number;
  readonly username: string;
  readonly first_name?: string | null;
  readonly last_name?: string | null;
  readonly email: string;
  readonly role: string;
}

export interface Solicitud {
  readonly id: string;
  readonly tipo: SolicitudTipo;
  readonly categoria?: CategoryType;
  readonly estado: SolicitudEstado;
  readonly usuario_id: number;
  readonly bodega_id?: number | null;
  readonly area_operativa_id?: number | null;
  readonly detalles: Record<string, any>;
  readonly creado_at: string;
  readonly resuelto_at?: string | null;
  readonly resuelto_por?: number | null;
  readonly motivo_rechazo?: string | null;
  readonly usuario?: UserSimple | null;
  readonly resuelto_por_usuario?: UserSimple | null;
}

export interface SolicitudesListResponse {
  readonly items: readonly Solicitud[];
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
}

export interface PendingCounts {
  readonly total: number;
  readonly operaciones: number;
  readonly inventario: number;
  readonly compras: number;
  readonly equipo: number;
  readonly by_area?: Record<string, number>;
}

// ============================================================================
// 4. Contratos de Buffet y Gobernanza
// ============================================================================

export interface BuffetApprovalDetail {
  readonly id: string;
  readonly tipo: string;
  readonly estado: SolicitudEstado;
  readonly usuario_id: number;
  readonly bodega_id?: number | null;
  readonly area_operativa_id?: number | null;
  readonly detalles: Record<string, any>;
  readonly resuelto_por?: number | null;
  readonly motivo_rechazo?: string | null;
  readonly created_at: string;
  readonly resuelto_at?: string | null;
}

export interface BuffetItemResolution {
  readonly item_id?: any;
  readonly producto_id?: number | null;
  readonly item_type?: string;
  readonly nombre?: string;
  readonly cantidad?: number | string;
  readonly cantidad_sobrante?: number | string;
  readonly accion_sobrante?: "retornar" | "merma";
  readonly motivo_merma?: string | null;
}

export interface BuffetResolvePayload {
  readonly accion: "aprobar" | "rechazar";
  readonly motivo_rechazo?: string | null;
  readonly items_override?: readonly BuffetItemResolution[] | null;
}

export interface NotificationMatrixRule {
  readonly cargo: string;
  readonly tipo_solicitud: string;
  readonly canal_in_app: boolean;
  readonly canal_email: boolean;
  readonly canal_push: boolean;
  readonly es_aprobador: boolean;
}

export interface CargoMatrixItem {
  readonly id: number;
  readonly name: string;
  readonly role_name: string;
  readonly description?: string | null;
  readonly is_system?: boolean;
  readonly notification_permissions?: Record<string, boolean>;
}

export interface NotificationCatalogItem {
  readonly type: string;
  readonly label: string;
  readonly category: string;
  readonly description: string;
}

export interface NotificationMatrixData {
  readonly catalog: readonly NotificationCatalogItem[];
  readonly cargos: readonly CargoMatrixItem[];
  readonly rules: readonly NotificationMatrixRule[];
  readonly is_admin: boolean;
}

// ============================================================================
// 5. Fallback Mock Data para Resiliencia (Cero Pantallas en Blanco)
// ============================================================================

export const MOCK_PENDING_COUNTS: PendingCounts = {
  total: 4,
  operaciones: 2,
  inventario: 1,
  compras: 1,
  equipo: 0,
  by_area: {
    "1": 2,
    "2": 1,
    "3": 1,
  },
};

export const MOCK_SOLICITUDES: readonly Solicitud[] = [
  {
    id: "sol-mock-001",
    tipo: "merma",
    categoria: "operaciones",
    estado: "pendiente",
    usuario_id: 10,
    bodega_id: 1,
    area_operativa_id: 1,
    creado_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    usuario: {
      id: 10,
      username: "chef_carlos",
      first_name: "Carlos",
      last_name: "Gómez",
      email: "carlos.gomez@restaurant.cl",
      role: "chef",
    },
    detalles: {
      producto_id: 101,
      producto_nombre: "Salmón Fresco Chileno",
      cantidad: 2.5,
      unidad: "kg",
      motivo: "vencimiento",
      costo_unitario: 12500,
      costo_total: 31250,
      observaciones: "Perdió cadena de frío en turno nocturno",
    },
  },
  {
    id: "sol-mock-002",
    tipo: "consumo_buffet",
    categoria: "operaciones",
    estado: "pendiente",
    usuario_id: 12,
    bodega_id: 2,
    area_operativa_id: 2,
    creado_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    usuario: {
      id: 12,
      username: "matias_bar",
      first_name: "Matías",
      last_name: "Silva",
      email: "matias.silva@restaurant.cl",
      role: "supervisor",
    },
    detalles: {
      sesion_buffet_id: 504,
      buffet_nombre: "Buffet Almuerzo Ejecutivo",
      pax_atendidos: 45,
      total_items: 8,
      costo_estimado: 142000,
      requiere_split: true,
    },
  },
  {
    id: "sol-mock-003",
    tipo: "conteo",
    categoria: "inventario",
    estado: "pendiente",
    usuario_id: 14,
    bodega_id: 1,
    area_operativa_id: 1,
    creado_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
    usuario: {
      id: 14,
      username: "bodega_roberto",
      first_name: "Roberto",
      last_name: "López",
      email: "roberto.lopez@restaurant.cl",
      role: "bodeguero",
    },
    detalles: {
      acta_conteo_id: 88,
      items_contados: 24,
      discrepancias_count: 2,
      delta_monetario: -14500,
      observaciones: "Diferencia física en bodega central Carnes",
    },
  },
  {
    id: "sol-mock-004",
    tipo: "recibir_pedido",
    categoria: "compras",
    estado: "pendiente",
    usuario_id: 15,
    bodega_id: 1,
    area_operativa_id: 1,
    creado_at: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
    usuario: {
      id: 15,
      username: "recepcion_ana",
      first_name: "Ana",
      last_name: "Morales",
      email: "ana.morales@restaurant.cl",
      role: "bodeguero",
    },
    detalles: {
      orden_compra_id: 312,
      proveedor_nombre: "Distribuidora Mayorista del Sur",
      monto_factura: 485000,
      discrepancia_bultos: 0,
      guia_despacho: "GD-88392",
    },
  },
];

export const MOCK_NOTIFICATION_MATRIX: NotificationMatrixData = {
  is_admin: true,
  catalog: [
    {
      type: "merma",
      label: "Mermas Operativas",
      category: "operaciones",
      description: "Descartes de insumos por vencimiento o rotura",
    },
    {
      type: "consumo",
      label: "Consumo de Cocina",
      category: "operaciones",
      description: "Retiros de cocina para pruebas o preparación",
    },
    {
      type: "conteo",
      label: "Conteos de Inventario",
      category: "inventario",
      description: "Ajustes de inventario y actas de recuento",
    },
    {
      type: "recibir_pedido",
      label: "Recepción de Mercadería",
      category: "compras",
      description: "Llegada de insumos desde proveedores",
    },
  ],
  cargos: [
    {
      id: 1,
      name: "administrador",
      role_name: "Administrador General",
      description: "Supervisión total y control de costos",
      is_system: true,
      notification_permissions: {
        merma: true,
        consumo: true,
        conteo: true,
        recibir_pedido: true,
      },
    },
    {
      id: 2,
      name: "supervisor",
      role_name: "Supervisor de Turno",
      description: "Control de piso y autorizaciones",
      is_system: true,
      notification_permissions: {
        merma: true,
        consumo: true,
        conteo: true,
        recibir_pedido: true,
      },
    },
    {
      id: 3,
      name: "chef",
      role_name: "Chef Ejecutivo",
      description: "Operaciones de cocina y recetas",
      is_system: true,
      notification_permissions: {
        merma: true,
        consumo: true,
        conteo: false,
        recibir_pedido: false,
      },
    },
  ],
  rules: [
    {
      cargo: "administrador",
      tipo_solicitud: "merma",
      canal_in_app: true,
      canal_email: true,
      canal_push: false,
      es_aprobador: true,
    },
    {
      cargo: "supervisor",
      tipo_solicitud: "merma",
      canal_in_app: true,
      canal_email: false,
      canal_push: false,
      es_aprobador: true,
    },
    {
      cargo: "chef",
      tipo_solicitud: "consumo",
      canal_in_app: true,
      canal_email: false,
      canal_push: false,
      es_aprobador: true,
    },
  ],
};
