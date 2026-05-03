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
    <div className="mt-5 rounded-2xl border border-emerald-400/10 bg-gradient-to-r from-emerald-400/10 via-slate-950 to-cyan-400/10 p-3 sm:p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-400">
          Mostrando{" "}
          <span className="font-semibold text-slate-100">{visibleCount}</span>{" "}
          de <span className="font-semibold text-slate-100">{totalItems}</span>{" "}
          {itemLabel}
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onPageChange(Math.max(safeCurrentPage - 1, 1))}
            disabled={safeCurrentPage === 1}
            className="inline-flex items-center justify-center rounded-full border border-slate-700/80 bg-slate-950 px-4 py-2 text-xs font-semibold text-slate-200 shadow-sm transition hover:border-emerald-400/40 hover:text-emerald-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Anterior
          </button>

          <div className="flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-950/80 p-1 shadow-sm">
            {pageNumbers.map((page) => {
              const active = page === safeCurrentPage;

              return (
                <button
                  key={page}
                  type="button"
                  onClick={() => onPageChange(page)}
                  className={`min-w-9 rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                    active
                      ? "bg-emerald-400/20 text-emerald-200 shadow-inner ring-1 ring-emerald-400/30"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
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
            className="inline-flex items-center justify-center rounded-full border border-slate-700/80 bg-slate-950 px-4 py-2 text-xs font-semibold text-slate-200 shadow-sm transition hover:border-cyan-400/40 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      </div>

      <p className="mt-3 text-[11px] uppercase tracking-[0.2em] text-slate-500">
        Pagina {safeCurrentPage} de {totalPages}
      </p>
    </div>
  );
}

export default Pagination;
