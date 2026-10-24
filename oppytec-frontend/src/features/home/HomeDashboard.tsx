import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Lightbulb,
  BarChart3,
  ArrowRight,
  ShieldCheck,
  ClipboardCheck,
  ShoppingCart,
  Users,
} from "lucide-react";
import { useAuth } from "@/shared/auth/usePermissions";
import { useTheme } from "@/shared/hooks";
import { cn, formatMoney } from "@/shared/lib";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { BodegaBadge } from "@/shared/components/layout/BodegaBadge";

export interface ExecutiveData {
  valor_total_inventario: number;
  porcentaje_merma: number;
  stock_total_unidades: number;
  rotacion_promedio: number;
}

export interface IAInsight {
  tipo: "fuga_dinero" | "sobrestock" | "oportunidad";
  mensaje: string;
  impacto_estimado?: number;
}

export interface LowStockItem {
  producto_id: string;
  nombre: string;
  bodega_nombre?: string;
  bodega_color?: string;
  bodega_icono?: string;
  stock_actual: number;
  stock_minimo: number;
}

export function HomeDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme } = useTheme();
  const isDark = theme === "dark" || theme === "ocean-blue";

  const [loading] = useState(false);
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");

  const [execData] = useState<ExecutiveData>({
    valor_total_inventario: 48500000,
    porcentaje_merma: 2.4,
    stock_total_unidades: 14280,
    rotacion_promedio: 4.8,
  });

  const [insights] = useState<IAInsight[]>([
    {
      tipo: "fuga_dinero",
      mensaje: "Se detectó merma anormal de Salmón Premium en Bodega Cocina Central (+14% vs promedio semanal).",
      impacto_estimado: 245000,
    },
    {
      tipo: "sobrestock",
      mensaje: "Sobrestock en Aceite de Oliva Extra Virgen (45 días de cobertura). Se recomienda congelar compras del ítem.",
      impacto_estimado: 580000,
    },
    {
      tipo: "oportunidad",
      mensaje: "Mejora de margen del 8.2% al consolidar compras de carnes rojas con Proveedor Frigorífico Central.",
      impacto_estimado: 920000,
    },
  ]);

  const [lowStock] = useState<LowStockItem[]>([
    {
      producto_id: "prod-1",
      nombre: "Filete de Res Premium (Lomo Liso)",
      bodega_nombre: "Cámara Fría -18°C",
      bodega_color: "#3b82f6",
      bodega_icono: "Snowflake",
      stock_actual: 4.2,
      stock_minimo: 15.0,
    },
    {
      producto_id: "prod-2",
      nombre: "Crema de Leche Gastronómica 35% MG",
      bodega_nombre: "Bodega Cocina Central",
      bodega_color: "#10b981",
      bodega_icono: "Warehouse",
      stock_actual: 8,
      stock_minimo: 24,
    },
    {
      producto_id: "prod-3",
      nombre: "Vino Cabernet Sauvignon Reserva",
      bodega_nombre: "Barra & Cava",
      bodega_color: "#ec4899",
      bodega_icono: "Wine",
      stock_actual: 3,
      stock_minimo: 12,
    },
    {
      producto_id: "prod-4",
      nombre: "Queso Parmesano D.O.P. Rallado",
      bodega_nombre: "Bodega Cocina Central",
      bodega_color: "#10b981",
      bodega_icono: "Warehouse",
      stock_actual: 1.5,
      stock_minimo: 6.0,
    },
  ]);

  const [pendingApprovals] = useState(2);
  const [enRutaCount] = useState(4);

  const isAdminOrOwner = user?.role === "admin" || user?.role === "propietario" || true;

  const rawDateStr = new Date().toLocaleDateString("es-ES", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const todayStr = rawDateStr.charAt(0).toUpperCase() + rawDateStr.slice(1);

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  };

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="relative z-20 rounded-3xl border border-border bg-card p-6 md:p-8 shadow-xl overflow-hidden">
        {/* Decorative backdrop glow */}
        <div className="absolute inset-0 overflow-hidden rounded-3xl pointer-events-none" aria-hidden="true">
          <div className="absolute -right-20 -top-20 w-80 h-80 rounded-full bg-primary/10 blur-3xl" />
        </div>

        <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest bg-primary/10 text-primary px-3 py-1 rounded-full border border-primary/20">
                {user?.role || "Administrador"}
              </span>
              <AreaSelector
                selectedAreaId={selectedAreaId}
                onSelectArea={setSelectedAreaId}
                buttonClassName="h-8 min-h-0 py-1 px-3 text-[9px] min-w-0"
              />
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-foreground">
              ¡Hola, {user?.firstName || user?.username || "Usuario"}!
            </h1>
            <p className="text-sm text-muted-foreground">{todayStr}</p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-muted-foreground font-medium">Sistema activo</span>
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex h-[40vh] items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Cargando Dashboard...
            </p>
          </div>
        </div>
      ) : (
        <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-8">
          {/* Executive & Owner View */}
          {isAdminOrOwner && (
            <>
              {/* KPIs Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <motion.div
                  variants={itemVariants}
                  onClick={() => navigate("/reportes/resumen-general")}
                  className="p-6 rounded-2xl bg-card border border-border shadow-sm relative overflow-hidden group hover:shadow-md hover:border-primary/40 hover:bg-secondary/20 cursor-pointer transition-all duration-300"
                >
                  <div className="absolute right-4 top-4 text-primary opacity-25 group-hover:scale-110 group-hover:opacity-40 transition-all duration-300">
                    <BarChart3 size={32} />
                  </div>
                  <h3 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest">
                    Valor Inventario
                  </h3>
                  <p className="text-2xl md:text-3xl font-black mt-2 text-foreground">
                    {formatMoney(execData.valor_total_inventario)}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">Activos totales en bodegas</p>
                </motion.div>

                <motion.div
                  variants={itemVariants}
                  onClick={() => navigate("/gestion?tab=mermas")}
                  className="p-6 rounded-2xl bg-card border border-border shadow-sm relative overflow-hidden group hover:shadow-md hover:border-red-500/40 hover:bg-red-500/5 cursor-pointer transition-all duration-300"
                >
                  <div className="absolute right-4 top-4 text-red-500 opacity-25 group-hover:scale-110 group-hover:opacity-40 transition-all duration-300">
                    <AlertTriangle size={32} />
                  </div>
                  <h3 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest">
                    % Merma Actual
                  </h3>
                  <p
                    className={cn(
                      "text-2xl md:text-3xl font-black mt-2",
                      execData.porcentaje_merma > 5 ? "text-red-500" : "text-emerald-500"
                    )}
                  >
                    {execData.porcentaje_merma}%
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">Pérdida sobre inventario total</p>
                </motion.div>

                <motion.div
                  variants={itemVariants}
                  onClick={() => navigate("/gestion?tab=pedidos")}
                  className="p-6 rounded-2xl bg-card border border-border shadow-sm relative overflow-hidden group hover:shadow-md hover:border-emerald-500/40 hover:bg-emerald-500/5 cursor-pointer transition-all duration-300"
                >
                  <div className="absolute right-4 top-4 text-emerald-500 opacity-25 group-hover:scale-110 group-hover:opacity-40 transition-all duration-300">
                    <ShoppingCart size={32} />
                  </div>
                  <h3 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest">
                    Pedidos En Ruta
                  </h3>
                  <p className="text-2xl md:text-3xl font-black mt-2 text-foreground">{enRutaCount}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">Compras emitidas al proveedor</p>
                </motion.div>

                <motion.div
                  variants={itemVariants}
                  onClick={() => navigate("/notificaciones")}
                  className="p-6 rounded-2xl bg-card border border-border shadow-sm relative overflow-hidden group hover:shadow-md hover:border-orange-500/40 hover:bg-orange-500/5 cursor-pointer transition-all duration-300"
                >
                  <div className="absolute right-4 top-4 text-orange-500 opacity-25 group-hover:scale-110 group-hover:opacity-40 transition-all duration-300">
                    <ShieldCheck size={32} />
                  </div>
                  <h3 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest">
                    Pendiente Aprobación
                  </h3>
                  <p
                    className={cn(
                      "text-2xl md:text-3xl font-black mt-2",
                      pendingApprovals > 0 ? "text-orange-500" : "text-foreground"
                    )}
                  >
                    {pendingApprovals}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">Solicitudes de ajuste en cola</p>
                </motion.div>
              </div>

              {/* Main Content Splits */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Decision Panel & AI Insights */}
                <motion.div variants={itemVariants} className="lg:col-span-2 space-y-6">
                  {/* AI Insights Card */}
                  <div className="p-6 rounded-2xl bg-card border border-border shadow-xl space-y-4">
                    <h3 className="font-black text-sm uppercase tracking-widest text-primary flex items-center gap-2">
                      <Lightbulb className="h-5 w-5" />
                      <span>Insights Automáticos (IA)</span>
                    </h3>

                    {insights.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic py-4">
                        No hay recomendaciones adicionales por ahora. Tu inventario está operando de forma óptima.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {insights.map((insight, idx) => (
                          <div
                            key={idx}
                            className={cn(
                              "p-4 rounded-xl border-l-4",
                              insight.tipo === "fuga_dinero" &&
                                (isDark
                                  ? "bg-red-500/10 border-red-500 text-red-200"
                                  : "bg-red-500/10 border-red-500 text-red-950"),
                              insight.tipo === "sobrestock" &&
                                (isDark
                                  ? "bg-yellow-500/10 border-yellow-500 text-yellow-200"
                                  : "bg-yellow-500/10 border-yellow-500 text-yellow-950"),
                              insight.tipo === "oportunidad" &&
                                (isDark
                                  ? "bg-green-500/10 border-green-500 text-green-200"
                                  : "bg-green-500/10 border-green-500 text-green-950")
                            )}
                          >
                            <p className="text-xs font-semibold uppercase tracking-wider opacity-75">
                              {insight.tipo.replace("_", " ")}
                            </p>
                            <p className="text-sm font-medium mt-1 leading-relaxed">{insight.mensaje}</p>
                            {insight.impacto_estimado && (
                              <p className="text-xs font-black mt-2 opacity-80">
                                Impacto financiero estimado: {formatMoney(insight.impacto_estimado)}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Stock Alerts Card */}
                  <div className="p-6 rounded-2xl bg-card border border-border shadow-xl space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-black text-sm uppercase tracking-widest text-destructive flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 animate-bounce-subtle" />
                        <span>Alertas Críticas de Stock</span>
                      </h3>
                      {lowStock.length > 0 && (
                        <span className="text-[10px] font-black uppercase tracking-wider bg-destructive/10 text-destructive px-2 py-0.5 rounded-full border border-destructive/20">
                          {lowStock.length} productos
                        </span>
                      )}
                    </div>

                    {lowStock.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic py-4">
                        No hay productos bajo el stock mínimo en tus bodegas.
                      </p>
                    ) : (
                      <div className="divide-y divide-border max-h-[300px] overflow-y-auto pr-1">
                        {lowStock.map((prod) => (
                          <div
                            key={prod.producto_id}
                            className="flex items-center justify-between py-3"
                          >
                            <div>
                              <p className="font-bold text-sm text-foreground">{prod.nombre}</p>
                              <div className="mt-1">
                                {prod.bodega_nombre ? (
                                  <BodegaBadge
                                    nombre={prod.bodega_nombre}
                                    color={prod.bodega_color}
                                    icono={prod.bodega_icono}
                                  />
                                ) : (
                                  <span className="text-xs text-muted-foreground">
                                    (Múltiples bodegas)
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="font-black text-sm text-red-500">
                                {prod.stock_actual} / {prod.stock_minimo}
                              </p>
                              <span className="text-[9px] font-bold text-muted-foreground uppercase">
                                Stock Actual / Mínimo
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <Link
                      to="/alertas"
                      className="text-xs text-primary font-bold hover:underline flex items-center gap-1 mt-2 w-fit"
                    >
                      <span>Ver todas las alertas</span>
                      <ArrowRight size={12} />
                    </Link>
                  </div>
                </motion.div>

                {/* Quick Actions Panel & Widget Estado del Negocio */}
                <motion.div variants={itemVariants} className="space-y-6">
                  {/* Quick Access */}
                  <div className="p-6 rounded-2xl bg-card border border-border shadow-xl space-y-4">
                    <h3 className="font-black text-sm uppercase tracking-widest text-muted-foreground">
                      Accesos Rápidos
                    </h3>

                    <div className="flex flex-col gap-3">
                      <button
                        type="button"
                        onClick={() => navigate("/gestion?tab=pedidos")}
                        className="touch-target flex items-center gap-3 p-3.5 rounded-xl border border-border hover:bg-muted/40 transition-colors text-left group"
                      >
                        <div className="h-10 w-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                          <ShoppingCart size={20} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm text-foreground">Gestionar Pedidos</p>
                          <p className="text-[10px] text-muted-foreground truncate">
                            Revisar compras y proveedores
                          </p>
                        </div>
                        <ArrowRight size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>

                      <button
                        type="button"
                        onClick={() => navigate("/contar-inventario")}
                        className="touch-target flex items-center gap-3 p-3.5 rounded-xl border border-border hover:bg-muted/40 transition-colors text-left group"
                      >
                        <div className="h-10 w-10 rounded-lg bg-purple-500/10 text-purple-500 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                          <ClipboardCheck size={20} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm text-foreground">Auditar Inventario</p>
                          <p className="text-[10px] text-muted-foreground truncate">
                            Realizar recuento físico ciego
                          </p>
                        </div>
                        <ArrowRight size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>

                      <button
                        type="button"
                        onClick={() => navigate("/reportes/resumen-ejecutivo")}
                        className="touch-target flex items-center gap-3 p-3.5 rounded-xl border border-border hover:bg-muted/40 transition-colors text-left group"
                      >
                        <div className="h-10 w-10 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                          <BarChart3 size={20} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm text-foreground">Reporte Ejecutivo</p>
                          <p className="text-[10px] text-muted-foreground truncate">
                            Métricas financieras y rotación
                          </p>
                        </div>
                        <ArrowRight size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>

                      <button
                        type="button"
                        onClick={() => navigate("/configuracion")}
                        className="touch-target flex items-center gap-3 p-3.5 rounded-xl border border-border hover:bg-muted/40 transition-colors text-left group"
                      >
                        <div className="h-10 w-10 rounded-lg bg-yellow-500/10 text-yellow-500 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                          <Users size={20} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm text-foreground">Ajustes & Usuarios</p>
                          <p className="text-[10px] text-muted-foreground truncate">
                            Configurar local y accesos
                          </p>
                        </div>
                        <ArrowRight size={14} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                    </div>
                  </div>

                  {/* Widget Estado del Negocio */}
                  <div className="p-6 rounded-2xl bg-card border border-border shadow-xl space-y-4">
                    <h3 className="font-black text-sm uppercase tracking-widest text-muted-foreground">
                      Estado del Negocio
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground font-medium">Unidades en stock</span>
                        <span className="font-bold tabular-nums text-foreground">
                          {execData.stock_total_unidades.toLocaleString("es-CL")}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground font-medium">Rotación mensual prom.</span>
                        <span className="font-bold tabular-nums text-foreground">
                          {execData.rotacion_promedio} veces
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground font-medium">Mermas Críticas</span>
                        <span
                          className={cn(
                            "font-bold tabular-nums",
                            lowStock.length > 5 ? "text-red-500 font-black" : "text-emerald-500"
                          )}
                        >
                          {lowStock.length > 5 ? "ALTO" : "NORMAL"}
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>
            </>
          )}
        </motion.div>
      )}
    </div>
  );
}

export default HomeDashboard;
