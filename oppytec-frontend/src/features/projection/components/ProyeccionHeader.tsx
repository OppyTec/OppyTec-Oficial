/**
 * oppytec-frontend/src/features/projection/components/ProyeccionHeader.tsx
 * Header Canónico de la feature Proyección con SectionHeader y ADN Visual Legacy (#10b981).
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import { TrendingUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { cn } from "@/shared/lib";

export interface ProyeccionHeaderProps {
  readonly center?: boolean;
  readonly className?: string;
}

export const PROJECTION_THEME_COLOR = "#10b981";

export const ProyeccionHeader: FC<ProyeccionHeaderProps> = ({
  center = true,
  className,
}) => {
  const { t } = useTranslation("projection");

  const title = t("header.title", { defaultValue: "Proyección" });
  const subtitle = t("header.subtitle", {
    defaultValue: "Simulación de Disponibilidad y Alertas",
  });

  return (
    <div
      className={cn("w-full mb-3", className)}
      data-testid="proyeccion-header"
    >
      <SectionHeader
        title={title}
        subtitle={subtitle}
        icon={TrendingUp}
        color={PROJECTION_THEME_COLOR}
        center={center}
      />
    </div>
  );
};

export default ProyeccionHeader;
