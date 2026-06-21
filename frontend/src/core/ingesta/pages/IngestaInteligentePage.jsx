import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, CheckCircle2, FileSearch, Link2, Plus, X } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import CriticalDocumentsPanel from "@/core/environmental/components/CriticalDocumentsPanel";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalItemGrid from "@/core/environmental/components/EnvironmentalItemGrid";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import {
  createEnvironmentalDocument,
  getEnvironmentalDocuments,
} from "@/features/environmental/services/environmentalComplianceApi";

const initialForm = {
  tipo_documento: "",
  nombre: "",
  fecha_documento: "",
  fuente_origen: "manual",
  resumen: "",
};

function IngestaInteligentePage() {
  const { activeCompany, matrix } = useEnvironmentalContext();
  const [documents, setDocuments] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const suggestedTypes = useMemo(() => matrix.criticalDocuments || [], [matrix]);
  const readiness = useMemo(() => buildIngestionReadiness({ documents, matrix, suggestedTypes }), [documents, matrix, suggestedTypes]);

  const refreshDocuments = useCallback(() => {
    if (!activeCompany?.constructora_id) return;
    setLoading(true);
    setError("");
    getEnvironmentalDocuments(activeCompany.constructora_id)
      .then(setDocuments)
      .catch(() => setError("No se pudieron cargar los documentos ambientales."))
      .finally(() => setLoading(false));
  }, [activeCompany?.constructora_id]);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!activeCompany?.constructora_id) return;
    setSaving(true);
    setError("");
    try {
      await createEnvironmentalDocument(activeCompany.constructora_id, {
        ...form,
        tipo_documento: form.tipo_documento || suggestedTypes[0] || "otro",
        nombre: form.nombre || form.tipo_documento || "Documento ambiental",
        fecha_documento: form.fecha_documento || new Date().toISOString().slice(0, 10),
      });
      setForm(initialForm);
      setIsModalOpen(false);
      refreshDocuments();
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo registrar el documento.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Ingesta Inteligente"
      description="Vista base para preparar carga documental y variables esperadas por industria. No ejecuta OCR ni procesamiento automatico."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />

      <IngestionHero
        onRegister={() => {
          setForm({ ...initialForm, tipo_documento: readiness.nextDocument || suggestedTypes[0] || "" });
          setIsModalOpen(true);
        }}
        readiness={readiness}
      />

      <section className="grid gap-4 md:grid-cols-3">
        <ReadinessMetric icon={BarChart3} label="Cobertura documental" value={`${readiness.score}%`} detail={`${readiness.matchedCount} de ${readiness.totalExpected} respaldos esperados`} tone="cyan" />
        <ReadinessMetric icon={FileSearch} label="Siguiente carga" value={readiness.nextDocument || "Sin brecha critica"} detail={readiness.whyItMatters} tone="amber" />
        <ReadinessMetric icon={CheckCircle2} label="Desbloquea" value={readiness.unlocks} detail="Impacta informe, decisiones y cierre de evidencia." tone="emerald" />
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <CriticalDocumentsPanel matrix={matrix} />
        <EnvironmentalItemGrid
          icon={Activity}
          tone="emerald"
          title="Variables que debe capturar la ingesta"
          description="Campos necesarios para validar calidad de datos y habilitar calculo de indicadores."
          items={matrix.criticalVariables}
        />
      </div>

      <section className="rounded-[24px] border border-amber-200 bg-amber-50/70 p-5">
        <div className="flex items-start gap-3">
          <span className="rounded-xl border border-amber-200 bg-white p-2 text-amber-800">
            <FileSearch size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-amber-950">Validacion esperada</h2>
            <p className="mt-1 text-sm leading-6 text-amber-900">
              El documento debe permitir reconocer dato, periodo, fuente, unidad y evidencia asociada antes de cerrar el registro.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {["Dato requerido", "Riesgo controlado", "Accion siguiente"].map((item) => (
            <div key={item} className="rounded-xl border border-amber-100 bg-white/80 p-4">
              <div className="flex items-center gap-2 text-sm font-black text-amber-950">
                <Link2 size={16} />
                {item}
              </div>
              <p className="mt-2 text-sm text-amber-900">
                Debe quedar vinculado a documentos, variables y responsables del cierre ambiental.
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-black text-[var(--text-main)]">Documentos ambientales registrados</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              Documentos persistidos para validar variables, evidencia y obligaciones.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setForm({ ...initialForm, tipo_documento: suggestedTypes[0] || "" });
              setIsModalOpen(true);
            }}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-black text-emerald-800"
          >
            <Plus size={16} />
            Registrar documento
          </button>
        </div>

        {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">{error}</p>}

        <div className="mt-4 overflow-hidden rounded-xl border border-[var(--border)]">
          <div className="grid grid-cols-[1.2fr_1fr_0.8fr_0.8fr] gap-3 bg-[var(--bg-surface)] px-4 py-3 text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
            <span>Documento</span>
            <span>Tipo</span>
            <span>Procesamiento</span>
            <span>Validacion</span>
          </div>
          {loading && <p className="px-4 py-5 text-sm text-[var(--text-muted)]">Cargando documentos...</p>}
          {!loading && documents.length === 0 && <p className="px-4 py-5 text-sm text-[var(--text-muted)]">No hay documentos ambientales registrados.</p>}
          {!loading &&
            documents.map((document) => (
              <div key={document.id} className="grid grid-cols-[1.2fr_1fr_0.8fr_0.8fr] gap-3 border-t border-[var(--border)] px-4 py-3 text-sm">
                <div>
                  <p className="font-black text-[var(--text-main)]">{document.nombre}</p>
                  <p className="text-xs text-[var(--text-muted)]">{document.fecha_documento}</p>
                </div>
                <p className="font-semibold text-[var(--text-muted)]">{document.tipo_documento}</p>
                <StatusPill value={document.estado_procesamiento} />
                <StatusPill value={document.estado_validacion} />
              </div>
            ))}
        </div>
      </section>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 p-4 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="w-full max-w-xl rounded-2xl border border-[var(--border)] bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-black text-[var(--text-main)]">Registrar documento ambiental</h2>
                <p className="mt-1 text-sm text-[var(--text-muted)]">Registro manual para iniciar trazabilidad documental.</p>
              </div>
              <button type="button" onClick={() => setIsModalOpen(false)} className="rounded-xl border border-[var(--border)] p-2 text-[var(--text-muted)]">
                <X size={18} />
              </button>
            </div>

            <div className="mt-5 grid gap-4">
              <label className="text-sm font-bold text-[var(--text-main)]">
                Tipo de documento
                <select value={form.tipo_documento} onChange={(event) => setForm((current) => ({ ...current, tipo_documento: event.target.value }))} className="mt-2 w-full px-3 py-2">
                  {suggestedTypes.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                  <option value="otro">Otro</option>
                </select>
              </label>
              <label className="text-sm font-bold text-[var(--text-main)]">
                Nombre
                <input value={form.nombre} onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))} className="mt-2 w-full px-3 py-2" />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-bold text-[var(--text-main)]">
                  Fecha documento
                  <input type="date" value={form.fecha_documento} onChange={(event) => setForm((current) => ({ ...current, fecha_documento: event.target.value }))} className="mt-2 w-full px-3 py-2" />
                </label>
                <label className="text-sm font-bold text-[var(--text-main)]">
                  Fuente origen
                  <select value={form.fuente_origen} onChange={(event) => setForm((current) => ({ ...current, fuente_origen: event.target.value }))} className="mt-2 w-full px-3 py-2">
                    {["manual", "excel", "csv", "pdf", "foto", "cems", "laboratorio", "otro"].map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="text-sm font-bold text-[var(--text-main)]">
                Resumen
                <textarea value={form.resumen} onChange={(event) => setForm((current) => ({ ...current, resumen: event.target.value }))} rows={3} className="mt-2 w-full px-3 py-2" />
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-3">
              <button type="button" onClick={() => setIsModalOpen(false)} className="rounded-xl border border-[var(--border)] bg-white px-4 py-2 text-sm font-black text-[var(--text-muted)]">
                Cancelar
              </button>
              <button type="submit" disabled={saving} className="rounded-xl border border-emerald-200 bg-emerald-600 px-4 py-2 text-sm font-black text-white disabled:opacity-60">
                {saving ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </form>
        </div>
      )}
    </EnvironmentalShell>
  );
}

function IngestionHero({ onRegister, readiness }) {
  const tone = readiness.score >= 75 ? "emerald" : readiness.score >= 35 ? "amber" : "cyan";
  const toneClass = {
    emerald: "border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.95))]",
    amber: "border-amber-200 bg-[linear-gradient(135deg,rgba(255,251,235,0.98),rgba(255,255,255,0.95))]",
    cyan: "border-cyan-200 bg-[linear-gradient(135deg,rgba(236,254,255,0.98),rgba(255,255,255,0.95))]",
  }[tone];

  return (
    <section className={`rounded-[28px] border p-6 shadow-[0_24px_70px_rgba(15,23,42,0.10)] ${toneClass}`}>
      <div className="grid gap-6 lg:grid-cols-[1fr_230px] lg:items-center">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-cyan-700">Que debo cargar ahora</p>
          <h1 className="mt-3 text-3xl font-black leading-tight text-slate-950 sm:text-4xl">{readiness.status}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
            Siguiente carga recomendada: <strong>{readiness.nextDocument || "mantener documentos actualizados"}</strong>. {readiness.whyItMatters}
          </p>
          <div className="mt-5 rounded-2xl border border-white/70 bg-white/75 p-4">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Que desbloquea</p>
            <p className="mt-1 text-sm font-black text-slate-950">{readiness.unlocks}</p>
          </div>
        </div>
        <div className="rounded-3xl border border-white/70 bg-white/75 p-5 text-center shadow-sm">
          <p className="text-xs font-black uppercase tracking-wide text-slate-500">Score ingesta</p>
          <p className="mt-2 text-5xl font-black text-slate-950">{readiness.score}%</p>
          <button type="button" onClick={onRegister} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-4 py-3 text-sm font-black text-white">
            <Plus size={16} /> Registrar documento
          </button>
        </div>
      </div>
    </section>
  );
}

function ReadinessMetric({ detail, icon: Icon, label, tone, value }) {
  const toneClass = {
    cyan: "border-cyan-200 bg-cyan-50 text-cyan-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-900",
  }[tone];
  return (
    <article className={`rounded-2xl border p-5 ${toneClass}`}>
      <Icon size={20} />
      <p className="mt-3 text-xs font-black uppercase tracking-wide opacity-75">{label}</p>
      <p className="mt-1 line-clamp-2 text-2xl font-black">{value}</p>
      <p className="mt-2 line-clamp-3 text-sm font-semibold leading-6 opacity-80">{detail}</p>
    </article>
  );
}

function StatusPill({ value }) {
  const tone = value === "validado" || value === "valido" ? "bg-emerald-50 text-emerald-700" : value === "observado" || value === "rechazado" || value === "error" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700";
  return <span className={`w-fit rounded-full px-3 py-1 text-xs font-black uppercase ${tone}`}>{value || "pendiente"}</span>;
}

function buildIngestionReadiness({ documents, matrix, suggestedTypes }) {
  const normalizedDocs = documents.map((document) => normalizeText(`${document.nombre} ${document.tipo_documento}`));
  const matched = suggestedTypes.filter((type) => normalizedDocs.some((documentText) => documentText.includes(normalizeText(type).slice(0, 18)) || normalizeText(type).split(" ").some((part) => part.length > 4 && documentText.includes(part))));
  const totalExpected = suggestedTypes.length || matrix.criticalDocuments?.length || 1;
  const matchedCount = new Set(matched).size;
  const score = Math.min(100, Math.round((matchedCount / totalExpected) * 100));
  const missing = suggestedTypes.find((type) => !matched.includes(type));
  const status = score >= 75 ? "Ingesta lista para sostener decisiones" : score >= 35 ? "Ingesta util con brechas" : "Ingesta incompleta";
  const isConstruction = matrix?.key === "construccion";
  const nextDocument = missing || (isConstruction ? "Vale de pesaje RCD / certificado de disposicion final" : suggestedTypes[0]);
  return {
    score,
    status,
    nextDocument,
    matchedCount,
    totalExpected,
    whyItMatters: isConstruction
      ? "Falta respaldo para materiales, RCD, combustible o consumos que sostienen el reporte ambiental de obra."
      : "Falta respaldo documental para cerrar trazabilidad, variables ambientales e informe ejecutivo.",
    unlocks: isConstruction ? "Informe mensual de obra, decisiones priorizadas y cierre de brecha documental." : "Informe ejecutivo, KPIs ambientales y cierre de acciones con evidencia.",
  };
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export default IngestaInteligentePage;
