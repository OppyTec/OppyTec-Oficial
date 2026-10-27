/**
 * oppytec-frontend/src/features/oppyfy/OppyfyWorkspacePage.tsx
 * Espacio de Trabajo Unificado e Inmersivo OppyFy / OppyBot Workspace (v2.0):
 * - Pantalla completa viewport-height (100% de la altura y ancho)
 * - Layout de 3 columnas (Sidebar de Hilos y Especialistas, Chat Inmersivo Central, Canvas Split-View Derecho)
 * - Ticker superior de citas célebres gastronómicas/empresariales (getRandomQuote)
 * - Especialistas gastronómicos: General (Oppy), Chef (Recetas & Costos), Stock (Inventario & Bodegas),
 *   Supply (Compras & Proveedores), Manager (Gestión & Eventos)
 * - Medidor semafórico de contexto (<65% verde, 66-85% ámbar, >85% rojo con Anti-Hallucination Guard y rollover al 5%)
 * - SmartNavLink: Enlaces interactivos con icono Compass para abrir vistas en nueva pestaña o ventana actual
 * - Tarjetas de cotizaciones multitienda (ShoppingCardsView) y confirmación de mermas/órdenes (ActionConfirmationCard)
 * - Split-View Canvas con tablas filtrables, exportación CSV, impresión PDF y gráficos Recharts
 * - Modal de Gobernanza y Ajustes OppyFy (dominios editables, permisos temporales, billetera y visor de auditoría)
 * - Cumplimiento estricto: Regla "Pollo King", Decimal FX CLP/USD, y cero setInterval
 */

import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Send,
  Sparkles,
  ChefHat,
  Package,
  Truck,
  TrendingUp,
  BarChart2,
  FileText,
  Bot,
  Pin,
  ChevronRight,
  ChevronLeft,
  Folder,
  Maximize2,
  Minimize2,
  Paperclip,
  X,
  SlidersHorizontal,
  Download,
  Printer,
  Search,
  ShieldAlert,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { toast } from "sonner";
import { useAuth } from "@/shared/auth/usePermissions";
import { ContextHealthMeter } from "./components/ContextHealthMeter";
import { OppyfyRolloverModal } from "./components/OppyfyRolloverModal";
import { OppyfyGovernancePanel } from "./components/governance/OppyfyGovernancePanel";
import { SmartNavLink } from "./components/SmartNavLink";
import { ActionConfirmationCard, type ActionDraftCard } from "./components/ActionConfirmationCard";
import { ShoppingCardsView, type ShoppingProduct } from "./components/ShoppingCardsView";
import { getRandomQuote, type Quote } from "./quotes";
import {
  calculateContextHealth,
  FRESH_THREAD_CONTEXT_PCT,
  type CanvasArtifact,
} from "./types";

export type SpecialistAgentType = "general" | "chef" | "stock" | "supply" | "manager";

export interface SpecialistAgentProfile {
  readonly id: SpecialistAgentType;
  readonly name: string;
  readonly role_title: string;
  readonly color: string;
  readonly welcome_message: string;
  readonly suggested_questions: readonly string[];
}

export const SPECIALIST_AGENTS: Record<SpecialistAgentType, SpecialistAgentProfile> = {
  general: {
    id: "general",
    name: "Oppy",
    role_title: "Asistente Universal & Tutor de OppyTec",
    color: "#10B981", // Verde
    welcome_message:
      "¡Hola! Soy Oppy, tu asistente integral. Puedo responder dudas de cualquier área, enseñarte a usar cada sección de OppyTec paso a paso o coordinar con mis agentes especializados.",
    suggested_questions: [
      "¿Cómo creo un producto o empaque a granel?",
      "¿Cómo funciona el costeo FIFO por capas?",
      "¿Cuáles son los productos con stock crítico?",
      "Explícame las reglas de cálculo de costos del sistema",
    ],
  },
  chef: {
    id: "chef",
    name: "Oppy Chef",
    role_title: "Especialista en Recetas, Costos y Escandallos",
    color: "#F97316", // Naranja
    welcome_message:
      "¡Hola, Chef! Soy Oppy Chef. Te ayudo a costear recetas, calcular el PPP de tus ingredientes, proyectar mermas y optimizar el margen del menú de Pollo King.",
    suggested_questions: [
      "¿Cuál es la fórmula del Precio Promedio Ponderado (PPP)?",
      "¿Cómo calculo el costo y margen de una receta en Pollo King?",
      "¿Cómo registro las mermas de producción?",
      "Recomiéndame cómo fijar el precio de venta de un plato",
    ],
  },
  stock: {
    id: "stock",
    name: "Oppy Stock",
    role_title: "Especialista en Inventario, Bodegas y Vencimientos",
    color: "#10B981", // Verde
    welcome_message:
      "¡Hola! Soy Oppy Stock, tu especialista en inventario. Monitoreo niveles críticos de stock, quiebres de bodega, lotes próximos a vencer (FEFO) y valorización de inventario.",
    suggested_questions: [
      "¿Qué productos están en stock crítico o agotados hoy?",
      "¿Qué lotes vencen en los próximos 7 días?",
      "¿Cómo realizo un recuento de inventario?",
      "Explícame cómo funciona la rotación FEFO",
    ],
  },
  supply: {
    id: "supply",
    name: "Oppy Supply",
    role_title: "Especialista en Compras, Proveedores y Facturas",
    color: "#3B82F6", // Azul
    welcome_message:
      "¡Hola! Soy Oppy Supply. Te ayudo a gestionar órdenes de compra, comparar precios históricos con proveedores de Pollo King, auditar facturas y generar sugerencias de abastecimiento.",
    suggested_questions: [
      "¿Qué proveedores tienen mejores precios históricos para Pollo King?",
      "¿Cómo creo una orden de compra o pedido?",
      "¿Qué compras están pendientes de recepción?",
      "¿Cómo se cargan las facturas al sistema?",
    ],
  },
  manager: {
    id: "manager",
    name: "Oppy Manager",
    role_title: "Especialista en Control Operacional y Eventos",
    color: "#8B5CF6", // Púrpura
    welcome_message:
      "¡Saludos! Soy Oppy Manager. Analizo la visión global de tu negocio: márgenes operacionales, eventos programados, ratios de eficiencia y resúmenes ejecutivos.",
    suggested_questions: [
      "¿Qué eventos tenemos programados esta semana?",
      "Dame un resumen ejecutivo del estado del negocio Pollo King",
      "¿Cuáles son los productos con mayor pérdida o merma?",
      "¿Cómo puedo mejorar la eficiencia operacional?",
    ],
  },
};

export const SPECIALIST_ICONS: Record<
  SpecialistAgentType,
  React.ComponentType<{ className?: string; style?: React.CSSProperties }>
> = {
  general: Sparkles,
  chef: ChefHat,
  stock: Package,
  supply: Truck,
  manager: TrendingUp,
};

export interface WorkspaceThread {
  id: string;
  agent_type: SpecialistAgentType;
  title: string;
  is_pinned: boolean;
  created_at: string;
  updated_at?: string;
  sections?: string[];
}

export interface WorkspaceAttachment {
  filename: string;
  file_type: string;
  size_bytes: number;
}

export interface WorkspaceChatMessage {
  id: string;
  sender: "user" | "assistant";
  agent_name?: string;
  content: string;
  attachment?: WorkspaceAttachment | null;
  canvasArtifact?: CanvasArtifact | null;
  suggested_actions?: string[];
  shopping_cards?: ShoppingProduct[];
  action_card?: ActionDraftCard | null;
  created_at: string;
  isStreaming?: boolean;
}

const DEFAULT_THREADS: WorkspaceThread[] = [
  {
    id: "th-1",
    agent_type: "chef",
    title: "Escandallo y Costeo Pollo King",
    is_pinned: true,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    sections: ["Recetas & Costos"],
  },
  {
    id: "th-2",
    agent_type: "stock",
    title: "Auditoría FEFO Pollo King Central",
    is_pinned: true,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    sections: ["Inventario & Stock"],
  },
  {
    id: "th-3",
    agent_type: "general",
    title: "Inducción al Sistema OppyTec v2.0",
    is_pinned: false,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    sections: ["General"],
  },
];

export function OppyfyWorkspacePage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Estados de Agente y Navegación
  const [currentAgent, setCurrentAgent] = useState<SpecialistAgentType>("general");
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<SpecialistAgentType | "all">("all");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isNewChatModalOpen, setIsNewChatModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isRolloverModalOpen, setIsRolloverModalOpen] = useState(false);

  // Estados de Hilos y Mensajes
  const [threads, setThreads] = useState<WorkspaceThread[]>(DEFAULT_THREADS);
  const [activeThreadId, setActiveThreadId] = useState<string>("th-1");
  const [messages, setMessages] = useState<WorkspaceChatMessage[]>([
    {
      id: "msg-init-1",
      sender: "assistant",
      agent_name: "Oppy Chef",
      content:
        "¡Hola! He cargado los datos del escandallo operativo de Pollo King. El costeo teórico bajo metodología PPP se encuentra optimizado en $3.850 CLP por ración. Puedes revisar el desglose en el panel Canvas lateral o consultar la vista de [Recetas & Escandallos](/recipes).",
      created_at: new Date().toISOString(),
      canvasArtifact: {
        type: "table",
        title: "Escandallo Pollo King Crujiente (PPP)",
        data: [
          { ingrediente: "Pechuga de Pollo Fresca", cantidad: "0.250 kg", costo_unit_clp: 1850, merma_pct: "4.5%" },
          { ingrediente: "Harina Especial Apando", cantidad: "0.080 kg", costo_unit_clp: 420, merma_pct: "1.2%" },
          { ingrediente: "Mix Especias Secretas", cantidad: "0.015 kg", costo_unit_clp: 380, merma_pct: "0.0%" },
          { ingrediente: "Aceite Alto Rendimiento", cantidad: "0.050 L", costo_unit_clp: 650, merma_pct: "2.0%" },
          { ingrediente: "Empaque Térmico Biodegradable", cantidad: "1 ud", costo_unit_clp: 550, merma_pct: "0.0%" },
        ],
        summary: "Cálculo en base a lotes FEFO ingresados en la última recepción de bodega.",
      },
      suggested_actions: [
        "¿Cómo registro una merma de producción?",
        "Ver cotizaciones de harina en proveedores",
        "Calcular margen bruto con precio de venta",
      ],
      shopping_cards: [
        {
          title: "Harina Especial Apando 25kg",
          price_clp: 28990,
          vendor: "Molinos del Sur",
          product_url: "https://ejemplo.cl/harina",
          image_url: "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300",
        },
        {
          title: "Aceite Vegetal Frigofry 20L",
          price_clp: 34500,
          vendor: "Distribuidora Central",
          product_url: "https://ejemplo.cl/aceite",
          image_url: "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=300",
        },
      ],
    },
  ]);

  // Mensaje y entrada
  const [inputMessage, setInputMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAttachment, setCurrentAttachment] = useState<WorkspaceAttachment | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Frase inspiracional gastronómica
  const [currentQuote, setCurrentQuote] = useState<Quote>(() => getRandomQuote());

  // Estados de salud de contexto y créditos
  const [contextPct, setContextPct] = useState<number>(38);
  const [remainingCredits, setRemainingCredits] = useState<number>(10000);

  // Estados del Split-View Canvas
  const [isCanvasOpen, setIsCanvasOpen] = useState(true);
  const [activeArtifact, setActiveArtifact] = useState<CanvasArtifact | null>(
    messages[0]?.canvasArtifact ?? null
  );
  const [canvasFilter, setCanvasFilter] = useState("");
  const [isCanvasFullscreen, setIsCanvasFullscreen] = useState(false);

  const contextHealth = calculateContextHealth(contextPct);

  // Scroll automático
  useEffect(() => {
    if (typeof chatEndRef.current?.scrollIntoView === "function") {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming]);

  // Volver al sistema
  const handleBackToSystem = () => {
    navigate(-1);
  };

  // Crear nueva conversación
  const handleCreateNewThread = (agentType: SpecialistAgentType = "general") => {
    const agentCfg = SPECIALIST_AGENTS[agentType];
    const sectionName = agentCfg.role_title.split("&")[0]?.trim() || "General";
    const newTh: WorkspaceThread = {
      id: `th-${Date.now()}`,
      agent_type: agentType,
      title: `Consulta con ${agentCfg.name}`,
      is_pinned: false,
      created_at: new Date().toISOString(),
      sections: [sectionName],
    };
    setThreads((prev) => [newTh, ...prev]);
    setActiveThreadId(newTh.id);
    setCurrentAgent(agentType);
    setMessages([]);
    setActiveArtifact(null);
    setCurrentQuote(getRandomQuote());
    setContextPct(FRESH_THREAD_CONTEXT_PCT);
  };

  // Fijar/Desfijar hilo
  const handleTogglePin = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    setThreads((prev) =>
      prev.map((t) => (t.id === threadId ? { ...t, is_pinned: !t.is_pinned } : t))
    );
    toast.success("Estado de fijado actualizado");
  };

  // Eliminar hilo
  const handleDeleteThread = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    setThreads((prev) => prev.filter((t) => t.id !== threadId));
    if (activeThreadId === threadId) {
      const remaining = threads.filter((t) => t.id !== threadId);
      if (remaining.length > 0 && remaining[0]) {
        setActiveThreadId(remaining[0].id);
        setCurrentAgent(remaining[0].agent_type);
      } else {
        handleCreateNewThread("general");
      }
    }
    toast.success("Conversación eliminada");
  };

  // Subir archivo adjunto
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowed = [".pdf", ".xlsx", ".xls", ".csv", ".docx", ".pptx", ".txt", ".md"];
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
    if (!allowed.includes(ext)) {
      toast.error(`Formato '${ext}' no soportado.`);
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      toast.error("El archivo excede los 15 MB permitidos.");
      return;
    }
    setCurrentAttachment({
      filename: file.name,
      file_type: ext,
      size_bytes: file.size,
    });
    toast.success(`Archivo '${file.name}' adjuntado.`);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Enviar mensaje
  const handleSendMessage = async (customPrompt?: string) => {
    const prompt = (customPrompt || inputMessage).trim();
    if ((!prompt && !currentAttachment) || isStreaming) return;

    if (contextHealth.isAntiHallucinationBlocked) {
      toast.error("El contexto del hilo superó el 85%. Realiza un rollover a hilo fresco.");
      setIsRolloverModalOpen(true);
      return;
    }

    const attachmentToSend = currentAttachment;
    setCurrentAttachment(null);
    setInputMessage("");

    const userMsg: WorkspaceChatMessage = {
      id: `msg-user-${Date.now()}`,
      sender: "user",
      content: prompt || (attachmentToSend ? `Documento adjunto: ${attachmentToSend.filename}` : ""),
      attachment: attachmentToSend,
      created_at: new Date().toISOString(),
    };

    const assistantMsgId = `msg-asst-${Date.now()}`;
    const assistantMsgPlaceholder: WorkspaceChatMessage = {
      id: assistantMsgId,
      sender: "assistant",
      agent_name: SPECIALIST_AGENTS[currentAgent].name,
      content: "",
      isStreaming: true,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsgPlaceholder]);
    setIsStreaming(true);

    // Deducir créditos y calcular incremento de contexto
    setRemainingCredits((prev) => Math.max(0, prev - 15));
    setContextPct((prev) => Math.min(100, Math.round((prev + 3.2) * 10) / 10));

    // Simulación reactiva
    const answerText = `He analizado tu consulta para ${SPECIALIST_AGENTS[currentAgent].name} en Pollo King.\n\n• Operación procesada con éxito bajo estándares FEFO y PPP.\n• Puedes consultar el detalle en [Kardex & Inventario](/inventario) o revisar las [Recetas de Pollo King](/recipes).\n\n$$\\text{PPP} = \\frac{\\text{Valor Total Existencias}}{\\text{Stock Disponible}}$$`;

    await new Promise((resolve) => setTimeout(resolve, 350));

    const generatedArtifact: CanvasArtifact = {
      type: "chart",
      chartType: "bar",
      title: "Costos Teóricos vs Reales — Pollo King",
      summary: "Comparativa de costos semanales por ingrediente",
      data: [
        { name: "Pechuga", teorico: 1850, real: 1920 },
        { name: "Harina", teorico: 420, real: 410 },
        { name: "Aceite", teorico: 650, real: 670 },
        { name: "Empaque", teorico: 550, real: 550 },
      ],
    };

    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantMsgId
          ? {
              ...m,
              content: answerText,
              isStreaming: false,
              canvasArtifact: generatedArtifact,
              suggested_actions: [
                "Generar borrador de compra",
                "Ver proveedores recomendados",
                "Exportar tabla a CSV",
              ],
            }
          : m
      )
    );

    setActiveArtifact(generatedArtifact);
    setIsStreaming(false);
  };

  // Exportar CSV del Canvas
  const handleExportCSV = () => {
    if (!activeArtifact || !Array.isArray(activeArtifact.data) || activeArtifact.data.length === 0) {
      toast.error("No hay datos tabulares para exportar.");
      return;
    }
    const data = activeArtifact.data as Array<Record<string, unknown>>;
    const firstRow = data[0];
    if (!firstRow) return;
    const headers = Object.keys(firstRow).join(",");
    const rows = data.map((item) => Object.values(item).join(",")).join("\n");
    const csvContent = "data:text/csv;charset=utf-8," + encodeURI(`${headers}\n${rows}`);
    const link = document.createElement("a");
    link.setAttribute("href", csvContent);
    link.setAttribute("download", `${activeArtifact.title.toLowerCase().replace(/\s+/g, "_")}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("CSV exportado exitosamente");
  };

  // Imprimir PDF
  const handlePrintPDF = () => {
    window.print();
  };

  // Filtrado de Hilos
  const filteredThreads = threads.filter((t) => {
    if (selectedAgentFilter === "all") return true;
    return t.agent_type === selectedAgentFilter;
  });
  const pinnedThreads = filteredThreads.filter((t) => t.is_pinned);
  const unpinnedThreads = filteredThreads.filter((t) => !t.is_pinned);

  const ActiveAgentIcon = SPECIALIST_ICONS[currentAgent];

  return (
    <div
      data-testid="oppyfy-workspace-page"
      className="fixed inset-0 z-50 w-full h-full flex flex-col bg-background text-foreground overflow-hidden select-none"
    >
      {/* ======================================================== */}
      {/* 1. TOP WORKSPACE NAVIGATION BAR */}
      {/* ======================================================== */}
      <header className="h-14 border-b border-border bg-card/70 backdrop-blur-md px-4 flex items-center justify-between shrink-0 z-30 relative">
        {/* Left: Volver al sistema */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            data-testid="workspace-back-btn"
            onClick={handleBackToSystem}
            className="touch-target inline-flex min-h-[44px] items-center gap-1.5 px-3 rounded-xl border border-border bg-card hover:bg-secondary text-xs font-semibold text-foreground transition-all cursor-pointer"
            title="Volver a la vista anterior"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Volver al sistema</span>
          </button>
        </div>

        {/* Center: Agent Title & Subtitle */}
        <div className="flex items-center gap-2.5 max-w-[45%] text-center truncate">
          <div
            className="p-1.5 rounded-lg shrink-0"
            style={{
              backgroundColor: `${SPECIALIST_AGENTS[currentAgent].color}20`,
              color: SPECIALIST_AGENTS[currentAgent].color,
            }}
          >
            <ActiveAgentIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0 text-left">
            <h2 className="text-sm font-bold text-foreground truncate">
              {SPECIALIST_AGENTS[currentAgent].name}
            </h2>
            <p className="text-[10px] text-muted-foreground truncate uppercase font-semibold">
              {SPECIALIST_AGENTS[currentAgent].role_title}
            </p>
          </div>
        </div>

        {/* Right Header Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Medidor Semafórico de Contexto */}
          <div className="hidden md:flex items-center gap-2">
            <ContextHealthMeter
              contextHealth={contextHealth}
              onOpenRolloverModal={() => setIsRolloverModalOpen(true)}
            />
          </div>

          {/* Bolsa de Créditos */}
          <div
            data-testid="credits-balance-badge"
            className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-primary/10 border border-primary/20 text-xs font-bold text-primary font-mono"
            title="Saldo de créditos disponibles sin caducidad"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{remainingCredits.toLocaleString("es-CL")} créditos</span>
          </div>

          {/* Canvas Split-View Toggle Button */}
          <button
            type="button"
            data-testid="toggle-split-canvas-btn"
            onClick={() => setIsCanvasOpen(!isCanvasOpen)}
            className={`touch-target inline-flex min-h-[44px] items-center gap-1.5 px-3 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
              isCanvasOpen
                ? "border-primary bg-primary/15 text-primary"
                : "border-border bg-card text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`}
            title="Alternar panel Canvas"
          >
            <BarChart2 className="w-4 h-4" />
            <span className="hidden lg:inline">Canvas</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </button>

          {/* Configuración & Gobernanza */}
          <button
            type="button"
            data-testid="oppyfy-settings-btn"
            onClick={() => setIsSettingsOpen(true)}
            className="touch-target inline-flex min-h-[44px] items-center gap-1.5 px-3 rounded-xl border border-border bg-card hover:bg-secondary text-xs font-semibold text-foreground transition-all cursor-pointer"
            title="Ajustes de Gobernanza OppyFy"
          >
            <SlidersHorizontal className="w-4 h-4 text-primary" />
            <span className="hidden sm:inline">Gobernanza</span>
          </button>

          {/* Indicador de Usuario */}
          <div className="text-xs text-muted-foreground hidden xl:block bg-secondary/50 px-2.5 py-1 rounded-lg">
            Usuario: <span className="font-semibold text-foreground">{user?.firstName || user?.username || "Pollo King Admin"}</span>
          </div>
        </div>
      </header>

      {/* ======================================================== */}
      {/* 2. MAIN 3-COLUMN WORKSPACE BODY */}
      {/* ======================================================== */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* LEFT SIDEBAR: THREADS & SPECIALIST FILTER */}
        <aside
          data-testid="oppyfy-sidebar"
          className={`border-r border-border bg-card/40 flex flex-col shrink-0 transition-all duration-300 ease-in-out relative overflow-hidden ${
            isSidebarCollapsed ? "w-16" : "w-72"
          }`}
        >
          {/* Sidebar Top: Collapse & New Chat */}
          <div className="p-3 border-b border-border space-y-2.5 shrink-0">
            <div className={`flex items-center ${isSidebarCollapsed ? "justify-center" : "justify-between"}`}>
              {!isSidebarCollapsed && (
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80 px-1">
                  Conversaciones
                </span>
              )}
              <button
                type="button"
                data-testid="toggle-sidebar-btn"
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-border/80 bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary transition-all cursor-pointer"
                title={isSidebarCollapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
              >
                {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
              </button>
            </div>

            {/* Botón Nueva Conversación */}
            <button
              type="button"
              data-testid="new-thread-btn"
              onClick={() => setIsNewChatModalOpen(true)}
              className={`touch-target min-h-[44px] w-full rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer ${
                isSidebarCollapsed ? "px-0" : "px-3"
              }`}
              title="Iniciar nueva conversación"
            >
              <Plus className="w-4 h-4 shrink-0" />
              {!isSidebarCollapsed && <span>Nueva conversación</span>}
            </button>

            {/* Selector de Especialistas (Filtro) */}
            {!isSidebarCollapsed && (
              <div
                data-testid="agent-filter-tabs"
                className="grid grid-cols-6 gap-1 p-1 bg-secondary/50 rounded-xl"
              >
                <button
                  type="button"
                  data-testid="filter-tab-all"
                  onClick={() => setSelectedAgentFilter("all")}
                  className={`h-7 rounded-lg text-[10px] font-medium transition-colors flex items-center justify-center cursor-pointer ${
                    selectedAgentFilter === "all"
                      ? "bg-background shadow-xs text-foreground font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="Todos los hilos"
                >
                  Todos
                </button>
                {(["general", "chef", "stock", "supply", "manager"] as SpecialistAgentType[]).map((key) => {
                  const cfg = SPECIALIST_AGENTS[key];
                  const Icon = SPECIALIST_ICONS[key];
                  const isSelected = selectedAgentFilter === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      data-testid={`filter-tab-${key}`}
                      onClick={() => {
                        setSelectedAgentFilter(key);
                        setCurrentAgent(key);
                      }}
                      className={`h-7 rounded-lg transition-colors flex items-center justify-center cursor-pointer ${
                        isSelected ? "bg-background shadow-xs font-semibold" : "text-muted-foreground hover:text-foreground"
                      }`}
                      style={{
                        color: isSelected ? cfg.color : undefined,
                        backgroundColor: isSelected ? `${cfg.color}20` : undefined,
                      }}
                      title={cfg.name}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Lista de Hilos */}
          <div className="flex-1 overflow-y-auto p-2.5 space-y-3">
            {/* Pinned Section */}
            {pinnedThreads.length > 0 && (
              <div className="space-y-1">
                {!isSidebarCollapsed && (
                  <div className="px-2 py-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                    <Pin className="w-3 h-3 fill-muted-foreground/70" />
                    <span>Fijadas</span>
                  </div>
                )}
                {pinnedThreads.map((th) => (
                  <div
                    key={th.id}
                    data-testid={`thread-item-${th.id}`}
                    onClick={() => {
                      setActiveThreadId(th.id);
                      setCurrentAgent(th.agent_type);
                    }}
                    className={`group rounded-xl cursor-pointer transition-all border p-2.5 flex items-center justify-between gap-2 ${
                      th.id === activeThreadId
                        ? "bg-secondary/80 border-primary/40 text-primary shadow-xs"
                        : "border-transparent hover:bg-secondary/40 text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold truncate leading-snug">{th.title}</p>
                      {!isSidebarCollapsed && (
                        <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-muted-foreground">
                          <Folder className="w-2.5 h-2.5 opacity-60 shrink-0" />
                          <span className="truncate">{th.sections?.[0] || "General"}</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        data-testid={`thread-pin-${th.id}`}
                        onClick={(e) => handleTogglePin(e, th.id)}
                        className="p-1 rounded hover:bg-secondary text-emerald-500 transition-colors"
                        title="Desfijar conversación"
                      >
                        <Pin className="w-3 h-3 fill-emerald-500" />
                      </button>
                      <button
                        type="button"
                        data-testid={`thread-delete-${th.id}`}
                        onClick={(e) => handleDeleteThread(e, th.id)}
                        className="p-1 rounded hover:bg-destructive/10 hover:text-destructive text-muted-foreground transition-colors"
                        title="Eliminar conversación"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Recientes Section */}
            {unpinnedThreads.length > 0 && (
              <div className="space-y-1">
                {!isSidebarCollapsed && (
                  <div className="px-2 pt-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                    <span>Recientes</span>
                  </div>
                )}
                {unpinnedThreads.map((th) => (
                  <div
                    key={th.id}
                    data-testid={`thread-item-${th.id}`}
                    onClick={() => {
                      setActiveThreadId(th.id);
                      setCurrentAgent(th.agent_type);
                    }}
                    className={`group rounded-xl cursor-pointer transition-all border p-2.5 flex items-center justify-between gap-2 ${
                      th.id === activeThreadId
                        ? "bg-secondary/80 border-primary/40 text-primary shadow-xs"
                        : "border-transparent hover:bg-secondary/40 text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold truncate leading-snug">{th.title}</p>
                      {!isSidebarCollapsed && (
                        <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-muted-foreground">
                          <Folder className="w-2.5 h-2.5 opacity-60 shrink-0" />
                          <span className="truncate">{th.sections?.[0] || "General"}</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        data-testid={`thread-pin-${th.id}`}
                        onClick={(e) => handleTogglePin(e, th.id)}
                        className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                        title="Fijar conversación"
                      >
                        <Pin className="w-3 h-3" />
                      </button>
                      <button
                        type="button"
                        data-testid={`thread-delete-${th.id}`}
                        onClick={(e) => handleDeleteThread(e, th.id)}
                        className="p-1 rounded hover:bg-destructive/10 hover:text-destructive text-muted-foreground transition-colors"
                        title="Eliminar conversación"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* CENTER: INMERSIVE CHAT PANEL */}
        <main
          data-testid="oppyfy-chat-main-pane"
          className="flex-1 flex flex-col min-w-0 bg-background overflow-hidden relative"
        >
          {/* Ticker Superior de Citas Célebres */}
          <div
            data-testid="quote-ticker-banner"
            className="h-8 px-4 border-b border-border/60 bg-secondary/30 flex items-center justify-center text-center shrink-0"
          >
            <p className="text-[11px] text-muted-foreground truncate italic">
              «{currentQuote.text}» <span className="font-semibold not-italic">— {currentQuote.author}</span>
            </p>
          </div>

          {/* Banner de Advertencia de Salud de Contexto (>85%) */}
          {contextHealth.isAntiHallucinationBlocked && (
            <div
              data-testid="anti-hallucination-warning-banner"
              role="alert"
              className="m-3 p-3 rounded-xl border border-destructive/40 bg-destructive/10 flex items-center justify-between gap-3 text-xs text-destructive shrink-0"
            >
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <span className="font-semibold">
                  Anti-Hallucination Guard: Contexto al {contextHealth.pct}%. Rollover requerido para evitar alucinaciones.
                </span>
              </div>
              <button
                type="button"
                data-testid="banner-rollover-btn"
                onClick={() => setIsRolloverModalOpen(true)}
                className="touch-target inline-flex min-h-[44px] items-center px-3 py-1.5 rounded-lg bg-destructive text-destructive-foreground font-bold shadow-xs hover:opacity-95"
              >
                Nuevo Hilo (5%)
              </button>
            </div>
          )}

          {/* Área de Mensajes del Chat */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-4 my-auto">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                  style={{
                    backgroundColor: `${SPECIALIST_AGENTS[currentAgent].color}20`,
                    color: SPECIALIST_AGENTS[currentAgent].color,
                  }}
                >
                  <ActiveAgentIcon className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-xl font-bold">{SPECIALIST_AGENTS[currentAgent].name}</h3>
                  <p
                    className="text-xs font-semibold uppercase tracking-wider mt-1"
                    style={{ color: SPECIALIST_AGENTS[currentAgent].color }}
                  >
                    {SPECIALIST_AGENTS[currentAgent].role_title}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
                    {SPECIALIST_AGENTS[currentAgent].welcome_message}
                  </p>
                </div>

                {/* Preguntas Sugeridas Grid */}
                <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-2 text-left pt-2">
                  {SPECIALIST_AGENTS[currentAgent].suggested_questions.map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      data-testid={`suggested-question-${idx}`}
                      onClick={() => handleSendMessage(q)}
                      className="p-3 rounded-xl border border-border bg-card hover:bg-secondary/70 transition-all text-xs text-foreground/90 flex items-start gap-2 shadow-xs cursor-pointer group"
                    >
                      <span style={{ color: SPECIALIST_AGENTS[currentAgent].color }}>
                        <ActiveAgentIcon className="w-4 h-4 shrink-0 mt-0.5" />
                      </span>
                      <span className="line-clamp-2 leading-snug">{q}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => {
                const isUser = msg.sender === "user";
                return (
                  <div
                    key={msg.id}
                    data-testid={`chat-message-${msg.id}`}
                    className={`flex flex-col gap-1.5 max-w-4xl w-full ${
                      isUser ? "ml-auto items-end" : "mr-auto items-start"
                    }`}
                  >
                    {!isUser && (
                      <div className="flex items-center gap-2 px-1">
                        <div
                          className="w-5 h-5 rounded-md flex items-center justify-center text-[10px]"
                          style={{
                            backgroundColor: `${SPECIALIST_AGENTS[currentAgent].color}20`,
                            color: SPECIALIST_AGENTS[currentAgent].color,
                          }}
                        >
                          <ActiveAgentIcon className="w-3 h-3" />
                        </div>
                        <span
                          className="text-xs font-semibold"
                          style={{ color: SPECIALIST_AGENTS[currentAgent].color }}
                        >
                          {msg.agent_name || SPECIALIST_AGENTS[currentAgent].name}
                        </span>
                        {msg.isStreaming && (
                          <span className="text-[10px] text-muted-foreground animate-pulse">
                            escribiendo...
                          </span>
                        )}
                      </div>
                    )}

                    <div
                      className={`p-4 rounded-2xl text-xs md:text-sm leading-relaxed shadow-xs ${
                        isUser
                          ? "bg-primary text-primary-foreground rounded-tr-none max-w-xl"
                          : "bg-card border border-border text-foreground rounded-tl-none w-full"
                      }`}
                    >
                      {/* Adjunto si existe */}
                      {msg.attachment && (
                        <div className="mb-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary border border-border text-xs font-medium">
                          <FileText className="w-3.5 h-3.5 text-primary" />
                          <span>{msg.attachment.filename}</span>
                        </div>
                      )}

                      {/* Contenido formateado con soporte para SmartNavLink y fórmulas */}
                      <div className="whitespace-pre-wrap leading-relaxed space-y-2">
                        {msg.content}
                      </div>

                      {/* SmartNavLinks en la respuesta */}
                      {!isUser && (
                        <div className="pt-2 flex flex-wrap gap-2">
                          <SmartNavLink href="/recipes">Recetas Pollo King</SmartNavLink>
                          <SmartNavLink href="/inventario">Kardex Bodega</SmartNavLink>
                          <SmartNavLink href="/proveedores">Cotizaciones Compras</SmartNavLink>
                        </div>
                      )}

                      {/* Cotizaciones Multitienda */}
                      {msg.shopping_cards && (
                        <ShoppingCardsView products={msg.shopping_cards} />
                      )}

                      {/* Tarjetas de Acción Human-in-the-Loop */}
                      {msg.action_card && (
                        <ActionConfirmationCard card={msg.action_card} />
                      )}

                      {/* Botón para abrir artefacto en Canvas */}
                      {!isUser && msg.canvasArtifact && (
                        <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
                          <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                            <BarChart2 className="w-3.5 h-3.5 text-primary" />
                            Visualización disponible: {msg.canvasArtifact.title}
                          </span>
                          <button
                            type="button"
                            data-testid="open-canvas-artifact-btn"
                            onClick={() => {
                              setActiveArtifact(msg.canvasArtifact!);
                              setIsCanvasOpen(true);
                            }}
                            className="touch-target inline-flex min-h-[44px] items-center gap-1 px-3 rounded-lg border border-border hover:bg-secondary text-xs font-semibold text-foreground cursor-pointer"
                          >
                            <Maximize2 className="w-3.5 h-3.5" />
                            <span>Abrir en Canvas</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Chips de Sugerencias Rápidas */}
                    {!isUser && msg.suggested_actions && (
                      <div className="flex flex-wrap gap-1.5 mt-1 pl-1">
                        {msg.suggested_actions.slice(0, 3).map((sugg, sIdx) => (
                          <button
                            key={sIdx}
                            type="button"
                            data-testid={`quick-chip-${sIdx}`}
                            onClick={() => handleSendMessage(sugg)}
                            className="touch-target inline-flex min-h-[44px] items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border border-border bg-card hover:bg-secondary text-foreground transition-all cursor-pointer shadow-2xs"
                          >
                            <Sparkles className="w-3 h-3 text-primary" />
                            <span>{sugg}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Barra de Entrada Inferior */}
          <div className="p-3 md:px-4 border-t border-border bg-card/50 shrink-0">
            {currentAttachment && (
              <div className="max-w-4xl mx-auto mb-2 flex items-center gap-2">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/10 border border-primary/20 text-xs text-foreground">
                  <FileText className="w-4 h-4 text-primary" />
                  <span className="font-semibold text-primary">{currentAttachment.filename}</span>
                  <button
                    type="button"
                    onClick={() => setCurrentAttachment(null)}
                    className="p-1 hover:text-destructive"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="max-w-4xl mx-auto flex items-center gap-2"
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".pdf,.xlsx,.xls,.csv,.docx,.pptx,.txt,.md"
                onChange={handleFileChange}
              />

              <button
                type="button"
                data-testid="chat-attachment-btn"
                onClick={() => fileInputRef.current?.click()}
                className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-all cursor-pointer"
                title="Adjuntar documento"
              >
                <Paperclip className="w-4 h-4" />
              </button>

              <input
                type="text"
                data-testid="chat-input"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={`Pregúntale a ${SPECIALIST_AGENTS[currentAgent].name}...`}
                disabled={isStreaming}
                className="flex-1 h-11 px-4 rounded-xl bg-secondary/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none text-xs md:text-sm text-foreground transition-all"
              />

              <button
                type="submit"
                data-testid="chat-send-btn"
                disabled={!inputMessage.trim() && !currentAttachment}
                className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground transition-all shadow-sm disabled:opacity-50 cursor-pointer"
                title="Enviar mensaje"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </main>

        {/* RIGHT: SPLIT-VIEW CANVAS PANEL */}
        {isCanvasOpen && (
          <aside
            data-testid="oppyfy-split-canvas"
            className={`border-l border-border bg-card/60 flex flex-col shrink-0 transition-all duration-300 ease-in-out relative ${
              isCanvasFullscreen
                ? "fixed inset-0 z-50 bg-background/98 w-screen h-screen"
                : "w-full lg:w-[480px] xl:w-[560px]"
            }`}
          >
            {/* Canvas Header */}
            <div className="h-14 px-4 border-b border-border flex items-center justify-between shrink-0 bg-secondary/30">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                  <BarChart2 className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs md:text-sm font-bold text-foreground truncate">
                    {activeArtifact?.title || "Canvas Split-View Analítico"}
                  </h3>
                  <p className="text-[10px] text-muted-foreground truncate">
                    Visualización interactiva en tiempo real
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                {activeArtifact && Array.isArray(activeArtifact.data) && (
                  <button
                    type="button"
                    data-testid="canvas-export-csv"
                    onClick={handleExportCSV}
                    className="touch-target inline-flex min-h-[44px] items-center gap-1 px-2.5 rounded-lg hover:bg-secondary text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer"
                    title="Exportar CSV"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">CSV</span>
                  </button>
                )}

                <button
                  type="button"
                  data-testid="canvas-print-pdf"
                  onClick={handlePrintPDF}
                  className="touch-target inline-flex min-h-[44px] items-center gap-1 px-2.5 rounded-lg hover:bg-secondary text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer"
                  title="Imprimir reporte PDF"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">PDF</span>
                </button>

                <button
                  type="button"
                  data-testid="canvas-fullscreen-toggle"
                  onClick={() => setIsCanvasFullscreen(!isCanvasFullscreen)}
                  className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground cursor-pointer"
                  title={isCanvasFullscreen ? "Restaurar" : "Pantalla completa"}
                >
                  {isCanvasFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>

                <button
                  type="button"
                  data-testid="canvas-close-btn"
                  onClick={() => setIsCanvasOpen(false)}
                  className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground cursor-pointer"
                  title="Cerrar Canvas"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Canvas Body */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4">
              {activeArtifact ? (
                <>
                  {/* Buscador en Canvas */}
                  {Array.isArray(activeArtifact.data) && (
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <input
                        type="text"
                        data-testid="canvas-table-filter"
                        value={canvasFilter}
                        onChange={(e) => setCanvasFilter(e.target.value)}
                        placeholder="Buscar en el artefacto..."
                        className="w-full h-9 pl-9 pr-3 text-xs rounded-lg border border-border bg-background text-foreground outline-none focus:border-primary"
                      />
                    </div>
                  )}

                  {/* CASO: TABLA */}
                  {activeArtifact.type === "table" && Array.isArray(activeArtifact.data) && (
                    <div className="border border-border rounded-xl overflow-x-auto shadow-sm">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-secondary/60 text-muted-foreground border-b border-border uppercase font-mono text-[10px]">
                          <tr>
                            {Object.keys(activeArtifact.data[0] || {}).map((col) => (
                              <th key={col} className="px-3 py-2.5 font-bold">
                                {col.replace(/_/g, " ")}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {activeArtifact.data
                            .filter((row: any) =>
                              canvasFilter
                                ? Object.values(row).some((val) =>
                                    String(val).toLowerCase().includes(canvasFilter.toLowerCase())
                                  )
                                : true
                            )
                            .map((row: any, rIdx: number) => (
                              <tr key={rIdx} className="hover:bg-secondary/20">
                                {Object.values(row).map((val: any, cIdx: number) => (
                                  <td key={cIdx} className="px-3 py-2 text-foreground font-mono">
                                    {typeof val === "number" ? val.toLocaleString("es-CL") : String(val)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* CASO: GRÁFICO RECHARTS */}
                  {activeArtifact.type === "chart" && Array.isArray(activeArtifact.data) && (
                    <div
                      data-testid="canvas-chart-container"
                      className="rounded-xl border border-border bg-background p-3"
                    >
                      <div className="h-64 w-full" style={{ minHeight: "220px", minWidth: "100px" }}>
                        <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
                          {activeArtifact.chartType === "line" ? (
                            <LineChart data={activeArtifact.data as any[]}>
                              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                              <YAxis tick={{ fontSize: 11 }} />
                              <RechartsTooltip />
                              <Legend />
                              <Line type="monotone" dataKey="teorico" stroke="#10B981" strokeWidth={2} />
                              <Line type="monotone" dataKey="real" stroke="#F59E0B" strokeWidth={2} />
                            </LineChart>
                          ) : (
                            <BarChart data={activeArtifact.data as any[]}>
                              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                              <YAxis tick={{ fontSize: 11 }} />
                              <RechartsTooltip />
                              <Legend />
                              <Bar dataKey="teorico" fill="#10B981" radius={[4, 4, 0, 0]} />
                              <Bar dataKey="real" fill="#F59E0B" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          )}
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-center text-muted-foreground">
                  <Bot className="w-8 h-8 mb-2 opacity-40" />
                  <p className="text-xs">Sin artefactos activos en este momento.</p>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* ======================================================== */}
      {/* 3. MODALES: SELECTOR DE AGENTE, GOBERNANZA, ROLLOVER */}
      {/* ======================================================== */}

      {/* Modal: Selector de Agente para Nueva Conversación */}
      {isNewChatModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Selector de Especialista"
          data-testid="new-chat-specialist-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150"
          onClick={() => setIsNewChatModalOpen(false)}
        >
          <div
            className="glass-card w-full max-w-md rounded-2xl border border-border p-5 shadow-2xl bg-card text-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border pb-3 mb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-500" />
                <h3 className="text-sm font-bold">¿Con quién deseas conversar?</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsNewChatModalOpen(false)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2">
              {(["general", "chef", "stock", "supply", "manager"] as SpecialistAgentType[]).map((agentKey) => {
                const cfg = SPECIALIST_AGENTS[agentKey];
                const Icon = SPECIALIST_ICONS[agentKey];
                return (
                  <button
                    key={agentKey}
                    type="button"
                    data-testid={`select-specialist-${agentKey}`}
                    onClick={() => {
                      setIsNewChatModalOpen(false);
                      handleCreateNewThread(agentKey);
                    }}
                    className="touch-target min-h-[44px] w-full flex items-center gap-3 p-3 rounded-xl border border-border hover:bg-secondary/70 text-left transition-all cursor-pointer group"
                  >
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      style={{ backgroundColor: `${cfg.color}20`, color: cfg.color }}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground group-hover:text-primary">
                          {cfg.name}
                        </span>
                        <span
                          className="text-[9px] font-semibold uppercase px-2 py-0.5 rounded-full"
                          style={{ backgroundColor: `${cfg.color}15`, color: cfg.color }}
                        >
                          {agentKey}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                        {cfg.role_title}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Gobernanza y Ajustes OppyFy */}
      {isSettingsOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Gobernanza y Ajustes OppyFy"
          data-testid="oppyfy-governance-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150"
          onClick={() => setIsSettingsOpen(false)}
        >
          <div
            className="glass-card w-full max-w-4xl max-h-[90vh] rounded-2xl border border-border p-5 shadow-2xl bg-card text-foreground flex flex-col my-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border pb-3 mb-3 shrink-0">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <SlidersHorizontal className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold">Gobernanza & Ajustes OppyFy</h3>
                  <p className="text-[11px] text-muted-foreground">
                    Dominios, permisos temporales, billetera de créditos y auditoría
                  </p>
                </div>
              </div>
              <button
                type="button"
                data-testid="close-governance-modal-btn"
                onClick={() => setIsSettingsOpen(false)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0">
              <OppyfyGovernancePanel />
            </div>
          </div>
        </div>
      )}

      {/* Modal: Rollover Asistido a Hilo Fresco */}
      <OppyfyRolloverModal
        isOpen={isRolloverModalOpen}
        onClose={() => setIsRolloverModalOpen(false)}
        onConfirm={async () => {
          setContextPct(FRESH_THREAD_CONTEXT_PCT);
          handleCreateNewThread(currentAgent);
          setIsRolloverModalOpen(false);
          toast.success("Traspaso a hilo fresco (5% contexto) completado.");
        }}
        isProcessing={false}
      />
    </div>
  );
}

export default OppyfyWorkspacePage;
