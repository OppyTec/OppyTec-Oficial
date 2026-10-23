import { Check, X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";

export type FormFieldType =
  | "text"
  | "number"
  | "boolean"
  | "select"
  | "multiselect"
  | "password";

export interface FormSelectOption {
  readonly label: string;
  readonly value: string | number;
  readonly parentId?: string | number;
}

export interface FormFieldDef {
  readonly name: string;
  readonly label: string;
  readonly type: FormFieldType;
  readonly required?: boolean;
  readonly options?: readonly FormSelectOption[];
  readonly disabled?: boolean;
  readonly placeholder?: string;
  readonly description?: string;
}

export interface DynamicAdminFormProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly title: string;
  readonly description?: string;
  readonly fields: readonly FormFieldDef[];
  readonly initialData?: Record<string, unknown> | null;
  readonly onSubmit: (data: Record<string, unknown>) => Promise<boolean> | boolean;
  readonly onFormChange?: (data: Record<string, unknown>) => void;
  readonly submitButtonLabel?: string;
  readonly testId?: string;
}

/**
 * ADN Visual Legacy: DynamicAdminForm
 * Modal Dialog flotante para creación y edición de registros sin sobrecargar la pantalla principal.
 */
export function DynamicAdminForm({
  open,
  onOpenChange,
  title,
  description,
  fields,
  initialData,
  onSubmit,
  onFormChange,
  submitButtonLabel = "Guardar",
  testId = "dynamic-admin-form",
}: DynamicAdminFormProps) {
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (open) {
      if (initialData) {
        setFormData({ ...initialData });
      } else {
        const emptyState: Record<string, unknown> = {};
        fields.forEach((f) => {
          if (f.type === "boolean") {
            emptyState[f.name] = false;
          } else if (f.type === "multiselect") {
            emptyState[f.name] = [];
          } else if (f.type === "number") {
            emptyState[f.name] = 0;
          } else {
            emptyState[f.name] = "";
          }
        });
        setFormData(emptyState);
      }
    }
  }, [open, initialData, fields]);

  const handleChange = (name: string, value: unknown) => {
    const updated = { ...formData, [name]: value };
    setFormData(updated);
    if (onFormChange) {
      onFormChange(updated);
    }
  };

  const handleToggleMultiselect = (fieldName: string, optionValue: string | number) => {
    const raw = formData[fieldName];
    const currentList: (string | number)[] = Array.isArray(raw)
      ? [...(raw as (string | number)[])]
      : [];
    const index = currentList.indexOf(optionValue);
    if (index >= 0) {
      currentList.splice(index, 1);
    } else {
      currentList.push(optionValue);
    }
    handleChange(fieldName, currentList);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const result = await onSubmit(formData);
      if (result !== false) {
        onOpenChange(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={() => onOpenChange(false)}
      title={title}
      description={description}
    >
      <form
        onSubmit={(e) => void handleSubmit(e)}
        data-testid={testId}
        className="space-y-4 max-h-[75vh] overflow-y-auto pr-1"
      >
        <div className="space-y-3.5">
          {fields.map((field) => {
            const val = formData[field.name];

            return (
              <div key={field.name} className="space-y-1.5 text-xs">
                <label
                  htmlFor={`field-${field.name}`}
                  className="font-semibold text-foreground flex items-center justify-between"
                >
                  <span>
                    {field.label}
                    {field.required && (
                      <span className="text-destructive ml-1">*</span>
                    )}
                  </span>
                  {field.description && (
                    <span className="text-[10px] text-muted-foreground font-normal">
                      {field.description}
                    </span>
                  )}
                </label>

                {field.type === "boolean" ? (
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      type="button"
                      id={`field-${field.name}`}
                      data-testid={`field-toggle-${field.name}`}
                      disabled={field.disabled}
                      onClick={() => handleChange(field.name, !val)}
                      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        val ? "bg-primary" : "bg-secondary"
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                          val ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                    <span className="text-xs text-muted-foreground">
                      {val ? "Activo" : "Inactivo"}
                    </span>
                  </div>
                ) : field.type === "select" ? (
                  <select
                    id={`field-${field.name}`}
                    data-testid={`field-select-${field.name}`}
                    value={val !== undefined && val !== null ? String(val) : ""}
                    disabled={field.disabled}
                    onChange={(e) => handleChange(field.name, e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="">Seleccione una opción...</option>
                    {(field.options ?? []).map((opt) => (
                      <option key={String(opt.value)} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === "multiselect" ? (
                  <div
                    data-testid={`field-multiselect-${field.name}`}
                    className="max-h-48 overflow-y-auto rounded-lg border border-border bg-background/50 p-2 space-y-1"
                  >
                    {(field.options ?? []).map((opt) => {
                      const isSelected =
                        Array.isArray(val) &&
                        (val as (string | number)[]).includes(opt.value);
                      return (
                        <div
                          key={String(opt.value)}
                          onClick={() => handleToggleMultiselect(field.name, opt.value)}
                          className={`flex items-center justify-between p-1.5 rounded-md text-xs cursor-pointer select-none transition-colors ${
                            isSelected
                              ? "bg-primary/15 text-primary font-medium"
                              : "hover:bg-secondary text-muted-foreground"
                          }`}
                        >
                          <span>{opt.label}</span>
                          {isSelected && <Check className="h-3.5 w-3.5 text-primary" />}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <input
                    id={`field-${field.name}`}
                    data-testid={`field-input-${field.name}`}
                    type={field.type}
                    value={val !== undefined && val !== null ? String(val) : ""}
                    disabled={field.disabled}
                    placeholder={field.placeholder}
                    onChange={(e) =>
                      handleChange(
                        field.name,
                        field.type === "number" ? Number(e.target.value) : e.target.value
                      )
                    }
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Footer del Modal */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <button
            type="button"
            data-testid={`${testId}-cancel-btn`}
            onClick={() => onOpenChange(false)}
            className="touch-target inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-secondary transition-colors"
          >
            <X className="h-3.5 w-3.5" />
            <span>Cancelar</span>
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            data-testid={`${testId}-submit-btn`}
            className="touch-target inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
          >
            <Check className="h-3.5 w-3.5" />
            <span>{submitButtonLabel}</span>
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
