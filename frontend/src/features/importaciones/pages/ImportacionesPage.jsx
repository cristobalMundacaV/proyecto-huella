import { useMemo, useState, useRef } from "react";
import {
  AlertTriangle,
  Boxes,
  Building2,
  CheckCircle2,
  DatabaseZap,
  Download,
  Factory,
  FileSpreadsheet,
  Loader2,
  Save,
  Upload,
} from "lucide-react";

import Toast from "@/shared/components/Toast";
import ImportarEvidenciaObraModal from "@/shared/components/ImportarEvidenciaObraModal";
import {
  confirmRegistroEmisionImport,
  confirmarImportFactores,
  previewImportacionCompletaConstruccion,
  confirmarImportacionCompletaConstruccion,
  previewImportConstructoras,
  confirmarImportConstructoras,
  previewRegistroEmisionImport,
  previewImportFactores,
  confirmarImportObrasForConstructora,
  confirmarImportEtapasForConstructora,
  confirmRegistroEmisionImportForConstructora,
  previewImportObrasForConstructora,
  previewImportEtapasForConstructora,
  previewRegistroEmisionImportForConstructora,
  getPlantillaImportacionConstruccionUrl,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import EmptyState from "@/shared/components/EmptyState";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { useFactores } from "@/features/factores/context/FactoresContext";

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
  ["posibles_creaciones", "constructoras nuevas"],
  ["posibles_actualizaciones", "Actualizaciones"],
];

const registroSummaryLabels = [
  ["filas_validas", "Filas validas"],
  ["filas_con_error", "Filas con error"],
  ["factores_encontrados", "Factores encontrados"],
  ["factores_faltantes", "Factores faltantes"],
  ["obras_encontrados", "Obras encontradas"],
  ["obras_nuevos_detectados", "Obras nuevas"],
];

const obraSummaryLabels = [
  ["validas", "Filas validas"],
  ["con_error", "Filas con error"],
  ["obras_nuevos", "Obras nuevas"],
  ["obras_existentes", "Obras existentes"],
  ["duplicadas", "Duplicados"],
];

const unitSummaryLabels = [
  ["validas", "Filas validas"],
  ["con_error", "Filas con error"],
  ["nuevas", "Etapas nuevas"],
  ["existentes", "Etapas existentes"],
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
            <th className="px-3 py-4 text-left min-w-40 font-semibold">Fuente de emisión</th>
            {isFactors ? <th className="px-3 py-4 text-center min-w-40 font-semibold">source key</th> : null}
            <th className="px-3 py-4 text-center min-w-20 font-semibold">Etapa</th>
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
                {row.data.fuente_emision || "-"}
              </td>
              {isFactors ? (
                <td className="px-3 py-4 text-center font-mono text-xs text-slate-400 whitespace-nowrap">
                  {row.data.fuente_emision_key || "-"}
                </td>
              ) : null}
              <td className="px-3 py-4 text-center text-slate-300 whitespace-nowrap">{row.data.unidad || "-"}</td>
              {isFactors ? <td className="px-3 py-4 text-center text-slate-300 whitespace-nowrap">{row.data.anio || "-"}</td> : <td className="px-3 py-4 text-center text-slate-300 whitespace-nowrap">{row.data.codigo_obra || row.data.etapa_id || row.data.constructora_id || "-"}</td>}
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

function ObraPreviewTable({ rows }) {
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
            <th className="px-3 py-4 text-left min-w-28 font-semibold">Código de obra</th>
            <th className="px-3 py-4 text-left min-w-40 font-semibold">constructora / proveedor</th>
            <th className="px-3 py-4 text-left min-w-28 font-semibold">Fecha</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Material / tipo de obra</th>
            <th className="px-3 py-4 text-right min-w-24 font-semibold">Cantidad base</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Ubicación / origen</th>
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
              <td className="px-3 py-4 font-semibold text-slate-100">{row.data.codigo_obra || "-"}</td>
              <td className="px-3 py-4 text-slate-300 truncate">{row.data.constructora || row.data.constructora_nombre || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.fecha || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.tipo_proyecto || "-"}</td>
              <td className="px-3 py-4 text-right text-emerald-300 font-semibold">{row.data.superficie_m2 || "-"}</td>
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

function ConstructoraPreviewTable({ rows }) {
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
            <th className="px-3 py-4 text-left min-w-32 font-semibold">constructora ID</th>
            <th className="px-3 py-4 text-left min-w-48 font-semibold">Nombre</th>
            <th className="px-3 py-4 text-left min-w-28 font-semibold">RUT</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Región</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Comuna</th>
            <th className="px-3 py-4 text-left min-w-40 font-semibold">Dirección</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Rubro</th>
            <th className="px-3 py-4 text-left min-w-36 font-semibold">Email</th>
            <th className="px-3 py-4 text-left min-w-28 font-semibold">Teléfono</th>
            <th className="px-3 py-4 text-left min-w-36 font-semibold">Contacto</th>
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
              <td className="px-3 py-4 font-mono text-xs text-cyan-200">{row.data.constructora_id || "-"}</td>
              <td className="px-3 py-4 font-semibold text-slate-100">{row.data.nombre || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.rut || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.region || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.comuna || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.direccion || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.rubro || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.email || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.telefono || "-"}</td>
              <td className="px-3 py-4 text-slate-300">{row.data.contacto || "-"}</td>
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
            <th className="px-3 py-4 text-left min-w-32 font-semibold">Etapa ID</th>
            <th className="px-3 py-4 text-left min-w-32 font-semibold">constructora ID</th>
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
              <td className="px-3 py-4 font-mono text-xs text-cyan-200">{row.data.etapa_id || "-"}</td>
              <td className="px-3 py-4 font-mono text-xs text-slate-300">{row.data.constructora_id || "-"}</td>
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
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 sm:p-6">
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

        <label className="premium-button premium-button-secondary flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold lg:w-fit">
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
          {type === "obras" ? (
            <ObraPreviewTable rows={state.result.rows} />
          ) : type === "constructoras" ? (
            <ConstructoraPreviewTable rows={state.result.rows} />
          ) : type === "etapas" ? (
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
            Confirmar importación
          </button>
        </>
      )}
    </section>
  );
}

function ConstructoraCompletaImportPanel({ state, onPreview, onConfirm }) {
  const blockingErrors = state.result?.blocking_errors || [];
  const sectionErrors =
    (state.result?.etapas?.errores || 0) +
    (state.result?.obras?.errores || 0) +
    (state.result?.registros_emision?.errores || 0) +
    (state.result?.factores?.errores || 0);
  const ConstructoraData = state.result?.constructora?.data || {};
  const summaryCards = [
    { label: "constructora", value: state.result?.constructora?.status === "valid" ? "Lista" : "Revisar" },
    { label: "Etapas", value: formatNumber(state.result?.etapas?.total || 0, 0) },
    { label: "Obras", value: formatNumber(state.result?.obras?.total || 0, 0) },
    { label: "Registros", value: formatNumber(state.result?.registros_emision?.total || 0, 0) },
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
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
            <Building2 size={18} />
          </div>
          <div>
            <h2 className="text-xl font-semibold">Importar operación completa</h2>
            <p className="text-sm text-slate-400">
              Archivo XLSX con hojas <span className="font-semibold text-slate-200">constructora</span>, <span className="font-semibold text-slate-200">etapas</span>, <span className="font-semibold text-slate-200">obras</span>, <span className="font-semibold text-slate-200">registros</span>, <span className="font-semibold text-slate-200">factores</span> y evidencias de obra.
            </p>
          </div>
        </div>

        <div className="flex w-full flex-col gap-2 sm:flex-row lg:w-fit">
          <a
            href={getPlantillaImportacionConstruccionUrl()}
            className="flex items-center justify-center gap-2 rounded-2xl border border-slate-600/60 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-100 transition hover:bg-slate-800"
          >
            <Download size={18} />
            Descargar plantilla
          </a>
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-100 transition hover:bg-cyan-400/20">
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
              <div key={card.label} className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-soft)]">
                <p className="text-xs text-slate-500">{card.label}</p>
                <p className="mt-1 text-2xl font-bold text-slate-100">{card.value}</p>
              </div>
            ))}
          </div>

          {state.result?.resumen && (
            <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--info-bg)] p-4">
              <h3 className="text-base font-semibold text-cyan-100">Resumen antes de confirmar</h3>
              <div className="mt-3 grid grid-cols-1 gap-3 text-sm text-slate-200 md:grid-cols-2 xl:grid-cols-3">
                <p>constructora detectada: <span className="font-semibold">{state.result.resumen.Constructora_detectada || "-"}</span></p>
                <p>Periodo detectado: <span className="font-semibold">{state.result.resumen.periodo_detectado || "-"}</span></p>
                <p>Emisiones estimadas: <span className="font-semibold">{formatNumber(Number(state.result.resumen.emisiones_estimadas_kg_co2e || 0), 1)} kg CO2e</span></p>
              </div>
              {state.result.resumen.alertas?.length > 0 && (
                <div className="mt-3 space-y-1 text-sm text-yellow-200">
                  {state.result.resumen.alertas.map((alerta) => (
                    <p key={alerta}>Advertencia: {alerta}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <h3 className="text-base font-semibold text-slate-100">Datos de la constructora</h3>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {companyFields.map(([key, label]) => (
                <div key={key} className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-3">
                  <p className="text-xs text-slate-500">{label}</p>
                  <p className="mt-1 break-words text-sm font-semibold text-slate-100">
                    {ConstructoraData[key] || "-"}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {blockingErrors.length > 0 && (
            <div className="premium-card-interactive rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-4 text-sm text-[#B42318]">
              <p className="font-semibold">Errores bloqueantes</p>
              <p className="mt-2 leading-6">{blockingErrors.join("; ")}</p>
            </div>
          )}

          {/* Mostrar errores y validación de etapas */}
          {state.result?.etapas && (
            <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <h3 className="text-base font-semibold text-slate-100">Etapas / frentes ({state.result.etapas.validas} válidas, {state.result.etapas.errores} errores)</h3>
              {state.result.etapas.errores > 0 && (
                <div className="mt-3 max-h-40 space-y-2 overflow-y-auto rounded border border-red-500/30 bg-red-500/10 p-2">
                  {state.result.etapas.rows.filter(r => r.status === 'error').map((row) => (
                    <div key={row.row_number} className="text-xs text-red-300">
                      <p className="font-semibold">Fila {row.row_number}:</p>
                      <p className="ml-2">{row.errors?.join(', ') || 'Error desconocido'}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mostrar errores y validación de obras */}
          {state.result?.obras && (
            <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <h3 className="text-base font-semibold text-slate-100">Obras ({state.result.obras.validos} válidas, {state.result.obras.errores} errores)</h3>
              {state.result.obras.errores > 0 && (
                <div className="mt-3 max-h-40 space-y-2 overflow-y-auto rounded border border-red-500/30 bg-red-500/10 p-2">
                  {state.result.obras.rows.filter(r => r.status === 'error').map((row) => (
                    <div key={row.row_number} className="text-xs text-red-300">
                      <p className="font-semibold">Fila {row.row_number}:</p>
                      <p className="ml-2">{row.errors?.join(', ') || 'Error desconocido'}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mostrar errores y validación de registros_emision */}
          {state.result?.registros_emision && (
            <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <h3 className="text-base font-semibold text-slate-100">
                Registros ({state.result.registros_emision.validas} válidos, {state.result.registros_emision.errores} errores)
                {state.result.registros_emision.factores_faltantes > 0 && (
                  <span className="text-xs text-yellow-400"> - {state.result.registros_emision.factores_faltantes} sin factor de emisión</span>
                )}
              </h3>
              {state.result.registros_emision.errores > 0 && (
                <div className="mt-3 max-h-40 space-y-2 overflow-y-auto rounded border border-red-500/30 bg-red-500/10 p-2">
                  {state.result.registros_emision.rows.filter(r => r.status === 'error').map((row) => (
                    <div key={row.row_number} className="text-xs text-red-300">
                      <p className="font-semibold">Fila {row.row_number}:</p>
                      <p className="ml-2">{row.errors?.join(', ') || 'Error desconocido'}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mostrar resumen de confirmación */}
          {state.result?.etapas_creadas !== undefined && (
            <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <h3 className="text-base font-semibold text-slate-100">Resumen de confirmación</h3>
              <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="rounded border border-slate-700 bg-slate-900/80 p-3 text-center">
                  <p className="text-xs text-slate-500">constructora creada</p>
                  <p className="mt-1 text-2xl font-bold text-emerald-400">{state.result.creados || 0}</p>
                </div>
                <div className="rounded border border-slate-700 bg-slate-900/80 p-3 text-center">
                  <p className="text-xs text-slate-500">Etapas</p>
                  <p className="mt-1 text-2xl font-bold text-cyan-400">{state.result.etapas_creadas || 0}</p>
                </div>
                <div className="rounded border border-slate-700 bg-slate-900/80 p-3 text-center">
                  <p className="text-xs text-slate-500">Obras</p>
                  <p className="mt-1 text-2xl font-bold text-cyan-400">{state.result.obras_creados || 0}</p>
                </div>
                <div className="rounded border border-slate-700 bg-slate-900/80 p-3 text-center">
                  <p className="text-xs text-slate-500">Registros</p>
                  <p className="mt-1 text-2xl font-bold text-cyan-400">{state.result.registros_emision_creadas || 0}</p>
                </div>
              </div>
            </div>
          )}

          {/* Mostrar errores de confirmación si existen */}
          {state.result?.errores && state.result.errores.length > 0 && (
            <div className="premium-card-interactive rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-4 text-sm text-[#B42318]">
              <p className="font-semibold">Errores durante confirmación ({state.result.errores.length})</p>
              <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                {state.result.errores.slice(0, 20).map((error, idx) => (
                  <div key={idx} className="text-xs font-mono">
                    {typeof error === 'string' ? error : `Fila ${error.row_number}: ${error.errors?.join(', ')}`}
                  </div>
                ))}
                {state.result.errores.length > 20 && (
                  <p className="text-xs italic">... y {state.result.errores.length - 20} errores más</p>
                )}
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => onConfirm(state.result?.batch_id)}
            disabled={!state.result?.batch_id || blockingErrors.length > 0 || sectionErrors > 0 || state.saving}
            className="premium-button premium-button-primary inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
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
  const [obras, setObras] = useState(emptyImportState);
  const [constructoras, setConstructoras] = useState(emptyImportState);
  const [ConstructoraCompleta, setConstructoraCompleta] = useState(emptyImportState);
  const [registros, setRegistros] = useState(emptyImportState);
  const [toast, setToast] = useState(null);
  const [documentImportOpen, setDocumentImportOpen] = useState(false);
  const { activeConstructora, activeConstructoraId, refreshConstructoras } = useConstructoraActiva();
  const { invalidate: invalidateFactores } = useFactores();
  const ConstructoraCompletaInputRef = useRef(null);

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

  const handleImportConstructoraCompleta = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setConstructoraCompleta({ ...emptyImportState, fileName: file.name, loading: true });

    try {
      const preview = await previewImportacionCompletaConstruccion(file);

      setConstructoraCompleta((current) => ({
        ...current,
        loading: false,
        result: preview,
      }));

      const hasBlockingErrors = (preview.blocking_errors || []).length > 0;

      if (hasBlockingErrors) {
        setConstructoraCompleta((current) => ({
          ...current,
          loading: false,
          error: preview.error || "El archivo tiene errores bloqueantes; revisa la previsualización antes de confirmar.",
        }));
      }
    } catch (err) {
      const resp = err.response?.data || {};
      setConstructoraCompleta((current) => ({
        ...current,
        loading: false,
        saving: false,
        error: resp.error || resp.detail || "Error durante la importación completa.",
      }));
    } finally {
      if (event?.target) event.target.value = "";
    }
  };

  const confirmConstructoraCompleta = async (batchId) => {
    if (!batchId) {
      setConstructoraCompleta((current) => ({
        ...current,
        error: "Falta batch_id para confirmar la importación.",
      }));
      return;
    }

    setConstructoraCompleta((current) => ({ ...current, saving: true, error: "", savedMessage: "" }));

    try {
      const result = await confirmarImportacionCompletaConstruccion({ batch_id: batchId });
      const created = result.creados ?? result.created ?? 0;
      
      // Agrupar errores por tipo
      const errorsBySheet = {};
      if (result.errores && result.errores.length > 0) {
        result.errores.forEach(error => {
          const sheetName = error.sheet || 'general';
          if (!errorsBySheet[sheetName]) errorsBySheet[sheetName] = [];
          errorsBySheet[sheetName].push(error);
        });
      }

      // Si hay errores, mostrarlos pero no considerar como fallo total si se creó algo
      let errorMessage = "";
      if (Object.keys(errorsBySheet).length > 0) {
        errorMessage = Object.entries(errorsBySheet)
          .map(([sheet, errors]) => {
            const errorList = errors.map(e => 
              typeof e === 'string' ? e : `Fila ${e.row_number}: ${e.errors?.join(', ')}`
            ).join('\n');
            return `${sheet}:\n${errorList}`;
          })
          .join('\n\n');
      }

      const msg = "Archivo importado correctamente. Los registros fueron validados y agregados a la constructora activa.";

      showToast(msg);
      
      // Refresh constructoras después de la importación completa
      await refreshConstructoras().catch(() => undefined);
      
      await onImportConfirmed?.();

      setConstructoraCompleta((current) => ({
        ...current,
        saving: false,
        savedMessage: msg,
        result: { 
          ...current.result,
          errores: result.errores || [],
          etapas_creadas: result.etapas_creadas || 0,
          obras_creados: result.obras_creados || 0,
          registros_emision_creadas: result.registros_emision_creadas || 0,
          factores_creados: result.factores_creados || 0,
        },
        error: errorMessage || ""
      }));
    } catch (err) {
      const resp = err.response?.data || {};
      setConstructoraCompleta((current) => ({
        ...current,
        saving: false,
        error: resp.error || resp.detail || "Error al confirmar la importación completa.",
      }));
    }
  };

  const confirmRows = async (rows, confirmFn, setState, batchId = null, onSuccess = null) => {
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
      
      // Refresh constructoras después de cualquier importación exitosa
      await refreshConstructoras().catch(() => undefined);
      
      // Call onSuccess callback if provided (e.g., to invalidate factores)
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess();
      }
      
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
      {!activeConstructora ? (
        <EmptyState
          title="Selecciona o crea una constructora para comenzar"
          description="Las importaciones operan dentro del contexto de la constructora activa."
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
            <p className="text-slate-400">Carga masiva de datos de obra para mantener actualizada la gestión ambiental de {activeConstructora.nombre}.</p>
          </div>
        </div>
      </header>
      <section className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-sm text-cyan-100 sm:p-5">
        Para evitar errores de relación entre datos, importa los archivos en este orden: constructoras, factores de emisión, etapas o frentes, obras y registros. También puedes usar la plantilla completa para cargar materiales, transporte, maquinaria, energía, residuos y evidencias en un solo archivo XLSX.
      </section>
      <section className="rounded-3xl border border-[#B7DEC9] bg-[var(--success-bg)] p-5 shadow-[0_18px_45px_var(--shadow)] sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--primary-dark)]">Flujo inteligente</p>
            <h2 className="mt-2 text-2xl font-bold text-[var(--text-main)]">Importar evidencia de obra</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#344054]">
              Analiza un evidencia, revisa la lectura sugerida y confirma manualmente antes de crear el registro de emisión.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDocumentImportOpen(true)}
            className="inline-flex items-center justify-center rounded-2xl border border-[var(--primary-dark)] bg-[var(--primary-dark)] px-5 py-3 text-sm font-bold text-white transition hover:bg-[var(--primary-dark-hover)]"
          >
            Importar evidencia de obra
          </button>
        </div>
      </section>
      <ConstructoraCompletaImportPanel
        state={ConstructoraCompleta}
        onPreview={(event) => previewFile(event, previewImportacionCompletaConstruccion, setConstructoraCompleta)}
        onConfirm={confirmConstructoraCompleta}
      />

      <ImportPanel
        title="Importar constructoras"
        icon={<Building2 size={18} />}
        columns={[
          "ID constructora",
          "Nombre",
          "RUT",
          "Región",
          "Comuna",
          "Dirección",
          "Rubro",
          "Email",
          "Teléfono",
          "Contacto",
          "Observaciones",
        ]}
        state={constructoras}
        type="constructoras"
        summaryLabels={companySummaryLabels}
        onPreview={(event) => previewFile(event, previewImportConstructoras, setConstructoras)}
        onConfirm={(rows, batchId) =>
          confirmRows(rows, (payload) => confirmarImportConstructoras(payload), setConstructoras, batchId)
        }
      />



      <ImportPanel
        title="Importar factores de emisión"
        icon={<FileSpreadsheet size={18} />}
        columns={["Fuente de emisión", "Etapa", "Factor de Emisión", "Fuente", "Año"]}
        state={factors}
        type="factors"
        summaryLabels={factorSummaryLabels}
        onPreview={(event) => previewFile(event, previewImportFactores, setFactors)}
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmarImportFactores(payload),
            setFactors,
            batchId,
            invalidateFactores
          )
        }
      />

      <ImportPanel
        title="Importar etapas"
        icon={<Factory size={18} />}
        columns={["ID Etapa", "ID constructora", "Nombre", "Tipo", "Región", "Comuna", "Dirección", "Estado"]}
        state={units}
        type="etapas"
        summaryLabels={unitSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewImportEtapasForConstructora(activeConstructoraId, file), setUnits)}
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmarImportEtapasForConstructora(activeConstructoraId, payload),
            setUnits,
            batchId
          )
        }
      />

      <ImportPanel
        title="Importar obras"
        icon={<Boxes size={18} />}
        columns={["Código de obra", "ID Etapa", "Fecha", "Material / tipo de obra", "Cantidad base", "Ubicación / origen"]}
        state={obras}
        type="obras"
        summaryLabels={obraSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewImportObrasForConstructora(activeConstructoraId, file), setObras)}
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmarImportObrasForConstructora(activeConstructoraId, payload),
            setObras,
            batchId
          )
        }
      />

      <ImportPanel
        title="Importar registros de emisión"
        icon={<DatabaseZap size={18} />}
        columns={["ID Registro", "Código de obra", "ID Etapa", "Fuente", "Cantidad", "Etapa", "Fecha", "Observación", "Fuente de dato"]}
        state={registros}
        type="registros"
        summaryLabels={registroSummaryLabels}
        onPreview={(event) =>
          previewFile(event, (file) => previewRegistroEmisionImportForConstructora(activeConstructoraId, file), setRegistros)
        }
        onConfirm={(rows, batchId) =>
          confirmRows(
            rows,
            (payload) => confirmRegistroEmisionImportForConstructora(activeConstructoraId, payload),
            setRegistros,
            batchId
          )
        }
      />
      <ImportarEvidenciaObraModal
        activeConstructoraId={activeConstructoraId}
        initialTitle="Importar evidencia de obra"
        onClose={() => setDocumentImportOpen(false)}
        open={documentImportOpen}
      />
        </>
      )}
    </div>
  );
}

export default ImportacionesView;
