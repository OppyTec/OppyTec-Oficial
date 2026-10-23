import { Edit, Plus, Search, Trash2 } from "lucide-react";
import { type ReactNode, useMemo, useState } from "react";
import { Can } from "@/shared/auth/Can";
import type { ThreeLevelPermission } from "@/shared/auth/usePermissions";
import { translateKey } from "@/shared/i18n";

export interface ColumnDef<T> {
  readonly key: string;
  readonly label: string;
  readonly render?: (row: T) => ReactNode;
}

export interface DynamicAdminTableProps<T> {
  readonly title: string;
  readonly description?: string;
  readonly data: readonly T[];
  readonly columns: readonly ColumnDef<T>[];
  readonly loading?: boolean;
  readonly searchable?: boolean;
  readonly searchPlaceholder?: string;
  readonly onSearch?: (query: string) => void;
  readonly onCreate?: () => void;
  readonly createButtonLabel?: string;
  readonly createPermission?: ThreeLevelPermission;
  readonly onEdit?: (row: T) => void;
  readonly editPermission?: ThreeLevelPermission;
  readonly onDelete?: (row: T) => void;
  readonly deletePermission?: ThreeLevelPermission;
  readonly primaryKey?: keyof T | string;
  readonly testId?: string;
}

/**
 * ADN Visual Legacy: DynamicAdminTable
 * Tabla administrativa de datos con buscador en tiempo real, botón "+ Nuevo",
 * hover en filas, badges de estado y botones de acción rápida protegidos con RBAC `<Can>`.
 */
export function DynamicAdminTable<T extends object>({
  title,
  description,
  data,
  columns,
  loading = false,
  searchable = true,
  searchPlaceholder,
  onSearch,
  onCreate,
  createButtonLabel = "Nuevo",
  createPermission,
  onEdit,
  editPermission,
  onDelete,
  deletePermission,
  primaryKey = "id",
  testId = "dynamic-admin-table",
}: DynamicAdminTableProps<T>) {
  const [localSearch, setLocalSearch] = useState<string>("");

  const resolvedSearchPlaceholder =
    searchPlaceholder ??
    translateKey("platform_admin", "table_common.search_placeholder", {
      defaultValue: "Buscar...",
    });

  const filteredData = useMemo(() => {
    if (onSearch || !localSearch.trim()) {
      return data;
    }
    const query = localSearch.toLowerCase();
    return data.filter((item) =>
      Object.values(item as Record<string, unknown>).some((val) =>
        String(val ?? "").toLowerCase().includes(query)
      )
    );
  }, [data, localSearch, onSearch]);

  const handleSearchChange = (val: string) => {
    setLocalSearch(val);
    if (onSearch) {
      onSearch(val);
    }
  };

  return (
    <div
      data-testid={testId}
      className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300"
    >
      {/* Header con Título, Descripción, Buscador y Botón "+ Nuevo" */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-foreground">
            {title}
          </h3>
          {description && (
            <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
          )}
        </div>

        <div className="flex items-center gap-3">
          {searchable && (
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                data-testid={`${testId}-search-input`}
                placeholder={resolvedSearchPlaceholder}
                value={localSearch}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-[240px] rounded-lg border border-border bg-background pl-9 pr-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          )}

          {onCreate && (() => {
            const btn = (
              <button
                type="button"
                data-testid={`${testId}-create-btn`}
                onClick={onCreate}
                className="touch-target inline-flex min-h-[40px] items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
              >
                <Plus className="h-4 w-4" />
                <span>{createButtonLabel}</span>
              </button>
            );
            return createPermission ? (
              <Can perform={createPermission}>{btn}</Can>
            ) : (
              btn
            );
          })()}
        </div>
      </div>

      {/* Contenedor de la Tabla Clásica Legacy */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="border-b border-border bg-secondary/30 text-muted-foreground font-semibold">
              <tr>
                {columns.map((col) => (
                  <th key={col.key} className="px-4 py-3 font-semibold">
                    {col.label}
                  </th>
                ))}
                {(onEdit || onDelete) && (
                  <th className="px-4 py-3 text-right font-semibold">
                    {translateKey("platform_admin", "table_common.actions", {
                      defaultValue: "Acciones",
                    })}
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={`loading-row-${idx}`} className="animate-pulse">
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3">
                        <div className="h-4 w-24 bg-secondary rounded" />
                      </td>
                    ))}
                    {(onEdit || onDelete) && (
                      <td className="px-4 py-3 text-right">
                        <div className="h-4 w-12 bg-secondary rounded ml-auto" />
                      </td>
                    )}
                  </tr>
                ))
              ) : filteredData.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length + (onEdit || onDelete ? 1 : 0)}
                    data-testid={`${testId}-empty-row`}
                    className="h-24 text-center text-xs text-muted-foreground"
                  >
                    {translateKey("platform_admin", "table_common.empty_message", {
                      defaultValue: "No hay datos disponibles.",
                    })}
                  </td>
                </tr>
              ) : (
                filteredData.map((row, rowIdx) => {
                  const rowObj = row as Record<string, unknown>;
                  const keyVal =
                    (rowObj[primaryKey as string] as string | number | undefined) ??
                    `row-${rowIdx}`;
                  return (
                    <tr
                      key={String(keyVal)}
                      data-testid={`${testId}-row-${keyVal}`}
                      className="group hover:bg-secondary/20 transition-colors"
                    >
                      {columns.map((col) => (
                        <td key={col.key} className="px-4 py-3 text-foreground">
                          {col.render ? col.render(row) : String(rowObj[col.key] ?? "—")}
                        </td>
                      ))}

                      {(onEdit || onDelete) && (
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex items-center justify-end gap-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
                            {onEdit && (() => {
                              const editBtn = (
                                <button
                                  type="button"
                                  data-testid={`${testId}-edit-btn-${keyVal}`}
                                  onClick={() => onEdit(row)}
                                  className="touch-target inline-flex min-h-[32px] min-w-[32px] items-center justify-center rounded-md border border-border bg-card p-1 text-primary hover:bg-secondary transition-colors"
                                  title={translateKey("platform_admin", "table_common.edit", {
                                    defaultValue: "Editar",
                                  })}
                                >
                                  <Edit className="h-3.5 w-3.5" />
                                </button>
                              );
                              return editPermission ? (
                                <Can perform={editPermission}>{editBtn}</Can>
                              ) : (
                                editBtn
                              );
                            })()}
                            {onDelete && (() => {
                              const delBtn = (
                                <button
                                  type="button"
                                  data-testid={`${testId}-delete-btn-${keyVal}`}
                                  onClick={() => onDelete(row)}
                                  className="touch-target inline-flex min-h-[32px] min-w-[32px] items-center justify-center rounded-md border border-destructive/30 bg-destructive/10 p-1 text-destructive hover:bg-destructive/20 transition-colors"
                                  title={translateKey("platform_admin", "table_common.delete", {
                                    defaultValue: "Eliminar",
                                  })}
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              );
                              return deletePermission ? (
                                <Can perform={deletePermission}>{delBtn}</Can>
                              ) : (
                                delBtn
                              );
                            })()}
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
