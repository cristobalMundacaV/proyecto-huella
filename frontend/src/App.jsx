import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  Factory,
  Menu,
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

import AiAdvisor from "./components/AiAdvisor";
import ChartCard from "./components/ChartCard";
import DataTable from "./components/DataTable";
import DecisionCenter from "./components/DecisionCenter";
import KpiCard from "./components/KpiCard";
import Sidebar from "./components/Sidebar";
import Toast from "./components/Toast";
import ExecutiveSummary from "./ExecutiveSummary";
import {
  api,
  getAiAdvisor,
  optimizeScenarioApi,
  uploadDataFile,
} from "./services/api";
import { formatNumber } from "./utils/formatters";
import { optimizeScenario } from "./utils/optimizer";
import { calculateRiskProfile } from "./utils/risk";

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
const DATASETS_STORAGE_KEY = "huella.datasets.v1";

function readStoredDatasetState() {
  const storedState = window.localStorage.getItem(DATASETS_STORAGE_KEY);

  if (!storedState) {
    return null;
  }

  try {
    const parsedState = JSON.parse(storedState);
    const restoredDatasets = parsedState.datasets || [];
    const activeDataset =
      restoredDatasets.find(
        (dataset) => dataset.id === parsedState.activeDatasetId
      ) || restoredDatasets[0];

    if (!activeDataset) {
      return null;
    }

    return {
      activeDataset,
      activeDatasetId: activeDataset.id,
      datasets: restoredDatasets,
    };
  } catch (error) {
    console.error(error);
    window.localStorage.removeItem(DATASETS_STORAGE_KEY);
    return null;
  }
}

function App() {
  const [initialDatasetState] = useState(readStoredDatasetState);
  const [data, setData] = useState(
    () => initialDatasetState?.activeDataset.data || null
  );
  const [datasets, setDatasets] = useState(
    () => initialDatasetState?.datasets || []
  );
  const [activeDatasetId, setActiveDatasetId] = useState(
    () => initialDatasetState?.activeDatasetId || null
  );
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [fileName, setFileName] = useState(
    () => initialDatasetState?.activeDataset.name || "Dataset interno"
  );
  const [uploadError, setUploadError] = useState("");
  const [simulatedScenario, setSimulatedScenario] = useState(null);
  const [optimizedScenario, setOptimizedScenario] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [aiSource, setAiSource] = useState("");
  const [loadingAi, setLoadingAi] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (data) {
      return;
    }

    let isCancelled = false;

    const loadInitialDataset = async () => {
      try {
        const response = await api.get("/dashboard/");
        const initialDataset = {
          id: "internal",
          name: "Dataset interno",
          data: response.data,
        };

        if (isCancelled) {
          return;
        }

        setData(response.data);
        setDatasets([initialDataset]);
        setActiveDatasetId(initialDataset.id);
      } catch (error) {
        if (!isCancelled) {
          setUploadError(
            error.response?.data?.error || "No se pudo cargar el dataset interno."
          );
        }
      }
    };

    loadInitialDataset();

    return () => {
      isCancelled = true;
    };
  }, [data]);

  useEffect(() => {
    if (!datasets.length || !activeDatasetId) {
      return;
    }

    window.localStorage.setItem(
      DATASETS_STORAGE_KEY,
      JSON.stringify({ activeDatasetId, datasets })
    );
  }, [activeDatasetId, datasets]);

  const selectDataset = (dataset) => {
    setData(dataset.data);
    setFileName(dataset.name);
    setActiveDatasetId(dataset.id);
    setAiAnalysis("");
    setAiSource("");
    setSimulatedScenario(null);
    setOptimizedScenario(null);
  };

  const clearDatasetDerivedState = () => {
    setAiAnalysis("");
    setAiSource("");
    setSimulatedScenario(null);
    setOptimizedScenario(null);
  };

  const closeDataset = (event, datasetId) => {
    event.stopPropagation();

    setDatasets((currentDatasets) => {
      const nextDatasets = currentDatasets.filter(
        (dataset) => dataset.id !== datasetId
      );

      if (datasetId === activeDatasetId) {
        const fallbackDataset = nextDatasets[0];

        if (fallbackDataset) {
          setData(fallbackDataset.data);
          setFileName(fallbackDataset.name);
          setActiveDatasetId(fallbackDataset.id);
        } else {
          api
            .get("/dashboard/")
            .then((response) => {
              const internalDataset = {
                id: "internal",
                name: "Dataset interno",
                data: response.data,
              };

              setData(response.data);
              setFileName(internalDataset.name);
              setDatasets([internalDataset]);
              setActiveDatasetId(internalDataset.id);
            })
            .catch((error) => {
              setUploadError(
                error.response?.data?.error ||
                  "No se pudo restaurar el dataset interno."
              );
            });
        }

        clearDatasetDerivedState();
      }

      return nextDatasets;
    });
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

  const handleLoadDemo = async () => {
    setLoadingUpload(true);
    setUploadError("");

    try {
      const response = await api.get("/dashboard/");
      const demoDataset = {
        id: "demo",
        name: "Escenario demo",
        data: response.data,
      };

      setData(response.data);
      setFileName(demoDataset.name);
      setAiAnalysis("");
      setAiSource("");
      setSimulatedScenario(null);
      setOptimizedScenario(null);
      setDatasets((currentDatasets) => {
        const withoutDemo = currentDatasets.filter(
          (dataset) => dataset.id !== demoDataset.id
        );
        return [demoDataset, ...withoutDemo];
      });
      setActiveDatasetId(demoDataset.id);
      showToast("Escenario de demostracion cargado");
    } catch (error) {
      setUploadError(
        error.response?.data?.error || "No se pudo cargar el escenario demo."
      );
    } finally {
      setLoadingUpload(false);
    }
  };

  const handleOptimize = async () => {
    try {
      const result = await optimizeScenarioApi(data.datos);
      setOptimizedScenario(result);
    } catch (error) {
      console.error(error);
      setOptimizedScenario(optimizeScenario(data.datos));
    }
  };

  const handleExportReport = () => {
    window.print();
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
  const validationSummary = {
    records: data.datos.length,
    errors: 0,
    activities: new Set(data.datos.map((row) => row.actividad)).size,
  };
  const formatTooltipValue = (value) => [
    `${formatNumber(value)} kg CO2e`,
    "Emisiones",
  ];

  const handleAiAnalysis = async () => {
    try {
      setLoadingAi(true);
      const analysisOptimizationScenario =
        optimizedScenario || recommendedScenario;

      const response = await getAiAdvisor({
        total_emisiones: data.total_emisiones,
        empresa_critica: empresaCritica,
        actividad_critica: actividadCritica,
        simulacion: simulatedScenario,
        optimizacion: analysisOptimizationScenario,
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
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col lg:flex-row">
      <Toast
        message={toast?.message}
        onClose={() => setToast(null)}
        toastKey={toast?.id}
      />

      <button
        type="button"
        onClick={() => setMobileMenuOpen(true)}
        className="fixed right-4 top-4 z-50 rounded-2xl border border-slate-700 bg-slate-900/90 p-3 text-slate-100 shadow-xl backdrop-blur lg:hidden"
      >
        <Menu size={22} />
      </button>

      <div className="hidden lg:block">
        <Sidebar
          activeDatasetId={activeDatasetId}
          datasets={datasets}
          fileName={fileName}
          loadingUpload={loadingUpload}
          onCloseDataset={closeDataset}
          onFileUpload={handleFileUpload}
          onLoadDemo={handleLoadDemo}
          onSelectDataset={selectDataset}
          uploadError={uploadError}
        />
      </div>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />

          <div className="absolute right-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-l border-slate-800 bg-slate-900 shadow-2xl">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              className="absolute right-4 top-4 rounded-2xl border border-slate-700 bg-slate-950 p-3 text-slate-200"
            >
              <X size={20} />
            </button>

            <Sidebar
              activeDatasetId={activeDatasetId}
              datasets={datasets}
              fileName={fileName}
              loadingUpload={loadingUpload}
              onCloseDataset={closeDataset}
              onFileUpload={(event) => {
                handleFileUpload(event);
                setMobileMenuOpen(false);
              }}
              onLoadDemo={() => {
                handleLoadDemo();
                setMobileMenuOpen(false);
              }}
              onSelectDataset={(dataset) => {
                selectDataset(dataset);
                setMobileMenuOpen(false);
              }}
              uploadError={uploadError}
            />
          </div>
        </div>
      )}

      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-12 overflow-y-auto">
        <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
          <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
                <Database className="text-emerald-400" />
              </div>
              <div>
                <h1 className="text-3xl sm:text-4xl font-bold">Huella</h1>
                <p className="text-slate-400">
                  Inteligencia para medir, analizar y optimizar la huella de
                  carbono empresarial.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleExportReport}
              className="w-full sm:w-fit rounded-2xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-slate-200 transition hover:border-emerald-400/30 hover:bg-emerald-400/10 hover:text-emerald-200"
            >
              Exportar reporte
            </button>
          </header>

          <ExecutiveSummary
            actividadCritica={actividadCritica}
            empresaCritica={empresaCritica}
            optimizedScenario={recommendedScenario}
            riskProfile={riskProfile}
            validationSummary={validationSummary}
          />

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
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

          <section className="rounded-3xl bg-emerald-400/10 border border-emerald-400/20 p-4 sm:p-6">
            <h2 className="text-xl font-semibold mb-2">Insight automatico</h2>
            <p className="text-emerald-300">
              La actividad <strong>{actividadCritica}</strong> concentra el
              mayor impacto ambiental del dataset analizado.
            </p>
          </section>

          <DecisionCenter
            data={data}
            optimizedScenario={optimizedScenario}
            onOptimize={handleOptimize}
            onSimulationChange={setSimulatedScenario}
          />

          <AiAdvisor
            aiAnalysis={aiAnalysis}
            aiSource={aiSource}
            loadingAi={loadingAi}
            onGenerateAnalysis={handleAiAnalysis}
          />

          <section className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
            <ChartCard title="Emisiones por empresa">
              <div className="h-64 sm:h-72 lg:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
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
              </div>
            </ChartCard>

            <ChartCard title="Emisiones por actividad">
              <div className="h-64 sm:h-72 lg:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
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
              </div>
            </ChartCard>
          </section>

          <DataTable rows={data.datos} />
        </div>
      </section>
    </main>
  );
}

export default App;
