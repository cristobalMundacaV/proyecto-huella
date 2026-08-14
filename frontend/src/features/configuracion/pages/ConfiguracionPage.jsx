import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  Calculator,
  Edit3,
  FileCheck2,
  FileText,
  Gauge,
  RotateCcw,
  Save,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  UploadCloud,
  X,
} from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import CapacidadesAmbientales from "@/features/diagnostico/components/CapacidadesAmbientales";
import { useDiagnostico } from "@/features/diagnostico/hooks/useDiagnostico";
import MethodologiesPanel from "../components/MethodologiesPanel";
import {
  getOrganizacionConfiguracion,
  updateOrganizacionConfiguracion,
} from "@/shared/services/api";

const tabs = [
  { value: "organizacion", label: "Empresa", icon: Building2 },
  { value: "calculo", label: "Cálculo", icon: Calculator },
  { value: "importaciones", label: "Importación", icon: UploadCloud },
  { value: "ficha_ambiental", label: "Ficha ambiental", icon: ShieldCheck },
  { value: "evidencias", label: "Evidencias", icon: FileCheck2 },
  { value: "reportes", label: "Reportes", icon: FileText },
];

const sectionCopy = {
  organizacion: {
    title: "Datos de empresa",
    description: "Información base de la empresa activa. El ID interno queda protegido para no romper relaciones con registros, evidencias y procesos.",
  },
  calculo: {
    title: "Reglas de cálculo",
    description: "Parámetros que afectan resultados, unidades, redondeo y balance ambiental.",
  },
  importaciones: {
    title: "Reglas de importación",
    description: "Define cómo se comporta el sistema al cargar archivos, crear relaciones y bloquear duplicados.",
  },
  ficha_ambiental: {
    title: "Criterios de ficha ambiental",
    description: "Condiciones mínimas para generar fichas verificables y confiables.",
  },
  evidencias: {
    title: "Control documental",
    description: "Reglas de evidencia, formatos permitidos, vínculos y tamaño máximo de archivo.",
  },
  reportes: {
    title: "Reportes ejecutivos",
    description: "Preferencias para periodo, agrupación, visualización y lectura ejecutiva.",
  },
};

const defaultConfig = {
  organizacion: {
    nombre: "",
    organizacion_id: "",
    rut: "",
    rubro: "Construcción",
    region: "",
    comuna: "",
    direccion: "",
    contacto: "",
    email: "",
    telefono: "",
    observaciones: "",
  },
  calculo: {
    unidad_emisiones: "kg CO2e",
    unidad_base_obra: "m2",
    porcentaje_carbono_default: 50,
    densidad_material_default: 420,
    factor_electrico_default: "Factor eléctrico vigente",
    region_electrica_default: "Biobío",
    redondeo_decimales: 1,
    mostrar_balance_neto: true,
    permitir_balance_ambiental: true,
  },
  importaciones: {
    modo_importacion: "flexible",
    crear_etapas_automaticamente: true,
    crear_obras_automaticamente: true,
    permitir_registros_emision_sin_factor: false,
    actualizar_registros_existentes: true,
    bloquear_duplicados: true,
    requerir_unidad_obra: false,
    requerir_obra_fuente_emision: false,
    permitir_evidencias_sin_vinculo: true,
  },
  ficha_ambiental: {
    ficha_ambiental_activo: true,
    requiere_balance_favorable: true,
    requiere_evidencia: true,
    requiere_trazabilidad: true,
    score_verde: 70,
    score_plus: 90,
    score_confianza_minimo: 75,
  },
  evidencias: {
    requerida_ficha_ambiental: true,
    requerida_obras_criticos: true,
    umbral_obra_critico: 1000,
    permitir_organizacion: true,
    permitir_unidad: true,
    permitir_obra: true,
    permitir_emision: true,
    formatos_permitidos: ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"],
    max_file_size_mb: 10,
  },
  reportes: {
    agrupacion_default: "mes",
    periodo_default: "ultimos_12_meses",
    mostrar_categoria: true,
    mostrar_unidad: true,
    mostrar_tabla: true,
    unidad_visual_emisiones: "kg CO2e",
    lectura_ejecutiva: true,
    equivalencias: true,
  },
};

const fieldLabels = {
  nombre: "Nombre",
  organizacion_id: "ID empresa",
  rut: "RUT",
  rubro: "Rubro",
  region: "Región",
  comuna: "Comuna",
  direccion: "Dirección",
  contacto: "Contacto",
  email: "Email",
  telefono: "Teléfono",
  observaciones: "Observaciones",
  unidad_emisiones: "Unidad de emisiones",
  unidad_base_obra: "Unidad base",
  porcentaje_carbono_default: "Carbono por defecto",
  densidad_material_default: "Densidad material kg/m³",
  factor_electrico_default: "Factor eléctrico preferido",
  region_electrica_default: "Región eléctrica",
  redondeo_decimales: "Redondeo de resultados",
  mostrar_balance_neto: "Mostrar balance neto",
  permitir_balance_ambiental: "Permitir balance ambiental",
  modo_importacion: "Modo de importación",
  crear_etapas_automaticamente: "Crear etapas automáticamente",
  crear_obras_automaticamente: "Crear obras automáticamente",
  permitir_registros_emision_sin_factor: "Permitir registros sin factor",
  actualizar_registros_existentes: "Actualizar registros existentes",
  bloquear_duplicados: "Bloquear duplicados",
  requerir_unidad_obra: "Requerir etapa/unidad",
  requerir_obra_fuente_emision: "Requerir obra para registros",
  permitir_evidencias_sin_vinculo: "Permitir evidencias sin vínculo",
  ficha_ambiental_activo: "Activar ficha ambiental",
  requiere_balance_favorable: "Requerir balance favorable",
  requiere_evidencia: "Requerir evidencia",
  requiere_trazabilidad: "Requerir trazabilidad",
  score_verde: "Score mínimo base",
  score_plus: "Score mínimo plus",
  score_confianza_minimo: "Confianza mínima",
  requerida_ficha_ambiental: "Evidencia obligatoria para ficha",
  requerida_obras_criticos: "Evidencia en obras críticas",
  umbral_obra_critico: "Umbral obra crítica kg CO₂e",
  permitir_organizacion: "Permitir evidencia empresa",
  permitir_unidad: "Permitir evidencia unidad",
  permitir_obra: "Permitir evidencia obra",
  permitir_emision: "Permitir evidencia emisión",
  formatos_permitidos: "Formatos permitidos",
  max_file_size_mb: "Tamaño máximo MB",
  agrupacion_default: "Agrupación predeterminada",
  periodo_default: "Periodo predeterminado",
  mostrar_categoria: "Mostrar categoría",
  mostrar_unidad: "Mostrar unidad",
  mostrar_tabla: "Mostrar tabla",
  unidad_visual_emisiones: "Unidad visual",
  lectura_ejecutiva: "Lectura ejecutiva",
  equivalencias: "Mostrar equivalencias",
};

const fieldHelp = {
  permitir_registros_emision_sin_factor: "Si está activo, el sistema permitirá registros incompletos para revisión posterior.",
  bloquear_duplicados: "Evita que importaciones creen registros idénticos repetidos.",
  requiere_trazabilidad: "Exige vínculos con registros, evidencias o procesos para validar ficha ambiental.",
  formatos_permitidos: "Controla qué archivos puede subir el equipo como respaldo documental.",
};

const selectOptions = {
  "calculo.unidad_emisiones": ["kg CO2e", "tCO2e"],
  "calculo.unidad_base_obra": ["m2", "m3"],
  "calculo.redondeo_decimales": [0, 1, 2],
  "importaciones.modo_importacion": ["flexible", "estricto"],
  "reportes.agrupacion_default": ["dia", "semana", "mes", "trimestre"],
  "reportes.periodo_default": ["ultimos_30_dias", "ultimos_6_meses", "ultimos_12_meses", "periodo_completo"],
  "reportes.unidad_visual_emisiones": ["kg CO2e", "tCO2e"],
};

const allowedFormats = ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"];

const formatLabel = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
    .trim();

function storageKey(organizacionId) {
  return `carbono_zero.configuracion.${organizacionId}`;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function buildInitialConfig(activeOrganizacion) {
  return {
    ...clone(defaultConfig),
    organizacion: {
      ...defaultConfig.organizacion,
      nombre: activeOrganizacion?.nombre || "",
      organizacion_id: activeOrganizacion?.organizacion_id || "",
      rut: activeOrganizacion?.rut || "",
      rubro: activeOrganizacion?.rubro || "Construcción",
      region: activeOrganizacion?.region || "",
      comuna: activeOrganizacion?.comuna || "",
      direccion: activeOrganizacion?.direccion || "",
      contacto: activeOrganizacion?.contacto || "",
      email: activeOrganizacion?.email || "",
      telefono: activeOrganizacion?.telefono || "",
      observaciones: activeOrganizacion?.observaciones || "",
    },
  };
}

function mergeConfig(base, incoming = {}) {
  const safeIncoming = incoming && typeof incoming === "object" ? incoming : {};

  return Object.keys(base).reduce((accumulator, section) => {
    accumulator[section] = {
      ...(base[section] || {}),
      ...(safeIncoming[section] && typeof safeIncoming[section] === "object" ? safeIncoming[section] : {}),
    };
    return accumulator;
  }, {});
}

function setNestedValue(source, section, field, value) {
  return {
    ...source,
    [section]: {
      ...(source?.[section] || {}),
      [field]: value,
    },
  };
}

function ConfiguracionPage() {
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [activeTab, setActiveTab] = useState("organizacion");
  const foundation = useDiagnostico(activeOrganizacionId);
  const [config, setConfig] = useState(null);
  const [savedConfig, setSavedConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isEditorOpen, setIsEditorOpen] = useState(false);

  useEffect(() => {
    if (!activeOrganizacionId) {
      setConfig(null);
      setSavedConfig(null);
      return;
    }

    let isCancelled = false;

    async function loadConfig() {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      const defaults = buildInitialConfig(activeOrganizacion);

      try {
        const remoteConfig = await getOrganizacionConfiguracion(activeOrganizacionId);
        if (isCancelled) return;
        const normalized = mergeConfig(defaults, remoteConfig);
        setConfig(clone(normalized));
        setSavedConfig(clone(normalized));
      } catch (requestError) {
        if (isCancelled) return;
        const parsedLocalConfig = (() => {
          try {
            return JSON.parse(window.localStorage.getItem(storageKey(activeOrganizacionId)) || "null");
          } catch {
            return null;
          }
        })();

        const localConfig = mergeConfig(defaults, parsedLocalConfig || {});
        setConfig(clone(localConfig));
        setSavedConfig(clone(localConfig));
        setError(
          requestError?.response?.data?.error ||
            "No se pudo cargar la configuración desde el backend. Se muestran valores locales."
        );
      } finally {
        if (!isCancelled) setLoading(false);
      }
    }

    loadConfig();

    return () => {
      isCancelled = true;
    };
  }, [activeOrganizacion, activeOrganizacionId]);

  const hasChanges = useMemo(
    () => JSON.stringify(config) !== JSON.stringify(savedConfig),
    [config, savedConfig]
  );

  const selectedSection = tabs.find((tab) => tab.value === activeTab) || tabs[0];
  const SelectedIcon = selectedSection.icon;

  if (!activeOrganizacionId || !config) {
    return (
      <EmptyState
        title="Configuración"
        description="Selecciona una empresa activa para definir las reglas del sistema."
      />
    );
  }

  if (loading && !savedConfig) {
    return (
      <PlatformLoader
        title="Cargando configuración"
        description="Estamos preparando reglas de cálculo, importación, evidencias y reportes."
      />
    );
  }

  function update(section, field, value) {
    setConfig((current) => setNestedValue(current, section, field, value));
    setSuccessMessage("");
  }

  function toggleFormat(format) {
    setConfig((current) => {
      const currentFormats = Array.isArray(current.evidencias.formatos_permitidos)
        ? current.evidencias.formatos_permitidos
        : [];
      const nextFormats = currentFormats.includes(format)
        ? currentFormats.filter((item) => item !== format)
        : [...currentFormats, format];
      return setNestedValue(current, "evidencias", "formatos_permitidos", nextFormats);
    });
    setSuccessMessage("");
  }

  async function saveConfig({ close = false } = {}) {
    setSaving(true);
    setError("");
    setSuccessMessage("");

    try {
      const remoteConfig = await updateOrganizacionConfiguracion(activeOrganizacionId, config);
      const normalized = mergeConfig(buildInitialConfig(activeOrganizacion), remoteConfig);
      window.localStorage.setItem(storageKey(activeOrganizacionId), JSON.stringify(normalized));
      setConfig(clone(normalized));
      setSavedConfig(clone(normalized));
      setSuccessMessage("Configuración guardada para la empresa activa.");
      if (close) setIsEditorOpen(false);
      return true;
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudo guardar la configuración.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  function restoreDefaults() {
    const defaults = buildInitialConfig(activeOrganizacion);
    setConfig(clone(defaults));
    setSuccessMessage("Valores predeterminados cargados. Guarda para aplicarlos.");
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-emerald-200/80 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(209,250,229,0.9))] p-3 text-[#0F766E] shadow-[0_14px_30px_rgba(14,124,102,0.14)] ring-1 ring-white/70">
            <Settings2 size={30} strokeWidth={2.1} />
          </div>
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">Reglas del sistema</p>
            <h1 className="text-3xl font-black tracking-tight text-[#0F172A] sm:text-4xl">Configuración</h1>
            <p className="max-w-3xl text-[#475569]">
              Revisa cómo Carbono Zero calcula, valida, importa y reporta la información ambiental de {activeOrganizacion?.nombre}.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <span className={`w-fit rounded-full border px-4 py-2 text-sm font-black ${hasChanges ? "border-[#FDBA74] bg-[#FFF7ED] text-[#B45309]" : "border-[#A7F3D0] bg-[#ECFDF3] text-[#047857]"}`}>
            {hasChanges ? "Cambios sin guardar" : "Configuración lista"}
          </span>
          <button
            type="button"
            onClick={() => setIsEditorOpen(true)}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)]"
          >
            <Edit3 size={17} />
            Editar reglas
          </button>
        </div>
      </header>

      {error ? (
        <div className="rounded-3xl border border-[#FDA29B] bg-[#FEF3F2] p-4 text-sm font-semibold text-[#B42318]">
          {error}
        </div>
      ) : null}

      {successMessage ? (
        <div className="rounded-3xl border border-[#A7F3D0] bg-[#ECFDF3] p-4 text-sm font-semibold text-[#047857]">
          {successMessage}
        </div>
      ) : null}

      <section className="rounded-[28px] border border-[#CBD5E1] bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)] sm:p-6">
        <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">Flujos / Capacidades ambientales</p>
        <h2 className="mt-1 text-2xl font-black tracking-tight text-[#0F172A]">Capacidades de la organización</h2>
        <p className="mb-5 mt-1 text-sm text-[#64748B]">La recomendación inicial proviene del backend y puede personalizarse sin alterar el preset.</p>
        {foundation.loading ? <p className="text-sm text-slate-500">Cargando capacidades...</p> : <CapacidadesAmbientales organizacionId={activeOrganizacionId} capacidades={foundation.capacidades} onChange={foundation.reload} />}
      </section>
      <MethodologiesPanel organizacionId={activeOrganizacionId} />

      <section className="rounded-[28px] border border-[#99F6E4] bg-[#F0FDFA] p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)] sm:p-6">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-center">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">Lectura operativa</p>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-[#0F172A]">Reglas activas para operar la plataforma</h2>
            <p className="mt-3 max-w-4xl text-sm leading-7 text-[#334155]">
              {activeOrganizacion?.nombre} trabaja con importación {formatLabel(config.importaciones.modo_importacion)}, ficha ambiental {config.ficha_ambiental.ficha_ambiental_activo ? "activa" : "inactiva"} y validación documental {config.evidencias.requerida_ficha_ambiental ? "obligatoria" : "flexible"}. Estos ajustes afectan nuevos cálculos, importaciones, evidencias y reportes; no modifican automáticamente registros históricos ya procesados.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <KpiCard icon={SlidersHorizontal} label="Gobernanza" value="Activa" detail="Por empresa" tone="emerald" />
            <KpiCard icon={Gauge} label="Unidad de salida" value={config.calculo.unidad_emisiones} detail="Formato de emisiones" tone="cyan" />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard icon={Building2} label="Empresa" value={config.organizacion.nombre || "Sin nombre"} tone="slate" />
        <KpiCard icon={UploadCloud} label="Importación" value={formatLabel(config.importaciones.modo_importacion)} tone={config.importaciones.modo_importacion === "estricto" ? "amber" : "cyan"} />
        <KpiCard icon={ShieldCheck} label="Ficha ambiental" value={config.ficha_ambiental.ficha_ambiental_activo ? "Activa" : "Inactiva"} tone="emerald" />
        <KpiCard icon={FileCheck2} label="Evidencias" value={config.evidencias.requerida_ficha_ambiental ? "Obligatorias" : "Flexibles"} tone="amber" />
        <KpiCard icon={Calculator} label="Emisiones" value={config.calculo.unidad_emisiones} tone="cyan" />
        <KpiCard icon={FileText} label="Reportes" value={formatLabel(config.reportes.periodo_default)} tone="slate" />
      </section>

      <section className="rounded-[28px] border border-[#CBD5E1] bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">Secciones configurables</p>
            <h2 className="mt-1 text-2xl font-black tracking-tight text-[#0F172A]">Resumen de reglas</h2>
            <p className="mt-1 text-sm text-[#64748B]">El detalle editable vive en modal para no convertir la vista en un formulario gigante.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const copy = sectionCopy[tab.value];
            const isActive = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                type="button"
                onClick={() => {
                  setActiveTab(tab.value);
                  setIsEditorOpen(true);
                }}
                className={`rounded-3xl border p-5 text-left shadow-[0_12px_28px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 ${isActive ? "border-[#99F6E4] bg-[#F0FDFA]" : "border-[#E2E8F0] bg-white hover:border-[#99F6E4]"}`}
              >
                <div className="flex items-start gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#A7F3D0] bg-[#ECFDF3] text-[#047857]">
                    <Icon size={20} />
                  </span>
                  <span>
                    <span className="block text-sm font-black text-[#0F172A]">{copy.title}</span>
                    <span className="mt-1 block text-xs leading-5 text-[#64748B]">{copy.description}</span>
                  </span>
                </div>
                <span className="mt-4 inline-flex rounded-full border border-[#CBD5E1] bg-white px-3 py-1 text-xs font-black text-[#334155]">
                  Editar {tab.label.toLowerCase()}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {isEditorOpen ? (
        <ConfigurationEditorModal
          activeTab={activeTab}
          config={config}
          hasChanges={hasChanges}
          onClose={() => setIsEditorOpen(false)}
          onRestoreDefaults={restoreDefaults}
          onSave={() => saveConfig({ close: true })}
          onSelectTab={setActiveTab}
          onToggleFormat={toggleFormat}
          onUpdate={update}
          saving={saving}
          selectedIcon={SelectedIcon}
          selectedSection={selectedSection}
        />
      ) : null}
    </div>
  );
}

function ConfigurationEditorModal({
  activeTab,
  config,
  hasChanges,
  onClose,
  onRestoreDefaults,
  onSave,
  onSelectTab,
  onToggleFormat,
  onUpdate,
  saving,
  selectedIcon: SelectedIcon,
  selectedSection,
}) {
  const copy = sectionCopy[activeTab];

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
      <div className="relative max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50"
          aria-label="Cerrar modal"
        >
          <X size={18} />
        </button>

        <div className="mb-5 flex flex-col gap-4 pr-12 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#A7F3D0] bg-[#ECFDF3] text-[#047857]">
              <SelectedIcon size={22} />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-[#047857]">Editar configuración</p>
              <h2 className="mt-1 text-2xl font-black text-[#0F172A]">{copy.title}</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-[#64748B]">{copy.description}</p>
            </div>
          </div>
          <span className={`w-fit rounded-full border px-4 py-2 text-sm font-black ${hasChanges ? "border-[#FDBA74] bg-[#FFF7ED] text-[#B45309]" : "border-[#A7F3D0] bg-[#ECFDF3] text-[#047857]"}`}>
            {hasChanges ? "Cambios sin guardar" : "Sin cambios pendientes"}
          </span>
        </div>

        <div className="mb-5 flex gap-2 overflow-x-auto rounded-[28px] border border-[#E2E8F0] bg-[#F8FAFC] p-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                type="button"
                onClick={() => onSelectTab(tab.value)}
                className={`flex shrink-0 items-center gap-2 rounded-2xl px-4 py-3 text-sm font-black transition ${isActive ? "border border-[#99F6E4] bg-white text-[#0F766E] shadow-sm" : "text-[#64748B] hover:bg-white hover:text-[#0F172A]"}`}
              >
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <section className="rounded-[28px] border border-[#E2E8F0] bg-[#F8FAFC] p-4 sm:p-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {Object.entries(config[activeTab] || {}).map(([field, value]) => (
              <ConfigField
                field={field}
                key={field}
                onToggleFormat={onToggleFormat}
                onUpdate={(nextValue) => onUpdate(activeTab, field, nextValue)}
                readOnly={activeTab === "organizacion" && field === "organizacion_id"}
                section={activeTab}
                value={value}
              />
            ))}
          </div>
        </section>

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
          <button
            type="button"
            onClick={onRestoreDefaults}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#CBD5E1] bg-white px-5 py-3 text-sm font-black text-[#334155]"
          >
            <RotateCcw size={17} />
            Restaurar valores base
          </button>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={onClose}
              className="rounded-2xl border border-[#CBD5E1] bg-white px-5 py-3 text-sm font-black text-[#334155]"
            >
              Cerrar
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60"
            >
              <Save size={17} />
              {saving ? "Guardando..." : "Guardar configuración"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfigField({ field, onToggleFormat, onUpdate, readOnly, section, value }) {
  const key = `${section}.${field}`;
  const label = fieldLabels[field] || formatLabel(field);
  const help = fieldHelp[field];

  if (Array.isArray(value)) {
    return (
      <div className="md:col-span-2">
        <p className="mb-2 text-xs font-black uppercase tracking-[0.16em] text-[#64748B]">{label}</p>
        <div className="flex flex-wrap gap-2">
          {allowedFormats.map((format) => {
            const active = value.includes(format);
            return (
              <button
                key={format}
                type="button"
                onClick={() => onToggleFormat(format)}
                className={`rounded-full border px-4 py-2 text-sm font-black ${active ? "border-[#99F6E4] bg-[#F0FDFA] text-[#0F766E]" : "border-[#CBD5E1] bg-white text-[#64748B]"}`}
              >
                {format}
              </button>
            );
          })}
        </div>
        {help ? <p className="mt-2 text-xs leading-5 text-[#64748B]">{help}</p> : null}
      </div>
    );
  }

  if (typeof value === "boolean") {
    return (
      <button
        type="button"
        onClick={() => onUpdate(!value)}
        className={`flex min-h-[86px] items-center justify-between gap-4 rounded-2xl border p-4 text-left shadow-[0_10px_26px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 ${value ? "border-[#99F6E4] bg-white text-[#0F766E]" : "border-[#E2E8F0] bg-white text-[#64748B]"}`}
      >
        <span>
          <span className="block text-sm font-black text-[#0F172A]">{label}</span>
          {help ? <span className="mt-1 block text-xs leading-5 text-[#64748B]">{help}</span> : null}
        </span>
        <span className={`flex h-7 w-12 shrink-0 items-center rounded-full border p-1 transition ${value ? "border-[#0F766E] bg-[#0F766E]" : "border-[#CBD5E1] bg-[#E2E8F0]"}`}>
          <span className={`h-5 w-5 rounded-full bg-white shadow-sm transition ${value ? "translate-x-5" : "translate-x-0"}`} />
        </span>
      </button>
    );
  }

  if (selectOptions[key]) {
    return (
      <label className="block">
        <span className="mb-2 block text-xs font-black uppercase tracking-[0.16em] text-[#64748B]">{label}</span>
        <select
          value={value ?? ""}
          onChange={(event) => {
            const raw = event.target.value;
            const numeric = typeof value === "number";
            onUpdate(numeric ? Number(raw) : raw);
          }}
          className="h-12 w-full rounded-2xl border border-[#CBD5E1] bg-white px-4 text-sm font-semibold text-[#0F172A] outline-none transition focus:border-[#14B8A6] focus:ring-4 focus:ring-[#99F6E4]/40"
        >
          {selectOptions[key].map((option) => (
            <option key={option} value={option}>{formatLabel(option)}</option>
          ))}
        </select>
        {help ? <span className="mt-2 block text-xs leading-5 text-[#64748B]">{help}</span> : null}
      </label>
    );
  }

  return (
    <label className={`block ${field === "observaciones" ? "md:col-span-2" : ""}`}>
      <span className="mb-2 block text-xs font-black uppercase tracking-[0.16em] text-[#64748B]">{label}</span>
      <input
        type={typeof value === "number" ? "number" : field === "email" ? "email" : "text"}
        value={value ?? ""}
        readOnly={readOnly}
        onChange={(event) => onUpdate(typeof value === "number" ? Number(event.target.value) : event.target.value)}
        className={`h-12 w-full rounded-2xl border border-[#CBD5E1] bg-white px-4 text-sm font-semibold text-[#0F172A] outline-none transition placeholder:text-[#94A3B8] focus:border-[#14B8A6] focus:ring-4 focus:ring-[#99F6E4]/40 ${readOnly ? "cursor-not-allowed bg-[#F8FAFC] text-[#64748B]" : ""}`}
      />
      {help ? <span className="mt-2 block text-xs leading-5 text-[#64748B]">{help}</span> : null}
    </label>
  );
}

function KpiCard({ icon: Icon, label, value, detail, tone = "slate" }) {
  const tones = {
    emerald: { card: "border-[#A7F3D0] bg-[#ECFDF3]", icon: "border-[#A7F3D0] text-[#047857]", value: "text-[#047857]" },
    cyan: { card: "border-[#BAE6FD] bg-[#F0F9FF]", icon: "border-[#BAE6FD] text-[#0369A1]", value: "text-[#0369A1]" },
    amber: { card: "border-[#FDBA74] bg-[#FFF7ED]", icon: "border-[#FDBA74] text-[#B45309]", value: "text-[#B45309]" },
    blue: { card: "border-[#BFDBFE] bg-[#EFF6FF]", icon: "border-[#BFDBFE] text-[#1D4ED8]", value: "text-[#1D4ED8]" },
    slate: { card: "border-[#E2E8F0] bg-white", icon: "border-[#E2E8F0] text-[#334155]", value: "text-[#0F172A]" },
  };
  const selectedTone = tones[tone] || tones.slate;

  return (
    <div className={`rounded-[24px] border p-5 text-center shadow-[0_18px_45px_rgba(15,23,42,0.08)] ${selectedTone.card}`}>
      <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border bg-white ${selectedTone.icon}`}>
        <Icon size={24} strokeWidth={2.1} />
      </div>
      <p className="mt-3 text-[11px] font-black uppercase tracking-[0.2em] text-[#64748B]">{label}</p>
      <p className={`mt-2 line-clamp-2 text-2xl font-black leading-tight ${selectedTone.value}`}>{value}</p>
      {detail ? <p className="mt-1 text-sm font-semibold text-[#64748B]">{detail}</p> : null}
    </div>
  );
}

export default ConfiguracionPage;
