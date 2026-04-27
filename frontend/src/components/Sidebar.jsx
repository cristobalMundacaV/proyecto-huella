import {
  Database,
  LayoutDashboard,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

function Sidebar({
  activeDatasetId,
  datasets,
  fileName,
  loadingUpload,
  onCloseDataset,
  onFileUpload,
  onLoadDemo,
  onSelectDataset,
  uploadError,
}) {
  return (
    <aside className="w-full lg:w-72 min-h-auto lg:min-h-screen bg-slate-900 border-b border-slate-800 lg:border-b-0 lg:border-r p-4 sm:p-6 shrink-0">
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
            onChange={onFileUpload}
            className="hidden"
          />
        </label>

        <button
          type="button"
          onClick={onLoadDemo}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl bg-cyan-400/10 text-cyan-200 border border-cyan-400/20 hover:bg-cyan-400/20 transition"
        >
          <Sparkles size={18} />
          Cargar demo
        </button>
      </nav>

      <div className="mt-10 rounded-2xl bg-slate-950 border border-slate-800 p-4">
        <p className="text-xs text-slate-500">Dataset actual</p>
        <p className="text-sm font-semibold text-slate-200 mt-1">{fileName}</p>
        {loadingUpload && (
          <p className="text-xs text-emerald-300 mt-2">
            Procesando archivo...
          </p>
        )}
        {uploadError && <p className="text-xs text-red-300 mt-2">{uploadError}</p>}
      </div>

      <div className="mt-6">
        <p className="px-1 text-xs text-slate-500">Datasets cargados</p>
        <div className="mt-3 max-h-56 space-y-2 overflow-y-auto pr-1">
          {datasets.map((dataset) => {
            const isActive = dataset.id === activeDatasetId;

            return (
              <div
                key={dataset.id}
                className={`group flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm transition ${
                  isActive
                    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                    : "border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-700 hover:bg-slate-800"
                }`}
                title={dataset.name}
              >
                <button
                  type="button"
                  onClick={() => onSelectDataset(dataset)}
                  className="min-w-0 flex-1 truncate text-left font-semibold"
                >
                  {dataset.name}
                </button>
                <button
                  type="button"
                  onClick={(event) => onCloseDataset(event, dataset.id)}
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-xl border transition ${
                    isActive
                      ? "border-emerald-400/20 bg-slate-950/50 text-emerald-200 hover:bg-emerald-400/10"
                      : "border-slate-700 bg-slate-900 text-slate-400 hover:border-red-400/30 hover:bg-red-400/10 hover:text-red-200"
                  }`}
                  aria-label={`Cerrar ${dataset.name}`}
                  title={`Cerrar ${dataset.name}`}
                >
                  <X size={14} />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
