import { useEffect, useMemo, useState } from "react";
import { Database, Loader2, Search } from "lucide-react";

import FactorCategoryBadge from "@/features/factores/components/FactorCategoryBadge";
import Pagination from "@/shared/components/Pagination";
import { getFactoresEmision } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

function FactoresView() {
  const [factores, setFactores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 8;

  const categories = useMemo(
    () => Array.from(new Set(factores.map((factor) => factor.categoria).filter(Boolean))).sort(),
    [factores]
  );

  const filteredFactores = useMemo(() => {
    const query = search.trim().toLowerCase();

    return factores.filter((factor) => {
      const matchesCategory = !category || factor.categoria === category;
      const searchable = [
        factor.actividad,
        factor.actividad_key,
        factor.unidad,
        factor.anio,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return matchesCategory && (!query || searchable.includes(query));
    });
  }, [category, factores, search]);

  const totalPages = Math.max(1, Math.ceil(filteredFactores.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleFactores = filteredFactores.slice(startIndex, startIndex + rowsPerPage);

  useEffect(() => {
    let isCancelled = false;

    async function loadFactores() {
      try {
        const data = await getFactoresEmision();

        if (!isCancelled) {
          setFactores(data);
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar los factores de emision."
          );
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadFactores();

    return () => {
      isCancelled = true;
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
            <Database className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold">
              Factores de emision
            </h1>
            <p className="text-slate-400">
              Catalogo de factores cargados para calcular actividades y transporte.
            </p>
          </div>
        </div>
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200">
          {formatNumber(filteredFactores.length, 0)} factores
        </div>
      </header>

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold">Tabla de factores</h2>
          {loading && <Loader2 className="animate-spin text-emerald-300" size={20} />}
        </div>

        <div className="mb-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_220px]">
          <label className="relative block">
            <Search
              size={18}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setCurrentPage(1);
              }}
              placeholder="Buscar actividad, key, unidad o año"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 py-3 pl-11 pr-4 text-sm text-slate-100 outline-none transition focus:border-cyan-400/60"
            />
          </label>
          <select
            value={category}
            onChange={(event) => {
              setCategory(event.target.value);
              setCurrentPage(1);
            }}
            className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400/60"
          >
            <option value="">Todas las categorias</option>
            {categories.map((factorCategory) => (
              <option key={factorCategory} value={factorCategory}>
                {factorCategory}
              </option>
            ))}
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[900px] w-full table-fixed text-sm factores-table">
            <thead className="border-b border-slate-800 text-slate-400">
              <tr>

                <th className="w-[20%] px-4 py-3 text-center">Actividad</th>
                <th className="w-[14%] px-4 py-3 text-left">Categoria</th>
                <th className="w-[12%] px-4 py-3 text-right">Factor</th>
                <th className="w-[10%] px-4 py-3 text-left">Unidad</th>
                <th className="w-[6%] px-4 py-3 text-right">Año</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-400">
                    Cargando factores...
                  </td>
                </tr>
              )}

              {!loading && filteredFactores.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-400">
                    No hay factores de emision cargados.
                  </td>
                </tr>
              )}

              {visibleFactores.map((factor) => (
                <tr key={factor.id} className="border-b border-slate-800/60">
<td className="w-[34%] px-4 py-3 text-left font-semibold text-slate-100">
  <span className="block text-left">
    {factor.actividad}
  </span>
</td>
                  <td className="px-4 py-4 text-left">
                    <FactorCategoryBadge category={factor.categoria} />
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-cyan-200">
                    {formatNumber(Number(factor.factor_emision), 6)}
                  </td>
                  <td className="px-4 py-3 texttext-slate-300">{factor.unidad}</td>                  
                  <td className="px-4 py-3 text-right text-slate-300">
                    {factor.anio}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!loading && (
          <Pagination
            currentPage={safeCurrentPage}
            itemLabel="factores"
            onPageChange={setCurrentPage}
            pageSize={rowsPerPage}
            totalItems={filteredFactores.length}
          />
        )}
      </section>
    </div>
  );
}

export default FactoresView;
