import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  Calculator,
  FileCheck2,
  FileText,
  Gauge,
  RotateCcw,
  Save,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  UploadCloud,
} from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import {
  getConstructoraConfiguracion,
  updateConstructoraConfiguracion,
} from "@/shared/services/api";

const tabs = [
  { value: "constructora", label: "Constructora", icon: Building2 },
  { value: "calculo", label: "Cálculo", icon: Calculator },
  { value: "importaciones", label: "Importación", icon: UploadCloud },
  { value: "ficha_ambiental", label: "Ficha ambiental", icon: ShieldCheck },
  { value: "evidencias", label: "Evidencias", icon: FileCheck2 },
  { value: "reportes", label: "Reportes", icon: FileText },
];

const defaultConfig = {
  constructora: {
    nombre: "",
    constructora_id: "",
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
    permitir_constructora: true,
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

const formatLabel = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .trim();

function storageKey(constructoraId) {
  return `carbono_zero.configuracion.${constructoraId}`;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function buildInitialConfig(activeConstructora) {
  return {
    ...clone(defaultConfig),
    constructora: {
      ...defaultConfig.constructora,
      nombre: activeConstructora?.nombre || "",
      constructora_id: activeConstructora?.constructora_id || "",
      rut: activeConstructora?.rut || "",
      rubro: activeConstructora?.rubro || "Construcción",
      region: activeConstructora?.region || "",
      comuna: activeConstructora?.comuna || "",
      direccion: activeConstructora?.direccion || "",
      contacto: activeConstructora?.contacto || "",
      email: activeConstructora?.email || "",
      telefono: activeConstructora?.telefono || "",
      observaciones: activeConstructora?.observaciones || "",
    },
  };
}

function mergeConfig(base, incoming = {}) {
  const safeIncoming = incoming && typeof incoming === "object" ? incoming : {};

  return Object.keys(base).reduce((accumulator, section) => {
    accumulator[section] = {
      ...(base[section] || {}),
      ...(safeIncoming[section] && typeof safeIncoming[section] === "object"
        ? safeIncoming[section]
        : {}),
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

function Field({ label, children, help, full = false }) {
  return (
    <label className={`block ${full ? "md:col-span-2" : ""}`}>
      <span className="mb-2 block text-xs font-black uppercase tracking-[0.16em] text-[#64748B]">
        {label}
      </span>
      {children}
      {help ? <span className="mt-2 block text-xs leading-5 text-[#64748B]">{help}</span> : null}
    </label>
  );
}

function TextInput({ value, onChange, readOnly = false, type = "text" }) {
  return (
    <input
      type={type}
      value={value ?? ""}
      readOnly={readOnly}
      onChange={(event) =>
        onChange(type === "number" ? Number(event.target.value) : event.target.value)
      }
      className={`h-12 w-full rounded-2xl border border-[#CBD5E1] bg-white px-4 text-sm font-semibold text-[#0F172A] outline-none transition placeholder:text-[#94A3B8] focus:border-[#14B8A6] focus:ring-4 focus:ring-[#99F6E4]/40 ${
        readOnly ? "cursor-not-allowed bg-[#F8FAFC] text-[#64748B]" : ""
      }`}
    />
  );
}

function SelectInput({ value, onChange, options }) {
  return (
    <select
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value)}
      className="h-12 w-full rounded-2xl border border-[#CBD5E1] bg-white px-4 text-sm font-semibold text-[#0F172A] outline-none transition focus:border-[#14B8A6] focus:ring-4 focus:ring-[#99F6E4]/40"
    >
      {options.map((option) => (
        <option key={option.value ?? option} value={option.value ?? option}>
          {option.label ?? option}
        </option>
      ))}
    </select>
  );
}

function SettingSwitch({ label, checked, onChange, help }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`flex min-h-[84px] items-center justify-between gap-4 rounded-2xl border p-4 text-left shadow-[0_10px_26px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 ${
        checked
          ? "border-[#99F6E4] bg-[#F0FDFA]"
          : "border-[#E2E8F0] bg-white"
      }`}
    >
      <span>
        <span className="block text-sm font-black text-[#0F172A]">{label}</span>
        {help ? <span className="mt-1 block text-xs leading-5 text-[#64748B]">{help}</span> : null}
      </span>
      <span
        className={`flex h-7 w-12 shrink-0 items-center rounded-full border p-1 transition ${
          checked ? "border-[#0F766E] bg-[#0F766E]" : "border-[#CBD5E1] bg-[#E2E8F0]"
        }`}
      >
        <span
          className={`h-5 w-5 rounded-full bg-white shadow-sm transition ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </span>
    </button>
  );
}

function SettingCard({ title, description, children }) {
  return (
    <section className="rounded-[28px] border border-[#CBD5E1] bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)] sm:p-6">
      <div className="mb-5">
        <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">
          Configuración
        </p>
        <h2 className="mt-1 text-2xl font-black tracking-tight text-[#0F172A]">{title}</h2>
        {description ? <p className="mt-2 max-w-4xl text-sm leading-6 text-[#64748B]">{description}</p> : null}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </section>
  );
}

function KpiCard({ icon: Icon, label, value, detail, tone = "slate" }) {
  const tones = {
    emerald: {
      card: "border-[#A7F3D0] bg-[#ECFDF3]",
      icon: "border-[#A7F3D0] text-[#047857]",
      value: "text-[#047857]",
    },
    cyan: {
      card: "border-[#BAE6FD] bg-[#F0F9FF]",
      icon: "border-[#BAE6FD] text-[#0369A1]",
      value: "text-[#0369A1]",
    },
    amber: {
      card: "border-[#FDBA74] bg-[#FFF7ED]",
      icon: "border-[#FDBA74] text-[#B45309]",
      value: "text-[#B45309]",
    },
    blue: {
      card: "border-[#BFDBFE] bg-[#EFF6FF]",
      icon: "border-[#BFDBFE] text-[#1D4ED8]",
      value: "text-[#1D4ED8]",
    },
    slate: {
      card: "border-[#E2E8F0] bg-white",
      icon: "border-[#E2E8F0] text-[#334155]",
      value: "text-[#0F172A]",
    },
  };
  const selectedTone = tones[tone] || tones.slate;

  return (
    <div className={`rounded-[24px] border p-5 text-center shadow-[0_18px_45px_rgba(15,23,42,0.08)] ${selectedTone.card}`}>
      <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border bg-white ${selectedTone.icon}`}>
        <Icon size={24} strokeWidth={2.1} />
      </div>
      <p className="mt-3 text-[11px] font-black uppercase tracking-[0.2em] text-[#64748B]">
        {label}
      </p>
      <p className={`mt-2 line-clamp-2 text-2xl font-black leading-tight ${selectedTone.value}`}>
        {value}
      </p>
      {detail ? <p className="mt-1 text-sm font-semibold text-[#64748B]">{detail}</p> : null}
    </div>
  );
}

function ConfiguracionPage() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [activeTab, setActiveTab] = useState("constructora");
  const [config, setConfig] = useState(null);
  const [savedConfig, setSavedConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!activeConstructoraId) {
      setConfig(null);
      setSavedConfig(null);
      return;
    }

    let isCancelled = false;

    async function loadConfig() {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      const defaults = buildInitialConfig(activeConstructora);

      try {
        const remoteConfig = await getConstructoraConfiguracion(activeConstructoraId);
        if (isCancelled) return;
        const normalized = mergeConfig(defaults, remoteConfig);
        setConfig(clone(normalized));
        setSavedConfig(clone(normalized));
      } catch (requestError) {
        if (isCancelled) return;
        let parsedLocalConfig = null;

        try {
          parsedLocalConfig = JSON.parse(
            window.localStorage.getItem(storageKey(activeConstructoraId)) || "null"
          );
        } catch {
          parsedLocalConfig = null;
        }

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
  }, [activeConstructora, activeConstructoraId]);

  const hasChanges = useMemo(
    () => JSON.stringify(config) !== JSON.stringify(savedConfig),
    [config, savedConfig]
  );

  if (!activeConstructoraId || !config) {
    return (
      <EmptyState
        title="Configuración"
        description="Selecciona una constructora activa para definir las reglas del sistema."
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

  async function saveConfig() {
    setSaving(true);
    setError("");
    setSuccessMessage("");

    try {
      const remoteConfig = await updateConstructoraConfiguracion(activeConstructoraId, config);
      const normalized = mergeConfig(buildInitialConfig(activeConstructora), remoteConfig);
      window.localStorage.setItem(storageKey(activeConstructoraId), JSON.stringify(normalized));
      setConfig(clone(normalized));
      setSavedConfig(clone(normalized));
      setSuccessMessage("Configuración guardada para la constructora activa.");
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudo guardar la configuración.");
    } finally {
      setSaving(false);
    }
  }

  function restoreDefaults() {
    const defaults = buildInitialConfig(activeConstructora);
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
            <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">
              Reglas del sistema
            </p>
            <h1 className="text-3xl font-black tracking-tight text-[#0F172A] sm:text-4xl">
              Configuración
            </h1>
            <p className="max-w-3xl text-[#475569]">
              Define cómo Carbono Zero calcula, valida, importa y reporta la información ambiental de {activeConstructora?.nombre}.
            </p>
          </div>
        </div>
        {hasChanges ? (
          <span className="w-fit rounded-full border border-[#FDBA74] bg-[#FFF7ED] px-4 py-2 text-sm font-black text-[#B45309]">
            Cambios sin guardar
          </span>
        ) : (
          <span className="w-fit rounded-full border border-[#A7F3D0] bg-[#ECFDF3] px-4 py-2 text-sm font-black text-[#047857]">
            Configuración lista
          </span>
        )}
      </header>

      {loading ? (
        <div className="rounded-3xl border border-[#BAE6FD] bg-[#F0F9FF] p-4 text-sm font-semibold text-[#0369A1]">
          Cargando configuración de la constructora activa...
        </div>
      ) : null}

      {error ? (
        <div className="rounded-3xl border border-[#FDA29B] bg-[#FEF3F2] p-4 text-sm font-semibold text-[#B42318]">
          {error}
        </div>
      ) : null}

      <section className="rounded-[28px] border border-[#99F6E4] bg-[#F0FDFA] p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)] sm:p-6">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-center">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-[#0F766E]">
              Lectura operativa
            </p>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-[#0F172A]">
              Reglas activas para operar la plataforma
            </h2>
            <p className="mt-3 max-w-4xl text-sm leading-7 text-[#334155]">
              {activeConstructora?.nombre} trabaja con importación {config.importaciones.modo_importacion}, ficha ambiental {config.ficha_ambiental.ficha_ambiental_activo ? "activa" : "inactiva"} y validación documental {config.evidencias.requerida_ficha_ambiental ? "obligatoria" : "flexible"}. Estos ajustes afectan nuevos cálculos, importaciones, evidencias y reportes; no modifican automáticamente registros históricos ya procesados.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <KpiCard icon={SlidersHorizontal} label="Gobernanza" value="Activa" detail="Por constructora" tone="emerald" />
            <KpiCard icon={Gauge} label="Unidad de salida" value={config.calculo.unidad_emisiones} detail="Formato de emisiones" tone="cyan" />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard icon={Building2} label="Constructora" value={config.constructora.nombre || "Sin nombre"} tone="slate" />
        <KpiCard icon={UploadCloud} label="Importación" value={formatLabel(config.importaciones.modo_importacion)} tone={config.importaciones.modo_importacion === "estricto" ? "amber" : "cyan"} />
        <KpiCard icon={ShieldCheck} label="Ficha ambiental" value={config.ficha_ambiental.ficha_ambiental_activo ? "Activa" : "Inactiva"} tone="emerald" />
        <KpiCard icon={FileCheck2} label="Evidencias" value={config.evidencias.requerida_ficha_ambiental ? "Obligatorias" : "Flexibles"} tone="amber" />
        <KpiCard icon={Calculator} label="Emisiones" value={config.calculo.unidad_emisiones} tone="cyan" />
        <KpiCard icon={FileText} label="Reportes" value={formatLabel(config.reportes.periodo_default)} tone="slate" />
      </section>

      <section className="rounded-[28px] border border-[#CBD5E1] bg-white p-2 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
        <div className="flex gap-2 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveTab(tab.value)}
                className={`flex shrink-0 items-center gap-2 rounded-2xl px-4 py-3 text-sm font-black transition ${
                  isActive
                    ? "border border-[#99F6E4] bg-[#F0FDFA] text-[#0F766E] shadow-[0_8px_18px_rgba(14,124,102,0.10)]"
                    : "text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
                }`}
              >
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {activeTab === "constructora" && (
        <SettingCard title="Datos básicos de la constructora" description="Datos visibles de la empresa activa. El ID interno queda bloqueado para proteger las relaciones con obras, etapas y registros.">
          {Object.entries({
            nombre: "Nombre",
            constructora_id: "ID constructora",
            rut: "RUT",
            rubro: "Rubro",
            region: "Región",
            comuna: "Comuna",
            direccion: "Dirección",
            contacto: "Contacto",
            email: "Email",
            telefono: "Teléfono",
            observaciones: "Observaciones",
          }).map(([field, label]) => (
            <Field key={field} label={label} full={field === "observaciones"}>
              <TextInput
                value={config.constructora[field]}
                readOnly={field === "constructora_id"}
                onChange={(value) => update("constructora", field, value)}
              />
            </Field>
          ))}
        </SettingCard>
      )}

      {activeTab === "calculo" && (
        <SettingCard title="Parámetros de cálculo ambiental" description="Valores usados cuando el sistema debe completar cálculos o construir indicadores ambientales derivados.">
          <Field label="Unidad de emisiones preferida"><SelectInput value={config.calculo.unidad_emisiones} onChange={(v) => update("calculo", "unidad_emisiones", v)} options={["kg CO2e", "tCO2e"]} /></Field>
          <Field label="Unidad base de obra"><SelectInput value={config.calculo.unidad_base_obra} onChange={(v) => update("calculo", "unidad_base_obra", v)} options={["m2", "m3"]} /></Field>
          <Field label="Porcentaje de carbono por defecto"><TextInput type="number" value={config.calculo.porcentaje_carbono_default} onChange={(v) => update("calculo", "porcentaje_carbono_default", v)} /></Field>
          <Field label="Densidad de material por defecto kg/m3"><TextInput type="number" value={config.calculo.densidad_material_default} onChange={(v) => update("calculo", "densidad_material_default", v)} /></Field>
          <Field label="Factor eléctrico preferido"><TextInput value={config.calculo.factor_electrico_default} onChange={(v) => update("calculo", "factor_electrico_default", v)} /></Field>
          <Field label="Región eléctrica por defecto"><TextInput value={config.calculo.region_electrica_default} onChange={(v) => update("calculo", "region_electrica_default", v)} /></Field>
          <Field label="Redondeo de resultados"><SelectInput value={config.calculo.redondeo_decimales} onChange={(v) => update("calculo", "redondeo_decimales", Number(v))} options={[0, 1, 2]} /></Field>
          <SettingSwitch label="Mostrar balance neto" checked={Boolean(config.calculo.mostrar_balance_neto)} onChange={(v) => update("calculo", "mostrar_balance_neto", v)} />
          <SettingSwitch label="Permitir balance ambiental" checked={Boolean(config.calculo.permitir_balance_ambiental)} onChange={(v) => update("calculo", "permitir_balance_ambiental", v)} />
        </SettingCard>
      )}

      {activeTab === "importaciones" && (
        <SettingCard title="Reglas de importación" description="Define qué tan estricto será el sistema al cargar archivos y cómo debe reaccionar ante datos incompletos o duplicados.">
          <Field label="Modo de importación" help={config.importaciones.modo_importacion === "flexible" ? "Permite cargar datos y advertir diferencias con la constructora activa." : "Bloquea archivos con relaciones inconsistentes."}>
            <SelectInput value={config.importaciones.modo_importacion} onChange={(v) => update("importaciones", "modo_importacion", v)} options={["flexible", "estricto"]} />
          </Field>
          {Object.entries({
            crear_etapas_automaticamente: "Crear etapas automáticamente",
            crear_obras_automaticamente: "Crear obras automáticamente",
            permitir_registros_emision_sin_factor: "Permitir registros sin factor",
            actualizar_registros_existentes: "Actualizar registros existentes",
            bloquear_duplicados: "Bloquear duplicados exactos",
            requerir_unidad_obra: "Requerir etapa para obras",
            requerir_obra_fuente_emision: "Requerir obra para registros",
            permitir_evidencias_sin_vinculo: "Permitir evidencias sin vínculo específico",
          }).map(([field, label]) => (
            <SettingSwitch key={field} label={label} checked={Boolean(config.importaciones[field])} onChange={(v) => update("importaciones", field, v)} />
          ))}
        </SettingCard>
      )}

      {activeTab === "ficha_ambiental" && (
        <SettingCard title="Criterios de ficha ambiental" description="Reglas que definen cuándo una obra puede generar una ficha ambiental verificable.">
          <SettingSwitch label="Activar ficha ambiental" checked={Boolean(config.ficha_ambiental.ficha_ambiental_activo)} onChange={(v) => update("ficha_ambiental", "ficha_ambiental_activo", v)} />
          <SettingSwitch label="Requerir balance neto favorable" checked={Boolean(config.ficha_ambiental.requiere_balance_favorable)} onChange={(v) => update("ficha_ambiental", "requiere_balance_favorable", v)} />
          <SettingSwitch label="Requerir evidencia documental" checked={Boolean(config.ficha_ambiental.requiere_evidencia)} onChange={(v) => update("ficha_ambiental", "requiere_evidencia", v)} />
          <SettingSwitch label="Requerir trazabilidad completa" checked={Boolean(config.ficha_ambiental.requiere_trazabilidad)} onChange={(v) => update("ficha_ambiental", "requiere_trazabilidad", v)} />
          <Field label="Score mínimo ficha base"><TextInput type="number" value={config.ficha_ambiental.score_verde} onChange={(v) => update("ficha_ambiental", "score_verde", v)} /></Field>
          <Field label="Score mínimo ficha avanzada"><TextInput type="number" value={config.ficha_ambiental.score_plus} onChange={(v) => update("ficha_ambiental", "score_plus", v)} /></Field>
          <Field label="Score mínimo confianza dato"><TextInput type="number" value={config.ficha_ambiental.score_confianza_minimo} onChange={(v) => update("ficha_ambiental", "score_confianza_minimo", v)} /></Field>
        </SettingCard>
      )}

      {activeTab === "evidencias" && (
        <SettingCard title="Reglas documentales" description="Las evidencias respaldan cálculos, obras, registros y fichas. Una mayor cobertura documental mejora la confianza del dato.">
          <SettingSwitch label="Requerir evidencia para emitir ficha" checked={Boolean(config.evidencias.requerida_ficha_ambiental)} onChange={(v) => update("evidencias", "requerida_ficha_ambiental", v)} />
          <SettingSwitch label="Requerir evidencia para obras críticas" checked={Boolean(config.evidencias.requerida_obras_criticos)} onChange={(v) => update("evidencias", "requerida_obras_criticos", v)} />
          <Field label="Umbral obra crítica kg CO2e"><TextInput type="number" value={config.evidencias.umbral_obra_critico} onChange={(v) => update("evidencias", "umbral_obra_critico", v)} /></Field>
          <Field label="Tamaño máximo archivo MB"><TextInput type="number" value={config.evidencias.max_file_size_mb} onChange={(v) => update("evidencias", "max_file_size_mb", v)} /></Field>
          <SettingSwitch label="Permitir evidencia corporativa" checked={Boolean(config.evidencias.permitir_constructora)} onChange={(v) => update("evidencias", "permitir_constructora", v)} />
          <SettingSwitch label="Permitir evidencia a nivel etapa" checked={Boolean(config.evidencias.permitir_unidad)} onChange={(v) => update("evidencias", "permitir_unidad", v)} />
          <SettingSwitch label="Permitir evidencia a nivel obra" checked={Boolean(config.evidencias.permitir_obra)} onChange={(v) => update("evidencias", "permitir_obra", v)} />
          <SettingSwitch label="Permitir evidencia a nivel emisión" checked={Boolean(config.evidencias.permitir_emision)} onChange={(v) => update("evidencias", "permitir_emision", v)} />
          <div className="md:col-span-2 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-4">
            <p className="mb-3 text-sm font-black text-[#0F172A]">Formatos permitidos</p>
            <div className="flex flex-wrap gap-2">
              {["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"].map((format) => {
                const enabled = Array.isArray(config.evidencias.formatos_permitidos) && config.evidencias.formatos_permitidos.includes(format);
                return (
                  <button
                    key={format}
                    type="button"
                    onClick={() => toggleFormat(format)}
                    className={`rounded-full border px-4 py-2 text-sm font-black transition ${
                      enabled
                        ? "border-[#99F6E4] bg-[#F0FDFA] text-[#0F766E]"
                        : "border-[#CBD5E1] bg-white text-[#64748B]"
                    }`}
                  >
                    {format}
                  </button>
                );
              })}
            </div>
          </div>
        </SettingCard>
      )}

      {activeTab === "reportes" && (
        <SettingCard title="Preferencias de reportes" description="Define cómo se presentan los reportes ejecutivos y analíticos de la constructora.">
          <Field label="Agrupación temporal por defecto"><SelectInput value={config.reportes.agrupacion_default} onChange={(v) => update("reportes", "agrupacion_default", v)} options={[{ value: "dia", label: "Día" }, { value: "semana", label: "Semana" }, { value: "mes", label: "Mes" }, { value: "trimestre", label: "Trimestre" }, { value: "anio", label: "Año" }]} /></Field>
          <Field label="Período por defecto"><SelectInput value={config.reportes.periodo_default} onChange={(v) => update("reportes", "periodo_default", v)} options={[{ value: "ultimos_30_dias", label: "Últimos 30 días" }, { value: "ultimos_3_meses", label: "Últimos 3 meses" }, { value: "ultimos_6_meses", label: "Últimos 6 meses" }, { value: "ultimos_12_meses", label: "Últimos 12 meses" }, { value: "anio_actual", label: "Año actual" }]} /></Field>
          <Field label="Unidad visual de emisiones"><SelectInput value={config.reportes.unidad_visual_emisiones} onChange={(v) => update("reportes", "unidad_visual_emisiones", v)} options={["kg CO2e", "tCO2e"]} /></Field>
          <SettingSwitch label="Mostrar gráficos por categoría" checked={Boolean(config.reportes.mostrar_categoria)} onChange={(v) => update("reportes", "mostrar_categoria", v)} />
          <SettingSwitch label="Mostrar gráficos por etapa" checked={Boolean(config.reportes.mostrar_unidad)} onChange={(v) => update("reportes", "mostrar_unidad", v)} />
          <SettingSwitch label="Mostrar tabla detallada por defecto" checked={Boolean(config.reportes.mostrar_tabla)} onChange={(v) => update("reportes", "mostrar_tabla", v)} />
          <SettingSwitch label="Incluir lectura ejecutiva automática" checked={Boolean(config.reportes.lectura_ejecutiva)} onChange={(v) => update("reportes", "lectura_ejecutiva", v)} />
          <SettingSwitch label="Incluir equivalencias de orden de magnitud" checked={Boolean(config.reportes.equivalencias)} onChange={(v) => update("reportes", "equivalencias", v)} />
        </SettingCard>
      )}

      <section className="sticky bottom-4 z-10 rounded-[28px] border border-[#CBD5E1] bg-white/95 p-4 shadow-[0_20px_60px_rgba(15,23,42,0.16)] backdrop-blur">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-black text-[#0F172A]">
              {hasChanges ? "Cambios pendientes" : "Configuración lista"}
            </p>
            <p className="text-xs leading-5 text-[#64748B]">
              {successMessage || "Los cambios se guardan por constructora activa y quedan listos para cálculos, importaciones y reportes."}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={restoreDefaults}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#CBD5E1] bg-white px-5 py-3 text-sm font-bold text-[#475569] shadow-[0_8px_20px_rgba(15,23,42,0.06)] transition hover:border-[#94A3B8]"
            >
              <RotateCcw size={18} />
              Restaurar valores
            </button>
            <button
              type="button"
              onClick={saveConfig}
              disabled={saving || !hasChanges}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#0F766E] bg-[#0F766E] px-5 py-3 text-sm font-bold text-white shadow-[0_14px_28px_rgba(14,124,102,0.22)] transition hover:bg-[#115E59] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save size={18} />
              {saving ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export default ConfiguracionPage;
