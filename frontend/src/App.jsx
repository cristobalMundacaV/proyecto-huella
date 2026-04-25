import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  Factory,
  LayoutDashboard,
  Upload,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import ComparacionEscenario from "./ComparacionEscenario";
import ExecutiveSummary from "./ExecutiveSummary";
import SimuladorOptimizacion from "./SimuladorOptimizacion";
import { api, getAiAdvisor, uploadDataFile } from "./services/api";
import { calculateRiskProfile } from "./utils/risk";

const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value));

const tooltipContentStyle = {
  backgroundColor: "#0F172A",
  border: "1px solid #1E293B",
  borderRadius: "12px",
  color: "#F8FAFC",
};

const activeBarStyle = {
  fill: "#CBD5E1",
  fillOpacity: 0.55,
  radius: [10, 10, 0, 0],
};

const getFileSignature = (file) => `${file.name}-${file.size}-${file.lastModified}`;

function optimizeScenario(rows) {
  let bestScenario = null;
  let evaluatedScenarios = 0;

  const currentTotal = rows.reduce(
    (acc, row) => acc + Number(row.emisiones),
    0
  );

  for (let dieselReduction = 0; dieselReduction <= 80; dieselReduction += 5) {
    for (
      let electricityIncrease = 0;
      electricityIncrease <= 60;
      electricityIncrease += 5
    ) {
      evaluatedScenarios += 1;
      const simulatedRows = rows.map((row) => {
        let cantidad = Number(row.cantidad);
        const actividad = String(row.actividad).toLowerCase();

        if (actividad === "diesel") {
          cantidad *= 1 - dieselReduction / 100;
        }

        if (actividad === "electricidad") {
          cantidad *= 1 + electricityIncrease / 100;
        }

        const emisiones = cantidad * Number(row.factor_emision);

        return {
          ...row,
          cantidad,
          emisiones,
        };
      });

      const simulatedTotal = simulatedRows.reduce(
        (acc, row) => acc + Number(row.emisiones),
        0
      );

      const reductionPct =
        currentTotal > 0
          ? ((currentTotal - simulatedTotal) / currentTotal) * 100
          : 0;

      if (!bestScenario || reductionPct > bestScenario.reductionPct) {
        bestScenario = {
          dieselReduction,
          electricityIncrease,
          currentTotal,
          evaluatedScenarios,
          simulatedTotal,
          reductionPct,
          rows: simulatedRows,
        };
      }
    }
  }

  return bestScenario;
}

function App() {
  const [data, setData] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [activeDatasetId, setActiveDatasetId] = useState(null);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [fileName, setFileName] = useState("Dataset interno");
  const [uploadError, setUploadError] = useState("");
  const [simulatedScenario, setSimulatedScenario] = useState(null);
  const [optimizedScenario, setOptimizedScenario] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [aiSource, setAiSource] = useState("");
  const [loadingAi, setLoadingAi] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    api.get("/dashboard/").then((response) => {
      const initialDataset = {
        id: "internal",
        name: "Dataset interno",
        data: response.data,
      };

      setData(response.data);
      setDatasets([initialDataset]);
      setActiveDatasetId(initialDataset.id);
    });
  }, []);

  const selectDataset = (dataset) => {
    setData(dataset.data);
    setFileName(dataset.name);
    setActiveDatasetId(dataset.id);
    setAiAnalysis("");
    setAiSource("");
    setSimulatedScenario(null);
    setOptimizedScenario(null);
  };

  const showToast = (message) => {
    setToast({ id: Date.now(), message });
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    const fileSignature = getFileSignature(file);
    const existingDataset = datasets.find(
      (dataset) => dataset.fileSignature === fileSignature
    );

    if (existingDataset) {
      showToast("El producto ya esta subido");
      selectDataset(existingDataset);
      event.target.value = "";
      return;
    }

    setLoadingUpload(true);
    setUploadError("");

    try {
      const uploadedData = await uploadDataFile(file);
      const uploadedDataset = {
        id: `${fileSignature}-${Date.now()}`,
        name: file.name,
        fileSignature,
        data: uploadedData,
      };

      setData(uploadedData);
      setFileName(file.name);
      setAiAnalysis("");
      setAiSource("");
      setSimulatedScenario(null);
      setOptimizedScenario(null);
      setDatasets((currentDatasets) => [
        ...currentDatasets,
        uploadedDataset,
      ]);
      setActiveDatasetId(uploadedDataset.id);
    } catch (error) {
      setUploadError(
        error.response?.data?.error || "No se pudo procesar el archivo."
      );
    } finally {
      setLoadingUpload(false);
      event.target.value = "";
    }
  };

  const handleOptimize = () => {
    const result = optimizeScenario(data.datos);
    setOptimizedScenario(result);
  };

  const recommendedScenario = useMemo(
    () => (data ? optimizeScenario(data.datos) : null),
    [data]
  );

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        Cargando Huella...
      </div>
    );
  }

  const empresas = Object.entries(data.emisiones_por_empresa).map(
    ([empresa, emisiones]) => ({
      empresa,
      emisiones,
    })
  );

  const actividades = Object.entries(data.emisiones_por_actividad).map(
    ([actividad, emisiones]) => ({
      actividad,
      emisiones,
    })
  );

  const empresaCritica = empresas[0]?.empresa || "Sin datos";
  const actividadCritica = actividades[0]?.actividad || "Sin datos";
  const riskProfile = calculateRiskProfile(data, recommendedScenario);
  const formatTooltipValue = (value) => [
    `${formatNumber(value)} kg CO2e`,
    "Emisiones",
  ];

  const handleAiAnalysis = async () => {
    try {
      setLoadingAi(true);

      const response = await getAiAdvisor({
        total_emisiones: data.total_emisiones,
        empresa_critica: empresaCritica,
        actividad_critica: actividadCritica,
        simulacion: simulatedScenario,
        optimizacion: optimizedScenario,
      });

      setAiAnalysis(response.analisis);
      setAiSource(response.fuente);
    } catch (error) {
      console.error(error);
      setAiAnalysis(
        error.response?.data?.error || "No se pudo generar el analisis IA."
      );
      setAiSource("");
    } finally {
      setLoadingAi(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Toast
        message={toast?.message}
        onClose={() => setToast(null)}
        toastKey={toast?.id}
      />

      <aside className="w-72 min-h-screen bg-slate-900 border-r border-slate-800 p-6 shrink-0">
        <div className="flex items-center gap-3 mb-10">
          <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
            <Database className="text-emerald-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold">Huella</h2>
            <p className="text-xs text-slate-400">Carbon Intelligence</p>
          </div>
        </div>

        <nav className="space-y-3">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl bg-emerald-400/10 text-emerald-300 border border-emerald-400/20">
            <LayoutDashboard size={18} />
            Dashboard
          </button>

          <label className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl bg-slate-800 text-slate-300 border border-slate-700 cursor-pointer hover:bg-slate-700 transition">
            <Upload size={18} />
            Cargar datos
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </nav>

        <div className="mt-10 rounded-2xl bg-slate-950 border border-slate-800 p-4">
          <p className="text-xs text-slate-500">Dataset actual</p>
          <p className="text-sm font-semibold text-slate-200 mt-1">
            {fileName}
          </p>
          {loadingUpload && (
            <p className="text-xs text-emerald-300 mt-2">
              Procesando archivo...
            </p>
          )}
          {uploadError && (
            <p className="text-xs text-red-300 mt-2">{uploadError}</p>
          )}
        </div>

        <div className="mt-6">
          <p className="px-1 text-xs text-slate-500">Datasets cargados</p>
          <div className="mt-3 max-h-56 space-y-2 overflow-y-auto pr-1">
            {datasets.map((dataset) => {
              const isActive = dataset.id === activeDatasetId;

              return (
                <button
                  key={dataset.id}
                  type="button"
                  onClick={() => selectDataset(dataset)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                    isActive
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                      : "border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-700 hover:bg-slate-800"
                  }`}
                  title={dataset.name}
                >
                  <span className="block truncate font-semibold">
                    {dataset.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </aside>

      <section className="flex-1 px-10 py-12 overflow-y-auto">
        <div className="max-w-7xl mx-auto space-y-8">
          <header>
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
                <Database className="text-emerald-400" />
              </div>
              <div>
                <h1 className="text-4xl font-bold">Huella</h1>
                <p className="text-slate-400">
                  Inteligencia para medir, analizar y optimizar la huella de
                  carbono empresarial.
                </p>
              </div>
            </div>
          </header>

          <ExecutiveSummary
            actividadCritica={actividadCritica}
            empresaCritica={empresaCritica}
            optimizedScenario={recommendedScenario}
            riskProfile={riskProfile}
          />

          <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <KpiCard
              icon={<Activity />}
              title="Emisiones Totales"
              value={`${formatNumber(data.total_emisiones)} kg CO2e`}
            />
            <KpiCard
              icon={<Factory />}
              title="Empresa Critica"
              value={empresaCritica}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Actividad Critica"
              value={actividadCritica}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Score de Riesgo"
              value={`${formatNumber(riskProfile.score, 0)}/100`}
              detail={riskProfile.label}
              tone={riskProfile}
            />
          </section>

          <section className="rounded-3xl bg-emerald-400/10 border border-emerald-400/20 p-6">
            <h2 className="text-xl font-semibold mb-2">Insight automatico</h2>
            <p className="text-emerald-300">
              La actividad <strong>{actividadCritica}</strong> concentra el
              mayor impacto ambiental del dataset analizado.
            </p>
          </section>

          <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-6 shadow-xl">
            <div>
              <p className="text-emerald-400 text-sm font-semibold">
                Centro de decisiones
              </p>
              <h2 className="text-2xl font-bold">
                Compara, simula y optimiza decisiones climaticas
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                Flujo recomendado: comparar escenarios, simular decisiones y
                dejar que Huella encuentre la mejor reduccion.
              </p>
            </div>

            <ComparacionEscenario />

            <SimuladorOptimizacion
              data={data}
              onSimulationChange={setSimulatedScenario}
            />

            <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 space-y-6">
              <div>
                <p className="text-emerald-400 text-sm font-semibold">
                  Optimizacion automatica
                </p>
                <h3 className="text-xl font-bold">
                  Huella recomienda el mejor escenario
                </h3>
              </div>

              <button
                type="button"
                onClick={handleOptimize}
                className="px-6 py-3 rounded-2xl bg-emerald-500 text-slate-950 font-bold hover:bg-emerald-400 transition"
              >
                Optimizar automaticamente
              </button>

              {optimizedScenario && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-2xl bg-slate-950 border border-slate-800 p-5">
                    <p className="text-slate-400 text-sm">Reducir diesel</p>
                    <h3 className="text-2xl font-bold text-emerald-300">
                      {optimizedScenario.dieselReduction}%
                    </h3>
                  </div>

                  <div className="rounded-2xl bg-slate-950 border border-slate-800 p-5">
                    <p className="text-slate-400 text-sm">
                      Ajustar electricidad
                    </p>
                    <h3 className="text-2xl font-bold text-cyan-300">
                      +{optimizedScenario.electricityIncrease}%
                    </h3>
                  </div>

                  <div className="rounded-2xl bg-emerald-400/10 border border-emerald-400/20 p-5">
                    <p className="text-slate-400 text-sm">
                      Reduccion estimada
                    </p>
                    <h3 className="text-2xl font-bold text-emerald-300">
                      {formatNumber(optimizedScenario.reductionPct, 1)}%
                    </h3>
                  </div>
                </div>
              )}

              {optimizedScenario && (
                <div className="rounded-2xl bg-cyan-400/10 border border-cyan-400/20 p-5 space-y-4">
                  <p className="text-cyan-300 text-sm font-semibold">
                    Decision generada por Huella
                  </p>
                  <p className="text-slate-200 mt-2 leading-7">
                    Huella evaluo{" "}
                    <strong>{optimizedScenario.evaluatedScenarios}</strong>{" "}
                    escenarios posibles y selecciono la combinacion con mayor
                    reduccion neta: reducir diesel en{" "}
                    <strong>{optimizedScenario.dieselReduction}%</strong> y
                    ajustar la electricidad en{" "}
                    <strong>{optimizedScenario.electricityIncrease}%</strong>.
                    Esto permitiria bajar las emisiones desde{" "}
                    <strong>
                      {formatNumber(optimizedScenario.currentTotal, 1)} kg CO2e
                    </strong>{" "}
                    a{" "}
                    <strong>
                      {formatNumber(optimizedScenario.simulatedTotal, 1)} kg
                      CO2e
                    </strong>
                    .
                  </p>
                  <p className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">
                    Recomendacion: ejecutar un piloto con esta configuracion y
                    monitorear la reduccion real antes de escalarla al resto de
                    la operacion.
                  </p>
                </div>
              )}
              </div>
          </section>

          <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-xl">
            <div>
              <p className="text-emerald-400 text-sm font-semibold">
                Huella AI
              </p>
              <h2 className="text-2xl font-bold">
                Analisis estrategico generado por IA
              </h2>
            </div>

            <button
              type="button"
              onClick={handleAiAnalysis}
              disabled={loadingAi}
              className="px-6 py-3 rounded-2xl bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 transition disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {loadingAi ? "Analizando..." : "Generar analisis IA"}
            </button>

            {aiAnalysis && (
              <div className="rounded-2xl bg-cyan-400/10 border border-cyan-400/20 p-5 whitespace-pre-line text-slate-200 leading-7">
                {aiSource === "huella_engine" && (
                  <p className="mb-4 text-xs font-semibold text-emerald-300">
                    Generado por motor analitico Huella
                  </p>
                )}
                {aiSource === "openai" && (
                  <p className="mb-4 text-xs font-semibold text-cyan-300">
                    Generado con OpenAI
                  </p>
                )}
                {aiAnalysis}
              </div>
            )}
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title="Emisiones por empresa">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={empresas}>
                  <XAxis dataKey="empresa" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" tickFormatter={formatNumber} />
                  <Tooltip
                    contentStyle={tooltipContentStyle}
                    cursor={false}
                    formatter={formatTooltipValue}
                    labelStyle={{ color: "#F8FAFC" }}
                    itemStyle={{ color: "#00D4AA" }}
                  />
                  <Bar
                    activeBar={activeBarStyle}
                    dataKey="emisiones"
                    fill="#00D4AA"
                    radius={[10, 10, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Emisiones por actividad">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={actividades}>
                  <XAxis dataKey="actividad" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" tickFormatter={formatNumber} />
                  <Tooltip
                    contentStyle={tooltipContentStyle}
                    cursor={false}
                    formatter={formatTooltipValue}
                    labelStyle={{ color: "#F8FAFC" }}
                    itemStyle={{ color: "#00D4AA" }}
                  />
                  <Bar
                    activeBar={activeBarStyle}
                    dataKey="emisiones"
                    fill="#38BDF8"
                    radius={[10, 10, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </section>

          <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6">
            <h2 className="text-xl font-semibold mb-4">Datos procesados</h2>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="text-left py-3">Empresa</th>
                    <th className="text-left py-3">Actividad</th>
                    <th className="text-right py-3">Cantidad</th>
                    <th className="text-right py-3">Factor</th>
                    <th className="text-right py-3">Emisiones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.datos.map((row, index) => (
                    <tr key={index} className="border-b border-slate-800/60">
                      <td className="py-3">{row.empresa}</td>
                      <td className="py-3">{row.actividad}</td>
                      <td className="py-3 text-right">
                        {formatNumber(row.cantidad)}
                      </td>
                      <td className="py-3 text-right">
                        {formatNumber(row.factor_emision, 4)}
                      </td>
                      <td className="py-3 text-right font-semibold text-emerald-300">
                        {formatNumber(row.emisiones)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function KpiCard({ detail, icon, title, tone, value }) {
  const toneClasses = tone
    ? `${tone.background} ${tone.border}`
    : "bg-slate-900 border-slate-800";

  return (
    <div className={`rounded-3xl border p-6 shadow-xl ${toneClasses}`}>
      <div className="text-emerald-400 mb-4">{icon}</div>
      <p className="text-slate-400 text-sm">{title}</p>
      <h3 className={`text-2xl font-bold mt-1 ${tone?.color || ""}`}>
        {value}
      </h3>
      {detail && <p className={`mt-2 text-sm font-semibold ${tone?.color}`}>{detail}</p>}
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
      <h2 className="text-xl font-semibold mb-4">{title}</h2>
      {children}
    </div>
  );
}

function Toast({ message, onClose, toastKey }) {
  useEffect(() => {
    if (!message) {
      return undefined;
    }

    const timeoutId = window.setTimeout(onClose, 2800);

    return () => window.clearTimeout(timeoutId);
  }, [message, onClose, toastKey]);

  if (!message) {
    return null;
  }

  return (
    <div className="fixed right-8 top-8 z-50 w-[460px] max-w-[calc(100vw-4rem)] rounded-3xl border border-emerald-400/30 bg-slate-900 px-7 py-6 text-slate-100 shadow-2xl shadow-slate-950/60">
      <div className="flex items-start gap-4">
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
          <CheckCircle2 size={26} className="text-emerald-400" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-lg font-bold leading-6 text-emerald-200">
            {message}
          </p>
          <p className="mt-2 text-sm leading-5 text-slate-400">
            Seleccionamos el dataset que ya estaba cargado.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
          aria-label="Cerrar notificacion"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}

export default App;
