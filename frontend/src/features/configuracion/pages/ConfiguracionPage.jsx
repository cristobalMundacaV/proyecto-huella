import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getOrganizacionConfiguracion, updateOrganizacionConfiguracion } from "@/shared/services/api";
import { Alert, Button, Card, CardContent, EmptyState, ErrorState, Input, LoadingState, PageHeader, Select } from "@/shared/ui";

const EDITABLE_FIELDS = [
  "modo_importacion",
  "crear_etapas_automaticamente",
  "crear_obras_automaticamente",
  "permitir_registros_sin_factor",
  "actualizar_registros_existentes",
  "bloquear_duplicados",
  "requerir_etapa_obra",
  "requerir_obra_registro",
  "permitir_evidencias_sin_vinculo",
  "evidencia_obligatoria",
  "formatos_evidencia_permitidos",
  "max_file_size_mb",
  "reporte_agrupacion_default",
  "reporte_periodo_default",
  "reporte_mostrar_categoria",
  "reporte_mostrar_etapa",
  "reporte_mostrar_tabla",
  "reporte_unidad_visual_emisiones",
  "reporte_lectura_ejecutiva",
  "reporte_equivalencias",
];
const SUGGESTED = {
  modo_importacion: "flexible",
  crear_etapas_automaticamente: true,
  crear_obras_automaticamente: true,
  permitir_registros_sin_factor: false,
  actualizar_registros_existentes: true,
  bloquear_duplicados: true,
  requerir_etapa_obra: false,
  requerir_obra_registro: true,
  permitir_evidencias_sin_vinculo: true,
  evidencia_obligatoria: false,
  formatos_evidencia_permitidos: ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"],
  max_file_size_mb: 10,
  reporte_agrupacion_default: "mes",
  reporte_periodo_default: "ultimos_12_meses",
  reporte_mostrar_categoria: true,
  reporte_mostrar_etapa: true,
  reporte_mostrar_tabla: true,
  reporte_unidad_visual_emisiones: "kg CO2e",
  reporte_lectura_ejecutiva: true,
  reporte_equivalencias: true,
};
const FORMATS = ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"];
const storageKey = (id) => `carbono_zero.configuracion.${id}`;
const pickEditable = (value = {}) => Object.fromEntries(EDITABLE_FIELDS.map((field) => [field, value[field]]));
const same = (a, b) => JSON.stringify(pickEditable(a)) === JSON.stringify(pickEditable(b));

export default function ConfiguracionPage() {
  const { user } = useAuth();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", status: "loading", data: null, saved: null, error: "", hasLocalCopy: false });
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState({ type: "", text: "" });
  const requestRef = useRef(0);
  const activeScopeRef = useRef(activeOrganizacionId);
  activeScopeRef.current = activeOrganizacionId;

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const scopeKey = String(activeOrganizacionId);
    const requestId = ++requestRef.current;
    setState({ scopeKey, status: "loading", data: null, saved: null, error: "", hasLocalCopy: false });
    setFeedback({ type: "", text: "" });

    getOrganizacionConfiguracion(activeOrganizacionId)
      .then((remote) => {
        if (requestRef.current !== requestId) return;
        setState({ scopeKey, status: "ready", data: remote, saved: remote, error: "", hasLocalCopy: false });
        try { window.localStorage.setItem(storageKey(activeOrganizacionId), JSON.stringify(remote)); } catch { /* copia local opcional */ }
      })
      .catch(() => {
        if (requestRef.current !== requestId) return;
        let hasLocalCopy = false;
        try { hasLocalCopy = Boolean(window.localStorage.getItem(storageKey(activeOrganizacionId))); } catch { hasLocalCopy = false; }
        setState({ scopeKey, status: "error", data: null, saved: null, error: "No se pudieron verificar las preferencias de esta organización.", hasLocalCopy });
      });

    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId]);

  const scopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  const update = (field, value) => setState((current) => current.status === "ready" ? { ...current, data: { ...current.data, [field]: value } } : current);
  const dirty = state.status === "ready" && !same(state.data, state.saved);

  async function save() {
    if (!dirty || !activeOrganizacionId || user?.is_demo) return;
    const organizationId = activeOrganizacionId;
    setSaving(true);
    setFeedback({ type: "", text: "" });
    try {
      const payload = pickEditable(state.data);
      const remote = await updateOrganizacionConfiguracion(organizationId, payload);
      if (String(activeScopeRef.current) !== String(organizationId)) return;
      setState((current) => ({ ...current, status: "ready", data: remote, saved: remote, error: "", hasLocalCopy: false }));
      try { window.localStorage.setItem(storageKey(organizationId), JSON.stringify(remote)); } catch { /* copia local opcional */ }
      setFeedback({ type: "success", text: "Preferencias guardadas." });
    } catch (error) {
      setFeedback({ type: "danger", text: error.response?.data?.error || "No se pudieron guardar las preferencias." });
    } finally {
      setSaving(false);
    }
  }

  function loadSuggested() {
    if (state.status !== "ready" || user?.is_demo) return;
    setState((current) => ({ ...current, data: { ...current.data, ...SUGGESTED } }));
    setFeedback({ type: "", text: "" });
  }

  if (!activeOrganizacionId) return <EmptyState title="Sin organización activa" description="Selecciona una organización antes de administrar preferencias." />;
  if (state.scopeKey !== scopeKey || state.status === "loading") return <LoadingState label="Cargando preferencias" />;

  return (
    <main className="space-y-7">
      <PageHeader
        eyebrow="Administración · Preferencias"
        title="Preferencias"
        description="Configura opciones de funcionamiento para importación, documentos y reportes."
        metadata={activeOrganizacion?.nombre || undefined}
      />

      <aside className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-4 text-sm text-[var(--text-muted)]">
        Factores y metodologías se gestionan desde <Link className="font-bold text-[var(--brand-primary)]" to="/gobernanza/factores">Gobernanza</Link>.
      </aside>

      {user?.is_demo && <Alert title="Solo lectura en modo demo">Las preferencias pueden revisarse, pero no modificarse.</Alert>}
      {feedback.text && <Alert tone={feedback.type === "danger" ? "danger" : "success"}>{feedback.text}</Alert>}

      {state.status === "error" ? (
        <div className="space-y-3">
          <ErrorState description={state.error} />
          {state.hasLocalCopy && <Alert title="Existe una copia local no confirmada">No se usa para mostrar valores vigentes ni para guardar cambios mientras la configuración de la organización no pueda verificarse.</Alert>}
        </div>
      ) : (
        <>
          {dirty && <Alert title="Hay cambios sin guardar">Los cambios permanecen en esta pantalla hasta que los guardes o cambies de organización.</Alert>}

          <section className="grid gap-4 xl:grid-cols-3">
            <PreferenceSection title="Importación" description="Opciones que cambian cómo se reciben y organizan los datos.">
              <Select label="Modo de importación" value={state.data.modo_importacion || "flexible"} onChange={(event) => update("modo_importacion", event.target.value)} disabled={user?.is_demo}>
                <option value="flexible">Flexible</option><option value="estricto">Estricto</option>
              </Select>
              <Toggle label="Crear etapas automáticamente" checked={state.data.crear_etapas_automaticamente} onChange={(value) => update("crear_etapas_automaticamente", value)} disabled={user?.is_demo} />
              <Toggle label="Crear obras automáticamente" checked={state.data.crear_obras_automaticamente} onChange={(value) => update("crear_obras_automaticamente", value)} disabled={user?.is_demo} />
              <Toggle label="Bloquear duplicados" checked={state.data.bloquear_duplicados} onChange={(value) => update("bloquear_duplicados", value)} disabled={user?.is_demo} />
              <Toggle label="Actualizar registros existentes" checked={state.data.actualizar_registros_existentes} onChange={(value) => update("actualizar_registros_existentes", value)} disabled={user?.is_demo} />
              <Toggle label="Requerir obra para cada registro" checked={state.data.requerir_obra_registro} onChange={(value) => update("requerir_obra_registro", value)} disabled={user?.is_demo} />
              <Toggle label="Requerir etapa de obra" checked={state.data.requerir_etapa_obra} onChange={(value) => update("requerir_etapa_obra", value)} disabled={user?.is_demo} />
              <Toggle label="Permitir datos pendientes de completar" description="Permite registrar información todavía sin factor para revisión posterior; no representa un cálculo confirmado." checked={state.data.permitir_registros_sin_factor} onChange={(value) => update("permitir_registros_sin_factor", value)} disabled={user?.is_demo} />
            </PreferenceSection>

            <PreferenceSection title="Documentos" description="Límites y requisitos administrativos de los archivos de respaldo.">
              <Toggle label="Evidencia obligatoria" checked={state.data.evidencia_obligatoria} onChange={(value) => update("evidencia_obligatoria", value)} disabled={user?.is_demo} />
              <Toggle label="Permitir evidencias sin vincular" checked={state.data.permitir_evidencias_sin_vinculo} onChange={(value) => update("permitir_evidencias_sin_vinculo", value)} disabled={user?.is_demo} />
              <Input label="Tamaño máximo por archivo (MB)" type="number" min="1" value={state.data.max_file_size_mb ?? ""} onChange={(event) => update("max_file_size_mb", Number(event.target.value))} disabled={user?.is_demo} />
              <fieldset className="space-y-2"><legend className="text-sm font-bold">Formatos permitidos</legend><div className="flex flex-wrap gap-2">{FORMATS.map((format) => {
                const selected = Array.isArray(state.data.formatos_evidencia_permitidos) && state.data.formatos_evidencia_permitidos.includes(format);
                return <label key={format} className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] px-3 py-2 text-sm"><input type="checkbox" checked={selected} disabled={user?.is_demo} onChange={(event) => { const current = Array.isArray(state.data.formatos_evidencia_permitidos) ? state.data.formatos_evidencia_permitidos : []; update("formatos_evidencia_permitidos", event.target.checked ? [...new Set([...current, format])] : current.filter((value) => value !== format)); }} />{format}</label>;
              })}</div></fieldset>
            </PreferenceSection>

            <PreferenceSection title="Reportes" description="Preferencias de presentación; no cambian factores ni metodologías.">
              <Select label="Agrupación predeterminada" value={state.data.reporte_agrupacion_default || "mes"} onChange={(event) => update("reporte_agrupacion_default", event.target.value)} disabled={user?.is_demo}>
                <option value="dia">Día</option><option value="semana">Semana</option><option value="mes">Mes</option><option value="trimestre">Trimestre</option><option value="anio">Año</option>
              </Select>
              <Select label="Periodo predeterminado" value={state.data.reporte_periodo_default || "ultimos_12_meses"} onChange={(event) => update("reporte_periodo_default", event.target.value)} disabled={user?.is_demo}>
                <option value="ultimos_30_dias">Últimos 30 días</option><option value="ultimos_3_meses">Últimos 3 meses</option><option value="ultimos_6_meses">Últimos 6 meses</option><option value="ultimos_12_meses">Últimos 12 meses</option><option value="anio_actual">Año actual</option>
              </Select>
              <Input label="Unidad visual de emisiones" value={state.data.reporte_unidad_visual_emisiones || ""} onChange={(event) => update("reporte_unidad_visual_emisiones", event.target.value)} disabled={user?.is_demo} />
              <Toggle label="Mostrar categoría" checked={state.data.reporte_mostrar_categoria} onChange={(value) => update("reporte_mostrar_categoria", value)} disabled={user?.is_demo} />
              <Toggle label="Mostrar etapa" checked={state.data.reporte_mostrar_etapa} onChange={(value) => update("reporte_mostrar_etapa", value)} disabled={user?.is_demo} />
              <Toggle label="Mostrar tabla" checked={state.data.reporte_mostrar_tabla} onChange={(value) => update("reporte_mostrar_tabla", value)} disabled={user?.is_demo} />
              <Toggle label="Lectura ejecutiva" checked={state.data.reporte_lectura_ejecutiva} onChange={(value) => update("reporte_lectura_ejecutiva", value)} disabled={user?.is_demo} />
              <Toggle label="Mostrar equivalencias" checked={state.data.reporte_equivalencias} onChange={(value) => update("reporte_equivalencias", value)} disabled={user?.is_demo} />
            </PreferenceSection>
          </section>

          {!user?.is_demo && <div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={loadSuggested}>Cargar valores sugeridos</Button><Button loading={saving} disabled={!dirty} onClick={save}>Guardar preferencias</Button></div>}
        </>
      )}
    </main>
  );
}

function PreferenceSection({ title, description, children }) {
  return <Card><CardContent><h2 className="text-lg font-black">{title}</h2><p className="mt-1 text-sm text-[var(--text-muted)]">{description}</p><div className="mt-5 space-y-4">{children}</div></CardContent></Card>;
}

function Toggle({ label, description = "", checked, onChange, disabled }) {
  return <label className="flex items-start gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] p-3"><input className="mt-1" type="checkbox" checked={Boolean(checked)} disabled={disabled} onChange={(event) => onChange(event.target.checked)} /><span><b className="text-sm">{label}</b>{description && <span className="mt-1 block text-xs leading-5 text-[var(--text-muted)]">{description}</span>}</span></label>;
}
