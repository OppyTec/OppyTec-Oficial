import { useState, useMemo, useEffect, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  Users,
  Search,
  Plus,
  Edit,
  Trash2,
  Shield,
  KeyRound,
  Mail,
  Phone,
  Building2,
  Camera,
  X,
  Eye,
  EyeOff,
  Palette,
  Check,
  Briefcase,
  Power,
  Lock,
} from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { AreaSelector, OFFICIAL_AREAS } from "@/shared/components/layout/AreaSelector";
import { useAuth } from "@/shared/auth/usePermissions";
import { Can } from "@/shared/auth/Can";
import { apiRequest } from "@/shared/api/httpClient";
import { cn, getImageUrl } from "@/shared/lib";
import { useIsMobile } from "@/shared/hooks/useIsMobile";

export interface UserListItem {
  id: number;
  username: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  userImage?: string | null;
  occupation?: string | null;
  role: "propietario" | "admin" | "supervisor" | "contador" | "user";
  phone?: string | null;
  isActive: boolean;
  areasOperativas?: Array<{ id: string; nombre: string }>;
  settings?: {
    color?: string;
    [key: string]: any;
  } | null;
  directPermissions?: string[];
}

export const CARGO_METADATA_MAP: Record<string, { icono: string; color: string }> = {
  dueño: { icono: "BadgeCheck", color: "#8B5CF6" },
  propietario: { icono: "BadgeCheck", color: "#8B5CF6" },
  administrador: { icono: "Shield", color: "#0EA5E9" },
  admin: { icono: "Shield", color: "#0EA5E9" },
  contador: { icono: "Calculator", color: "#F59E0B" },
  supervisor: { icono: "Search", color: "#10B981" },
  cajero: { icono: "Banknote", color: "#06B6D4" },
  cocinero: { icono: "Utensils", color: "#F97316" },
  chef: { icono: "ChefHat", color: "#F97316" },
  garzón: { icono: "ConciergeBell", color: "#EC4899" },
  garzon: { icono: "ConciergeBell", color: "#EC4899" },
  barman: { icono: "Wine", color: "#EC4899" },
  sommelier: { icono: "Wine", color: "#EC4899" },
  bodeguero: { icono: "Box", color: "#6366F1" },
  steward: { icono: "Sparkles", color: "#14B8A6" },
  recepcionista: { icono: "Luggage", color: "#3B82F6" },
  mucamas: { icono: "Bed", color: "#A855F7" },
};

export const PRESET_COLORS = [
  "#EF4444", "#DC2626", "#B91C1C", "#F43F5E", "#E11D48", "#EC4899", "#DB2777",
  "#F97316", "#EA580C", "#D97706", "#F59E0B", "#EAB308", "#FACC15", "#CA8A04",
  "#84CC16", "#65A30D", "#22C55E", "#16A34A", "#15803D", "#10B981", "#059669",
  "#14B8A6", "#06B6D4", "#0891B2", "#0EA5E9", "#0284C7", "#3B82F6", "#2563EB",
  "#6366F1", "#4F46E5", "#A855F7", "#9333EA", "#8B5CF6", "#7C3AED", "#C026D3",
  "#94A3B8", "#64748B", "#475569", "#78716C", "#57534E", "#525252", "#334155"
];

export const INITIAL_MOCK_USERS: UserListItem[] = [
  {
    id: 1,
    username: "jcampillay",
    email: "jcampillay@oppytec.cl",
    firstName: "Juan",
    lastName: "Campillay",
    occupation: "Dueño",
    role: "propietario",
    phone: "+56 9 8765 4321",
    isActive: true,
    settings: { color: "#8B5CF6" },
    areasOperativas: [
      { id: "cocina-caliente", nombre: "Cocina Caliente" },
      { id: "barra-salon", nombre: "Barra & Salón" },
      { id: "pasteleria", nombre: "Pastelería & Postres" },
      { id: "bodega-central", nombre: "Bodega Central" },
    ],
  },
  {
    id: 2,
    username: "vsoto",
    email: "valentina.soto@oppytec.cl",
    firstName: "Valentina",
    lastName: "Soto",
    occupation: "Administrador",
    role: "admin",
    phone: "+56 9 7654 3210",
    isActive: true,
    settings: { color: "#0EA5E9" },
    areasOperativas: [
      { id: "cocina-caliente", nombre: "Cocina Caliente" },
      { id: "barra-salon", nombre: "Barra & Salón" },
      { id: "bodega-central", nombre: "Bodega Central" },
    ],
  },
  {
    id: 3,
    username: "cmendoza",
    email: "carlos.mendoza@oppytec.cl",
    firstName: "Carlos",
    lastName: "Mendoza",
    occupation: "Supervisor",
    role: "supervisor",
    phone: "+56 9 6543 2109",
    isActive: true,
    settings: { color: "#10B981" },
    areasOperativas: [
      { id: "cocina-caliente", nombre: "Cocina Caliente" },
      { id: "barra-salon", nombre: "Barra & Salón" },
    ],
  },
  {
    id: 4,
    username: "mmorales",
    email: "mateo.morales@oppytec.cl",
    firstName: "Mateo",
    lastName: "Morales",
    occupation: "Chef",
    role: "user",
    phone: "+56 9 5432 1098",
    isActive: true,
    settings: { color: "#F97316" },
    areasOperativas: [
      { id: "cocina-caliente", nombre: "Cocina Caliente" },
    ],
  },
  {
    id: 5,
    username: "crivas",
    email: "camila.rivas@oppytec.cl",
    firstName: "Camila",
    lastName: "Rivas",
    occupation: "Sommelier",
    role: "user",
    phone: "+56 9 4321 0987",
    isActive: true,
    settings: { color: "#EC4899" },
    areasOperativas: [
      { id: "barra-salon", nombre: "Barra & Salón" },
    ],
  },
  {
    id: 6,
    username: "rfigueroa",
    email: "rodrigo.figueroa@oppytec.cl",
    firstName: "Rodrigo",
    lastName: "Figueroa",
    occupation: "Contador",
    role: "contador",
    phone: "+56 9 3210 9876",
    isActive: true,
    settings: { color: "#F59E0B" },
    areasOperativas: [
      { id: "bodega-central", nombre: "Bodega Central" },
    ],
  },
];

export const SYSTEM_MODULE_PERMISSIONS = [
  { code: "inventory.view_products", name: "Ver Productos", module: "Inventario" },
  { code: "inventory.manage_stock", name: "Gestionar Stock", module: "Inventario" },
  { code: "operations.view_movements", name: "Ver Movimientos", module: "Operaciones" },
  { code: "operations.record_consumption", name: "Registrar Consumos", module: "Operaciones" },
  { code: "finance.view_reports", name: "Ver Informes Financieros", module: "Finanzas" },
  { code: "rbac_audit.users.manage", name: "Administrar Usuarios", module: "Configuración" },
];

export function UsuariosPage() {
  const { t } = useTranslation(["users", "common", "navigation"]);
  const { user: currentUser } = useAuth();
  const isMobile = useIsMobile();

  const [activeTab, setActiveTab] = useState<"usuarios" | "cargos" | "roles">("usuarios");
  const [users, setUsers] = useState<UserListItem[]>(INITIAL_MOCK_USERS);
  const [loading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAreaFilter, setSelectedAreaFilter] = useState("all");

  // Create / Edit modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserListItem["role"]>("user");
  const [occupation, setOccupation] = useState("");
  const [color, setColor] = useState("#3B82F6");
  const [selectedAreaIds, setSelectedAreaIds] = useState<string[]>([]);
  const [userImage, setUserImage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Change password modal states
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [passwordTargetUser, setPasswordTargetUser] = useState<UserListItem | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Status toggle confirmation modal
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [statusTargetUser, setStatusTargetUser] = useState<UserListItem | null>(null);

  // Special Permissions modal
  const [isPermsModalOpen, setIsPermsModalOpen] = useState(false);
  const [permsTargetUser, setPermsTargetUser] = useState<UserListItem | null>(null);
  const [userDirectPerms, setUserDirectPerms] = useState<string[]>([]);

  // Load from API with safe fallback
  useEffect(() => {
    let isSubscribed = true;
    async function loadData() {
      try {
        const response = await apiRequest<UserListItem[]>("/user/all", {
          fallbackData: INITIAL_MOCK_USERS,
        });
        if (isSubscribed && response?.data && response.data.length > 0) {
          setUsers(response.data);
        }
      } catch {
        // Safe fallback preserved
      }
    }
    loadData();
    return () => {
      isSubscribed = false;
    };
  }, []);

  // Filtered users
  const filteredUsers = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    return users.filter((u) => {
      const matchesSearch =
        !term ||
        `${u.firstName || ""} ${u.lastName || ""} ${u.username} ${u.email} ${u.occupation || ""}`
          .toLowerCase()
          .includes(term);

      const isGlobal = u.role === "propietario" || u.role === "admin";
      const matchesArea =
        selectedAreaFilter === "all" ||
        !selectedAreaFilter ||
        isGlobal ||
        u.areasOperativas?.some((a) => a.id === selectedAreaFilter);

      return matchesSearch && matchesArea;
    });
  }, [users, searchTerm, selectedAreaFilter]);

  const getInitials = (u: UserListItem) => {
    const f = u.firstName || "";
    const l = u.lastName || "";
    if (f && l) return `${f[0]}${l[0]}`.toUpperCase();
    return (u.username?.[0] || "U").toUpperCase();
  };

  const getRoleBadge = (r: UserListItem["role"]) => {
    switch (r) {
      case "propietario":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-violet-500/10 text-violet-500 border border-violet-500/20">
            {t("users:role_owner", "Propietario")}
          </span>
        );
      case "admin":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-sky-500/10 text-sky-500 border border-sky-500/20">
            {t("users:role_admin", "Administrador")}
          </span>
        );
      case "supervisor":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            {t("users:role_supervisor", "Supervisor")}
          </span>
        );
      case "contador":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-500 border border-amber-500/20">
            {t("users:role_counter", "Contador")}
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-slate-500/10 text-slate-500 border border-slate-500/20">
            {t("users:role_user", "Trabajador")}
          </span>
        );
    }
  };

  const handleOpenCreate = () => {
    setEditingUserId(null);
    setFirstName("");
    setLastName("");
    setUsername("");
    setEmail("");
    setPhone("");
    setPassword("");
    setRole("user");
    setOccupation("Cocinero");
    setColor("#3B82F6");
    setSelectedAreaIds([]);
    setUserImage(null);
    setShowPassword(false);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (u: UserListItem) => {
    setEditingUserId(u.id);
    setFirstName(u.firstName || "");
    setLastName(u.lastName || "");
    setUsername(u.username || "");
    setEmail(u.email || "");
    setPhone(u.phone || "");
    setPassword("");
    setRole(u.role);
    setOccupation(u.occupation || "Cocinero");
    setColor(u.settings?.color || "#3B82F6");
    setSelectedAreaIds(u.areasOperativas?.map((a) => a.id) || []);
    setUserImage(u.userImage || null);
    setIsFormOpen(true);
  };

  const handleSaveUser = async () => {
    if (!firstName.trim() || !lastName.trim() || !email.trim()) {
      toast.error(t("users:validation_name_email", "Por favor completa nombre, apellido y correo electrónico"));
      return;
    }
    if (!editingUserId && (!username.trim() || !password.trim())) {
      toast.error(t("users:validation_username_pass", "Por favor completa el nombre de usuario y contraseña"));
      return;
    }
    if (!editingUserId && password.length < 6) {
      toast.error(t("users:validation_password_len", "La contraseña debe tener al menos 6 caracteres"));
      return;
    }

    setSubmitting(true);
    try {
      const assignedAreas = OFFICIAL_AREAS.filter((a) => selectedAreaIds.includes(a.id)).map((a) => ({
        id: a.id,
        nombre: a.nombre,
      }));

      if (editingUserId) {
        setUsers((prev) =>
          prev.map((u) =>
            u.id === editingUserId
              ? {
                  ...u,
                  firstName: firstName.trim(),
                  lastName: lastName.trim(),
                  email: email.trim(),
                  phone: phone.trim() || null,
                  role,
                  occupation: occupation.trim() || null,
                  areasOperativas: assignedAreas,
                  settings: { ...(u.settings || {}), color },
                  userImage,
                }
              : u
          )
        );
        toast.success(t("users:user_updated", "Usuario actualizado correctamente"));
      } else {
        const newUser: UserListItem = {
          id: Date.now(),
          username: username.trim(),
          firstName: firstName.trim(),
          lastName: lastName.trim(),
          email: email.trim(),
          phone: phone.trim() || null,
          role,
          occupation: occupation.trim() || null,
          isActive: true,
          areasOperativas: assignedAreas,
          settings: { color },
          userImage,
        };
        setUsers((prev) => [newUser, ...prev]);
        toast.success(t("users:user_created", "Usuario creado exitosamente"));
      }
      setIsFormOpen(false);
    } catch {
      toast.error("Error al guardar el usuario");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteUser = (u: UserListItem) => {
    if (u.id === currentUser?.id) {
      toast.error("No puedes eliminar tu propio usuario");
      return;
    }
    const name = u.firstName ? `${u.firstName} ${u.lastName || ""}`.trim() : u.username;
    if (confirm(`¿Estás seguro de que deseas eliminar permanentemente a ${name}?`)) {
      setUsers((prev) => prev.filter((item) => item.id !== u.id));
      toast.success(t("users:user_deleted", "Usuario eliminado correctamente"));
    }
  };

  const handleOpenChangePassword = (u: UserListItem) => {
    setPasswordTargetUser(u);
    setNewPassword("");
    setConfirmPassword("");
    setIsPasswordModalOpen(true);
  };

  const handleSavePassword = () => {
    if (newPassword.length < 6) {
      toast.error(t("users:validation_password_len", "La contraseña debe tener al menos 6 caracteres"));
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Las contraseñas no coinciden");
      return;
    }
    toast.success(t("users:password_changed", "Contraseña actualizada exitosamente"));
    setIsPasswordModalOpen(false);
  };

  const handleOpenStatusToggle = (u: UserListItem) => {
    setStatusTargetUser(u);
    setIsStatusModalOpen(true);
  };

  const handleConfirmStatusToggle = () => {
    if (!statusTargetUser) return;
    setUsers((prev) =>
      prev.map((u) => (u.id === statusTargetUser.id ? { ...u, isActive: !u.isActive } : u))
    );
    toast.success(t("users:status_changed", "Estado del usuario actualizado"));
    setIsStatusModalOpen(false);
  };

  const handleOpenSpecialPerms = (u: UserListItem) => {
    setPermsTargetUser(u);
    setUserDirectPerms(u.directPermissions || []);
    setIsPermsModalOpen(true);
  };

  const handleTogglePerm = (code: string) => {
    setUserDirectPerms((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleSaveDirectPerms = () => {
    if (!permsTargetUser) return;
    setUsers((prev) =>
      prev.map((u) => (u.id === permsTargetUser.id ? { ...u, directPermissions: userDirectPerms } : u))
    );
    toast.success("Permisos actualizados correctamente");
    setIsPermsModalOpen(false);
  };

  const handleImageFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Formato no válido. Debe ser una imagen.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setUserImage(reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="relative min-h-screen px-2 md:px-6 py-4 space-y-6">
      {/* 1. Header con SectionHeader y badge azul */}
      <SectionHeader
        title={t("users:header_title", "Usuarios")}
        subtitle={t("users:header_subtitle", "Administración de accesos, roles y cargos del personal")}
        icon={Users}
        color="#3b82f6"
      />

      {/* 2. Barra de Control / Toolbar Central */}
      <div className="bg-card backdrop-blur-md p-4 rounded-3xl border border-border shadow-xl space-y-4">
        {/* Pestañas Sub-módulos */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center gap-1.5 p-1 bg-muted/60 rounded-2xl border border-border">
            <button
              type="button"
              onClick={() => setActiveTab("usuarios")}
              className={cn(
                "h-9 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2",
                activeTab === "usuarios"
                  ? "bg-[#3b82f6] text-white shadow-md shadow-[#3b82f6]/25"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <Users size={14} />
              <span>{t("users:tab_users", "Usuarios y Accesos")}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("cargos")}
              className={cn(
                "h-9 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2",
                activeTab === "cargos"
                  ? "bg-[#3b82f6] text-white shadow-md shadow-[#3b82f6]/25"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <Briefcase size={14} />
              <span>{t("users:tab_cargos", "Gestión de Cargos")}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("roles")}
              className={cn(
                "h-9 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2",
                activeTab === "roles"
                  ? "bg-[#3b82f6] text-white shadow-md shadow-[#3b82f6]/25"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <Shield size={14} />
              <span>{t("users:tab_roles", "Matriz de Roles")}</span>
            </button>
          </div>

          {/* Botón Acción Primaria */}
          <Can perform="rbac_audit.users.manage">
            <button
              type="button"
              data-testid="btn-nuevo-usuario"
              onClick={handleOpenCreate}
              className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 px-5 rounded-2xl bg-[#3b82f6] hover:bg-[#2563eb] text-white text-xs font-black uppercase tracking-wider shadow-lg shadow-[#3b82f6]/25 active:scale-95 transition-all cursor-pointer"
            >
              <Plus size={16} />
              <span>{t("users:new_user_button", "+ Nuevo Usuario")}</span>
            </button>
          </Can>
        </div>

        {/* Buscador y Selector de Área Operativa */}
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="w-full md:w-auto shrink-0">
            <AreaSelector
              allowAll
              selectedAreaId={selectedAreaFilter}
              onSelectArea={setSelectedAreaFilter}
              buttonClassName="w-full md:w-auto h-11 min-h-[44px] rounded-2xl text-xs font-bold"
            />
          </div>

          <div className="relative flex-1 w-full">
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2 p-1 rounded-lg bg-[#3b82f6]/10 text-[#3b82f6]">
              <Search size={16} />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t("users:search_placeholder", "Buscar usuarios por nombre, usuario, correo o cargo...")}
              className="w-full h-11 min-h-[44px] pl-11 pr-10 rounded-2xl bg-background border border-[#3b82f6]/30 shadow-[0_0_12px_rgba(59,130,246,0.12)] focus:shadow-[0_0_16px_rgba(59,130,246,0.25)] focus:border-[#3b82f6] outline-none text-xs font-medium text-foreground transition-all"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm("")}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground cursor-pointer"
                title={t("users:clear_search", "Limpiar búsqueda")}
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 3. Listado de Usuarios / Tarjetas */}
      {activeTab === "usuarios" && (
        <div className="space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="h-10 w-10 animate-spin rounded-2xl border-4 border-[#3b82f6] border-t-transparent shadow-md" />
              <p className="text-sm font-semibold text-muted-foreground">
                {t("users:loading", "Cargando personal...")}
              </p>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-16 border-2 border-dashed rounded-[2.5rem] border-border bg-card/40 p-8">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3 opacity-40" />
              <p className="text-sm font-bold text-muted-foreground">
                {t("users:no_users_found", "No se encontraron usuarios.")}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4" data-testid="users-list-container">
              {filteredUsers.map((u) => {
                const cargoMeta = u.occupation
                  ? CARGO_METADATA_MAP[u.occupation.toLowerCase()] || { icono: "Briefcase", color: "#3B82F6" }
                  : { icono: "Briefcase", color: "#3B82F6" };

                return (
                  <div
                    key={u.id}
                    data-testid={`user-card-${u.username}`}
                    className="p-5 rounded-3xl border border-border bg-card/70 backdrop-blur-xl shadow-lg hover:shadow-xl hover:border-[#3b82f6]/40 transition-all duration-300 relative overflow-hidden"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
                      {/* Avatar y Perfil */}
                      <div className="flex items-center gap-4">
                        <div
                          className="h-16 w-16 rounded-2xl overflow-hidden border-2 bg-muted flex items-center justify-center shrink-0 shadow-inner relative"
                          style={{
                            borderColor: u.settings?.color || "#3B82F6",
                            backgroundColor: `${u.settings?.color || "#3B82F6"}15`,
                          }}
                        >
                          {u.userImage ? (
                            <img src={getImageUrl(u.userImage)} alt="Avatar" className="h-full w-full object-cover" />
                          ) : (
                            <span
                              className="text-lg font-black"
                              style={{ color: u.settings?.color || "#3B82F6" }}
                            >
                              {getInitials(u)}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="text-base font-extrabold tracking-tight text-foreground">
                              {u.firstName || u.lastName ? `${u.firstName || ""} ${u.lastName || ""}`.trim() : u.username}
                            </h3>
                            {getRoleBadge(u.role)}
                            <span
                              className={cn(
                                "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border",
                                u.isActive
                                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                                  : "bg-zinc-500/10 text-zinc-500 border-zinc-500/20"
                              )}
                            >
                              {u.isActive ? t("users:active", "Activo") : t("users:inactive", "Inactivo")}
                            </span>
                          </div>

                          <p className="text-xs font-bold text-muted-foreground">
                            @{u.username}
                          </p>

                          {u.occupation && (
                            <div
                              className="flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded-lg border w-fit shadow-xs"
                              style={{
                                color: cargoMeta.color,
                                backgroundColor: `${cargoMeta.color}15`,
                                borderColor: `${cargoMeta.color}35`,
                              }}
                            >
                              <CategoryIcon name={cargoMeta.icono} className="h-3.5 w-3.5" />
                              <span>{u.occupation}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Áreas Operativas */}
                      <div className="space-y-1.5 md:max-w-xs w-full">
                        <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground flex items-center gap-1">
                          <Building2 size={12} className="text-primary" /> {t("users:operational_areas", "Áreas Operativas")}
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {u.areasOperativas && u.areasOperativas.length > 0 ? (
                            u.areasOperativas.map((area) => (
                              <span
                                key={area.id}
                                className="px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-primary/10 border border-primary/20 text-primary"
                              >
                                {area.nombre}
                              </span>
                            ))
                          ) : u.role === "admin" || u.role === "propietario" ? (
                            <span className="px-2.5 py-0.5 rounded-full text-[9px] font-black tracking-wider uppercase bg-sky-500/10 border border-sky-500/20 text-sky-400">
                              {t("users:global_access", "Todas las Áreas (Global)")}
                            </span>
                          ) : (
                            <span className="text-[10px] text-muted-foreground font-semibold italic">
                              {t("users:unassigned_area", "Sin área asignada")}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Contacto */}
                      <div className="space-y-1 text-xs">
                        <div className="flex items-center gap-2 font-bold text-foreground">
                          <Mail size={13} className="text-primary shrink-0" />
                          <span>{u.email}</span>
                        </div>
                        {u.phone && (
                          <div className="flex items-center gap-2 font-bold text-muted-foreground">
                            <Phone size={13} className="text-primary shrink-0" />
                            <span>{u.phone}</span>
                          </div>
                        )}
                      </div>

                      {/* Botones de Acción (Touch targets >= 44px) */}
                      <div className="flex items-center justify-end gap-2 border-t md:border-t-0 pt-3 md:pt-0 border-border shrink-0">
                        <Can perform="rbac_audit.users.manage">
                          <button
                            type="button"
                            onClick={() => handleOpenSpecialPerms(u)}
                            title={t("users:action_special_perms", "Permisos especiales")}
                            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border bg-card hover:bg-blue-500/10 hover:text-blue-500 hover:border-blue-500/30 transition-all cursor-pointer"
                          >
                            <KeyRound size={16} />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleOpenChangePassword(u)}
                            title={t("users:action_change_password", "Cambiar Contraseña")}
                            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border bg-card hover:bg-amber-500/10 hover:text-amber-500 hover:border-amber-500/30 transition-all cursor-pointer"
                          >
                            <Lock size={16} />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleOpenEdit(u)}
                            title={t("users:action_edit", "Editar")}
                            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border bg-card hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all cursor-pointer"
                          >
                            <Edit size={16} />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleOpenStatusToggle(u)}
                            title={t("users:action_toggle_status", "Activar / Desactivar")}
                            className={cn(
                              "touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border bg-card transition-all cursor-pointer",
                              u.isActive
                                ? "hover:bg-amber-500/10 hover:text-amber-500"
                                : "hover:bg-emerald-500/10 hover:text-emerald-500"
                            )}
                          >
                            <Power size={16} />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleDeleteUser(u)}
                            title={t("users:action_delete", "Eliminar")}
                            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-border bg-card hover:bg-destructive/15 hover:text-destructive hover:border-destructive/30 transition-all cursor-pointer"
                          >
                            <Trash2 size={16} />
                          </button>
                        </Can>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 4. Tab Cargos Placeholder / Overview */}
      {activeTab === "cargos" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(CARGO_METADATA_MAP).map(([name, meta]) => {
            const count = users.filter((u) => u.occupation?.toLowerCase() === name.toLowerCase()).length;
            return (
              <div
                key={name}
                className="p-5 rounded-3xl border border-border bg-card/60 backdrop-blur-xl shadow-lg flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="h-12 w-12 rounded-2xl flex items-center justify-center shrink-0 border"
                    style={{
                      backgroundColor: `${meta.color}15`,
                      borderColor: `${meta.color}35`,
                      color: meta.color,
                    }}
                  >
                    <CategoryIcon name={meta.icono} className="h-6 w-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-black capitalize text-foreground">{name}</h4>
                    <p className="text-[10px] text-muted-foreground">
                      {count} {t("users:collaborators_count_plural", "colaboradores")}
                    </p>
                  </div>
                </div>
                <span
                  className="px-2.5 py-1 rounded-xl text-[10px] font-black uppercase tracking-wider border"
                  style={{
                    backgroundColor: `${meta.color}10`,
                    borderColor: `${meta.color}30`,
                    color: meta.color,
                  }}
                >
                  {name === "dueño" || name === "administrador" ? t("users:system", "Sistema") : t("users:custom", "Personalizado")}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Tab Roles Placeholder / Matriz */}
      {activeTab === "roles" && (
        <div className="p-6 rounded-3xl border border-border bg-card/60 backdrop-blur-xl space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h3 className="text-lg font-black text-foreground">
                {t("users:tab_roles", "Matriz de Roles y Permisos")}
              </h3>
              <p className="text-xs text-muted-foreground">
                Configuración granular de los permisos asignados a cada nivel jerárquico.
              </p>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
              RBAC v2.0
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {SYSTEM_MODULE_PERMISSIONS.map((p) => (
              <div key={p.code} className="p-4 rounded-2xl border border-border bg-background/50 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-foreground">{p.name}</span>
                  <span className="text-[9px] font-bold text-primary uppercase">{p.module}</span>
                </div>
                <p className="text-[10px] text-muted-foreground font-mono">{p.code}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL 1: Crear / Editar Usuario */}
      <ResponsiveDialog
        open={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        title={editingUserId ? t("users:modal_edit_title", "Editar Usuario") : t("users:modal_create_title", "Crear Nuevo Usuario")}
        description={
          editingUserId
            ? t("users:modal_edit_desc", "Modifica la información de perfil, cargo, rol y áreas operativas asignadas al usuario.")
            : t("users:modal_create_desc", "Registra un nuevo miembro del equipo. Se activará inmediatamente sin requerir validación de correo.")
        }
        isMobile={isMobile}
      >
        <div className="max-h-[75vh] overflow-y-auto pr-1 space-y-5 custom-scrollbar">
          {/* Avatar Preview & Upload */}
          <div className="flex items-center gap-4 p-3 rounded-2xl bg-muted/40 border border-border">
            <div
              className="relative h-16 w-16 rounded-2xl overflow-hidden border-2 bg-muted flex items-center justify-center shrink-0 shadow-inner"
              style={{ borderColor: color, backgroundColor: `${color}20` }}
            >
              {userImage ? (
                <img src={getImageUrl(userImage)} alt="Avatar" className="h-full w-full object-cover" />
              ) : (
                <span className="text-xl font-black" style={{ color }}>
                  {firstName && firstName[0] ? firstName[0].toUpperCase() : "U"}
                </span>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-xs font-black uppercase tracking-wider text-foreground block">
                {t("users:field_profile_picture", "Foto de Perfil")}
              </label>
              <p className="text-[10px] text-muted-foreground">
                {t("users:field_profile_picture_help", "Formatos JPG, PNG o WebP (máx. 5MB).")}
              </p>
              <div className="flex items-center gap-2 pt-1">
                <label className="touch-target inline-flex min-h-[36px] items-center gap-1.5 px-3 rounded-xl bg-primary text-primary-foreground text-xs font-bold cursor-pointer hover:bg-primary/90">
                  <Camera size={14} />
                  <span>Subir</span>
                  <input type="file" accept="image/*" onChange={handleImageFileChange} className="hidden" />
                </label>
                {userImage && (
                  <button
                    type="button"
                    onClick={() => setUserImage(null)}
                    className="text-xs font-bold text-destructive hover:underline cursor-pointer"
                  >
                    {t("users:remove_picture", "Quitar foto")}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_first_name", "Nombre")} *
              </label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder={t("users:field_first_name_placeholder", "Ej: Juan")}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_last_name", "Apellido")} *
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder={t("users:field_last_name_placeholder", "Ej: Pérez")}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_username", "Nombre de Usuario")} *
              </label>
              <input
                type="text"
                value={username}
                disabled={Boolean(editingUserId)}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t("users:field_username_placeholder", "Ej: juan.perez")}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary disabled:opacity-50"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_email", "Correo Electrónico")} *
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("users:field_email_placeholder", "juan@restaurante.com")}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_phone", "Teléfono")}
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder={t("users:field_phone_placeholder", "+56 9 1234 5678")}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
              />
            </div>

            {!editingUserId && (
              <div className="space-y-1">
                <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                  {t("users:field_password", "Contraseña")} *
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t("users:field_password_placeholder", "Mínimo 6 caracteres")}
                    className="w-full h-11 pl-3 pr-10 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_role", "Rol del Sistema")}
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserListItem["role"])}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary cursor-pointer"
              >
                <option value="user">{t("users:role_user", "Trabajador")}</option>
                <option value="supervisor">{t("users:role_supervisor", "Supervisor")}</option>
                <option value="contador">{t("users:role_counter", "Contador")}</option>
                <option value="admin">{t("users:role_admin", "Administrador")}</option>
                <option value="propietario">{t("users:role_owner", "Propietario")}</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                {t("users:field_cargo", "Cargo / Posición")}
              </label>
              <select
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary cursor-pointer"
              >
                <option value="Cocinero">Cocinero</option>
                <option value="Chef">Chef Ejecutivo</option>
                <option value="Garzón">Garzón / Salón</option>
                <option value="Barman">Barman / Sommelier</option>
                <option value="Bodeguero">Bodeguero / Almacén</option>
                <option value="Stewart">Stewart / Limpieza</option>
                <option value="Cajero">Cajero / Tesorería</option>
                <option value="Supervisor">Supervisor de Operaciones</option>
                <option value="Administrador">Administrador General</option>
                <option value="Dueño">Dueño / Propietario</option>
              </select>
            </div>
          </div>

          {/* Color Selector */}
          <div className="space-y-2 border-t border-border pt-3">
            <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Palette size={14} className="text-primary" />
              {t("users:field_color", "Color Representativo")}
            </label>
            <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-1 bg-muted/20 rounded-2xl border border-border custom-scrollbar">
              {PRESET_COLORS.map((c) => (
                <button
                  type="button"
                  key={c}
                  onClick={() => setColor(c)}
                  style={{ backgroundColor: c }}
                  className={cn(
                    "h-7 w-7 rounded-full flex items-center justify-center transition-all cursor-pointer border border-black/20",
                    color === c ? "scale-110 ring-2 ring-primary ring-offset-2 ring-offset-card shadow-md" : "hover:scale-105 opacity-80"
                  )}
                >
                  {color === c && <Check size={14} className="text-white stroke-[3]" />}
                </button>
              ))}
            </div>
          </div>

          {/* Multi-select Operational Areas */}
          <div className="space-y-2 border-t border-border pt-3">
            <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Building2 size={14} className="text-primary" />
              {t("users:field_areas", "Asignar Áreas Operativas")}
            </label>
            <div className="flex flex-wrap gap-2">
              {OFFICIAL_AREAS.filter((a) => a.id !== "all").map((area) => {
                const isSelected = selectedAreaIds.includes(area.id);
                return (
                  <button
                    type="button"
                    key={area.id}
                    onClick={() => {
                      setSelectedAreaIds((prev) =>
                        isSelected ? prev.filter((id) => id !== area.id) : [...prev, area.id]
                      );
                    }}
                    className={cn(
                      "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all border cursor-pointer",
                      isSelected
                        ? "bg-primary text-primary-foreground border-primary shadow-sm"
                        : "bg-muted/40 text-muted-foreground border-border hover:bg-muted"
                    )}
                  >
                    {area.nombre}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Dialog Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setIsFormOpen(false)}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-4 rounded-xl border border-border text-xs font-bold text-muted-foreground hover:bg-muted cursor-pointer"
            >
              {t("users:btn_cancel", "Cancelar")}
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={handleSaveUser}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-6 rounded-xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider shadow-lg shadow-primary/25 hover:bg-primary/90 cursor-pointer"
            >
              {submitting
                ? t("users:saving", "Guardando...")
                : editingUserId
                  ? t("users:btn_save", "Guardar Cambios")
                  : t("users:btn_create", "Crear Usuario")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      {/* MODAL 2: Cambiar Contraseña */}
      <ResponsiveDialog
        open={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
        title={t("users:modal_password_title", "Cambiar Contraseña")}
        description={t("users:modal_password_desc", { username: passwordTargetUser?.username || "" })}
        isMobile={isMobile}
      >
        <div className="space-y-4 pt-2">
          <div className="space-y-1">
            <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
              {t("users:new_password", "Nueva Contraseña")}
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Mínimo 6 caracteres"
              className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
              {t("users:confirm_password", "Confirmar Contraseña")}
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repite la nueva contraseña"
              className="w-full h-11 px-3 rounded-xl bg-background border border-border text-xs font-bold text-foreground outline-none focus:border-primary"
            />
          </div>
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setIsPasswordModalOpen(false)}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-4 rounded-xl border border-border text-xs font-bold text-muted-foreground hover:bg-muted cursor-pointer"
            >
              {t("users:btn_cancel", "Cancelar")}
            </button>
            <button
              type="button"
              onClick={handleSavePassword}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-6 rounded-xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider shadow-lg shadow-primary/25 cursor-pointer"
            >
              {t("users:btn_confirm", "Confirmar")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      {/* MODAL 3: Activar / Desactivar Estado */}
      <ResponsiveDialog
        open={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
        title={t("users:modal_status_title", "¿Cambiar estado del usuario?")}
        description={t("users:modal_status_desc", {
          username: statusTargetUser?.username || "",
          status: statusTargetUser?.isActive
            ? t("users:status_inactive", "inactivo y no podrá ingresar al sistema")
            : t("users:status_active", "activo y podrá iniciar sesión"),
        })}
        isMobile={isMobile}
      >
        <div className="space-y-4 pt-2">
          <p className="text-xs text-muted-foreground">
            {statusTargetUser?.isActive
              ? "El colaborador no podrá acceder a la plataforma hasta que sea reactivado por un administrador."
              : "El colaborador recuperará el acceso inmediato a todas sus funciones asignadas."}
          </p>
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setIsStatusModalOpen(false)}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-4 rounded-xl border border-border text-xs font-bold text-muted-foreground hover:bg-muted cursor-pointer"
            >
              {t("users:btn_cancel", "Cancelar")}
            </button>
            <button
              type="button"
              onClick={handleConfirmStatusToggle}
              className={cn(
                "touch-target inline-flex min-h-[44px] items-center justify-center px-6 rounded-xl text-white text-xs font-black uppercase tracking-wider shadow-lg cursor-pointer",
                statusTargetUser?.isActive ? "bg-amber-600 hover:bg-amber-700" : "bg-emerald-600 hover:bg-emerald-700"
              )}
            >
              {t("users:btn_confirm", "Confirmar")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      {/* MODAL 4: Permisos Excepcionales Directos */}
      <ResponsiveDialog
        open={isPermsModalOpen}
        onClose={() => setIsPermsModalOpen(false)}
        title={t("users:modal_perms_title", "Permisos Especiales Excepcionales")}
        description={t("users:modal_perms_desc", "Otorga o revoca accesos individuales para el colaborador.")}
        isMobile={isMobile}
      >
        <div className="space-y-4 pt-2 max-h-[60vh] overflow-y-auto custom-scrollbar pr-1">
          <div className="p-3 bg-primary/10 border border-primary/20 rounded-xl text-xs flex items-center justify-between">
            <span className="font-bold text-foreground">
              {permsTargetUser?.firstName} {permsTargetUser?.lastName} (@{permsTargetUser?.username})
            </span>
            <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-primary/20 text-primary">
              {permsTargetUser?.role}
            </span>
          </div>

          <div className="space-y-2">
            {SYSTEM_MODULE_PERMISSIONS.map((perm) => {
              const isAssigned = userDirectPerms.includes(perm.code);
              return (
                <button
                  type="button"
                  key={perm.code}
                  onClick={() => handleTogglePerm(perm.code)}
                  className={cn(
                    "w-full flex items-center justify-between p-3 rounded-xl border text-left text-xs transition-all cursor-pointer",
                    isAssigned ? "bg-primary/15 border-primary/40 text-foreground" : "bg-card/50 border-border text-muted-foreground hover:bg-muted"
                  )}
                >
                  <div className="space-y-0.5">
                    <span className="font-bold block text-foreground">{perm.name}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">{perm.code}</span>
                  </div>
                  <div
                    className={cn(
                      "h-5 w-5 rounded-md flex items-center justify-center border",
                      isAssigned ? "bg-primary border-primary text-primary-foreground" : "border-border"
                    )}
                  >
                    {isAssigned && <Check size={12} className="stroke-[3]" />}
                  </div>
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={() => setIsPermsModalOpen(false)}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-4 rounded-xl border border-border text-xs font-bold text-muted-foreground hover:bg-muted cursor-pointer"
            >
              {t("users:btn_cancel", "Cancelar")}
            </button>
            <button
              type="button"
              onClick={handleSaveDirectPerms}
              className="touch-target inline-flex min-h-[44px] items-center justify-center px-6 rounded-xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider shadow-lg shadow-primary/25 cursor-pointer"
            >
              {t("users:btn_save_perms", "Guardar y Cerrar")}
            </button>
          </div>
        </div>
      </ResponsiveDialog>
    </div>
  );
}

export default UsuariosPage;
