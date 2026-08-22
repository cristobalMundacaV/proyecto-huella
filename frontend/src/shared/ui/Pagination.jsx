import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";

export default function Pagination({ page, currentPage, totalPages, onChange, onPageChange, totalItems = 0, pageSize = 8, itemLabel = "registros" }) {
  const current = page || currentPage || 1;
  const total = totalPages || Math.max(1, Math.ceil(totalItems / pageSize));
  const change = onChange || onPageChange;
  if (total <= 1) return null;
  const first = (current - 1) * pageSize + 1;
  const last = Math.min(current * pageSize, totalItems);
  return <nav aria-label={`Paginación de ${itemLabel}`} className="mt-4 flex flex-col gap-3 border-t border-[var(--border-subtle)] pt-4 sm:flex-row sm:items-center sm:justify-between">
    {totalItems > 0 ? <p className="text-xs text-[var(--text-muted)]">Mostrando {first}–{last} de {totalItems}</p> : <span />}
    <div className="flex items-center justify-between gap-3 sm:justify-end">
      <Button type="button" variant="secondary" size="sm" disabled={current <= 1} onClick={() => change?.(current - 1)} aria-label="Página anterior"><ChevronLeft aria-hidden="true" size={15} />Anterior</Button>
      <span className="min-w-24 text-center text-xs font-bold text-[var(--text-secondary)]">Página {current} de {total}</span>
      <Button type="button" variant="secondary" size="sm" disabled={current >= total} onClick={() => change?.(current + 1)} aria-label="Página siguiente">Siguiente<ChevronRight aria-hidden="true" size={15} /></Button>
    </div>
  </nav>;
}
