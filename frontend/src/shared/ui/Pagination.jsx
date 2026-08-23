import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";

export default function Pagination({ page, currentPage, totalPages, onChange, onPageChange, totalItems = 0, pageSize = 8, itemLabel = "registros" }) {
  const current = page || currentPage || 1;
  const total = totalPages || Math.max(1, Math.ceil(totalItems / pageSize));
  const change = onChange || onPageChange;
  if (total <= 1) return null;
  const first = (current - 1) * pageSize + 1;
  const last = Math.min(current * pageSize, totalItems);
  return <nav aria-label={`Paginación de ${itemLabel}`} className="mt-4 grid gap-3 border-t border-[var(--border-subtle)] pt-4 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-center">
    {totalItems > 0 ? <p className="text-left text-xs text-[var(--text-muted)]">Mostrando {first}–{last} de {totalItems}</p> : <span />}
    <div className="flex flex-nowrap items-center justify-center gap-3">
      <Button className="whitespace-nowrap" type="button" variant="secondary" size="sm" disabled={current <= 1} onClick={() => change?.(current - 1)} aria-label="Página anterior"><ChevronLeft aria-hidden="true" size={15} />Anterior</Button>
      <span className="min-w-24 text-center text-xs font-bold text-[var(--text-secondary)]">Página {current} de {total}</span>
      <Button className="whitespace-nowrap" type="button" variant="secondary" size="sm" disabled={current >= total} onClick={() => change?.(current + 1)} aria-label="Página siguiente">Siguiente<ChevronRight aria-hidden="true" size={15} /></Button>
    </div>
    <span aria-hidden="true" className="hidden sm:block" />
  </nav>;
}
