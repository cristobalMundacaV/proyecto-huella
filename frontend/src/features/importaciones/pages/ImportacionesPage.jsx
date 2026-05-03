import { useMemo, useState, useRef } from "react";
import {
  AlertTriangle,
  Boxes,
  Building2,
  CheckCircle2,
  DatabaseZap,
  Factory,
  FileSpreadsheet,
  Loader2,
  Save,
  Upload,
} from "lucide-react";

import Toast from "@/shared/components/Toast";
import {
  confirmActivityImport,
  confirmarImportFactores,
  previewEmpresaCompleta,
  confirmarEmpresaCompleta,
  previewImportEmpresas,
  confirmarImportEmpresas,
  previewActivityImport,
  previewImportFactores,
  confirmarImportLotesForEmpresa,
  confirmarImportUnidadesForEmpresa,
  confirmActivityImportForEmpresa,
  previewImportLotesForEmpresa,
  previewImportUnidadesForEmpresa,
  previewActivityImportForEmpresa,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import EmptyState from "@/shared/components/EmptyState";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";

const emptyImportState = {
  fileName: "",
  loading: false,
  saving: false,
  error: "",
  result: null,
  savedMessage: "",
};

const factorSummaryLabels = [
  ["total_filas", "Total filas"],
  ["validas", "Validas"],
  ["con_error", "Con error"],
  ["duplicadas", "Duplicadas"],
  ["posibles_creaciones", "Posibles creaciones"],
  ["posibles_actualizaciones", "Posibles actualizaciones"],
];

const companySummaryLabels = [
  ["total_filas", "Total filas"],
  ["validas", "Validas"],
  ["con_error", "Con error"],
  ["duplicadas", "Duplicadas"],
  ["posibles_creaciones", "Empresas nuevas"],
  ["posibles_actualizaciones", "Actualizaciones"],
];

const activitySummaryLabels = [
  ["filas_validas", "Filas validas"],
  ["filas_con_error", "Filas con error"],
  ["factores_encontrados", "Factores encontrados"],
  ["factores_faltantes", "Factores faltantes"],
  ["lotes_encontrados", "Lotes encontrados"],
  ["lotes_nuevos_detectados", "Lotes nuevos"],
];

const loteSummaryLabels = [
  ["validas", "Filas validas"],
  ["con_error", "Filas con error"],
  ["lotes_nuevos", "Lotes nuevos"],
  ["lotes_existentes", "Lotes existentes"],
  ["duplicadas", "Duplicados"],
];

const unitSummaryLabels = [
  ["validas", "Filas validas"],
  ["con_error", "Filas con error"],
  ["nuevas", "Unidades nuevas"],
  ["existentes", "Unidades existentes"],
  ["duplicadas", "Duplicados"],
];

function SummaryGrid({ summary, labels }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
      {labels.map(([key, label]) => (
        <div key={key} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
          <p className="text-xs text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-100">
            {formatNumber(summary?.[key] || 0, 0)}
          </p>
        </div>
      ))}
    </div>
  );
}

function PreviewTable({ rows, type }) {
  const [currentPage, setCurrentPage] = useState(1);
  const isFactors = type === "factors";
  const rowsPerPage = 8;
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleRows = rows.slice(startIndex, startIndex + rowsPerPage);

  return (
    <div className="overflow-x-auto">
      <table className="mt-4 w-full text-sm">
        <thead className="border-b border-slate-800 text-slate-400">
          <tr>
            <th className="px-2 py-4 text-center min-w-12 font-semibold">Fila</th>
            <th className="px-3 py-4 text-center min-w-24 font-semibold">Estado</th>
            {isFactors ? <th className="px-3 py-4 text-center min-w-32 font-semibold">Categoria</th> : null}
            <th className="px-3 py-4 text-left min-w-40 font-semibold">Actividad</th>
            {isFactors ? <th className="px-3 py-4 text-center min-w-40 font-semibold">Activity key</th> : null}
            <th className="px-3 py-4 text-center min-w-20 font-semibold">Unidad</th>
            {isFactors ? <th className="px-3 py-4 text-center min-w-14 font-semibold">Año</th> : <th className="px-3 py-4 text-center min-w-32 font-semibold">Asignacion</th>}
            <th className="px-3 py-4 text-center min-w-24 font-semibold">Factor</th>
            <th className="px-3 py-4 text-center min-w-64 font-semibold">Observaciones</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => (
            <tr key={row.row_number} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition">
              <td className="px-2 py-4 text-center text-slate-300 whitespace-nowrap">{row.row_number}</td>
              <td className="px-3 py-4 text-center">
                <span
                  className={`inline-flex items-center gap-2 rounded-2xl border px-3 py-1 text-xs font-bold whitespace-nowrap ${
                    row.status === "valid"
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                      : "border-red-400/30 bg-red-400/10 text-red-200"
                  }`}
                >
                  {row.status === "valid" ? (
                    <CheckCircle2 size={14} />
                  ) : (
                    <AlertTriangle size={14} />
                  )}
                  {row.status === "valid" ? "Válida" : "Error"}
                </span>
              </td>
              {isFactors ? (
                <td className="px-3 py-4 text-center">
                  <span
                    className={`inline-flex rounded-2xl border px-3 py-1 text-xs font-bold ${
                      row.data.categoria === "Otros"
                        ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
                        : "border-cyan-400/30 bg-cyan-400/10 text-cyan-200"
                    }`}
                  >
                    {row.data.categoria || "-"}
                  </span>
                </td>
              ) : null}
              <td className="px-3 py-4 text-left font-semibold text-slate-100 truncate">
                {row.data.actividad || "-"}
              </td>
              {isFactors ? (
                <td className="px-3 py-4 text-center font-mono text-xs text-slate-400 whitespace-nowrap">
                  {row.data.actividad_key || "-"}
                </td>
              ) : null}
              <td className="px-3 py-4 text-center text-slate-300 whitespace-nowrap">{row.data.unidad || "-"}</td>
              {isFactors ? <td className="px-3 py-4 text-center text-slate-300 whitespace-nowrap">{row.data.anio || "-"}</td> : <td className="px-3 py-4 text-center text-slate-300 whitespace-nowrap">{row.data.id_lote || row.data.unidad_id || row.data.empresa_id || "-"}</td>}
              <td className="px-3 py-4 text-center font-semibold text-emerald-300 whitespace-nowrap">{row.data.factor_emision || "-"}</td>
              <td className="px-3 py-4 text-center text-slate-300 text-sm">
                {row.errors?.length ? (
                  <span className="text-red-300">{row.errors.join("; ")}</span>
                ) : row.warnings?.length || row.data.observaciones?.length ? (
                  <span className="text-amber-200">
                    {(row.warnings?.length ? row.warnings : row.data.observaciones).join("; ")}
                  </span>
                ) : (
                  <span className="text-emerald-300">Listo para guardar</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > rowsPerPage && (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            Mostrando {startIndex + 1}-{Math.min(startIndex + rowsPerPage, rows.length)} de {rows.length} filas.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={safeCurrentPage === 1}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="min-w-20 text-center text-xs text-slate-400">
              {safeCurrentPage} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={safeCurrentPage === totalPages}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function LotePreviewTable({ rows }) {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 8;
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleRows = rows.slice(startIndex, startIndex + rowsPerPage);

  return (
    <div className="overflow-x-auto">
      <table className="mt-4 w-full text-sm">
        <thead className="border-b border-slate-800 text-slate-400">
          <tr>
            <th className="px-2 py-4 text-left min-w-12 font-semibold">Fila</th>
            <th className="px-3 py-4 text-left min-w-24 font-semibold">Estado</th>
            <th className="px-3 py-4 text-left min-w-28 font-semibold">ID lote</th>
            <th className="px-3 py-4 text-left min-w-40 font-semibold">Empresa</th>
            <th className="px-3 py-4 text-left min-w-28 font-semibold">Fecha</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Especie</th>
            <th className="px-3 py-4 text-right min-w-24 font-semibold">Volumen</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Origen</th>
            <th className="px-3 py-4 text-left min-w-64 font-semibold">Observaciones</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => (
            <tr key={row.row_number} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition">
              <td className="px-2 py-4 text-slate-300">{row.row_number}</td>
              <td className="px-3 py-4">
                <span
                  className={`inline-flex items-center gap-2 rounded-2xl border px-3 py-1 text-xs font-bold whitespace-nowrap ${
                    row.status === "valid"
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                      : "border-red-400/30 bg-red-400/10 text-red-200"
                  }`}
                >
                  {row.status === "valid" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                  {row.status === "valid" ? "Valida" : "Error"}
                </span>
              </td>
              <td className="px-3 py-4 font-semibold text-slate-100">{row.data.id_lote || "-"}</td>
              <td className="px-3 py-4 text-slate-300 truncate">{row.data.empresa || row.data.empresa_aserradero || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.fecha || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.especie || "-"}</td>
              <td className="px-3 py-4 text-right text-emerald-300 font-semibold">{row.data.volumen_m3 || "-"}</td>
              <td className="px-3 py-4 text-slate-300 truncate">{row.data.origen || "-"}</td>
              <td className="px-3 py-4 text-slate-300 text-sm">
                {row.errors?.length ? (
                  <span className="text-red-300">{row.errors.join("; ")}</span>
                ) : row.warnings?.length ? (
                  <span className="text-amber-300">{row.warnings.join("; ")}</span>
                ) : row.db_action === "actualizar" ? (
                  <span className="text-cyan-300">Posible actualizacion</span>
                ) : (
                  <span className="text-emerald-300">Listo para crear</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > rowsPerPage && (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            Mostrando {startIndex + 1}-{Math.min(startIndex + rowsPerPage, rows.length)} de {rows.length} filas.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={safeCurrentPage === 1}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="min-w-20 text-center text-xs text-slate-400">
              {safeCurrentPage} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={safeCurrentPage === totalPages}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function EmpresaPreviewTable({ rows }) {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 8;
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleRows = rows.slice(startIndex, startIndex + rowsPerPage);

  return (
    <div className="overflow-x-auto">
      <table className="mt-4 w-full text-sm">
        <thead className="border-b border-slate-800 text-slate-400">
          <tr>
            <th className="px-2 py-4 text-left min-w-12 font-semibold">Fila</th>
            <th className="px-3 py-4 text-left min-w-24 font-semibold">Estado</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Empresa ID</th>
            <th className="px-3 py-4 text-left min-w-48 font-semibold">Nombre</th>
            <th className="px-3 py-4 text-left min-w-28 font-semibold">RUT</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Region</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Rubro</th>
            <th className="px-3 py-4 text-left min-w-64 font-semibold">Observaciones</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => (
            <tr key={row.row_number} className="border-b border-slate-800/60 transition hover:bg-slate-800/30">
              <td className="px-2 py-4 text-slate-300">{row.row_number}</td>
              <td className="px-3 py-4">
                <span
                  className={`inline-flex items-center gap-2 rounded-2xl border px-3 py-1 text-xs font-bold whitespace-nowrap ${
                    row.status === "valid"
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                      : "border-red-400/30 bg-red-400/10 text-red-200"
                  }`}
                >
                  {row.status === "valid" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                  {row.status === "valid" ? "Valida" : "Error"}
                </span>
              </td>
              <td className="px-3 py-4 font-mono text-xs text-cyan-200">{row.data.empresa_id || "-"}</td>
              <td className="px-3 py-4 font-semibold text-slate-100">{row.data.nombre || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.rut || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.region || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.rubro || "-"}</td>
              <td className="px-3 py-4 text-sm text-slate-300">
                {row.errors?.length ? (
                  <span className="text-red-300">{row.errors.join("; ")}</span>
                ) : row.db_action === "actualizar" ? (
                  <span className="text-cyan-300">Posible actualizacion</span>
                ) : (
                  <span className="text-emerald-300">Listo para crear</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > rowsPerPage && (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            Mostrando {startIndex + 1}-{Math.min(startIndex + rowsPerPage, rows.length)} de {rows.length} filas.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={safeCurrentPage === 1}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="min-w-20 text-center text-xs text-slate-400">
              {safeCurrentPage} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={safeCurrentPage === totalPages}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function UnitPreviewTable({ rows }) {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 8;
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleRows = rows.slice(startIndex, startIndex + rowsPerPage);

  return (
    <div className="overflow-x-auto">
      <table className="mt-4 w-full text-sm">
        <thead className="border-b border-slate-800 text-slate-400">
          <tr>
            <th className="px-2 py-4 text-left min-w-12 font-semibold">Fila</th>
            <th className="px-3 py-4 text-left min-w-24 font-semibold">Estado</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Unidad ID</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Empresa ID</th>
            <th className="px-3 py-4 text-left min-w-40 font-semibold">Nombre</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Tipo</th>
            <th className="px-3 py-4 text-left min-w-24 font-semibold">Activa</th>
            <th className="px-3 py-4 text-left min-w-64 font-semibold">Observaciones</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => (
            <tr key={row.row_number} className="border-b border-slate-800/60 transition hover:bg-slate-800/30">
              <td className="px-2 py-4 text-slate-300">{row.row_number}</td>
              <td className="px-3 py-4">
                <span
                  className={`inline-flex items-center gap-2 rounded-2xl border px-3 py-1 text-xs font-bold whitespace-nowrap ${
                    row.status === "valid"
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                      : "border-red-400/30 bg-red-400/10 text-red-200"
                  }`}
                >
                  {row.status === "valid" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                  {row.status === "valid" ? "Valida" : "Error"}
                </span>
              </td>
              <td className="px-3 py-4 font-mono text-xs text-cyan-200">{row.data.unidad_id || "-"}</td>
              <td className="px-3 py-4 font-mono text-xs text-slate-300">{row.data.empresa_id || "-"}</td>
              <td className="px-3 py-4 font-semibold text-slate-100">{row.data.nombre || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.tipo || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.activa ? "Si" : "No"}</td>
              <td className="px-3 py-4 text-sm text-slate-300">
                {row.errors?.length ? (
                  <span className="text-red-300">{row.errors.join("; ")}</span>
                ) : row.warnings?.length ? (
                  <span className="text-amber-300">{row.warnings.join("; ")}</span>
                ) : row.db_action === "actualizar" ? (
                  <span className="text-cyan-300">Posible actualizacion</span>
                ) : (
                  <span className="text-emerald-300">Listo para crear</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > rowsPerPage && (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            Mostrando {startIndex + 1}-{Math.min(startIndex + rowsPerPage, rows.length)} de {rows.length} filas.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={safeCurrentPage === 1}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="min-w-20 text-center text-xs text-slate-400">
              {safeCurrentPage} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={safeCurrentPage === totalPages}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ImportPanel({
  title,
  icon,
  columns,
  state,
  type,
  summaryLabels,
  onPreview,
  onConfirm,
}) {
  const validRows = useMemo(
    () => state.result?.rows?.filter((row) => row.status === "valid") || [],
    [state.result]
  );

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-300">
            {icon}
          </div>
          <div>
            <h2 className="text-xl font-semibold">{title}</h2>
            <p className="text-sm text-slate-400">{columns.join(", ")}</p>
          </div>
        </div>

        <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-200 transition hover:bg-slate-800 lg:w-fit">
          {state.loading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
          {state.loading ? "Previsualizando" : "Cargar archivo"}
          <input
            type="file"
            accept=".csv,.xlsx"
            disabled={state.loading || state.saving}
            onChange={onPreview}
            className="hidden"
          />
        </label>
      </div>

      {state.fileName && (
        <p className="mb-4 text-sm text-slate-400">
          Archivo: <span className="font-semibold text-slate-200">{state.fileName}</span>
        </p>
      )}

      {state.result?.batch_id && (
        <p className="mb-4 text-xs text-slate-500">
          Batch ID: <span className="font-mono text-slate-300">{state.result.batch_id}</span>
        </p>
      )}

      {state.error && <p className="mb-4 text-sm text-red-300">{state.error}</p>}
      {state.savedMessage && (
        <p className="mb-4 text-sm text-emerald-300">{state.savedMessage}</p>
      )}

      {state.result && (
        <>
          <SummaryGrid summary={state.result.summary} labels={summaryLabels} />
          {type === "lotes" ? (
            <LotePreviewTable rows={state.result.rows} />
          ) : type === "empresas" ? (
            <EmpresaPreviewTable rows={state.result.rows} />
          ) : type === "unidades" ? (
            <UnitPreviewTable rows={state.result.rows} />
          ) : (
            <PreviewTable rows={state.result.rows} type={type} />
          )}
          <button
            type="button"
            onClick={() => onConfirm(validRows, state.result?.batch_id)}
            disabled={!validRows.length || state.saving}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60 sm:w-fit"
          >
            {state.saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            Confirmar importacion
          </button>
        </>
      )}
    </section>
  );
}

function EmpresaCompletaImportPanel({ state, onPreview, onConfirm }) {
  const blockingErrors = state.result?.blocking_errors || [];
  const empresaData = state.result?.empresa?.data || {};
  const summaryCards = [
    { label: "Empresa", value: state.result?.empresa?.status === "valid" ? "Lista" : "Revisar" },
    { label: "Unidades", value: formatNumber(state.result?.unidades?.total || 0, 0) },
    { label: "Lotes", value: formatNumber(state.result?.lotes?.total || 0, 0) },
    { label: "Actividades", value: formatNumber(state.result?.actividades?.total || 0, 0) },
    { label: "Factores", value: formatNumber(state.result?.factores?.total || 0, 0) },
  ];

  const companyFields = [
    ["nombre", "Nombre"],
    ["rut", "RUT"],
    ["region", "Región"],
    ["comuna", "Comuna"],
    ["direccion", "Dirección"],
    ["rubro", "Rubro"],
    ["email", "Email"],
    ["telefono", "Teléfono"],
    ["contacto", "Contacto"],
    ["observaciones", "Observaciones"],
  ];

  return (
    <section className="rounded-3xl border border-cyan-400/20 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
            <Building2 size={18} />
          </div>
          <div>
            <h2 className="text-xl font-semibold">Importador de empresa completa</h2>
            <p className="text-sm text-slate-400">
              Archivo XLSX con hojas <span className="font-semibold text-slate-200">empresa</span>, <span className="font-semibold text-slate-200">unidades</span>, <span className="font-semibold text-slate-200">lotes</span>, <span className="font-semibold text-slate-200">actividades</span> y <span className="font-semibold text-slate-200">factores</span>.
            </p>
          </div>
        </div>

        <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-100 transition hover:bg-cyan-400/20 lg:w-fit">
          {state.loading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
          {state.loading ? "Previsualizando" : "Cargar archivo"}
          <input
            type="file"
            accept=".xlsx"
            disabled={state.loading || state.saving}
            onChange={onPreview}
            className="hidden"
          />
        </label>
      </div>


      {state.fileName && (
        <p className="mb-4 mt-4 text-sm text-slate-400">
          Archivo: <span className="font-semibold text-slate-200">{state.fileName}</span>
        </p>
      )}

      {state.result?.batch_id && (
        <p className="mb-4 text-xs text-slate-500">
          Batch ID: <span className="font-mono text-slate-300">{state.result.batch_id}</span>
        </p>
      )}

      {state.error && <p className="mb-4 text-sm text-red-300">{state.error}</p>}
      {state.savedMessage && <p className="mb-4 text-sm text-emerald-300">{state.savedMessage}</p>}

      {state.result && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            {summaryCards.map((card) => (
              <div key={card.label} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs text-slate-500">{card.label}</p>
                <p className="mt-1 text-2xl font-bold text-slate-100">{card.value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <h3 className="text-base font-semibold text-slate-100">Datos de la empresa</h3>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {companyFields.map(([key, label]) => (
                <div key={key} className="rounded-2xl border border-slate-800/80 bg-slate-900/80 p-3">
                  <p className="text-xs text-slate-500">{label}</p>
                  <p className="mt-1 break-words text-sm font-semibold text-slate-100">
                    {empresaData[key] || "-"}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {blockingErrors.length > 0 && (
            <div className="rounded-2xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">
              <p className="font-semibold">Errores bloqueantes</p>
              <p className="mt-2 leading-6">{blockingErrors.join("; ")}</p>
            </div>
          )}

          <button
            type="button"
            onClick={() => onConfirm(state.result?.batch_id)}
            disabled={!state.result?.batch_id || blockingErrors.length > 0 || state.saving}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-100 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {state.saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            Confirmar importación completa
          </button>
        </div>
      )}
    </section>
  );
}

function ImportacionesView({ onImportConfirmed }) {
  const [factors, setFactors] = useState(emptyImportState);
  const [units, setUnits] = useState(emptyImportState);
  const [lotes, setLotes] = useState(emptyImportState);
  const [empresas, setEmpresas] = useState(emptyImportState);
  const [empresaCompleta, setEmpresaCompleta] = useState(emptyImportState);
  const [activities, setActivities] = useState(emptyImportState);
  const [toast, setToast] = useState(null);
  const { activeEmpresa, activeEmpresaId } = useEmpresaActiva();
  const empresaCompletaInputRef = useRef(null);

  const previewFile = async (event, previewFn, setState) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setState({
      ...emptyImportState,
      fileName: file.name,
      loading: true,
    });

    try {
      const result = await previewFn(file);
      setState((current) => ({ ...current, loading: false, result }));
    } catch (requestError) {
      const resp = requestError.response?.data || {};

      // If the backend returned a partial preview (rows + summary), show it but also surface the error message
      if (resp.result || resp.rows) {
        setState((current) => ({
          ...current,
          loading: false,
          result: resp.result || { rows: resp.rows, summary: resp.summary },
          error: resp.error || resp.detail || "El archivo contiene advertencias o errores.",
        }));
      } else {
        setState((current) => ({
          ...current,
          loading: false,
          error: resp.error || resp.detail || "No se pudo previsualizar el archivo.",
        }));
      }
    } finally {
      event.target.value = "";
    }
  };

  const showToast = (message) => {
    setToast({ id: Date.now(), message });
  };

  const handleImportEmpresaCompleta = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setEmpresaCompleta({ ...emptyImportState, fileName: file.name, loading: true });

    try {
      const preview = await previewEmpresaCompleta(file);

      setEmpresaCompleta((current) => ({
        ...current,
        loading: false,
        result: preview,
      }));

      const hasBlockingErrors = (preview.blocking_errors || []).length > 0;

      if (hasBlockingErrors) {
        setEmpresaCompleta((current) => ({
          ...current,
          loading: false,
          error: preview.error || "El archivo tiene errores bloqueantes; revisa la previsualización antes de confirmar.",
        }));
        return;
      }

      const result = await confirmarEmpresaCompleta({ batch_id: preview.batch_id });

      const created = result.creados ?? result.created ?? 0;
      const msg = `${formatNumber(created, 0)} creadas.`;
      showToast(msg);

      setEmpresaCompleta((current) => ({
        ...current,
        loading: false,
        saving: false,
        savedMessage: msg,
      }));
    } catch (err) {
      const resp = err.response?.data || {};
      setEmpresaCompleta((current) => ({
        ...current,
        loading: false,
        saving: false,
        error: resp.error || resp.detail || "Error durante la importación completa.",
      }));
    } finally {
      if (event?.target) event.target.value = "";
    }
  };

  const confirmEmpresaCompleta = async (batchId) => {
    if (!batchId) {
      setEmpresaCompleta((current) => ({
        ...current,
        error: "Falta batch_id para confirmar la importación.",
      }));
      return;
    }

    setEmpresaCompleta((current) => ({ ...current, saving: true, error: "", savedMessage: "" }));

    try {
      const result = await confirmarEmpresaCompleta({ batch_id: batchId });
      const created = result.creados ?? result.created ?? 0;
      const msg = `Importación completa: ${formatNumber(created, 0)} creadas.`;

      showToast(msg);
      await onImportConfirmed?.();

      setEmpresaCompleta((current) => ({
        ...current,
        saving: false,
        savedMessage: msg,
      }));
    } catch (err) {
      const resp = err.response?.data || {};
      setEmpresaCompleta((current) => ({
        ...current,
        saving: false,
        error: resp.error || resp.detail || "Error al confirmar la importación completa.",
      }));
    }
  };

  const confirmRows = async (rows, confirmFn, setState, batchId = null) => {
    setState((current) => ({ ...current, saving: true, error: "", savedMessage: "" }));

    try {
      const payload = batchId ? { batch_id: batchId } : { rows };
      const result = await confirmFn(payload);
      
      const createdCount = result.creados ?? result.created ?? 0;
      const toastMessage = `${formatNumber(createdCount, 0)} creados, ${formatNumber(
        result.actualizados || 0,
        0
      )} actualizados, ${formatNumber(result.rechazados || 0, 0)} rechazados.`;
      
      showToast(toastMessage);
      await onImportConfirmed?.();
      
      setState((current) => ({
        ...current,
        saving: false,
        savedMessage: toastMessage,
      }));
    } catch (requestError) {
      setState((current) => ({
        ...current,
        saving: false,
        error: requestError.response?.data?.error || "No se pudo guardar.",
      }));
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      {!activeEmpresa ? (
        <EmptyState
          title="Selecciona o crea una empresa para comenzar"
          description="Las importaciones ahora operan dentro del contexto de una empresa activa."
        />
      ) : (
        <>
      <Toast
        message={toast?.message}
        onClose={() => setToast(null)}
        toastKey={toast?.id}
      />

      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
            <DatabaseZap className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">Importaciones</h1>
            <p className="text-slate-400">Importaciones de {activeEmpresa.nombre}.</p>
          </div>
        </div>
      </header>
      <section className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-sm text-cyan-100 sm:p-5">
        Es importante que realizes las importaciones en el orden correcto: primero empresas, factores, unidades operativas, lotes y finalmente actividades.
      </section>
      <EmpresaCompletaImportPanel
        state={empresaCompleta}
        onPreview={(event) => previewFile(event, previewEmpresaCompleta, setEmpresaCompleta)}
        onConfirm={confirmEmpresaCompleta}
      />

      <ImportPanel
        title="Importador de empresas"
        icon={<Building2 size={18} />}
        columns={["ID Empresa", "Nombre", "RUT", "Dirección"]}
        state={empresas}
        type="empresas"
        summaryLabels={companySummaryLabels}
        onPreview={(event) => previewFile(event, previewImportEmpresas, setEmpresas)}
        onConfirm={(rows, batchId) =>
          confirmRows(rows, (payload) => confirmarImportEmpresas(payload), setEmpresas, batchId)
        }
      />



      <ImportPanel
        title="Importador de factores"
        icon={<FileSpreadsheet size={18} />}
        columns={["Actividad", "Unidad", "Factor de Emisión", "Año"]}
        state={factors}
        type="factors"
        summaryLabels={factorSummaryLabels}
        onPreview={(event) => previewFile(event, previewImportFactores, setFactors)}
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmarImportFactores(payload),
            setFactors,
            batchId
          )
        }
      />

      <ImportPanel
        title="Importador de unidades operativas"
        icon={<Factory size={18} />}
        columns={["ID Unidad", "Nombre", "Tipo", "Región", "Comuna", "Dirección"]}
        state={units}
        type="unidades"
        summaryLabels={unitSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewImportUnidadesForEmpresa(activeEmpresaId, file), setUnits)}
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmarImportUnidadesForEmpresa(activeEmpresaId, payload),
            setUnits,
            batchId
          )
        }
      />

      <ImportPanel
        title="Importador de lotes"
        icon={<Boxes size={18} />}
        columns={["ID Lote", "ID Unidad", "Fecha", "Especie", "Volumen (m³)"]}
        state={lotes}
        type="lotes"
        summaryLabels={loteSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewImportLotesForEmpresa(activeEmpresaId, file), setLotes)}
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmarImportLotesForEmpresa(activeEmpresaId, payload),
            setLotes,
            batchId
          )
        }
      />

      <ImportPanel
        title="Importador de actividades"
        icon={<DatabaseZap size={18} />}
        columns={["ID Unidad", "ID Lote", "Actividad", "Cantidad", "Unidad", "Fecha"]}
        state={activities}
        type="activities"
        summaryLabels={activitySummaryLabels}
        onPreview={(event) =>
          previewFile(event, (file) => previewActivityImportForEmpresa(activeEmpresaId, file), setActivities)
        }
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmActivityImportForEmpresa(activeEmpresaId, payload),
            setActivities,
            batchId
          )
        }
      />
        </>
      )}
    </div>
  );
}

export default ImportacionesView;
