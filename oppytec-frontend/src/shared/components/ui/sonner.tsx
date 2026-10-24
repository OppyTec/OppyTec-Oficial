import type { ComponentProps } from "react";
import { Toaster as Sonner, toast } from "sonner";
import { useTheme } from "@/shared/hooks/useTheme";

export type ToasterProps = ComponentProps<typeof Sonner>;

/**
 * Toast Notification Card unificado de OppyTec v2.0.
 * Réplica de la experiencia Legacy con ADN Visual Mobile-First,
 * soporte para los 3 temas (light, dark, ocean-blue), richColors y backdrop blur.
 */
export function Toaster({
  position = "top-right",
  duration = 4000,
  closeButton = true,
  richColors = true,
  toastOptions,
  ...props
}: ToasterProps) {
  const { theme } = useTheme();

  return (
    <Sonner
      theme={theme === "light" ? "light" : "dark"}
      className="toaster group"
      position={position}
      duration={duration}
      closeButton={closeButton}
      richColors={richColors}
      data-theme={theme}
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-card group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-xl group-[.toaster]:backdrop-blur-md rounded-xl p-4 font-sans text-sm border",
          description: "group-[.toast]:text-muted-foreground text-xs",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground font-medium text-xs px-3 py-1.5 rounded-lg",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground font-medium text-xs px-3 py-1.5 rounded-lg",
          closeButton:
            "group-[.toast]:bg-card group-[.toast]:border-border group-[.toast]:text-foreground hover:group-[.toast]:bg-muted",
          ...toastOptions?.classNames,
        },
        ...toastOptions,
      }}
      {...props}
    />
  );
}

export { toast };
