import { motion } from "framer-motion";
import { Package, ShieldAlert } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/auth/usePermissions";
import { translateKey } from "@/shared/i18n";

export function LoginBranding() {
  return (
    <div className="hidden lg:flex flex-col justify-center p-12 bg-primary text-primary-foreground relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none">
        <div className="absolute top-10 left-10 w-64 h-64 bg-white rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-white rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 space-y-6">
        <div className="bg-white/20 w-16 h-16 rounded-2xl flex items-center justify-center backdrop-blur-md">
          <Package size={32} />
        </div>
        <h1 className="text-5xl font-black tracking-tighter leading-tight">
          OppyTec
        </h1>
        <p className="text-xl opacity-80 font-medium">
          Gestión inteligente para la industria hotelera y restaurantes.
        </p>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const result = await signIn(email, password, undefined, false);
    if (result.error) {
      setError(result.error);
      setSubmitting(false);
    } else {
      setSubmitting(false);
      navigate("/", { replace: true });
    }
  };

  return (
    <div
      className="min-h-screen w-full grid lg:grid-cols-2 bg-secondary/30"
      data-testid="client-login-page"
    >
      <LoginBranding />

      <main className="flex items-center justify-center p-6 md:p-12">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-sm space-y-8"
        >
          <div className="text-center lg:text-left space-y-2">
            <h2 className="text-3xl font-black tracking-tight">Bienvenido</h2>
            <p className="text-muted-foreground">
              Ingresa al panel de control de inventario.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-sm font-medium leading-none"
              >
                Usuario o Email
              </label>
              <input
                id="email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="usuario@ejemplo.com"
                className="h-12 w-full rounded-md border border-input bg-background/50 px-3 py-2 text-sm backdrop-blur-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                autoCapitalize="none"
                autoComplete="username"
                autoCorrect="off"
                spellCheck="false"
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-sm font-medium leading-none"
              >
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-12 w-full rounded-md border border-input bg-background/50 px-3 py-2 text-sm backdrop-blur-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                autoCapitalize="none"
                autoComplete="current-password"
                autoCorrect="off"
                spellCheck="false"
                required
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                data-testid="login-error-box"
                className="bg-destructive/10 border border-destructive/20 text-destructive text-xs font-bold text-center p-3 rounded-xl"
              >
                {error}
              </motion.div>
            )}

            <button
              type="submit"
              className="w-full h-12 rounded-md bg-primary text-primary-foreground font-bold text-base shadow-lg shadow-primary/20 hover:bg-primary/90 disabled:opacity-50"
              disabled={submitting}
            >
              {submitting ? "Validando..." : "Ingresar al Sistema"}
            </button>
          </form>

          <p className="text-center text-xs text-muted-foreground pt-4">
            ® {new Date().getFullYear()} OppyTec. Todos los derechos reservados.
          </p>
        </motion.div>
      </main>
    </div>
  );
}

export function AdminLoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const result = await signIn(email, password, undefined, true);
    if (result.error) {
      setError(result.error);
      setSubmitting(false);
    } else {
      setSubmitting(false);
      navigate("/admin", { replace: true });
    }
  };

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center bg-zinc-950 p-4"
      data-testid="admin-login-page"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden"
      >
        <div className="p-8 space-y-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="h-16 w-16 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
              <ShieldAlert className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Acceso Restringido
              </h2>
              <p className="text-sm text-zinc-400 mt-1">
                Global SaaS Administration
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="admin-email"
                className="text-sm font-medium leading-none text-zinc-300"
              >
                Usuario Administrador
              </label>
              <input
                id="admin-email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@oppytec.com"
                className="h-12 w-full rounded-md bg-zinc-950/50 border border-zinc-800 px-3 py-2 text-white placeholder:text-zinc-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                autoCapitalize="none"
                autoComplete="username"
                autoCorrect="off"
                spellCheck="false"
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="admin-password"
                className="text-sm font-medium leading-none text-zinc-300"
              >
                Clave de Acceso
              </label>
              <input
                id="admin-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-12 w-full rounded-md bg-zinc-950/50 border border-zinc-800 px-3 py-2 text-white placeholder:text-zinc-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                autoCapitalize="none"
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <div
                data-testid="admin-login-error-box"
                className="p-3 rounded-lg bg-red-950/50 border border-red-900/50 text-red-400 text-sm font-medium text-center"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="w-full h-12 rounded-md bg-primary text-primary-foreground font-bold text-base mt-2 hover:bg-primary/90 disabled:opacity-50"
              disabled={submitting}
            >
              {submitting ? "Autenticando..." : "Ingresar"}
            </button>
          </form>
        </div>
        <div className="bg-zinc-950 p-4 text-center border-t border-zinc-800">
          <p className="text-xs text-zinc-600">
            OppyTec Cloud Infrastructure © {new Date().getFullYear()}
          </p>
        </div>
      </motion.div>
    </div>
  );
}

export function AuthFeatureView() {
  const [viewMode, setViewMode] = useState<"client" | "admin">("client");

  return (
    <section data-testid="feature-auth" className="space-y-4">
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          data-testid="switch-auth-client"
          onClick={() => setViewMode("client")}
          className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground"
        >
          {translateKey("auth", "login.title")}
        </button>
        <button
          type="button"
          data-testid="switch-auth-admin"
          onClick={() => setViewMode("admin")}
          className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground"
        >
          {translateKey("auth", "admin_login.title")}
        </button>
      </div>
      {viewMode === "admin" ? <AdminLoginPage /> : <LoginPage />}
    </section>
  );
}
