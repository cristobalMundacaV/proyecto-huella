import { useMemo, useState } from "react";

export function usePagination(items = [], pageSize = 8) {
  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const pageItems = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * pageSize;
    return items.slice(startIndex, startIndex + pageSize);
  }, [items, pageSize, safeCurrentPage]);

  return {
    currentPage: safeCurrentPage,
    onPageChange: setCurrentPage,
    pageItems,
    pageSize,
    totalItems: items.length,
    totalPages,
  };
}
