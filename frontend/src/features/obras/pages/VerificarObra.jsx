import { useEffect, useState } from "react";
import { BadgeCheck, Boxes, Loader2, ShieldCheck } from "lucide-react";
import { useParams } from "react-router-dom";

import { getVerificacionObra } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

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

function VerificarObra() {
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { codigo: codigoObra } = useParams();

  useEffect(() => {
    let isCancelled = false;

    async function loadVerification() {
      try {
        const data = await getVerificacionObra(codigoObra);

        if (!isCancelled) {
          setVerification(data);
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.status === 404
              ? "No existe una ficha ambiental verificable para esta obra."
              : "No se pudo verificar la ficha ambiental."
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
  }, [codigoObra]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex items-center gap-3 text-slate-300">
          <Loader2 className="animate-spin" size={22} />
          Verificando obra...
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

  const emittedAt = verification.fecha_emision
    ? new Date(verification.fecha_emision).toLocaleDateString("es-CL")
    : "No informado";
  const resumen = verification.resumen || {};

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-6 lg:px-10">
      <section className="mx-auto max-w-5xl space-y-6">
        <header className="rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-6 sm:p-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-3 text-emerald-200">
                <ShieldCheck size={24} />
                <p className="text-sm font-bold uppercase tracking-wide">
                  Ficha verificable
                </p>
              </div>
              <h1 className="mt-3 text-3xl font-bold sm:text-4xl">
                {verification.codigo_obra}
              </h1>
              <p className="mt-3 max-w-2xl text-slate-300">
                El QR permite validar que la ficha no es solo un PDF, sino
                un registro trazable del sistema.
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-400/20 bg-slate-950/60 px-5 py-4 text-emerald-200">
              <div className="flex items-center gap-2 font-bold">
                <BadgeCheck size={20} />
                {verification.estado_ficha_ambiental || verification.estado || "Verificada"}
              </div>
            </div>
          </div>
        </header>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <PublicMetric label="Fecha de emision" value={emittedAt} />
          <PublicMetric label="organizacion / proveedor" value={verification.organizacion} />
          <PublicMetric label="Material / tipo de obra" value={verification.tipo_proyecto || verification.obra} />
          <PublicMetric
            label="Cantidad base / superficie"
            value={`${formatNumber(Number(verification.superficie_m2 || 0))} m2`}
          />
          <PublicMetric
            label="Confianza del dato"
            value={`${verification.estado_confianza || "Pendiente"} (${formatNumber(
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
            <h2 className="text-xl font-bold">Resumen climático de obra</h2>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <PublicMetric
              label="Emisiones generadas"
              value={`${formatNumber(
                Number(resumen.total_emisiones || verification.emisiones_generadas_kg_co2e || 0)
              )} kg CO2e`}
            />
            <PublicMetric
              label="Balance ambiental"
              value={`${formatNumber(
                Number(verification.balance_ambiental_kg || 0)
              )} kg`}
            />
            <PublicMetric
              label="Balance neto"
              value={`${formatNumber(
                Number(resumen.total_emisiones || verification.balance_neto_kg_co2e || 0)
              )} kg CO2e`}
            />
          </div>

          <p className="mt-5 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
            {verification.descripcion_balance || verification.mensaje || resumen.insight}
          </p>
        </section>
      </section>
    </main>
  );
}

export default VerificarObra;
