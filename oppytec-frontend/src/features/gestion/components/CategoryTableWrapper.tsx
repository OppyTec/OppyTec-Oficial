import React, { useRef, useEffect, useCallback } from "react";
import { cn } from "@/shared/lib";

export interface ColumnDef {
  key: string;
  label: string;
}

export interface CategoryTableWrapperProps {
  catId: string;
  activeCols: ColumnDef[];
  minTableWidth: number;
  columnWidths: Record<string, string>;
  getColWidthPx: (key: string) => number;
  onHorizontalScroll?: (scrollLeft: number, sourceId: string) => void;
  registerContainer?: (id: string, el: HTMLDivElement | null) => void;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
}

export const CategoryTableWrapper: React.FC<CategoryTableWrapperProps> = ({
  catId,
  activeCols,
  minTableWidth,
  columnWidths,
  getColWidthPx,
  onHorizontalScroll,
  registerContainer,
  children,
  className,
  headerClassName,
}) => {
  const headerScrollRef = useRef<HTMLDivElement>(null);
  const bodyScrollRef = useRef<HTMLDivElement>(null);

  // Registrar contenedor del cuerpo para sincronización horizontal global entre categorías
  useEffect(() => {
    if (registerContainer) {
      registerContainer(catId, bodyScrollRef.current);
      return () => registerContainer(catId, null);
    }
  }, [catId, registerContainer]);

  // Sincronizar encabezado al desplazar el cuerpo
  const handleBodyScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const scrollLeft = e.currentTarget.scrollLeft;
      if (headerScrollRef.current && headerScrollRef.current.scrollLeft !== scrollLeft) {
        headerScrollRef.current.scrollLeft = scrollLeft;
      }
      if (onHorizontalScroll) {
        onHorizontalScroll(scrollLeft, catId);
      }
    },
    [catId, onHorizontalScroll]
  );

  // Desplazamiento horizontal con clic en la rueda del mouse (botón central / middle click drag)
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button === 1) {
      // Middle click / wheel button
      e.preventDefault();
      e.stopPropagation();

      const body = bodyScrollRef.current;
      const header = headerScrollRef.current;
      if (!body) return;

      const startX = e.clientX;
      const startScrollLeft = body.scrollLeft;
      let hasMoved = false;

      document.body.style.userSelect = "none";
      document.body.style.cursor = "grabbing";

      const onMouseMove = (ev: MouseEvent) => {
        ev.preventDefault();
        const dx = ev.clientX - startX;
        if (Math.abs(dx) > 3) {
          hasMoved = true;
        }
        const newScrollLeft = startScrollLeft - dx;
        body.scrollLeft = newScrollLeft;
        if (header) header.scrollLeft = newScrollLeft;
      };

      const cleanup = () => {
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        window.removeEventListener("blur", cleanup);
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
      };

      const onMouseUp = (ev: MouseEvent) => {
        if (ev.button === 1 || ev.buttons === 0) {
          ev.preventDefault();
          cleanup();

          // Si sólo hizo clic sin arrastrar, permitir desplazamiento horizontal libre hasta el siguiente clic
          if (!hasMoved) {
            activateClickPan(startX, body, header);
          }
        }
      };

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
      window.addEventListener("blur", cleanup);
    }
  };

  const activateClickPan = (
    initialX: number,
    body: HTMLDivElement,
    header: HTMLDivElement | null
  ) => {
    const initialScroll = body.scrollLeft;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "ew-resize";

    const onPanMove = (ev: MouseEvent) => {
      const dx = ev.clientX - initialX;
      const newScroll = initialScroll - dx;
      body.scrollLeft = newScroll;
      if (header) header.scrollLeft = newScroll;
    };

    const endPan = (ev?: Event) => {
      if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
      }
      window.removeEventListener("mousemove", onPanMove);
      window.removeEventListener("mousedown", endPan, true);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("blur", endPan);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") endPan();
    };

    setTimeout(() => {
      window.addEventListener("mousemove", onPanMove);
      window.addEventListener("mousedown", endPan, true);
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("blur", endPan);
    }, 50);
  };

  const handleAuxClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button === 1) {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const colGroup = (
    <colgroup>
      <col style={{ width: "240px", minWidth: "200px" }} />
      {activeCols.map((col) => {
        const colW = getColWidthPx(col.key);
        return (
          <col
            key={col.key}
            style={{ width: `${colW}px`, minWidth: `${colW}px` }}
          />
        );
      })}
      <col style={{ width: "96px", minWidth: "96px" }} />
    </colgroup>
  );

  return (
    <div
      data-testid={`category-table-wrapper-${catId}`}
      className={cn("hidden md:block pb-4 px-1", className)}
    >
      {/* ─── ENCABEZADO FIJO NATIVO (Sticky top-20 z-20 sin JavaScript en vertical) ─── */}
      <div className={cn("sticky top-20 z-20 pb-1 select-none", headerClassName)}>
        <div
          ref={headerScrollRef}
          onMouseDown={handleMouseDown}
          onAuxClick={handleAuxClick}
          className="overflow-x-hidden"
        >
          <table
            className="w-full text-sm border-separate table-fixed"
            style={{ minWidth: `${minTableWidth}px`, borderSpacing: "0" }}
          >
            {colGroup}
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="bg-card border-y border-l border-input rounded-l-xl px-4 py-3 font-bold text-[10px] uppercase tracking-wider shadow-xs">
                  Producto
                </th>
                {activeCols.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      "bg-card border-y border-input px-3 py-3 font-bold text-[10px] uppercase tracking-wider text-center shadow-xs",
                      columnWidths[col.key] || "w-[120px]"
                    )}
                  >
                    {col.label}
                  </th>
                ))}
                <th className="bg-card border-y border-r border-input rounded-r-xl px-4 py-3 w-24 text-center font-bold text-[10px] uppercase tracking-wider shadow-xs">
                  Acciones
                </th>
              </tr>
            </thead>
          </table>
        </div>
      </div>

      {/* ─── CUERPO DE LA TABLA CON SCROLL HORIZONTAL Y ARRASTRE DE RUEDA ─── */}
      <div
        ref={bodyScrollRef}
        onScroll={handleBodyScroll}
        onMouseDown={handleMouseDown}
        onAuxClick={handleAuxClick}
        data-testid={`category-table-body-${catId}`}
        className="overflow-x-auto overflow-y-hidden pb-4 custom-table-scrollbar"
      >
        <table
          className="w-full text-sm border-separate table-fixed"
          style={{ minWidth: `${minTableWidth}px`, borderSpacing: "0 8px" }}
        >
          {colGroup}
          <tbody>{children}</tbody>
        </table>
      </div>
    </div>
  );
};

export default CategoryTableWrapper;
