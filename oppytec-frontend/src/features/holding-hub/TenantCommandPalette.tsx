import { useEffect, useRef, useState } from "react";
import { Building2, Check, Search, X } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { HoldingTenantCard } from "./types";

export interface TenantCommandPaletteProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly tenants: readonly HoldingTenantCard[];
  readonly onSelectTenant: (tenant: HoldingTenantCard) => void;
}

export function TenantCommandPalette({
  isOpen,
  onClose,
  tenants,
  onSelectTenant,
}: TenantCommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filtered = tenants.filter(
    (t) =>
      t.name.toLowerCase().includes(query.toLowerCase()) ||
      t.schema_name.toLowerCase().includes(query.toLowerCase()) ||
      (t.business_type && t.business_type.toLowerCase().includes(query.toLowerCase()))
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (filtered.length > 0 ? (prev + 1) % filtered.length : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          filtered.length > 0 ? (prev - 1 + filtered.length) % filtered.length : 0
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          onSelectTenant(filtered[selectedIndex]);
          onClose();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose, onSelectTenant]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={translateKey("holding_hub", "command_palette.title")}
      data-testid="tenant-command-palette-modal"
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl border border-border bg-card/95 shadow-2xl backdrop-blur-xl overflow-hidden transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Bar */}
        <div className="flex items-center gap-3 border-b border-border/80 px-4 py-3.5">
          <Search className="h-5 w-5 text-primary shrink-0" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls="tenant-command-list"
            data-testid="tenant-command-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder={translateKey("holding_hub", "command_palette.placeholder")}
            className="flex-1 bg-transparent text-sm md:text-base font-medium text-foreground placeholder:text-muted-foreground outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="text-muted-foreground hover:text-foreground p-1 rounded-md"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <span className="hidden sm:inline-flex items-center rounded border border-border bg-muted/60 px-2 py-0.5 text-[11px] font-mono text-muted-foreground">
            ESC
          </span>
        </div>

        {/* Results List */}
        <div id="tenant-command-list" role="listbox" className="max-h-[380px] overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              {translateKey("holding_hub", "command_palette.empty", { query })}
            </div>
          ) : (
            filtered.map((tenant, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={tenant.id}
                  role="option"
                  aria-selected={isSelected}
                  data-testid={`tenant-command-option-${tenant.id}`}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  onClick={() => {
                    onSelectTenant(tenant);
                    onClose();
                  }}
                  className={`flex items-center justify-between gap-3 px-3.5 py-3 rounded-xl cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-primary/15 text-foreground border border-primary/30"
                      : "text-foreground/90 hover:bg-muted/50 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                        isSelected
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <Building2 className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm truncate">{tenant.name}</span>
                        <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-500">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          {translateKey("holding_hub", "central.status_active")}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5 font-mono">
                        <span>{tenant.schema_name}</span>
                        {tenant.business_type && (
                          <>
                            <span>•</span>
                            <span className="font-sans">{tenant.business_type}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {isSelected && (
                      <span className="flex items-center gap-1 text-xs font-medium text-primary">
                        <Check className="h-3.5 w-3.5" />
                        <span className="hidden sm:inline font-mono text-[11px]">↵</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer Hint */}
        <div className="flex items-center justify-between border-t border-border/60 bg-muted/30 px-4 py-2.5 text-[12px] text-muted-foreground">
          <span>{translateKey("holding_hub", "command_palette.navigate_hint")}</span>
          <span className="font-mono text-[11px]">
            {translateKey("holding_hub", "command_palette.count_locations", {
              count: filtered.length,
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
