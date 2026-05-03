import { Boxes } from "lucide-react";

function LotesHeader() {
  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
          <Boxes className="text-emerald-400" />
        </div>
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold">Lotes</h1>
          <p className="text-slate-400">
            Trazabilidad base para el Pasaporte Verde de madera.
          </p>
        </div>
      </div>
    </header>
  );
}

export default LotesHeader;
