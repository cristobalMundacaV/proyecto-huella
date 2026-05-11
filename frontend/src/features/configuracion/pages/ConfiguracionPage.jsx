import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  Calculator,
  FileCheck2,
  FileText,
  Gauge,
  Import,
  RotateCcw,
  Save,
  Settings2,
  ShieldCheck,
} from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";
import {
  getEmpresaConfiguracion,
  updateEmpresaConfiguracion,
} from "@/shared/services/api";

const tabs = [
  { value: "empresa", label: "Empresa", icon: Building2 },
  { value: "calculo", label: "Cálculo", icon: Calculator },
  { value: "importaciones", label: "Importación", icon: Import },
  { value: "pasaporte", label: "Pasaporte Verde", icon: ShieldCheck },
  { value: "evidencias", label: "Evidencias", icon: FileCheck2 },
  { value: "reportes", label: "Reportes", icon: FileText },
];

const defaultConfig = {
  empresa: {
    nombre: "",
    empresa_id: "",
    rut: "",
    rubro: "Madera",
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
    unidad_volumen_madera: "m3",
    porcentaje_carbono_default: 50,
    densidad_madera_default: 420,
    factor_electrico_default: "Factor electrico vigente",
    region_electrica_default: "Biobio",
    redondeo_decimales: 1,
    mostrar_balance_neto: true,
    permitir_co2_almacenado: true,
  },
  importaciones: {
    modo_importacion: "flexible",
    crear_unidades_automaticamente: true,
    crear_lotes_automaticamente: true,
    permitir_actividades_sin_factor: false,
    actualizar_registros_existentes: true,
    bloquear_duplicados: true,
    requerir_unidad_lote: false,
    requerir_lote_actividad: false,
    permitir_evidencias_sin_vinculo: true,
  },
  pasaporte: {
    pasaporte_activo: true,
    requiere_balance_favorable: true,
    requiere_evidencia: true,
    requiere_trazabilidad: true,
    score_verde: 70,
    score_plus: 90,
    score_confianza_minimo: 75,
  },
  evidencias: {
    requerida_pasaporte: true,
    requerida_lotes_criticos: true,
    umbral_lote_critico: 1000,
    permitir_empresa: true,
    permitir_unidad: true,
    permitir_lote: true,
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

function storageKey(empresaId) {
  return `carbono_zero.configuracion.${empresaId}`;
}

function buildInitialConfig(activeEmpresa) {
  return {
    ...defaultConfig,
    empresa: {
      ...defaultConfig.empresa,
      nombre: activeEmpresa?.nombre || "",
      empresa_id: activeEmpresa?.empresa_id || "",
      rut: activeEmpresa?.rut || "",
      rubro: activeEmpresa?.rubro || "Madera",
      region: activeEmpresa?.region || "",
      comuna: activeEmpresa?.comuna || "",
      direccion: activeEmpresa?.direccion || "",
      contacto: activeEmpresa?.contacto || "",
      email: activeEmpresa?.email || "",
      telefono: activeEmpresa?.telefono || "",
      observaciones: activeEmpresa?.observaciones || "",
    },
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function setNestedValue(source, section, field, value) {
  return {
    ...source,
    [section]: {
      ...source[section],
      [field]: value,
    },
  };
}

function SettingCard({ title, description, children }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_18px_45px_var(--shadow)] sm:p-6">
      <div className="mb-5">
        <h2 className="text-xl font-semibold text-[var(--text-main)]">{title}</h2>
        {description ? <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{description}</p> : null}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </section>
  );
}

function Field({ label, children, help }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-semibold text-[#344054]">{label}</span>
      {children}
      {help ? <span className="mt-1 block text-xs leading-5 text-[var(--text-muted)]">{help}</span> : null}
    </label>
  );
}

function TextInput({ value, onChange, readOnly = false, type = "text" }) {
  return (
    <input
      type={type}
      value={value ?? ""}
      readOnly={readOnly}
      onChange={(event) => onChange(type === "number" ? Number(event.target.value) : event.target.value)}
      className={`w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-emerald-100 ${readOnly ? "cursor-not-allowed opacity-70" : ""}`}
    />
  );
}

function SelectInput({ value, onChange, options }) {
  return (
    <select
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-emerald-100"
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
      className="flex min-h-[76px] items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-left transition hover:border-[var(--primary)] hover:bg-[var(--success-bg)]"
    >
      <span>
        <span className="block text-sm font-semibold text-[var(--text-main)]">{label}</span>
        {help ? <span className="mt-1 block text-xs leading-5 text-[var(--text-muted)]">{help}</span> : null}
      </span>
      <span className={`flex h-7 w-12 shrink-0 items-center rounded-full border p-1 transition ${checked ? "border-[#064E3B] bg-[#0B5F49]" : "border-[#B9C7BF] bg-[#DDE6E0]"}`}>
        <span className={`h-5 w-5 rounded-full shadow-sm transition ${checked ? "translate-x-5 bg-[#A7F3D0]" : "bg-[#7B8F86]"}`} />
      </span>
    </button>
  );
}

function KpiCard({ icon, label, value, detail, tone = "slate" }) {
  const toneClass = {
    emerald: "border-[#B7DEC9] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    cyan: "border-[#B9D8D3] bg-[var(--info-bg)] text-[#155E75]",
    amber: "border-[#E6CC82] bg-[var(--warning-bg)] text-[#7A4F00]",
    slate: "border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)]",
  }[tone];

  return (
    <div className={`rounded-3xl border p-5 ${toneClass}`}>
      <div className="mb-3 flex items-center gap-3">
        <div className="opacity-90">{icon}</div>
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">
          {label}
        </p>
      </div>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      {detail ? <p className="mt-2 text-sm opacity-75">{detail}</p> : null}
    </div>
  );
}

function ConfiguracionPage() {
  const { activeEmpresa, activeEmpresaId } = useEmpresaActiva();
  const [activeTab, setActiveTab] = useState("empresa");
  const [config, setConfig] = useState(null);
  const [savedConfig, setSavedConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!activeEmpresaId) {
      setConfig(null);
      setSavedConfig(null);
      return;
    }

    let isCancelled = false;

    async function loadConfig() {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      try {
        const remoteConfig = await getEmpresaConfiguracion(activeEmpresaId);
        if (isCancelled) return;
        setConfig(clone(remoteConfig));
        setSavedConfig(clone(remoteConfig));
      } catch (requestError) {
        if (isCancelled) return;
        const defaults = buildInitialConfig(activeEmpresa);
        const persisted = window.localStorage.getItem(storageKey(activeEmpresaId));
        const localConfig = persisted
          ? { ...defaults, ...JSON.parse(persisted), empresa: { ...defaults.empresa, ...JSON.parse(persisted).empresa } }
          : defaults;
        setConfig(clone(localConfig));
        setSavedConfig(clone(localConfig));
        setError(
          requestError?.response?.data?.error ||
            "No se pudo cargar la configuración desde el backend. Se muestran valores locales."
        );
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadConfig();

    return () => {
      isCancelled = true;
    };
  }, [activeEmpresa, activeEmpresaId]);

  const hasChanges = useMemo(
    () => JSON.stringify(config) !== JSON.stringify(savedConfig),
    [config, savedConfig]
  );

  if (!activeEmpresaId || !config) {
    return (
      <EmptyState
        title="Configuración"
        description="Selecciona una empresa activa para definir las reglas del sistema."
      />
    );
  }

  function update(section, field, value) {
    setConfig((current) => setNestedValue(current, section, field, value));
    setSuccessMessage("");
  }

  function toggleFormat(format) {
    setConfig((current) => {
      const currentFormats = current.evidencias.formatos_permitidos || [];
      const nextFormats = currentFormats.includes(format)
        ? currentFormats.filter((item) => item !== format)
        : [...currentFormats, format];
      return setNestedValue(current, "evidencias", "formatos_permitidos", nextFormats);
    });
  }

  async function saveConfig() {
    setSaving(true);
    setError("");
    setSuccessMessage("");

    try {
      const remoteConfig = await updateEmpresaConfiguracion(activeEmpresaId, config);
      window.localStorage.setItem(storageKey(activeEmpresaId), JSON.stringify(remoteConfig));
      setConfig(clone(remoteConfig));
      setSavedConfig(clone(remoteConfig));
      setSuccessMessage("Configuración guardada en el backend para la empresa activa.");
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudo guardar la configuración.");
    } finally {
      setSaving(false);
    }
  }

  function restoreDefaults() {
    const defaults = buildInitialConfig(activeEmpresa);
    setConfig(clone(defaults));
    setSuccessMessage("Valores predeterminados cargados. Guarda para aplicarlos.");
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--primary-dark)]">Configuración</p>
          <h1 className="mt-2 text-3xl font-bold text-[var(--text-main)] sm:text-4xl">Configuración</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
            Define cómo Carbono Zero calcula emisiones, valida datos, exige evidencias y construye reportes para la empresa activa.
          </p>
        </div>
        {hasChanges ? (
          <div className="rounded-2xl border border-[#E6CC82] bg-[var(--warning-bg)] px-4 py-3 text-sm font-bold text-[#7A4F00]">
            Cambios sin guardar
          </div>
        ) : null}
      </header>

      {loading ? (
        <div className="rounded-3xl border border-[#B9D8D3] bg-[var(--info-bg)] p-4 text-sm font-semibold text-[#155E75]">
          Cargando configuración de la empresa activa...
        </div>
      ) : null}

      {error ? (
        <div className="rounded-3xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-4 text-sm font-semibold text-[#B42318]">
          {error}
        </div>
      ) : null}

      <section className="rounded-3xl border border-[#B7DEC9] bg-[var(--success-bg)] p-5 shadow-[0_18px_45px_var(--shadow)] sm:p-7">
        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.75fr] lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--primary-dark)]">Reglas de operación</p>
            <h2 className="mt-3 text-2xl font-bold text-[var(--text-main)] sm:text-3xl">
              Reglas activas para calcular, validar e interpretar la información de {activeEmpresa?.nombre || "la empresa"}
            </h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-[#344054]">
              {activeEmpresa?.nombre || "La empresa"} usa importación {config.importaciones.modo_importacion}, Pasaporte Verde {config.pasaporte.pasaporte_activo ? "activo" : "inactivo"} y evidencia obligatoria para fortalecer la trazabilidad documental. Estos ajustes definen cómo se procesan nuevos datos, cómo se calculan emisiones y qué condiciones debe cumplir la información antes de aparecer en reportes.
            </p>
            <p className="mt-4 rounded-2xl border border-[#E6CC82] bg-[var(--warning-bg)] p-3 text-sm font-semibold text-[#7A4F00]">
              Los cambios pueden afectar nuevos cálculos, importaciones y validaciones. Los registros históricos no se modifican automáticamente; solo cambiarán si vuelves a procesarlos.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <KpiCard icon={<Settings2 size={22} />} label="Gobernanza" value="Configuración activa" detail="Por empresa activa" tone="emerald" />
            <KpiCard icon={<Gauge size={22} />} label="Unidad de emisión" value={config.calculo.unidad_emisiones} detail="Formato de salida" tone="cyan" />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard icon={<Building2 size={22} />} label="Empresa seleccionada" value={config.empresa.nombre || "Sin nombre"} tone="slate" />
        <KpiCard icon={<Import size={22} />} label="Modo de importación" value={config.importaciones.modo_importacion} tone={config.importaciones.modo_importacion === "estricto" ? "amber" : "cyan"} />
        <KpiCard icon={<ShieldCheck size={22} />} label="Pasaporte Verde" value={config.pasaporte.pasaporte_activo ? "Activo" : "Inactivo"} tone="emerald" />
        <KpiCard icon={<FileCheck2 size={22} />} label="Evidencia obligatoria" value={config.evidencias.requerida_pasaporte ? "Si" : "No"} tone="amber" />
        <KpiCard icon={<Calculator size={22} />} label="Emisiones" value={config.calculo.unidad_emisiones} tone="cyan" />
        <KpiCard icon={<FileText size={22} />} label="Período de reportes" value={config.reportes.periodo_default.replace(/_/g, " ")} tone="slate" />
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-[0_14px_35px_var(--shadow)]">
        <div className="flex gap-2 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveTab(tab.value)}
                className={`flex shrink-0 items-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold transition ${isActive ? "bg-[var(--success-bg)] text-[var(--primary-dark)]" : "text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-main)]"}`}
              >
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {activeTab === "empresa" && (
        <SettingCard title="Datos básicos de empresa" description="Puedes actualizar los datos visibles de la empresa sin modificar las emisiones ya registradas. El ID de empresa se mantiene en solo lectura para proteger las relaciones existentes.">
          {Object.entries({
            nombre: "Nombre",
            empresa_id: "Empresa ID",
            rut: "RUT",
            rubro: "Rubro",
            region: "Región",
            comuna: "Comuna",
            direccion: "Dirección",
            contacto: "Contacto",
            email: "Email",
            telefono: "Telefono",
            observaciones: "Observaciones",
          }).map(([field, label]) => (
            <Field key={field} label={label}>
              <TextInput value={config.empresa[field]} readOnly={field === "empresa_id"} onChange={(value) => update("empresa", field, value)} />
            </Field>
          ))}
        </SettingCard>
      )}

      {activeTab === "calculo" && (
        <SettingCard title="Parámetros de cálculo ambiental" description="Estos valores se aplican cuando los datos importados no incluyen toda la información necesaria o cuando el sistema debe calcular indicadores ambientales derivados.">
          <Field label="Unidad de emisiones preferida"><SelectInput value={config.calculo.unidad_emisiones} onChange={(v) => update("calculo", "unidad_emisiones", v)} options={["kg CO2e", "tCO2e"]} /></Field>
          <Field label="Unidad de volumen madera"><SelectInput value={config.calculo.unidad_volumen_madera} onChange={(v) => update("calculo", "unidad_volumen_madera", v)} options={["m3"]} /></Field>
          <Field label="Porcentaje de carbono por defecto"><TextInput type="number" value={config.calculo.porcentaje_carbono_default} onChange={(v) => update("calculo", "porcentaje_carbono_default", v)} /></Field>
          <Field label="Densidad madera por defecto kg/m3"><TextInput type="number" value={config.calculo.densidad_madera_default} onChange={(v) => update("calculo", "densidad_madera_default", v)} /></Field>
          <Field label="Factor electrico preferido"><TextInput value={config.calculo.factor_electrico_default} onChange={(v) => update("calculo", "factor_electrico_default", v)} /></Field>
          <Field label="Region electrica por defecto"><TextInput value={config.calculo.region_electrica_default} onChange={(v) => update("calculo", "region_electrica_default", v)} /></Field>
          <Field label="Redondeo de resultados"><SelectInput value={config.calculo.redondeo_decimales} onChange={(v) => update("calculo", "redondeo_decimales", Number(v))} options={[0, 1, 2]} /></Field>
          <SettingSwitch label="Mostrar balance neto" checked={config.calculo.mostrar_balance_neto} onChange={(v) => update("calculo", "mostrar_balance_neto", v)} />
          <SettingSwitch label="Permitir carbono almacenado" checked={config.calculo.permitir_co2_almacenado} onChange={(v) => update("calculo", "permitir_co2_almacenado", v)} />
        </SettingCard>
      )}

      {activeTab === "importaciones" && (
        <SettingCard title="Reglas de importación" description="Estas reglas reducen errores al cargar datos y permiten adaptar Carbono Zero a flujos de trabajo más estrictos o más flexibles.">
          <Field label="Modo de importación" help={config.importaciones.modo_importacion === "flexible" ? "Si un archivo trae empresa_id distinto, Carbono Zero usa la empresa activa y muestra advertencia." : "Si un archivo trae empresa_id distinto, Carbono Zero bloquea la importación."}><SelectInput value={config.importaciones.modo_importacion} onChange={(v) => update("importaciones", "modo_importacion", v)} options={["flexible", "estricto"]} /></Field>
          {Object.entries({
            crear_unidades_automaticamente: "Permitir crear unidades automáticamente",
            crear_lotes_automaticamente: "Permitir crear lotes automáticamente",
            permitir_actividades_sin_factor: "Permitir actividades sin factor",
            actualizar_registros_existentes: "Actualizar registros existentes",
            bloquear_duplicados: "Bloquear duplicados exactos",
            requerir_unidad_lote: "Requerir unidad para lotes",
            requerir_lote_actividad: "Requerir lote para actividades",
            permitir_evidencias_sin_vinculo: "Permitir evidencias sin vinculo especifico",
          }).map(([field, label]) => <SettingSwitch key={field} label={label} checked={config.importaciones[field]} onChange={(v) => update("importaciones", field, v)} />)}
        </SettingCard>
      )}

      {activeTab === "pasaporte" && (
        <SettingCard title="Criterios de Pasaporte Verde" description="Estos criterios definen cuando un lote puede calificarse como Pasaporte Verde o Pasaporte Verde Plus. Ajustarlos cambia el nivel de exigencia documental y ambiental.">
          <SettingSwitch label="Activar Pasaporte Verde" checked={config.pasaporte.pasaporte_activo} onChange={(v) => update("pasaporte", "pasaporte_activo", v)} />
          <SettingSwitch label="Requerir balance neto favorable" checked={config.pasaporte.requiere_balance_favorable} onChange={(v) => update("pasaporte", "requiere_balance_favorable", v)} />
          <SettingSwitch label="Requerir evidencia documental" checked={config.pasaporte.requiere_evidencia} onChange={(v) => update("pasaporte", "requiere_evidencia", v)} />
          <SettingSwitch label="Requerir trazabilidad completa" checked={config.pasaporte.requiere_trazabilidad} onChange={(v) => update("pasaporte", "requiere_trazabilidad", v)} />
          <Field label="Score minimo Pasaporte Verde"><TextInput type="number" value={config.pasaporte.score_verde} onChange={(v) => update("pasaporte", "score_verde", v)} /></Field>
          <Field label="Score minimo Pasaporte Verde Plus"><TextInput type="number" value={config.pasaporte.score_plus} onChange={(v) => update("pasaporte", "score_plus", v)} /></Field>
          <Field label="Score minimo confianza dato"><TextInput type="number" value={config.pasaporte.score_confianza_minimo} onChange={(v) => update("pasaporte", "score_confianza_minimo", v)} /></Field>
        </SettingCard>
      )}

      {activeTab === "evidencias" && (
        <SettingCard title="Reglas documentales" description="Las evidencias permiten respaldar cálculos, lotes, actividades y pasaportes. Una mayor cobertura documental mejora la confianza del dato. Subir una evidencia no la valida automáticamente.">
          <SettingSwitch label="Requerir evidencia para emitir pasaporte" checked={config.evidencias.requerida_pasaporte} onChange={(v) => update("evidencias", "requerida_pasaporte", v)} />
          <SettingSwitch label="Requerir evidencia para lotes críticos" checked={config.evidencias.requerida_lotes_criticos} onChange={(v) => update("evidencias", "requerida_lotes_criticos", v)} />
          <Field label="Umbral lote crítico kg CO2e"><TextInput type="number" value={config.evidencias.umbral_lote_critico} onChange={(v) => update("evidencias", "umbral_lote_critico", v)} /></Field>
          <Field label="Tamaño maximo archivo MB"><TextInput type="number" value={config.evidencias.max_file_size_mb} onChange={(v) => update("evidencias", "max_file_size_mb", v)} /></Field>
          <SettingSwitch label="Permitir evidencia corporativa" checked={config.evidencias.permitir_empresa} onChange={(v) => update("evidencias", "permitir_empresa", v)} />
          <SettingSwitch label="Permitir evidencia a nivel unidad" checked={config.evidencias.permitir_unidad} onChange={(v) => update("evidencias", "permitir_unidad", v)} />
          <SettingSwitch label="Permitir evidencia a nivel lote" checked={config.evidencias.permitir_lote} onChange={(v) => update("evidencias", "permitir_lote", v)} />
          <SettingSwitch label="Permitir evidencia a nivel emision" checked={config.evidencias.permitir_emision} onChange={(v) => update("evidencias", "permitir_emision", v)} />
          <div className="md:col-span-2">
            <p className="mb-3 text-sm font-semibold text-[#344054]">Formatos permitidos</p>
            <div className="flex flex-wrap gap-2">
              {["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"].map((format) => (
                <button key={format} type="button" onClick={() => toggleFormat(format)} className={`rounded-full border px-4 py-2 text-sm font-bold ${config.evidencias.formatos_permitidos.includes(format) ? "border-[#B7DEC9] bg-[var(--success-bg)] text-[var(--primary-dark)]" : "border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-muted)]"}`}>{format}</button>
              ))}
            </div>
          </div>
        </SettingCard>
      )}

      {activeTab === "reportes" && (
        <SettingCard title="Preferencias de reportes" description="Estas preferencias definen como se presentan los reportes ejecutivos y analiticos de la empresa.">
          <Field label="Agrupacion temporal por defecto"><SelectInput value={config.reportes.agrupacion_default} onChange={(v) => update("reportes", "agrupacion_default", v)} options={[{ value: "dia", label: "Dia" }, { value: "semana", label: "Semana" }, { value: "mes", label: "Mes" }, { value: "trimestre", label: "Trimestre" }, { value: "anio", label: "Año" }]} /></Field>
          <Field label="Período por defecto"><SelectInput value={config.reportes.periodo_default} onChange={(v) => update("reportes", "periodo_default", v)} options={[{ value: "ultimos_30_dias", label: "Últimos 30 días" }, { value: "ultimos_3_meses", label: "Últimos 3 meses" }, { value: "ultimos_6_meses", label: "Últimos 6 meses" }, { value: "ultimos_12_meses", label: "Últimos 12 meses" }, { value: "anio_actual", label: "Año actual" }]} /></Field>
          <Field label="Unidad visual de emisiones"><SelectInput value={config.reportes.unidad_visual_emisiones} onChange={(v) => update("reportes", "unidad_visual_emisiones", v)} options={["kg CO2e", "tCO2e"]} /></Field>
          <SettingSwitch label="Mostrar gráficos por categoría" checked={config.reportes.mostrar_categoria} onChange={(v) => update("reportes", "mostrar_categoria", v)} />
          <SettingSwitch label="Mostrar gráficos por unidad" checked={config.reportes.mostrar_unidad} onChange={(v) => update("reportes", "mostrar_unidad", v)} />
          <SettingSwitch label="Mostrar tabla detallada por defecto" checked={config.reportes.mostrar_tabla} onChange={(v) => update("reportes", "mostrar_tabla", v)} />
          <SettingSwitch label="Incluir lectura ejecutiva automática" checked={config.reportes.lectura_ejecutiva} onChange={(v) => update("reportes", "lectura_ejecutiva", v)} />
          <SettingSwitch label="Incluir equivalencias de orden de magnitud" checked={config.reportes.equivalencias} onChange={(v) => update("reportes", "equivalencias", v)} />
        </SettingCard>
      )}

      <section className="sticky bottom-4 z-10 rounded-3xl border border-[var(--border)] bg-[#F9FBF9]/95 p-4 shadow-[0_20px_60px_rgba(15,23,42,0.16)] backdrop-blur">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-[var(--text-main)]">{hasChanges ? "Cambios pendientes" : "Configuración lista"}</p>
            <p className="text-xs text-[var(--text-muted)]">{successMessage || "Los cambios se guardan por empresa activa y quedan listos para usarse en cálculos, importaciones y reportes."}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={restoreDefaults} className="inline-flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-3 text-sm font-bold text-[#475467]">
              <RotateCcw size={18} />
              Restaurar valores predeterminados
            </button>
            <button type="button" onClick={saveConfig} disabled={saving} className="inline-flex items-center gap-2 rounded-2xl border border-[var(--primary-dark)] bg-[var(--primary-dark)] px-5 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60">
              <Save size={18} />
              {saving ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

export default ConfiguracionPage;
