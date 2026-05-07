import { useEffect, useMemo, useState } from "react";
import { Building2, FileCheck2, FileText, Link2, ShieldAlert, UploadCloud } from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import Pagination from "@/shared/components/Pagination";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";
import {
  crearEvidenciaEmpresa,
  getEvidenciasEmpresa,
  getEvidenciasKpisEmpresa,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const pageSize = 10;

const tipoOptions = [
  "guia_despacho",
  "factura_combustible",
  "factura_electrica",
  "certificado_origen",
  "certificado_forestal",
  "documento_transporte",
  "ticket_pesaje",
  "registro_gps",
  "fotografia",
  "ficha_tecnica",
  "otro",
];

function formatOptionLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const alcanceOptions = [
  { value: "empresa", label: "Empresa completa", helper: "Respalda a la empresa activa completa." },
  { value: "unidad", label: "Unidad operativa", helper: "Requiere ID unidad de la empresa activa." },
  { value: "lote", label: "Lote", helper: "Requiere ID lote; la unidad se infiere si existe." },
  { value: "emision", label: "Actividad / emision", helper: "Requiere ID emision; lote y unidad se infieren si existen." },
  { value: "transporte", label: "Transporte", helper: "Puede vincularse a un lote o quedar como respaldo corporativo." },
];

const alcanceLabels = {
  empresa: "Empresa completa",
  unidad: "Unidad",
  lote: "Lote",
  emision: "Emision",
  transporte: "Transporte",
};

const sistemaLabels = {
  corporativa: "Corporativa",
  vinculada: "Vinculada",
  sin_vinculo: "Sin revisar",
};

const sistemaStyles = {
  corporativa: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  vinculada: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
  sin_vinculo: "border-slate-700 bg-slate-950 text-slate-300",
};

const revisionLabels = {
  sin_revisar: "Sin revisar",
  validada: "Validada",
  observada: "Observada",
  rechazada: "Rechazada",
};

const revisionStyles = {
  sin_revisar: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  validada: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  observada: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
  rechazada: "border-rose-400/30 bg-rose-400/10 text-rose-200",
};

const emptyForm = {
  nombre: "",
  tipo_documento: "guia_despacho",
  alcance: "empresa",
  lote_id: "",
  unidad_id: "",
  emision_id: "",
  fecha_documento: "",
  observaciones: "",
  archivo: null,
};

function KpiImpact({ icon, label, value, detail, tone = "slate" }) {
  const toneClass = {
    cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-100",
    emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-100",
    amber: "border-amber-400/20 bg-amber-400/10 text-amber-100",
    rose: "border-rose-400/20 bg-rose-400/10 text-rose-100",
    slate: "border-slate-800 bg-slate-900 text-slate-100",
  }[tone];

  return (
    <div className={`rounded-3xl border p-5 ${toneClass}`}>
      <div className="mb-3 text-current opacity-90">{icon}</div>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
      {detail ? <p className="mt-2 text-sm opacity-75">{detail}</p> : null}
    </div>
  );
}

function EvidenceBadge({ value }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${sistemaStyles[value] || sistemaStyles.sin_vinculo}`}>
      {sistemaLabels[value] || "Sin revisar"}
    </span>
  );
}

function RevisionBadge({ value, label }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${revisionStyles[value] || revisionStyles.sin_revisar}`}>
      {label || revisionLabels[value] || "Sin revisar"}
    </span>
  );
}

function EvidenciasPage() {
  const { activeEmpresaId, activeEmpresa } = useEmpresaActiva();
  const [evidencias, setEvidencias] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState({ search: "", tipo: "", alcance: "", estado_sistema: "" });
  const [draftFilters, setDraftFilters] = useState(filters);
  const [form, setForm] = useState(emptyForm);

  async function loadData(nextFilters = filters) {
    if (!activeEmpresaId) return;

    try {
      setLoading(true);
      setError("");
      const [evidenciasData, kpisData] = await Promise.all([
        getEvidenciasEmpresa(activeEmpresaId, nextFilters),
        getEvidenciasKpisEmpresa(activeEmpresaId),
      ]);
      setEvidencias(Array.isArray(evidenciasData) ? evidenciasData : []);
      setKpis(kpisData || null);
      setCurrentPage(1);
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudieron cargar las evidencias.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeEmpresaId]);

  const totalPages = Math.max(1, Math.ceil((evidencias?.length || 0) / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return evidencias.slice(start, start + pageSize);
  }, [evidencias, safeCurrentPage]);

  const cobertura = Number(kpis?.cobertura_documental || 0);
  const selectedScope = alcanceOptions.find((item) => item.value === form.alcance) || alcanceOptions[0];

  async function onApplyFilters() {
    setFilters(draftFilters);
    await loadData(draftFilters);
  }

  async function onClearFilters() {
    const reset = { search: "", tipo: "", alcance: "", estado_sistema: "" };
    setDraftFilters(reset);
    setFilters(reset);
    await loadData(reset);
  }

  function updateScope(nextScope) {
    setForm((current) => ({
      ...current,
      alcance: nextScope,
      lote_id: "",
      unidad_id: "",
      emision_id: "",
    }));
  }

  function validateForm() {
    if (!form.nombre.trim() || !form.tipo_documento || !form.archivo) {
      return "Nombre, tipo de documento y archivo son obligatorios.";
    }
    if (form.alcance === "unidad" && !form.unidad_id.trim()) {
      return "Debes indicar un ID de unidad para respaldar una unidad operativa.";
    }
    if (form.alcance === "lote" && !form.lote_id.trim()) {
      return "Debes indicar un ID de lote para respaldar un lote.";
    }
    if (form.alcance === "emision" && !form.emision_id.trim()) {
      return "Debes indicar un ID de emision para respaldar una actividad.";
    }
    return "";
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!activeEmpresaId) return;

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setSaving(true);
      setError("");
      const formData = new FormData();
      formData.append("nombre", form.nombre.trim());
      formData.append("tipo_documento", form.tipo_documento);
      formData.append("alcance", form.alcance);
      formData.append("archivo", form.archivo);
      if (form.alcance === "unidad") formData.append("unidad_id", form.unidad_id.trim());
      if (form.alcance === "lote") formData.append("lote_id", form.lote_id.trim());
      if (form.alcance === "emision") formData.append("emision_id", form.emision_id.trim());
      if (form.alcance === "transporte" && form.lote_id.trim()) formData.append("lote_id", form.lote_id.trim());
      if (form.fecha_documento) formData.append("fecha_documento", form.fecha_documento);
      if (form.observaciones.trim()) formData.append("observaciones", form.observaciones.trim());

      await crearEvidenciaEmpresa(activeEmpresaId, formData);
      setForm(emptyForm);
      await loadData(filters);
    } catch (requestError) {
      const responseData = requestError?.response?.data;
      const firstError =
        responseData?.error ||
        (typeof responseData === "object" && responseData !== null
          ? Object.values(responseData).flat().find(Boolean)
          : null);
      setError(firstError || "No se pudo crear la evidencia.");
    } finally {
      setSaving(false);
    }
  }

  if (!activeEmpresaId) {
    return (
      <EmptyState
        title="Evidencias"
        description="Selecciona o crea una empresa para gestionar evidencias."
      />
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
      <section className="rounded-3xl border border-emerald-400/25 bg-emerald-400/10 p-5 shadow-[0_0_40px_rgba(16,185,129,0.08)] sm:p-7">
        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.75fr] lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">Centro documental</p>
            <h1 className="mt-3 text-3xl font-bold text-slate-100 sm:text-4xl">
              Evidencias flexibles para respaldar empresa, unidades, lotes y emisiones
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-emerald-50">
              Toda evidencia queda dentro de {activeEmpresa?.nombre || activeEmpresaId}. Elige que quieres respaldar y el sistema validara que el vinculo pertenezca a la empresa activa.
            </p>
            <p className="mt-3 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-3 text-sm font-semibold text-amber-100">
              Una evidencia cargada no significa que este validada. La validacion documental requiere revision humana o auditoria.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <KpiImpact icon={<FileText size={22} />} label="Documentos" value={formatNumber(kpis?.total_evidencias || 0, 0)} detail="Evidencias cargadas" tone="emerald" />
            <KpiImpact icon={<Link2 size={22} />} label="Vinculadas" value={formatNumber(kpis?.vinculadas || 0, 0)} detail="Con alcance especifico" tone="cyan" />
            <KpiImpact icon={<Building2 size={22} />} label="Corporativas" value={formatNumber(kpis?.corporativas || 0, 0)} detail="Respaldo empresa" tone="slate" />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiImpact icon={<FileCheck2 size={22} />} label="Cobertura lotes" value={`${formatNumber(cobertura, 1)}%`} detail={`${formatNumber(kpis?.lotes_con_evidencia || 0, 0)} de ${formatNumber(kpis?.total_lotes || 0, 0)} lotes`} tone={cobertura >= 75 ? "emerald" : cobertura >= 40 ? "amber" : "rose"} />
        <KpiImpact icon={<ShieldAlert size={22} />} label="Sin revisar" value={formatNumber(kpis?.sin_revisar || 0, 0)} detail="Revision humana pendiente" tone="amber" />
        <KpiImpact icon={<Link2 size={22} />} label="Lotes sin respaldo" value={formatNumber(kpis?.lotes_sin_evidencia || 0, 0)} detail="Prioriza alto impacto" tone="rose" />
        <KpiImpact icon={<UploadCloud size={22} />} label="Tipos documento" value={formatNumber(Object.keys(kpis?.por_tipo || {}).length, 0)} detail="Fuentes documentales" tone="cyan" />
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_180px_180px_180px_auto]">
          <input
            className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none focus:border-emerald-400/60"
            placeholder="Buscar documento, lote o unidad"
            value={draftFilters.search}
            onChange={(event) => setDraftFilters((current) => ({ ...current, search: event.target.value }))}
          />
          <select className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" value={draftFilters.tipo} onChange={(event) => setDraftFilters((current) => ({ ...current, tipo: event.target.value }))}>
            <option value="">Tipo</option>
            {tipoOptions.map((tipo) => <option key={tipo} value={tipo}>{formatOptionLabel(tipo)}</option>)}
          </select>
          <select className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" value={draftFilters.alcance} onChange={(event) => setDraftFilters((current) => ({ ...current, alcance: event.target.value }))}>
            <option value="">Alcance</option>
            {alcanceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" value={draftFilters.estado_sistema} onChange={(event) => setDraftFilters((current) => ({ ...current, estado_sistema: event.target.value }))}>
            <option value="">Estado sistema</option>
            <option value="corporativa">Corporativa</option>
            <option value="vinculada">Vinculada</option>
            <option value="sin_vinculo">Sin revisar</option>
          </select>
          <div className="flex gap-2">
            <button type="button" onClick={onApplyFilters} className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm font-bold text-emerald-200">Aplicar</button>
            <button type="button" onClick={onClearFilters} className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-bold text-slate-300">Limpiar</button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <form onSubmit={onSubmit} className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
          <div className="mb-5">
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">Nuevo respaldo</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-100">Adjuntar evidencia</h2>
            <p className="mt-2 text-sm text-slate-400">{selectedScope.helper}</p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" placeholder="Nombre documento" value={form.nombre} onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))} />
            <select className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" value={form.tipo_documento} onChange={(event) => setForm((current) => ({ ...current, tipo_documento: event.target.value }))}>
              {tipoOptions.map((tipo) => <option key={tipo} value={tipo}>{formatOptionLabel(tipo)}</option>)}
            </select>
            <label className="md:col-span-2">
              <span className="mb-1 block text-sm font-semibold text-slate-300">Alcance de la evidencia</span>
              <select className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" value={form.alcance} onChange={(event) => updateScope(event.target.value)}>
                {alcanceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            {form.alcance === "unidad" && <input className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 md:col-span-2" placeholder="ID unidad" value={form.unidad_id} onChange={(event) => setForm((current) => ({ ...current, unidad_id: event.target.value }))} />}
            {form.alcance === "lote" && <input className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 md:col-span-2" placeholder="ID lote" value={form.lote_id} onChange={(event) => setForm((current) => ({ ...current, lote_id: event.target.value }))} />}
            {form.alcance === "emision" && <input className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 md:col-span-2" placeholder="ID emision" value={form.emision_id} onChange={(event) => setForm((current) => ({ ...current, emision_id: event.target.value }))} />}
            {form.alcance === "transporte" && <input className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 md:col-span-2" placeholder="ID lote opcional" value={form.lote_id} onChange={(event) => setForm((current) => ({ ...current, lote_id: event.target.value }))} />}
            <input type="date" className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100" value={form.fecha_documento} onChange={(event) => setForm((current) => ({ ...current, fecha_documento: event.target.value }))} />
            <input type="file" className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 file:mr-4 file:rounded-xl file:border-0 file:bg-emerald-400/10 file:px-3 file:py-2 file:font-bold file:text-emerald-200" onChange={(event) => setForm((current) => ({ ...current, archivo: event.target.files?.[0] || null }))} />
            <textarea className="min-h-24 rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 md:col-span-2" placeholder="Observaciones" value={form.observaciones} onChange={(event) => setForm((current) => ({ ...current, observaciones: event.target.value }))} />
          </div>

          {error ? <p className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p> : null}

          <div className="mt-5 flex flex-wrap gap-3">
            <button type="submit" disabled={saving} className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 disabled:opacity-60">{saving ? "Guardando..." : "Adjuntar evidencia"}</button>
            <button type="button" onClick={() => setForm(emptyForm)} className="rounded-2xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-300">Limpiar formulario</button>
          </div>
        </form>

        <section className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 sm:p-6">
          <h2 className="text-xl font-semibold text-slate-100">Alcances disponibles</h2>
          <div className="mt-4 space-y-3">
            {alcanceOptions.map((option) => (
              <div key={option.value} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="font-semibold text-cyan-100">{option.label}</p>
                <p className="mt-1 text-sm text-slate-400">{option.helper}</p>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Evidencias registradas</h2>
            <p className="mt-1 text-sm text-slate-400">Mostrando {visibleRows.length} de {evidencias.length} evidencias.</p>
          </div>
          {loading ? <p className="text-sm font-semibold text-emerald-200">Cargando...</p> : null}
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-[1120px] w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-3 py-3">Documento</th>
                <th className="px-3 py-3">Tipo</th>
                <th className="px-3 py-3">Alcance</th>
                <th className="px-3 py-3">Vinculo</th>
                <th className="px-3 py-3">Fecha</th>
                <th className="px-3 py-3">Estado sistema</th>
                <th className="px-3 py-3">Revision documental</th>
                <th className="px-3 py-3">Archivo</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((item) => (
                <tr key={item.id} className="border-b border-slate-800/70">
                  <td className="px-3 py-3 font-semibold text-slate-100">{item.nombre}</td>
                  <td className="px-3 py-3 text-slate-300">{formatOptionLabel(item.tipo_documento)}</td>
                  <td className="px-3 py-3 text-slate-300">{item.alcance_label || alcanceLabels[item.alcance] || "Empresa completa"}</td>
                  <td className="px-3 py-3 text-slate-300">
                    {item.emision ? `Emision ${item.emision}` : item.lote_codigo || item.unidad_codigo || item.empresa_codigo}
                  </td>
                  <td className="px-3 py-3 text-slate-300">{item.fecha_documento || "-"}</td>
                  <td className="px-3 py-3"><EvidenceBadge value={item.estado_sistema} /></td>
                  <td className="px-3 py-3">
                    <RevisionBadge
                      label={item.estado_revision_label}
                      value={item.estado_revision}
                    />
                  </td>
                  <td className="px-3 py-3">
                    {item.archivo_url ? <a className="font-semibold text-cyan-300 underline" href={item.archivo_url} target="_blank" rel="noreferrer">Ver</a> : <span className="text-slate-500">-</span>}
                  </td>
                </tr>
              ))}
              {!loading && visibleRows.length === 0 ? (
                <tr>
                  <td className="px-3 py-8 text-center text-slate-400" colSpan={8}>
                    No hay evidencias registradas para los filtros seleccionados.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <Pagination
          currentPage={safeCurrentPage}
          onPageChange={setCurrentPage}
          pageSize={pageSize}
          totalItems={evidencias.length}
          itemLabel="evidencias"
        />
      </section>
    </main>
  );
}

export default EvidenciasPage;
