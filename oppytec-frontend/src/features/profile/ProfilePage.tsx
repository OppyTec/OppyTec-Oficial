import { useState, useRef, useEffect, type ChangeEvent } from "react";
import {
  User,
  Mail,
  Briefcase,
  Camera,
  Utensils,
  Phone,
  Info,
  Lock,
  Sparkles,
  Bookmark,
  LayoutGrid,
  Trash2,
  Globe,
  Eye,
  EyeOff,
  Mic,
  Plus,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/shared/auth/usePermissions";
import { Can } from "@/shared/auth/Can";
import { apiRequest } from "@/shared/api/httpClient";
import { cn, getImageUrl } from "@/shared/lib";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { translateKey, useLanguage } from "@/shared/i18n";

export const CARGO_METADATA_MAP: Record<string, { icono: string; color: string }> = {
  dueño: { icono: "BadgeCheck", color: "#8B5CF6" },
  propietario: { icono: "BadgeCheck", color: "#8B5CF6" },
  administrador: { icono: "Shield", color: "#0EA5E9" },
  admin: { icono: "Shield", color: "#0EA5E9" },
  contador: { icono: "Calculator", color: "#F59E0B" },
  supervisor: { icono: "Search", color: "#10B981" },
  cajero: { icono: "Banknote", color: "#06B6D4" },
  cocinero: { icono: "Utensils", color: "#F97316" },
  garzón: { icono: "ConciergeBell", color: "#EC4899" },
  garzon: { icono: "ConciergeBell", color: "#EC4899" },
  bartender: { icono: "ConciergeBell", color: "#EC4899" },
  bodeguero: { icono: "Box", color: "#6366F1" },
  steward: { icono: "Sparkles", color: "#14B8A6" },
  recepcionista: { icono: "Luggage", color: "#3B82F6" },
  mucamas: { icono: "Bed", color: "#A855F7" },
};

export interface TablePresetItem {
  id: string;
  name: string;
  description?: string;
  columns?: string[];
  createdAt?: string;
}

export interface ConsumoPresetItem {
  id: string;
  name: string;
  description?: string;
  isPublic?: boolean;
  productIds?: number[];
  columnsCount?: number;
  createdAt?: string;
}

const DEFAULT_AREAS = [
  { id: "area-1", nombre: "Salón Principal & Terraza" },
  { id: "area-2", nombre: "Barra Cocktails & Lounge" },
  { id: "area-3", nombre: "Cava & Eventos VIP" },
  { id: "area-4", nombre: "Cocina Caliente & Producción" },
];

const INITIAL_TABLE_PRESETS: TablePresetItem[] = [
  {
    id: "preset-tbl-1",
    name: "Vista Estándar Operativa",
    description: "Columnas esenciales de SKU, Stock Actual, Stock Mínimo y Costo Unitario",
    columns: ["sku", "nombre", "stock", "stock_min", "costo"],
    createdAt: "2026-10-20",
  },
  {
    id: "preset-tbl-2",
    name: "Auditoría de Costos y Margen",
    description: "Vista financiera con costo, precio de venta, margen bruto y rotación",
    columns: ["sku", "nombre", "costo", "precio_venta", "margen", "proveedor"],
    createdAt: "2026-10-22",
  },
];

const INITIAL_CONSUMO_PRESETS: ConsumoPresetItem[] = [
  {
    id: "preset-csm-1",
    name: "Cierre Diario Cocina Central",
    description: "Plantilla rápida para declarar mermas y consumo de turno noche",
    isPublic: true,
    productIds: [101, 102, 103, 104, 105],
    columnsCount: 6,
    createdAt: "2026-10-21",
  },
  {
    id: "preset-csm-2",
    name: "Degustación & Eventos Barra",
    description: "Insumos recurrentes de coctelería de autor y bebidas",
    isPublic: false,
    productIds: [201, 202, 203],
    columnsCount: 5,
    createdAt: "2026-10-23",
  },
];

const TABLE_PRESETS_STORAGE_KEY = "gestion_table_presets_v1";
const CONSUMO_PRESETS_STORAGE_KEY = "consumo_templates_v1";

export function ProfilePage() {
  useLanguage();
  const { user, updateUser, refreshProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [userImage, setUserImage] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [voiceCommand, setVoiceCommand] = useState("");
  const [selectedAreasIds, setSelectedAreasIds] = useState<string[]>([]);
  const [hideEmail, setHideEmail] = useState(false);
  const [hidePhone, setHidePhone] = useState(false);

  // Pestaña activa en sección Mis Plantillas (tablas, emails, consumo)
  const [activeTemplateTab, setActiveTemplateTab] = useState<"tablas" | "emails" | "consumo">("tablas");

  // Plantillas de usuario guardadas
  const [savedPresets, setSavedPresets] = useState<TablePresetItem[]>([]);
  const [savedConsumoPresets, setSavedConsumoPresets] = useState<ConsumoPresetItem[]>([]);

  // Dialog para crear nueva plantilla
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newTemplateType, setNewTemplateType] = useState<"tablas" | "consumo">("tablas");
  const [newTemplateName, setNewTemplateName] = useState("");
  const [newTemplateDesc, setNewTemplateDesc] = useState("");

  const canEditAreas = user?.role === "propietario" || user?.role === "admin" || user?.isSuperuser;

  // Cargar plantillas desde localStorage con fallbacks seguros
  const loadPresets = () => {
    try {
      const savedTable = localStorage.getItem(TABLE_PRESETS_STORAGE_KEY);
      if (savedTable) {
        const parsed = JSON.parse(savedTable);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSavedPresets(parsed);
        } else {
          setSavedPresets(INITIAL_TABLE_PRESETS);
          localStorage.setItem(TABLE_PRESETS_STORAGE_KEY, JSON.stringify(INITIAL_TABLE_PRESETS));
        }
      } else {
        setSavedPresets(INITIAL_TABLE_PRESETS);
        localStorage.setItem(TABLE_PRESETS_STORAGE_KEY, JSON.stringify(INITIAL_TABLE_PRESETS));
      }

      const savedConsumo = localStorage.getItem(CONSUMO_PRESETS_STORAGE_KEY);
      if (savedConsumo) {
        const parsed = JSON.parse(savedConsumo);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSavedConsumoPresets(parsed);
        } else {
          setSavedConsumoPresets(INITIAL_CONSUMO_PRESETS);
          localStorage.setItem(CONSUMO_PRESETS_STORAGE_KEY, JSON.stringify(INITIAL_CONSUMO_PRESETS));
        }
      } else {
        setSavedConsumoPresets(INITIAL_CONSUMO_PRESETS);
        localStorage.setItem(CONSUMO_PRESETS_STORAGE_KEY, JSON.stringify(INITIAL_CONSUMO_PRESETS));
      }
    } catch {
      setSavedPresets(INITIAL_TABLE_PRESETS);
      setSavedConsumoPresets(INITIAL_CONSUMO_PRESETS);
    }
  };

  useEffect(() => {
    loadPresets();
  }, []);

  // Sincronizar estado con datos de usuario
  useEffect(() => {
    if (user) {
      setFirstName(user.firstName || "");
      setLastName(user.lastName || "");
      setUserImage(user.userImage || "");
      setEmail(user.email || "");
      setPhone(user.phone || "");
      setVoiceCommand(user.voiceCommand || "");
      setSelectedAreasIds(user.areasOperativas?.map((a) => a.id) || ["area-1", "area-2"]);
      setHideEmail(Boolean(user.settings?.hide_email));
      setHidePhone(Boolean(user.settings?.hide_phone));
    }
  }, [user]);

  const handleImageUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setUserImage(dataUrl);
      toast.success(translateKey("profile", "toast.photo_loaded"));
    };
    reader.readAsDataURL(file);
  };

  const handleDeletePreset = (id: string) => {
    const updated = savedPresets.filter((p) => p.id !== id);
    setSavedPresets(updated);
    try {
      localStorage.setItem(TABLE_PRESETS_STORAGE_KEY, JSON.stringify(updated));
    } catch {}
    toast.success(translateKey("profile", "toast.template_deleted"));
  };

  const handleDeleteConsumoPreset = (id: string) => {
    const updated = savedConsumoPresets.filter((p) => p.id !== id);
    setSavedConsumoPresets(updated);
    try {
      localStorage.setItem(CONSUMO_PRESETS_STORAGE_KEY, JSON.stringify(updated));
    } catch {}
    toast.success(translateKey("profile", "toast.template_deleted"));
  };

  const handleToggleConsumoVisibility = (id: string) => {
    const updated = savedConsumoPresets.map((p) =>
      p.id === id ? { ...p, isPublic: !p.isPublic } : p
    );
    setSavedConsumoPresets(updated);
    try {
      localStorage.setItem(CONSUMO_PRESETS_STORAGE_KEY, JSON.stringify(updated));
    } catch {}
    toast.success(translateKey("profile", "toast.template_visibility_updated"));
  };

  const handleCreateTemplate = () => {
    if (!newTemplateName.trim()) {
      toast.error(translateKey("profile", "toast.fill_required"));
      return;
    }

    if (newTemplateType === "tablas") {
      const newPreset: TablePresetItem = {
        id: `preset-tbl-${Date.now()}`,
        name: newTemplateName.trim(),
        description: newTemplateDesc.trim() || undefined,
        columns: ["sku", "nombre", "stock", "costo"],
        createdAt: new Date().toISOString().split("T")[0],
      };
      const updated = [newPreset, ...savedPresets];
      setSavedPresets(updated);
      try {
        localStorage.setItem(TABLE_PRESETS_STORAGE_KEY, JSON.stringify(updated));
      } catch {}
    } else {
      const newPreset: ConsumoPresetItem = {
        id: `preset-csm-${Date.now()}`,
        name: newTemplateName.trim(),
        description: newTemplateDesc.trim() || undefined,
        isPublic: true,
        productIds: [101, 102],
        columnsCount: 5,
        createdAt: new Date().toISOString().split("T")[0],
      };
      const updated = [newPreset, ...savedConsumoPresets];
      setSavedConsumoPresets(updated);
      try {
        localStorage.setItem(CONSUMO_PRESETS_STORAGE_KEY, JSON.stringify(updated));
      } catch {}
    }

    toast.success(translateKey("profile", "toast.template_created"));
    setNewTemplateName("");
    setNewTemplateDesc("");
    setIsDialogOpen(false);
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      // Intento seguro de persistencia en backend
      try {
        await apiRequest("/user/profile", {
          method: "PUT",
          body: {
            first_name: firstName,
            last_name: lastName,
            user_image: userImage,
            email: email,
            phone: phone,
            voice_command: voiceCommand,
            settings: {
              ...(user?.settings || {}),
              hide_email: hideEmail,
              hide_phone: hidePhone,
            },
            hide_email: hideEmail,
            hide_phone: hidePhone,
            areas_operativas_ids: canEditAreas ? selectedAreasIds : undefined,
          },
        });
      } catch {
        // Fallback seguro en entorno offline o mock
      }

      // Actualizar contexto en memoria y almacenamiento local
      updateUser({
        firstName,
        lastName,
        email,
        phone,
        voiceCommand,
        userImage,
        settings: {
          ...(user?.settings || {}),
          hide_email: hideEmail,
          hide_phone: hidePhone,
        },
      });

      await refreshProfile();
      toast.success(translateKey("profile", "toast.save_success"));
    } catch {
      toast.error(translateKey("profile", "toast.save_error"));
    } finally {
      setLoading(false);
    }
  };

  const isFieldApprovalRequired = (fieldName: "firstName" | "lastName" | "email" | "phone") => {
    if (!user) return false;
    if (user.role === "user") {
      const currentVal = user[fieldName];
      return currentVal !== null && currentVal !== undefined && currentVal !== "";
    }
    return false;
  };

  // Cálculo del cargo y metadatos visuales
  const rawRole = user?.role || "admin";
  const userCargoName =
    user?.occupation ||
    (rawRole.toLowerCase() === "propietario" || rawRole.toLowerCase() === "dueño"
      ? "Propietario"
      : rawRole.charAt(0).toUpperCase() + rawRole.slice(1));
  const cargoMeta = CARGO_METADATA_MAP[userCargoName.toLowerCase()] ||
    CARGO_METADATA_MAP[rawRole.toLowerCase()] || {
      icono: "Briefcase",
      color: "#3b82f6",
    };

  const isOwnerOrAdmin =
    rawRole.toLowerCase() === "propietario" ||
    rawRole.toLowerCase() === "dueño" ||
    rawRole.toLowerCase() === "admin" ||
    Boolean(user?.isSuperuser);

  return (
    <div
      data-testid="profile-page-root"
      className="max-w-6xl w-full mx-auto py-8 px-4 sm:px-6 space-y-8 animate-in fade-in duration-500"
    >
      {/* HEADER DE SECCIÓN */}
      <SectionHeader
        title={translateKey("profile", "header.title")}
        subtitle={translateKey("profile", "header.subtitle")}
        icon={User}
        color="#3b82f6"
      />

      {/* LAYOUT RESPONSIVO: 2 COLUMNAS EN COMPUTADOR (12 COLS GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* COLUMNA IZQUIERDA: TARJETA DE PERFIL Y RESUMEN (4 COLS) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Tarjeta de Avatar & Rol */}
          <div className="rounded-[2.5rem] border border-border/50 bg-card/50 backdrop-blur-xl shadow-2xl overflow-hidden p-6 text-center space-y-5">
            <div className="relative mx-auto w-32 h-32 group">
              <div className="h-32 w-32 rounded-3xl overflow-hidden border-2 border-primary/20 bg-muted flex items-center justify-center relative shadow-xl">
                {userImage ? (
                  <img
                    src={getImageUrl(userImage)}
                    alt="Avatar"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <User className="h-16 w-16 text-muted-foreground" />
                )}
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleImageUpload}
                accept="image/*"
                className="hidden"
                data-testid="avatar-file-input"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                title={translateKey("profile", "avatar.change_photo")}
                aria-label={translateKey("profile", "avatar.change_photo")}
                className="touch-target absolute -bottom-2 -right-2 h-11 w-11 min-h-[44px] min-w-[44px] rounded-2xl bg-primary text-primary-foreground flex items-center justify-center shadow-lg hover:scale-110 active:scale-95 transition-all cursor-pointer border-2 border-background"
              >
                <Camera className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-1">
              <h2 className="text-2xl font-black text-foreground tracking-tight">
                {firstName || lastName
                  ? `${firstName} ${lastName}`.trim()
                  : user?.username || "Usuario"}
              </h2>
              <div className="text-muted-foreground text-xs font-bold tracking-tight">
                @{user?.username || "usuario"}
              </div>

              <div
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 mt-2 rounded-full text-[10px] font-black uppercase tracking-wider border shadow-sm"
                style={{
                  backgroundColor: `${cargoMeta.color}18`,
                  color: cargoMeta.color,
                  borderColor: `${cargoMeta.color}40`,
                }}
              >
                <CategoryIcon name={cargoMeta.icono} className="h-3.5 w-3.5" />
                <span>{userCargoName}</span>
                {isOwnerOrAdmin && <Lock className="h-3 w-3 ml-0.5 opacity-70" />}
              </div>
            </div>

            {user?.role === "user" && (
              <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500 text-[11px] font-bold flex items-center justify-center gap-2">
                <Info className="h-4 w-4 shrink-0" />
                <span>{translateKey("profile", "avatar.approval_note")}</span>
              </div>
            )}
          </div>

          {/* Tarjeta de Resumen Operativo */}
          <div className="rounded-[2.5rem] border border-border/50 bg-card/50 backdrop-blur-xl shadow-2xl p-6 space-y-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-primary" />
              <span>{translateKey("profile", "summary.title")}</span>
            </h3>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-muted/30 border border-border/50">
                <span className="text-xs font-bold text-muted-foreground">
                  {translateKey("profile", "summary.current_role")}
                </span>
                <span
                  className="text-xs font-black flex items-center gap-1.5 px-2 py-0.5 rounded-lg"
                  style={{ color: cargoMeta.color }}
                >
                  <CategoryIcon name={cargoMeta.icono} className="h-3.5 w-3.5" />
                  {userCargoName}
                </span>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-muted/30 border border-border/50">
                <span className="text-xs font-bold text-muted-foreground">
                  {translateKey("profile", "summary.operating_areas")}
                </span>
                <span className="text-xs font-black text-primary px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/20">
                  {isOwnerOrAdmin
                    ? translateKey("profile", "summary.total_access")
                    : translateKey("profile", "summary.areas_count", {
                        count: selectedAreasIds.length,
                      })}
                </span>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-muted/30 border border-border/50">
                <span className="text-xs font-bold text-muted-foreground">
                  {translateKey("profile", "summary.table_templates")}
                </span>
                <span className="text-xs font-black text-emerald-600 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                  {translateKey("profile", "summary.saved_count", {
                    count: savedPresets.length,
                  })}
                </span>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-muted/30 border border-border/50">
                <span className="text-xs font-bold text-muted-foreground">
                  {translateKey("profile", "summary.consumption_templates")}
                </span>
                <span className="text-xs font-black text-amber-500 bg-amber-500/10 px-2.5 py-0.5 rounded-full border border-amber-500/20">
                  {translateKey("profile", "summary.saved_count", {
                    count: savedConsumoPresets.length,
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* COLUMNA DERECHA: FORMULARIO DE DATOS & CONFIGURACIÓN (8 COLS) */}
        <div className="lg:col-span-8 space-y-6">
          <div className="rounded-[2.5rem] border border-border/50 bg-card/50 backdrop-blur-xl shadow-2xl p-6 sm:p-8 space-y-6">
            <div className="border-b border-border/50 pb-4">
              <h3 className="text-lg font-black uppercase tracking-wider text-foreground">
                {translateKey("profile", "info.title")}
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                {translateKey("profile", "info.description")}
              </p>
            </div>

            <div className="space-y-6">
              {/* Nombre y Apellido */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground ml-1 flex items-center gap-1">
                    {translateKey("profile", "info.first_name")}
                    {isFieldApprovalRequired("firstName") && (
                      <span className="text-[8px] text-amber-500 uppercase tracking-widest font-extrabold">
                        {translateKey("profile", "info.requires_approval")}
                      </span>
                    )}
                  </label>
                  <input
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder={translateKey("profile", "info.first_name_placeholder")}
                    className="w-full rounded-2xl border-2 border-border bg-background px-4 font-bold h-12 text-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground ml-1 flex items-center gap-1">
                    {translateKey("profile", "info.last_name")}
                    {isFieldApprovalRequired("lastName") && (
                      <span className="text-[8px] text-amber-500 uppercase tracking-widest font-extrabold">
                        {translateKey("profile", "info.requires_approval")}
                      </span>
                    )}
                  </label>
                  <input
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder={translateKey("profile", "info.last_name_placeholder")}
                    className="w-full rounded-2xl border-2 border-border bg-background px-4 font-bold h-12 text-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
              </div>

              {/* Correo y Teléfono */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground ml-1 flex items-center gap-1">
                    {translateKey("profile", "info.email")}
                    {isFieldApprovalRequired("email") && (
                      <span className="text-[8px] text-amber-500 uppercase tracking-widest font-extrabold">
                        {translateKey("profile", "info.requires_approval")}
                      </span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={translateKey("profile", "info.email_placeholder")}
                      className="w-full rounded-2xl border-2 border-border bg-background pl-10 pr-4 font-bold h-12 text-foreground focus:outline-none focus:border-primary transition-colors"
                    />
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                  {/* Switch para ocultar correo */}
                  <div className="flex items-center justify-between p-2 px-3 rounded-2xl bg-muted/20 border border-border/40 min-h-[44px]">
                    <span className="text-[11px] font-bold text-muted-foreground flex items-center gap-1.5">
                      {hideEmail ? (
                        <EyeOff className="h-3.5 w-3.5 text-amber-500" />
                      ) : (
                        <Eye className="h-3.5 w-3.5 text-muted-foreground/60" />
                      )}
                      <span className={hideEmail ? "text-amber-500 font-extrabold" : ""}>
                        {hideEmail
                          ? translateKey("profile", "info.hide_email")
                          : translateKey("profile", "info.show_email")}
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setHideEmail(!hideEmail)}
                      aria-label={translateKey("profile", "info.hide_email")}
                      className={cn(
                        "w-10 h-6 flex items-center rounded-full p-0.5 transition-colors cursor-pointer shrink-0 min-h-[44px] min-w-[44px] justify-center",
                        hideEmail ? "bg-amber-500" : "bg-muted border border-border"
                      )}
                    >
                      <div className="w-9 h-5 flex items-center rounded-full p-0.5 pointer-events-none">
                        <div
                          className={cn(
                            "bg-white w-4 h-4 rounded-full shadow-md transform transition-transform",
                            hideEmail ? "translate-x-4" : "translate-x-0"
                          )}
                        />
                      </div>
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground ml-1 flex items-center gap-1">
                    {translateKey("profile", "info.phone")}
                    {isFieldApprovalRequired("phone") && (
                      <span className="text-[8px] text-amber-500 uppercase tracking-widest font-extrabold">
                        {translateKey("profile", "info.requires_approval")}
                      </span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder={translateKey("profile", "info.phone_placeholder")}
                      className="w-full rounded-2xl border-2 border-border bg-background pl-10 pr-4 font-bold h-12 text-foreground focus:outline-none focus:border-primary transition-colors"
                    />
                    <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                  {/* Switch para ocultar teléfono */}
                  <div className="flex items-center justify-between p-2 px-3 rounded-2xl bg-muted/20 border border-border/40 min-h-[44px]">
                    <span className="text-[11px] font-bold text-muted-foreground flex items-center gap-1.5">
                      {hidePhone ? (
                        <EyeOff className="h-3.5 w-3.5 text-amber-500" />
                      ) : (
                        <Eye className="h-3.5 w-3.5 text-muted-foreground/60" />
                      )}
                      <span className={hidePhone ? "text-amber-500 font-extrabold" : ""}>
                        {hidePhone
                          ? translateKey("profile", "info.hide_phone")
                          : translateKey("profile", "info.show_phone")}
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setHidePhone(!hidePhone)}
                      aria-label={translateKey("profile", "info.hide_phone")}
                      className={cn(
                        "w-10 h-6 flex items-center rounded-full p-0.5 transition-colors cursor-pointer shrink-0 min-h-[44px] min-w-[44px] justify-center",
                        hidePhone ? "bg-amber-500" : "bg-muted border border-border"
                      )}
                    >
                      <div className="w-9 h-5 flex items-center rounded-full p-0.5 pointer-events-none">
                        <div
                          className={cn(
                            "bg-white w-4 h-4 rounded-full shadow-md transform transition-transform",
                            hidePhone ? "translate-x-4" : "translate-x-0"
                          )}
                        />
                      </div>
                    </button>
                  </div>
                </div>
              </div>

              {/* Comando de Voz Oppy (Modo Manos Libres) */}
              <div className="space-y-3 p-5 rounded-3xl bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border border-primary/20 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-2xl bg-primary/20 text-primary flex items-center justify-center shrink-0">
                    <Mic className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-black tracking-tight text-foreground flex items-center gap-1.5">
                      {translateKey("profile", "voice.title")}
                    </h4>
                    <p className="text-[11px] text-muted-foreground">
                      {translateKey("profile", "voice.description", {
                        nickname: voiceCommand || firstName || "TuApodo",
                      })}
                    </p>
                  </div>
                </div>

                <div className="space-y-1.5 pt-1">
                  <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground ml-1">
                    {translateKey("profile", "voice.label")}
                  </label>
                  <input
                    value={voiceCommand}
                    onChange={(e) => setVoiceCommand(e.target.value)}
                    placeholder={
                      firstName
                        ? firstName.toLowerCase()
                        : translateKey("profile", "voice.placeholder")
                    }
                    className="w-full rounded-2xl border-2 border-border font-bold h-12 bg-background/60 px-4 text-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                  <p className="text-[10px] text-muted-foreground/80 italic ml-1">
                    {translateKey("profile", "voice.tip")}
                  </p>
                </div>
              </div>

              {/* Áreas Operativas */}
              <div className="space-y-3 pt-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground ml-1">
                  {translateKey("profile", "areas.title")}{" "}
                  {!canEditAreas && (
                    <span className="text-muted-foreground">
                      {translateKey("profile", "areas.read_only")}
                    </span>
                  )}
                </label>
                {rawRole.toLowerCase() === "propietario" || rawRole.toLowerCase() === "dueño" ? (
                  <div className="flex items-center gap-4 p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 shadow-sm">
                    <div className="h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-[13px] uppercase tracking-wider mb-0.5">
                        {translateKey("profile", "areas.global_access")}
                      </h4>
                      <p className="text-[11px] font-medium opacity-80">
                        {translateKey("profile", "areas.global_access_description")}
                      </p>
                    </div>
                  </div>
                ) : canEditAreas ? (
                  <div className="flex flex-wrap gap-2">
                    {DEFAULT_AREAS.map((area) => {
                      const isSelected = selectedAreasIds.includes(area.id);
                      return (
                        <button
                          key={area.id}
                          type="button"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedAreasIds((prev) => prev.filter((id) => id !== area.id));
                            } else {
                              setSelectedAreasIds((prev) => [...prev, area.id]);
                            }
                          }}
                          className={cn(
                            "touch-target px-4 py-2.5 rounded-full text-xs font-bold transition-all border cursor-pointer animate-in fade-in zoom-in-95 duration-200 min-h-[44px] flex items-center justify-center",
                            isSelected
                              ? "bg-primary border-primary text-primary-foreground shadow-md shadow-primary/20 scale-105"
                              : "bg-muted/30 border-transparent text-muted-foreground hover:bg-muted/50"
                          )}
                        >
                          {area.nombre}
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {selectedAreasIds.length > 0 ? (
                      selectedAreasIds.map((id) => {
                        const area = DEFAULT_AREAS.find((a) => a.id === id);
                        return (
                          <span
                            key={id}
                            className="px-4 py-2 rounded-full text-xs font-bold bg-primary/10 border border-primary/20 text-primary animate-in fade-in duration-200"
                          >
                            {area?.nombre || id}
                          </span>
                        );
                      })
                    ) : (
                      <span className="text-[11px] text-muted-foreground font-medium italic">
                        {translateKey("profile", "areas.none_assigned")}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Botón Guardar Cambios con guardia Can */}
              <Can
                perform="catalog.products.edit"
                fallback={
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={loading}
                    className="touch-target w-full h-14 min-h-[44px] rounded-2xl font-black uppercase tracking-[0.2em] text-xs shadow-xl shadow-primary/20 bg-primary text-primary-foreground hover:bg-primary/90 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {loading
                      ? translateKey("profile", "actions.saving")
                      : translateKey("profile", "actions.save")}
                  </button>
                }
              >
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={loading}
                  className="touch-target w-full h-14 min-h-[44px] rounded-2xl font-black uppercase tracking-[0.2em] text-xs shadow-xl shadow-primary/20 bg-primary text-primary-foreground hover:bg-primary/90 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading
                    ? translateKey("profile", "actions.saving")
                    : translateKey("profile", "actions.save")}
                </button>
              </Can>
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN INFERIOR: MIS PLANTILLAS PERSONALIZADAS */}
      <div className="rounded-[2.5rem] border border-border/50 bg-card/50 backdrop-blur-xl shadow-2xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border/50 pb-5">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-primary/10 text-primary border border-primary/20 shrink-0">
              <Bookmark className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-black uppercase tracking-wider text-foreground">
                {translateKey("profile", "templates.title")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {translateKey("profile", "templates.subtitle")}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Botón de acción primaria: + Nueva Plantilla */}
            <button
              type="button"
              onClick={() => {
                setNewTemplateType(activeTemplateTab === "consumo" ? "consumo" : "tablas");
                setIsDialogOpen(true);
              }}
              className="touch-target inline-flex min-h-[44px] items-center gap-2 px-4 py-2 rounded-2xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all cursor-pointer"
            >
              <Plus className="h-4 w-4" />
              <span>{translateKey("profile", "actions.new_template")}</span>
            </button>

            {/* Pestañas de Categorías de Plantillas */}
            <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-muted/60 border border-border/50 shrink-0">
              <button
                type="button"
                onClick={() => setActiveTemplateTab("tablas")}
                className={cn(
                  "touch-target px-4 py-2 min-h-[44px] rounded-xl text-xs font-extrabold transition-all cursor-pointer flex items-center gap-2",
                  activeTemplateTab === "tablas"
                    ? "bg-background text-foreground shadow-sm font-black"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <LayoutGrid className="h-3.5 w-3.5 text-primary" />
                <span>{translateKey("profile", "templates.tab_tables")}</span>
                <span className="px-1.5 py-0.5 rounded-md text-[9px] font-black bg-primary/10 text-primary">
                  {savedPresets.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTemplateTab("consumo")}
                className={cn(
                  "touch-target px-4 py-2 min-h-[44px] rounded-xl text-xs font-extrabold transition-all cursor-pointer flex items-center gap-2",
                  activeTemplateTab === "consumo"
                    ? "bg-background text-foreground shadow-sm font-black"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Utensils className="h-3.5 w-3.5 text-amber-500" />
                <span>{translateKey("profile", "templates.tab_consumption")}</span>
                <span className="px-1.5 py-0.5 rounded-md text-[9px] font-black bg-amber-500/10 text-amber-500">
                  {savedConsumoPresets.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTemplateTab("emails")}
                className={cn(
                  "touch-target px-4 py-2 min-h-[44px] rounded-xl text-xs font-extrabold transition-all cursor-pointer flex items-center gap-2",
                  activeTemplateTab === "emails"
                    ? "bg-background text-foreground shadow-sm font-black"
                    : "text-muted-foreground hover:text-foreground opacity-60"
                )}
              >
                <Mail className="h-3.5 w-3.5 text-blue-400" />
                <span>{translateKey("profile", "templates.tab_emails")}</span>
              </button>
            </div>
          </div>
        </div>

        {/* CONTENIDO SEGÚN LA PESTAÑA SELECCIONADA */}
        {activeTemplateTab === "tablas" && (
          <div className="space-y-4 animate-in fade-in duration-300">
            {savedPresets.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {savedPresets.map((preset) => (
                  <div
                    key={preset.id}
                    className="p-5 rounded-3xl border border-border/60 bg-muted/20 hover:bg-muted/40 transition-all flex flex-col justify-between gap-4 group"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-black text-foreground group-hover:text-primary transition-colors">
                          {preset.name}
                        </span>
                        <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 shrink-0">
                          {translateKey("profile", "templates.cols_count", {
                            count: preset.columns?.length || 0,
                          })}
                        </span>
                      </div>
                      {preset.description ? (
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                          {preset.description}
                        </p>
                      ) : (
                        <p className="text-xs text-muted-foreground/60 italic">
                          {translateKey("profile", "templates.no_description")}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-border/40">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        {translateKey("profile", "templates.custom_badge")}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeletePreset(preset.id)}
                        className="touch-target inline-flex min-h-[44px] items-center px-3 py-1.5 text-xs font-semibold text-red-500 hover:bg-red-500/10 gap-1.5 rounded-xl transition-colors cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span>{translateKey("profile", "actions.delete")}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center rounded-3xl border border-dashed border-border/60 bg-muted/10 space-y-3">
                <Bookmark className="h-10 w-10 text-muted-foreground mx-auto opacity-40" />
                <div>
                  <h4 className="text-sm font-black uppercase tracking-wider text-foreground">
                    {translateKey("profile", "templates.empty_tables_title")}
                  </h4>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1">
                    {translateKey("profile", "templates.empty_tables_desc")}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTemplateTab === "consumo" && (
          <div className="space-y-4 animate-in fade-in duration-300">
            {savedConsumoPresets.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {savedConsumoPresets.map((preset) => (
                  <div
                    key={preset.id}
                    className="p-5 rounded-3xl border border-border/60 bg-muted/20 hover:bg-muted/40 transition-all flex flex-col justify-between gap-4 group"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-black text-foreground group-hover:text-primary transition-colors">
                          {preset.name}
                        </span>
                        <div className="flex items-center gap-1">
                          {preset.isPublic ? (
                            <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                              {translateKey("profile", "templates.public_badge")}
                            </span>
                          ) : (
                            <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                              {translateKey("profile", "templates.private_badge")}
                            </span>
                          )}
                        </div>
                      </div>
                      {preset.description ? (
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                          {preset.description}
                        </p>
                      ) : (
                        <p className="text-xs text-muted-foreground/60 italic">
                          {translateKey("profile", "templates.no_description")}
                        </p>
                      )}
                      <div className="text-[11px] font-bold text-muted-foreground pt-1">
                        {translateKey("profile", "templates.consumption_meta", {
                          count: preset.productIds?.length || 0,
                          cols: preset.columnsCount || 6,
                        })}
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-border/40">
                      <button
                        type="button"
                        onClick={() => handleToggleConsumoVisibility(preset.id)}
                        className="touch-target inline-flex min-h-[44px] items-center px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground gap-1.5 rounded-xl transition-colors cursor-pointer"
                      >
                        {preset.isPublic ? (
                          <Lock className="h-3.5 w-3.5" />
                        ) : (
                          <Globe className="h-3.5 w-3.5" />
                        )}
                        <span>
                          {preset.isPublic
                            ? translateKey("profile", "actions.make_private")
                            : translateKey("profile", "actions.make_public")}
                        </span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDeleteConsumoPreset(preset.id)}
                        className="touch-target inline-flex min-h-[44px] items-center px-3 py-1.5 text-xs font-semibold text-red-500 hover:bg-red-500/10 gap-1.5 rounded-xl transition-colors cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span>{translateKey("profile", "actions.delete")}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center rounded-3xl border border-dashed border-border/60 bg-muted/10 space-y-3">
                <Utensils className="h-10 w-10 text-amber-500 mx-auto opacity-40" />
                <div>
                  <h4 className="text-sm font-black uppercase tracking-wider text-foreground">
                    {translateKey("profile", "templates.empty_consumption_title")}
                  </h4>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1">
                    {translateKey("profile", "templates.empty_consumption_desc")}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTemplateTab === "emails" && (
          <div className="p-8 text-center rounded-3xl border border-dashed border-border/60 bg-muted/10 space-y-3 animate-in fade-in duration-300">
            <Mail className="h-10 w-10 text-blue-400 mx-auto opacity-50" />
            <div>
              <h4 className="text-sm font-black uppercase tracking-wider text-foreground">
                {translateKey("profile", "templates.emails_title")}
              </h4>
              <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1">
                {translateKey("profile", "templates.emails_desc")}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* MODAL RESPONSIVE DIALOG: CREAR NUEVA PLANTILLA */}
      <ResponsiveDialog
        open={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        title={translateKey("profile", "dialog.new_title")}
        description={translateKey("profile", "dialog.new_description")}
      >
        <div className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground">
              {translateKey("profile", "dialog.type_label")}
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setNewTemplateType("tablas")}
                className={cn(
                  "touch-target flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition-all min-h-[44px]",
                  newTemplateType === "tablas"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted/30 text-muted-foreground border-border hover:bg-muted/50"
                )}
              >
                <LayoutGrid className="h-4 w-4" />
                <span>{translateKey("profile", "templates.tab_tables")}</span>
              </button>
              <button
                type="button"
                onClick={() => setNewTemplateType("consumo")}
                className={cn(
                  "touch-target flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition-all min-h-[44px]",
                  newTemplateType === "consumo"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted/30 text-muted-foreground border-border hover:bg-muted/50"
                )}
              >
                <Utensils className="h-4 w-4" />
                <span>{translateKey("profile", "templates.tab_consumption")}</span>
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground">
              {translateKey("profile", "dialog.name_label")}
            </label>
            <input
              value={newTemplateName}
              onChange={(e) => setNewTemplateName(e.target.value)}
              placeholder={translateKey("profile", "dialog.name_placeholder")}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground">
              {translateKey("profile", "dialog.description_label")}
            </label>
            <textarea
              value={newTemplateDesc}
              onChange={(e) => setNewTemplateDesc(e.target.value)}
              rows={3}
              placeholder={translateKey("profile", "dialog.description_placeholder")}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary resize-none"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsDialogOpen(false)}
              className="touch-target min-h-[44px] px-4 py-2 rounded-xl text-xs font-bold text-muted-foreground hover:bg-muted/50 transition-colors"
            >
              {translateKey("common", "actions.cancel")}
            </button>
            <button
              type="button"
              onClick={handleCreateTemplate}
              className="touch-target min-h-[44px] px-5 py-2 rounded-xl text-xs font-black uppercase tracking-wider bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md shadow-primary/20"
            >
              {translateKey("profile", "dialog.save_button")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}

export default ProfilePage;
