import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, FileSearch, Link2, Plus, X } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import CriticalDocumentsPanel from "@/core/environmental/components/CriticalDocumentsPanel";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalIngestionReadinessPanel from "@/core/environmental/components/EnvironmentalIngestionReadinessPanel";
import EnvironmentalItemGrid from "@/core/environmental/components/EnvironmentalItemGrid";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import {
  createEnvironmentalDocument,
  getEnvironmentalDocuments,
} from "@/features/environmental/services/environmentalComplianceApi";
import { getEnvironmentalIngestionReadiness } from "@/features/environmental/services/environmentalIngestionReadinessApi";

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
  const [readiness, setReadiness] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const suggestedTypes = useMemo(() => matrix.criticalDocuments || [], [matrix]);

  const refreshDocuments = useCallback(() => {
    if (!activeCompany?.constructora_id) return;
    setLoading(true);
    setError("");
    Promise.allSettled([
      getEnvironmentalDocuments(activeCompany.constructora_id),
      getEnvironmentalIngestionReadiness(activeCompany.constructora_id),
    ])
      .then(([documentsResult, readinessResult]) => {
        if (documentsResult.status === "fulfilled") setDocuments(documentsResult.value);
        else setDocuments([]);
        if (readinessResult.status === "fulfilled") setReadiness(readinessResult.value);
        else setReadiness(null);
        if (documentsResult.status === "rejected" && readinessResult.status === "rejected") {
          setError("No se pudieron cargar los documentos ambientales.");
        }
      })
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
      <EnvironmentalIngestionReadinessPanel readiness={readiness} />

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

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="rounded-xl border border-amber-200 bg-amber-50 p-2 text-amber-800">
            <FileSearch size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-[var(--text-main)]">Validacion esperada</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              El documento debe permitir reconocer dato, periodo, fuente, unidad y evidencia asociada antes de cerrar el registro.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {["Dato requerido", "Riesgo controlado", "Accion siguiente"].map((item) => (
            <div key={item} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <div className="flex items-center gap-2 text-sm font-black text-[var(--text-main)]">
                <Link2 size={16} />
                {item}
              </div>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Debe quedar vinculado a documentos, variables y responsables del cierre ambiental.
              </p>
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

function StatusPill({ value }) {
  const tone = value === "validado" || value === "valido" ? "bg-emerald-50 text-emerald-700" : value === "observado" || value === "rechazado" || value === "error" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700";
  return <span className={`w-fit rounded-full px-3 py-1 text-xs font-black uppercase ${tone}`}>{value || "pendiente"}</span>;
}

export default IngestaInteligentePage;
