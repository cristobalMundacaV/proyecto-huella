import { useEffect, useState } from "react";
import { BadgeCheck, Boxes, Loader2, ShieldCheck } from "lucide-react";

import { getVerificacionLote } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

function getLoteIdFromPath() {
  const [, route, idLote] = window.location.pathname.split("/");
  return route === "verificar" ? decodeURIComponent(idLote || "") : "";
}

function PublicMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-words text-lg font-bold text-slate-100">
        {value}
      </p>
    </div>
  );
}

function VerificarLote() {
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const idLote = getLoteIdFromPath();

  useEffect(() => {
    let isCancelled = false;

    async function loadVerification() {
      try {
        const data = await getVerificacionLote(idLote);

        if (!isCancelled) {
          setVerification(data);
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.status === 404
              ? "No existe un Pasaporte Verde verificable para este lote."
              : "No se pudo verificar el Pasaporte Verde."
          );
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadVerification();

    return () => {
      isCancelled = true;
    };
  }, [idLote]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex items-center gap-3 text-slate-300">
          <Loader2 className="animate-spin" size={22} />
          Verificando lote...
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
        <section className="max-w-lg rounded-3xl border border-red-400/20 bg-red-400/10 p-6 text-red-100">
          <h1 className="text-2xl font-bold">Verificacion no disponible</h1>
          <p className="mt-3 text-sm">{error}</p>
        </section>
      </main>
    );
  }

  const emittedAt = new Date(verification.fecha_emision).toLocaleDateString(
    "es-CL"
  );

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-6 lg:px-10">
      <section className="mx-auto max-w-5xl space-y-6">
        <header className="rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-6 sm:p-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-3 text-emerald-200">
                <ShieldCheck size={24} />
                <p className="text-sm font-bold uppercase tracking-wide">
                  Pasaporte verificable
                </p>
              </div>
              <h1 className="mt-3 text-3xl font-bold sm:text-4xl">
                {verification.id_lote}
              </h1>
              <p className="mt-3 max-w-2xl text-slate-300">
                El QR permite validar que el pasaporte no es solo un PDF, sino
                un registro trazable del sistema.
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-400/20 bg-slate-950/60 px-5 py-4 text-emerald-200">
              <div className="flex items-center gap-2 font-bold">
                <BadgeCheck size={20} />
                {verification.estado_pasaporte}
              </div>
            </div>
          </div>
        </header>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <PublicMetric label="Fecha de emision" value={emittedAt} />
          <PublicMetric label="Aserradero" value={verification.aserradero} />
          <PublicMetric label="Especie" value={verification.especie} />
          <PublicMetric
            label="Volumen"
            value={`${formatNumber(Number(verification.volumen_m3 || 0))} m3`}
          />
          <PublicMetric
            label="Confianza del dato"
            value={`${verification.estado_confianza} (${formatNumber(
              Number(verification.confianza_score || 0),
              0
            )}%)`}
          />
        </section>

        <section className="rounded-3xl border border-slate-800 bg-slate-900 p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-emerald-300">
              <Boxes size={22} />
            </div>
            <h2 className="text-xl font-bold">Resumen climatico del lote</h2>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <PublicMetric
              label="Emisiones generadas"
              value={`${formatNumber(
                Number(verification.emisiones_generadas_kg_co2e || 0)
              )} kg CO2e`}
            />
            <PublicMetric
              label="CO2 almacenado"
              value={`${formatNumber(
                Number(verification.co2_almacenado_kg || 0)
              )} kg`}
            />
            <PublicMetric
              label="Balance neto"
              value={`${formatNumber(
                Number(verification.balance_neto_kg_co2e || 0)
              )} kg CO2e`}
            />
          </div>

          <p className="mt-5 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
            {verification.descripcion_balance}
          </p>
        </section>
      </section>
    </main>
  );
}

export default VerificarLote;
