import { useMemo } from "react";

function Pagination({
  currentPage,
  onPageChange,
  pageSize,
  totalItems,
  itemLabel = "registros",
}) {
  const totalPages = Math.max(1, Math.ceil((totalItems || 0) / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleCount =
    totalItems === 0
      ? 0
      : Math.min(pageSize, totalItems - (safeCurrentPage - 1) * pageSize);

  const pageNumbers = useMemo(() => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, index) => index + 1);
    }

    const pages = new Set([
      1,
      totalPages,
      safeCurrentPage - 1,
      safeCurrentPage,
      safeCurrentPage + 1,
    ]);

    return Array.from(pages)
      .filter((page) => page >= 1 && page <= totalPages)
      .sort((left, right) => left - right);
  }, [safeCurrentPage, totalPages]);

  if (totalItems <= pageSize) {
    return null;
  }

  return (
    <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--info-bg)] p-3 sm:p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs font-medium text-[var(--text-muted)]">
          Mostrando{" "}
          <span className="font-bold text-[var(--text-main)]">{visibleCount}</span>{" "}
          de <span className="font-bold text-[var(--text-main)]">{totalItems}</span>{" "}
          {itemLabel}
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onPageChange(Math.max(safeCurrentPage - 1, 1))}
            disabled={safeCurrentPage === 1}
            className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-xs font-semibold text-[var(--text-muted)] shadow-sm transition hover:border-[var(--primary)]/40 hover:text-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Anterior
          </button>

          <div className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-card)] p-1 shadow-sm">
            {pageNumbers.map((page) => {
              const active = page === safeCurrentPage;

              return (
                <button
                  key={page}
                  type="button"
                  onClick={() => onPageChange(page)}
                  className={`min-w-9 rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                    active
                      ? "bg-[var(--primary-dark)] text-white shadow-inner ring-1 ring-[var(--primary)]/30"
                      : "text-[var(--text-muted)] hover:bg-[var(--success-bg)] hover:text-[var(--primary-dark)]"
                  }`}
                >
                  {page}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => onPageChange(Math.min(safeCurrentPage + 1, totalPages))}
            disabled={safeCurrentPage === totalPages}
            className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-xs font-semibold text-[var(--text-main)] shadow-sm transition hover:border-[var(--primary)]/40 hover:text-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      </div>

      <p className="mt-3 text-[11px] uppercase tracking-[0.2em] text-[var(--text-muted)]">
        Pagina {safeCurrentPage} de {totalPages}
      </p>
    </div>
  );
}

export default Pagination;
