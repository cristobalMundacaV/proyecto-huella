import { useState, useRef } from "react";
import { Building2, Loader2, Upload, Save } from "lucide-react";
import { previewEmpresaCompleta, confirmarEmpresaCompleta } from "@/shared/services/api";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";
import Toast from "@/shared/components/Toast";

function RowsPreviewTable({ rows }) {
  const visible = (rows || []).slice(0, 8);
  if (!visible.length) return <p className="text-sm text-slate-400">No hay filas para mostrar.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-slate-800 text-slate-400">
          <tr>
            <th className="px-2 py-2 text-left">Fila</th>
            <th className="px-3 py-2 text-left">Estado</th>
            <th className="px-3 py-2 text-left">Clave</th>
            <th className="px-3 py-2 text-left">Observaciones</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((r, idx) => (
            <tr key={idx} className="border-b border-slate-800/60">
              <td className="px-2 py-3 text-slate-300">{r.row_number ?? idx + 1}</td>
              <td className="px-3 py-3 text-slate-300">{r.status}</td>
              <td className="px-3 py-3 text-slate-300">{JSON.stringify(r.data || {})}</td>
              <td className="px-3 py-3 text-sm text-red-300">{(r.errors || []).join("; ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function EmpresaCompletaImport({ onImported }) {
  const [state, setState] = useState({
    loading: false,
    result: null,
    error: "",
    saving: false,
    savedMessage: "",
  });
  const inputRef = useRef(null);
  const { setActiveEmpresa } = useEmpresaActiva();
  const [toast, setToast] = useState(null);

  const showToast = (message) => setToast({ id: Date.now(), message });

  const onFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setState((s) => ({ ...s, loading: true, error: "", result: null }));

    try {
      const preview = await previewEmpresaCompleta(file);
      setState((s) => ({ ...s, loading: false, result: preview }));
    } catch (err) {
      const resp = err.response?.data || {};
      // If partial preview included
      if (resp.result || resp.unidades || resp.lotes) {
        setState((s) => ({ ...s, loading: false, result: resp, error: resp.error || resp.detail }));
      } else {
        setState((s) => ({ ...s, loading: false, error: resp.error || resp.detail || "No se pudo previsualizar el archivo." }));
      }
    } finally {
      if (event.target) event.target.value = "";
    }
  };

  const confirm = async () => {
    if (!state.result?.batch_id) {
      setState((s) => ({ ...s, error: "Falta batch_id para confirmar la importación." }));
      return;
    }

    setState((s) => ({ ...s, saving: true, error: "" }));
    try {
      const res = await confirmarEmpresaCompleta({ batch_id: state.result.batch_id });
      const created = res.creados ?? res.created ?? 0;
      const msg = `Importación completa: ${created} creadas.`;
      setState((s) => ({ ...s, saving: false, savedMessage: msg }));
      showToast(msg);

      // If backend returns the created empresa object, set it active
      if (res.empresa) {
        setActiveEmpresa(res.empresa);
      } else if (res.empresa_id) {
        setActiveEmpresa({ id: res.empresa_id, nombre: res.empresa_nombre || "" });
      }

      onImported?.(res);
    } catch (err) {
      const resp = err.response?.data || {};
      setState((s) => ({ ...s, saving: false, error: resp.error || resp.detail || "Error al confirmar importación." }));
    }
  };

  const blocking = (state.result?.blocking_errors || []).length > 0;
  const sectionErrors =
    (state.result?.unidades?.errores || 0) +
    (state.result?.lotes?.errores || 0) +
    (state.result?.actividades?.errores || 0) +
    (state.result?.factores?.errores || 0);

  return (
    <div>
      <Toast message={toast?.message} onClose={() => setToast(null)} toastKey={toast?.id} />

      <label className="inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm font-bold text-emerald-200 hover:bg-emerald-400/20">
        <Upload size={16} />
        Importar empresa completa
        <input ref={inputRef} type="file" accept=".xlsx" onChange={onFile} className="hidden" />
      </label>
      <p className="mt-2 text-xs text-slate-500">
        Empresa: ID Empresa, Nombre, RUT, Región, Comuna, Dirección, Rubro, Email, Teléfono, Contacto, Observaciones; Factores: Actividad, Unidad, Factor de Emisión, Fuente, Año, Categoría, Activity key, Descripción; Unidades: ID Unidad, Nombre, Tipo, Región, Comuna, Dirección, Descripción, Activa; Lotes: ID Lote, ID Empresa, ID Unidad, Empresa, Fecha, Especie, Volumen (m³), Origen, Tipo producto, Densidad kg/m3, Porcentaje carbono, Estado, Observaciones; Actividades: ID Empresa, ID Unidad, ID Lote, Actividad, Cantidad, Unidad, Fecha.
      </p>

      {state.loading && (
        <div className="mt-3 text-sm text-slate-400 inline-flex items-center gap-2">
          <Loader2 className="animate-spin" /> Procesando previsualización...
        </div>
      )}

      {state.error && (
        <p className="mt-3 text-sm text-red-300">{state.error}</p>
      )}

      {state.result && (
        <div className="mt-4 space-y-4">
          <div className="rounded-2xl border bg-slate-950 p-4">
            <h3 className="text-lg font-semibold">Resumen</h3>
            <p className="text-sm text-slate-400 mt-2">Empresa: {state.result.empresa?.data?.nombre || "(sin datos)"}</p>
            <p className="text-sm text-slate-400">Unidades: {state.result.unidades?.total ?? 0} — Lotes: {state.result.lotes?.total ?? 0} — Actividades: {state.result.actividades?.total ?? 0}</p>
            {state.result.blocking_errors && state.result.blocking_errors.length > 0 && (
              <div className="mt-2 text-sm text-red-300">Errores bloqueantes: {state.result.blocking_errors.join("; ")}</div>
            )}
          </div>

          {/* Sections previews: empresa, unidades, lotes, actividades, factores */}
          {state.result.empresa && (
            <div className="rounded-2xl border bg-slate-950 p-4">
              <h4 className="font-semibold">Empresa</h4>
              <pre className="text-xs text-slate-300 mt-2">{JSON.stringify(state.result.empresa.data, null, 2)}</pre>
            </div>
          )}

          {state.result.unidades && (
            <div className="rounded-2xl border bg-slate-950 p-4">
              <h4 className="font-semibold">Unidades</h4>
              <RowsPreviewTable rows={state.result.unidades.rows || []} />
            </div>
          )}

          {state.result.lotes && (
            <div className="rounded-2xl border bg-slate-950 p-4">
              <h4 className="font-semibold">Lotes</h4>
              <RowsPreviewTable rows={state.result.lotes.rows || []} />
            </div>
          )}

          {state.result.actividades && (
            <div className="rounded-2xl border bg-slate-950 p-4">
              <h4 className="font-semibold">Actividades</h4>
              <RowsPreviewTable rows={state.result.actividades.rows || []} />
            </div>
          )}

          {state.result.factores && (
            <div className="rounded-2xl border bg-slate-950 p-4">
              <h4 className="font-semibold">Factores</h4>
              <RowsPreviewTable rows={state.result.factores.rows || []} />
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={confirm}
              disabled={blocking || sectionErrors > 0 || state.saving}
              className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm font-bold text-emerald-200 disabled:opacity-60"
            >
              {state.saving ? <Loader2 className="animate-spin" /> : <Save size={16} />} Confirmar importación completa
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
