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
import ImportarDocumentoObraModal from "@/shared/components/ImportarDocumentoObraModal";
import {
  constructionEvidenceScopeOptions,
  constructionEvidenceTypeOptions,
  getConstructionEvidenceLinkLabel,
  getConstructionEvidenceReviewLabel,
  getConstructionEvidenceScopeLabel,
  getConstructionEvidenceTypeLabel,
} from "@/shared/utils/constructionEvidenceLabels";
import { formatNumber } from "@/shared/utils/formatters";

const pageSize = 10;

const sistemaStyles = {
  corporativa: "border-[#B7DEC9] bg-[var(--success-bg)] text-[var(--primary-dark)]",
  vinculada: "border-[#B9D8D3] bg-[var(--info-bg)] text-[#075985]",
  sin_vinculo: "border-[var(--border)] bg-[var(--bg-surface)] text-[#475467]",
};

const revisionStyles = {
  sin_revisar: "border-[#E6CC82] bg-[var(--warning-bg)] text-[#7A4F00]",
  validada: "border-[#B7DEC9] bg-[var(--success-bg)] text-[var(--primary-dark)]",
  observada: "border-[#B9D8D3] bg-[var(--info-bg)] text-[#075985]",
  rechazada: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
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
    cyan: "border-[var(--kpi-info-border)] bg-[var(--kpi-info-bg)] text-[var(--kpi-info-text)]",
    emerald: "border-[var(--kpi-success-border)] bg-[var(--kpi-success-bg)] text-[var(--kpi-success-text)]",
    amber: "border-[var(--kpi-warning-border)] bg-[var(--kpi-warning-bg)] text-[var(--kpi-warning-text)]",
    rose: "border-[var(--kpi-danger-border)] bg-[var(--kpi-danger-bg)] text-[var(--kpi-danger-text)]",
    slate: "border-[var(--kpi-neutral-border)] bg-[var(--kpi-neutral-bg)] text-[var(--kpi-dark-text)]",
  }[tone];

  return (
    <div className={`premium-card premium-card-interactive rounded-3xl border p-5 shadow-[0_14px_35px_var(--shadow)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_40px_rgba(15,23,42,0.10)] ${toneClass}`}>
      <div className="mb-3 flex items-center gap-3">
        <div className="text-current opacity-90">{icon}</div>
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {label}
        </p>
      </div>
      <p className="mt-2 text-3xl font-black tracking-tight text-current">{value}</p>
      {detail ? <p className="mt-2 text-sm text-[var(--text-muted)]">{detail}</p> : null}
    </div>
  );
}

function EvidenceBadge({ value }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${sistemaStyles[value] || sistemaStyles.sin_vinculo}`}>
      {getConstructionEvidenceLinkLabel(value)}
    </span>
  );
}

function RevisionBadge({ value, label }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${revisionStyles[value] || revisionStyles.sin_revisar}`}>
      {label || getConstructionEvidenceReviewLabel(value)}
    </span>
  );
}

function formatEvidenceType(value) {
  return getConstructionEvidenceTypeLabel(value);
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
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importModalContext, setImportModalContext] = useState(null);

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
  const selectedScope = constructionEvidenceScopeOptions.find((item) => item.value === form.alcance) || constructionEvidenceScopeOptions[0];
  const totalObservadas = Number(kpis?.por_revision?.observada || 0);
  const totalPendientes = Number(kpis?.sin_revisar || 0);
  const totalVinculadas = Number(kpis?.vinculadas || 0);
  const obrasConRespaldo = Number(kpis?.lotes_con_evidencia || 0);
  const alcanceOptions = constructionEvidenceScopeOptions;
  const coverageValue = Number(kpis?.total_lotes || 0) > 0 && obrasConRespaldo > 0 ? `${formatNumber(cobertura, 1)}%` : "Pendiente de vinculación";
  const coverageDetail = Number(kpis?.total_lotes || 0)
    ? `${formatNumber(obrasConRespaldo, 0)} de ${formatNumber(kpis?.total_lotes || 0, 0)} obras`
    : "Sin obras registradas";

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

  function openImportModal(item) {
    setImportModalContext({
      archivoNombre: item.nombre,
      archivoUrl: item.archivo_url,
      initialLoteId: item.lote_codigo || "",
    });
    setImportModalOpen(true);
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
      return "Nombre, tipo de evidencia y archivo son obligatorios.";
    }
    if (form.alcance === "unidad" && !form.unidad_id.trim()) {
      return "Debes indicar un ID de etapa para respaldar un frente de obra.";
    }
    if (form.alcance === "lote" && !form.lote_id.trim()) {
      return "Debes indicar un código de obra para respaldar una obra.";
    }
    if (form.alcance === "emision" && !form.emision_id.trim()) {
      return "Debes indicar un ID de emisión para respaldar un registro.";
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
        description="Selecciona o crea una constructora para gestionar respaldos documentales de obra."
      />
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
      <section className="rounded-3xl border border-[#B7DEC9] bg-[var(--success-bg)] p-5 shadow-[0_18px_45px_var(--shadow)] sm:p-7">
        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.75fr] lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--primary-dark)]">Centro documental</p>
            <h1 className="mt-3 text-3xl font-bold text-[var(--text-main)] sm:text-4xl">
              Respalda constructoras, etapas, obras y emisiones con documentos verificables
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-[#344054]">
              Sube documentos reales de obra para respaldar cálculos de emisiones, materiales, transporte, maquinaria, energía y residuos.
            </p>
            <p className="mt-3 rounded-2xl border border-[#E6CC82] bg-[var(--warning-bg)] p-3 text-sm font-semibold text-[#7A4F00]">
              {activeEmpresa?.nombre || activeEmpresaId} permanece como constructora activa. La evidencia se puede vincular a una obra, etapa o registro de emisión sin cambiar el flujo técnico existente.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <KpiImpact icon={<FileText size={22} />} label="Evidencias totales" value={formatNumber(kpis?.total_evidencias || 0, 0)} detail="Documentos de respaldo" tone="emerald" />
            <KpiImpact icon={<Link2 size={22} />} label="Evidencias vinculadas" value={formatNumber(totalVinculadas, 0)} detail="Relacionadas con registros" tone="cyan" />
            <KpiImpact icon={<Building2 size={22} />} label="Obras con respaldo" value={formatNumber(obrasConRespaldo, 0)} detail="Obras con evidencia asociada" tone="slate" />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiImpact icon={<FileCheck2 size={22} />} label="Cobertura documental" value={coverageValue} detail={coverageDetail} tone={cobertura >= 75 ? "emerald" : cobertura >= 40 ? "amber" : "rose"} />
        <KpiImpact icon={<ShieldAlert size={22} />} label="Evidencias pendientes" value={formatNumber(totalPendientes, 0)} detail="A la espera de revisión" tone="amber" />
        <KpiImpact icon={<Link2 size={22} />} label="Evidencias observadas" value={formatNumber(totalObservadas, 0)} detail="Requieren ajuste o respaldo" tone="rose" />
        <KpiImpact icon={<UploadCloud size={22} />} label="Tipos presentes" value={formatNumber(Object.keys(kpis?.por_tipo || {}).length, 0)} detail="Fuentes documentales" tone="cyan" />
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_14px_35px_var(--shadow)] sm:p-6">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_180px_180px_180px_auto]">
          <input
            className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-emerald-100"
            placeholder="Buscar documento, obra, etapa o registro"
            value={draftFilters.search}
            onChange={(event) => setDraftFilters((current) => ({ ...current, search: event.target.value }))}
          />
          <select className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" value={draftFilters.tipo} onChange={(event) => setDraftFilters((current) => ({ ...current, tipo: event.target.value }))}>
            <option value="">Tipo de evidencia</option>
            {constructionEvidenceTypeOptions.map(([tipo, label]) => <option key={tipo} value={tipo}>{label}</option>)}
          </select>
          <select className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" value={draftFilters.alcance} onChange={(event) => setDraftFilters((current) => ({ ...current, alcance: event.target.value }))}>
            <option value="">Vinculación</option>
            {constructionEvidenceScopeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" value={draftFilters.estado_sistema} onChange={(event) => setDraftFilters((current) => ({ ...current, estado_sistema: event.target.value }))}>
            <option value="">Estado documental</option>
            <option value="corporativa">Sin vínculo</option>
            <option value="vinculada">Vinculada</option>
            <option value="sin_vinculo">Sin vínculo</option>
          </select>
          <div className="flex gap-2">
            <button type="button" onClick={onApplyFilters} className="rounded-2xl border border-[var(--primary-dark)] bg-[var(--primary-dark)] px-4 py-3 text-sm font-bold text-white">Aplicar</button>
            <button type="button" onClick={onClearFilters} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-bold text-[#475467]">Limpiar</button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <form onSubmit={onSubmit} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_18px_45px_var(--shadow)] sm:p-6">
          <div className="mb-5">
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--primary-dark)]">Nuevo respaldo</p>
            <h2 className="mt-1 text-xl font-semibold text-[var(--text-main)]">Subir evidencia</h2>
            <p className="mt-2 text-sm text-[var(--text-muted)]">{selectedScope.helper}</p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" placeholder="Nombre de la evidencia" value={form.nombre} onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))} />
            <select className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" value={form.tipo_documento} onChange={(event) => setForm((current) => ({ ...current, tipo_documento: event.target.value }))}>
              {constructionEvidenceTypeOptions.map(([tipo, label]) => <option key={tipo} value={tipo}>{label}</option>)}
            </select>
            <label className="md:col-span-2">
              <span className="mb-1 block text-sm font-semibold text-[#344054]">Vincular evidencia a</span>
              <select className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" value={form.alcance} onChange={(event) => updateScope(event.target.value)}>
                {constructionEvidenceScopeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            {form.alcance === "unidad" && <input className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] md:col-span-2" placeholder="Etapa / frente" value={form.unidad_id} onChange={(event) => setForm((current) => ({ ...current, unidad_id: event.target.value }))} />}
            {form.alcance === "lote" && <input className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] md:col-span-2" placeholder="Obra asociada" value={form.lote_id} onChange={(event) => setForm((current) => ({ ...current, lote_id: event.target.value }))} />}
            {form.alcance === "emision" && <input className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] md:col-span-2" placeholder="Registro de emisión asociado" value={form.emision_id} onChange={(event) => setForm((current) => ({ ...current, emision_id: event.target.value }))} />}
            {form.alcance === "transporte" && <input className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] md:col-span-2" placeholder="Obra asociada opcional" value={form.lote_id} onChange={(event) => setForm((current) => ({ ...current, lote_id: event.target.value }))} />}
            <input type="date" className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]" value={form.fecha_documento} onChange={(event) => setForm((current) => ({ ...current, fecha_documento: event.target.value }))} />
            <input type="file" className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] file:mr-4 file:rounded-xl file:border-0 file:bg-[var(--success-bg)] file:px-3 file:py-2 file:font-bold file:text-[var(--primary-dark)]" onChange={(event) => setForm((current) => ({ ...current, archivo: event.target.files?.[0] || null }))} />
            <textarea className="min-h-24 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] md:col-span-2" placeholder="Observaciones" value={form.observaciones} onChange={(event) => setForm((current) => ({ ...current, observaciones: event.target.value }))} />
          </div>

          {error ? <p className="mt-4 rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm text-[#B42318]">{error}</p> : null}

          <div className="mt-5 flex flex-wrap gap-3">
            <button type="submit" disabled={saving} className="rounded-2xl border border-[var(--primary-dark)] bg-[var(--primary-dark)] px-5 py-3 text-sm font-bold text-white disabled:opacity-60">{saving ? "Guardando..." : "Subir evidencia"}</button>
            <button type="button" onClick={() => setForm(emptyForm)} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-3 text-sm font-bold text-[#475467]">Limpiar formulario</button>
          </div>
        </form>

        <section className="rounded-3xl border border-[#B9D8D3] bg-[var(--info-bg)] p-4 shadow-[0_18px_45px_var(--shadow)] sm:p-6">
          <h2 className="text-xl font-semibold text-[var(--text-main)]">Alcances disponibles</h2>
          <div className="mt-4 space-y-3">
            {alcanceOptions.map((option) => (
              <div key={option.value} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-sm">
                <p className="font-semibold text-[#075985]">{option.label}</p>
                <p className="mt-1 text-sm text-[var(--text-muted)]">{option.helper}</p>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-main)]">Evidencias registradas</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Mostrando {visibleRows.length} de {evidencias.length} evidencias.</p>
          </div>
          {loading ? <p className="text-sm font-semibold text-[var(--primary-dark)]">Cargando...</p> : null}
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-[1500px] w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--text-muted)]">
                <th className="px-3 py-3">Documento</th>
                <th className="px-3 py-3">Tipo de evidencia</th>
                <th className="px-3 py-3">Obra asociada</th>
                <th className="px-3 py-3">Etapa / frente</th>
                <th className="px-3 py-3">Registro asociado</th>
                <th className="px-3 py-3">Fecha documento</th>
                <th className="px-3 py-3">Estado documental</th>
                <th className="px-3 py-3">Archivo</th>
                <th className="px-3 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((item) => (
                <tr key={item.id} className="border-b border-[#C9D6CF] text-[#1F2937] hover:bg-[var(--bg-surface)]">
                  <td className="px-3 py-3 font-semibold text-[var(--text-main)]">{item.nombre}</td>
                  <td className="px-3 py-3 text-[#475467]">
                    {formatEvidenceType(item.tipo_documento)}
                  </td>
                  <td className="px-3 py-3">
                    <div className="space-y-1">
                      <p className="font-semibold text-[var(--text-main)]">{item.lote_codigo || item.empresa_codigo || "Obra asociada"}</p>
                      <p className="text-xs text-[var(--text-muted)]">{getConstructionEvidenceScopeLabel(item.alcance)}</p>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-[#475467]">{item.unidad_codigo || item.unidad_nombre || "Sin etapa"}</td>
                  <td className="px-3 py-3 text-[#475467]">
                    {item.emision ? `Registro ${item.emision}` : item.estado_sistema === "sin_vinculo" ? "Pendiente de vinculación" : getConstructionEvidenceLinkLabel(item.estado_sistema)}
                  </td>
                  <td className="px-3 py-3 text-[#475467]">{item.fecha_documento || "-"}</td>
                  <td className="px-3 py-3">
                    <div className="space-y-2">
                      <RevisionBadge label={getConstructionEvidenceReviewLabel(item.estado_revision || item.estado)} value={item.estado_revision || item.estado} />
                      <EvidenceBadge value={item.estado_sistema} />
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    {item.archivo_url ? <a className="font-semibold text-[#00689B] underline" href={item.archivo_url} target="_blank" rel="noreferrer">Ver</a> : <span className="text-[var(--text-muted)]">-</span>}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      {item.archivo_url ? <a className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1 text-xs font-bold text-[#475467]" href={item.archivo_url} target="_blank" rel="noreferrer">Ver</a> : null}
                      {item.archivo_url ? <a className="rounded-full border border-[var(--primary-dark)] bg-[var(--success-bg)] px-3 py-1 text-xs font-bold text-[var(--primary-dark)]" href={item.archivo_url} download>Descargar</a> : null}
                      {item.archivo_url ? <button type="button" onClick={() => openImportModal(item)} className="rounded-full border border-[#B7DEC9] bg-[var(--success-bg)] px-3 py-1 text-xs font-bold text-[var(--primary-dark)]">Analizar documento</button> : null}
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && visibleRows.length === 0 ? (
                <tr>
                  <td className="px-3 py-8 text-center text-[var(--text-muted)]" colSpan={9}>
                    No hay evidencias documentales.
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

        <ImportarDocumentoObraModal
          activeEmpresaId={activeEmpresaId}
          archivoNombre={importModalContext?.archivoNombre || ""}
          archivoUrl={importModalContext?.archivoUrl || ""}
          initialLoteId={importModalContext?.initialLoteId || ""}
          onClose={() => {
            setImportModalOpen(false);
            setImportModalContext(null);
          }}
          open={importModalOpen}
        />
      </section>
    </main>
  );
}

export default EvidenciasPage;
