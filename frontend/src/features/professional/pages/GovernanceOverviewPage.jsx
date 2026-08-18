import {
  useEffect,
  useRef,
  useState,
} from "react";

import { Link } from "react-router-dom";

import {
  AlertTriangle,
  ArrowRight,
  BookOpenCheck,
  ClipboardCheck,
  Database,
  FileCheck2,
  Scale,
  ShieldCheck,
} from "lucide-react";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  EmptyState,
} from "@/shared/ui";

import {
  getDiscrepancies,
  getDossiers,
  getProfessionalReviews,
} from "../api/professionalV2Api";

import {
  DossierLink,
  State,
  isOpenDiscrepancy,
  reviewReference,
} from "../components/GovernanceShared";


const resource = (
  status = "loading",
  data = []
) => ({
  status,
  data,
});


export default function GovernanceOverviewPage() {
  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const [
    state,
    setState,
  ] = useState({
    scopeKey: "",
    reviews: resource(),
    discrepancies:
      resource(),
    dossiers: resource(),
  });

  const requestRef =
    useRef(0);


  useEffect(() => {
    if (!activeOrganizacionId) {
      return undefined;
    }

    const scopeKey =
      String(
        activeOrganizacionId
      );

    const requestId =
      ++requestRef.current;

    setState({
      scopeKey,
      reviews: resource(),
      discrepancies:
        resource(),
      dossiers: resource(),
    });

    Promise.allSettled([
      getProfessionalReviews(
        activeOrganizacionId,
        {
          estado:
            "pendiente",
        }
      ),

      getDiscrepancies(
        activeOrganizacionId
      ),

      getDossiers(
        activeOrganizacionId
      ),
    ]).then(
      ([
        reviews,
        discrepancies,
        dossiers,
      ]) => {
        if (
          requestRef.current !==
          requestId
        ) {
          return;
        }

        setState({
          scopeKey,

          reviews:
            reviews.status ===
              "fulfilled"
              ? resource(
                "ready",
                reviews.value
              )
              : resource(
                "error"
              ),

          discrepancies:
            discrepancies.status ===
              "fulfilled"
              ? resource(
                "ready",
                discrepancies.value
              )
              : resource(
                "error"
              ),

          dossiers:
            dossiers.status ===
              "fulfilled"
              ? resource(
                "ready",
                dossiers.value
              )
              : resource(
                "error"
              ),
        });
      }
    );

    return () => {
      requestRef.current += 1;
    };
  }, [
    activeOrganizacionId,
  ]);


  const requestedScopeKey =
    activeOrganizacionId
      ? String(
        activeOrganizacionId
      )
      : "";


  if (
    state.scopeKey !==
    requestedScopeKey
  ) {
    return (
      <PlatformLoader
        compact
        title="Cargando gobernanza"
        description="Estamos preparando revisiones, discrepancias y expedientes."
      />
    );
  }


  const openDiscrepancies =
    state.discrepancies
      .status === "ready"
      ? state.discrepancies.data.filter(
        isOpenDiscrepancy
      )
      : [];


  const activeDossiers =
    state.dossiers.status ===
      "ready"
      ? state.dossiers.data.filter(
        (item) =>
          item.estado !==
          "cerrado"
      )
      : [];


  const attention = [];


  if (
    state.reviews.status ===
    "ready"
  ) {
    state.reviews.data.forEach(
      (review) =>
        attention.push({
          kind: "review",
          item: review,
        })
    );
  }


  if (
    state.discrepancies
      .status === "ready"
  ) {
    openDiscrepancies.forEach(
      (item) =>
        attention.push({
          kind:
            "discrepancy",
          item,
        })
    );
  }


  if (
    state.dossiers.status ===
    "ready"
  ) {
    state.dossiers.data
      .filter(
        (item) =>
          item.estado ===
          "requiere_antecedentes"
      )
      .forEach((item) =>
        attention.push({
          kind: "dossier",
          item,
        })
      );
  }


  const visibleAttention =
    attention.slice(0, 5);


  const resources = [
    state.reviews,
    state.discrepancies,
    state.dossiers,
  ];


  const anyLoading =
    resources.some(
      (item) =>
        item.status ===
        "loading"
    );


  const anyError =
    resources.some(
      (item) =>
        item.status ===
        "error"
    );


  const allReady =
    resources.every(
      (item) =>
        item.status ===
        "ready"
    );


  return (
    <main className="space-y-6">

      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="max-w-3xl">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
            Control · Gobernanza ambiental
          </p>

          <h1 className="mt-2 text-3xl font-black">
            Gobernanza
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">
            Controla revisiones,
            discrepancias, expedientes y
            decisiones profesionales sin
            perder trazabilidad ni
            antecedentes históricos.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <HeroMetric
              value={
                state.reviews
                  .status ===
                  "ready"
                  ? state.reviews
                    .data.length
                  : "—"
              }
              label="revisiones pendientes"
            />

            <HeroMetric
              value={
                state.discrepancies
                  .status ===
                  "ready"
                  ? openDiscrepancies.length
                  : "—"
              }
              label="discrepancias abiertas"
              warning
            />

            <HeroMetric
              value={
                state.dossiers
                  .status ===
                  "ready"
                  ? activeDossiers.length
                  : "—"
              }
              label="expedientes activos"
            />
          </div>
        </div>
      </section>


      <section
        className="grid gap-4 md:grid-cols-3"
        aria-label="Resumen de gobernanza"
      >
        <Metric
          icon={ClipboardCheck}
          label="Revisiones pendientes"
          resourceState={
            state.reviews
          }
          value={
            state.reviews.data
              .length
          }
          to="/gobernanza/revision"
          tone="emerald"
        />

        <Metric
          icon={AlertTriangle}
          label="Discrepancias abiertas"
          resourceState={
            state.discrepancies
          }
          value={
            openDiscrepancies.length
          }
          to="/gobernanza/calidad"
          tone="amber"
        />

        <Metric
          icon={FileCheck2}
          label="Expedientes activos"
          resourceState={
            state.dossiers
          }
          value={
            activeDossiers.length
          }
          to="/gobernanza/expedientes"
          tone="sky"
        />
      </section>


      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Prioridad de control
          </p>

          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            Requiere atención
          </h2>

          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Trabajo formal que necesita
            revisión, antecedentes o una
            decisión profesional.
          </p>
        </div>


        {anyLoading &&
          !visibleAttention.length ? (
          <PlatformLoader
            compact
            title="Revisando pendientes"
            description="Comprobando los recursos de gobernanza disponibles."
          />
        ) : !visibleAttention.length &&
          anyError ? (
          <article className="rounded-[22px] border border-amber-200 bg-amber-50/60 p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle
                className="mt-0.5 text-amber-700"
                size={20}
              />

              <div>
                <p className="font-black text-amber-950">
                  Atención no completamente
                  disponible
                </p>

                <p className="mt-1 text-sm leading-6 text-amber-900/70">
                  Uno o más recursos no
                  pudieron verificarse. Los
                  recursos disponibles siguen
                  visibles.
                </p>
              </div>
            </div>
          </article>
        ) : !visibleAttention.length &&
          allReady ? (
          <EmptyState
            icon={ShieldCheck}
            title="No hay elementos pendientes registrados"
            description="No existen pendientes conocidos en los recursos consultados. Esto no certifica por sí solo que toda la operación esté validada."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))]"
          />
        ) : (
          <div className="grid gap-3">
            {visibleAttention.map(
              ({
                kind,
                item,
              }) => {
                if (
                  kind ===
                  "review"
                ) {
                  const reference =
                    reviewReference(
                      item
                    );

                  return (
                    <AttentionCard
                      key={`r-${item.id}`}
                      icon={
                        ClipboardCheck
                      }
                      title={
                        reference.title
                      }
                      description="Revisión profesional pendiente"
                      to="/gobernanza/revision"
                      state={
                        item.estado
                      }
                    />
                  );
                }


                if (
                  kind ===
                  "discrepancy"
                ) {
                  return (
                    <AttentionCard
                      key={`d-${item.id}`}
                      icon={
                        AlertTriangle
                      }
                      title={
                        item.concepto ||
                        `Discrepancia #${item.id}`
                      }
                      description="Dato que requiere revisión"
                      to="/gobernanza/calidad"
                      state={
                        item.estado
                      }
                    />
                  );
                }


                return (
                  <article
                    key={`e-${item.id}`}
                    className="rounded-[22px] border border-emerald-100 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
                          <FileCheck2
                            aria-hidden="true"
                            size={18}
                          />
                        </div>

                        <div>
                          <DossierLink
                            id={
                              item.id
                            }
                          >
                            {item.problematica_titulo ||
                              `Expediente #${item.id}`}
                          </DossierLink>

                          <p className="mt-1 text-sm text-[var(--text-muted)]">
                            Faltan
                            antecedentes
                            para continuar
                          </p>
                        </div>
                      </div>

                      <State
                        value={
                          item.estado
                        }
                      />
                    </div>
                  </article>
                );
              }
            )}
          </div>
        )}
      </section>


      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Superficies de control
          </p>

          <h2 className="mt-1 text-xl font-black">
            Gestión profesional
          </h2>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <ControlCard
            icon={ClipboardCheck}
            title="Revisión profesional"
            description="Hallazgos y decisiones formales registradas por personas autorizadas."
            to="/gobernanza/revision"
            action="Ver revisiones"
          />

          <ControlCard
            icon={AlertTriangle}
            title="Calidad y discrepancias"
            description={
              state.discrepancies
                .status ===
                "error"
                ? "Información no disponible."
                : `${openDiscrepancies.length} discrepancias abiertas registradas.`
            }
            to="/gobernanza/calidad"
            action="Revisar calidad"
          />

          <ControlCard
            icon={FileCheck2}
            title="Expedientes"
            description="Antecedentes gobernados asociados a problemas y revisiones ambientales."
            to="/gobernanza/expedientes"
            action="Ver expedientes"
          />
        </div>
      </section>


      <section className="space-y-4">
        <h2 className="text-lg font-black">
          Herramientas de control
        </h2>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Quick
            icon={Database}
            to="/gobernanza/factores"
            label="Factores y metodologías"
          />

          <Quick
            icon={ShieldCheck}
            to="/gobernanza/auditoria"
            label="Auditoría"
          />

          <Quick
            icon={BookOpenCheck}
            to="/gobernanza/conocimiento"
            label="Conocimiento"
          />

          <Quick
            icon={Scale}
            to="/gobernanza/informes"
            label="Informes"
          />
        </div>
      </section>
    </main>
  );
}


function HeroMetric({
  value,
  label,
  warning = false,
}) {
  return (
    <span
      className={
        warning
          ? "rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100"
          : "rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold"
      }
    >
      {value} {label}
    </span>
  );
}


function Metric({
  icon: Icon,
  label,
  resourceState,
  value,
  to,
  tone,
}) {
  const content =
    resourceState.status ===
      "loading"
      ? "…"
      : resourceState.status ===
        "error"
        ? "—"
        : value;


  const iconClass =
    tone === "amber"
      ? "bg-amber-50 text-amber-700"
      : tone === "sky"
        ? "bg-sky-50 text-sky-700"
        : "bg-emerald-50 text-emerald-700";


  return (
    <Link
      to={to}
      className="rounded-[22px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
    >
      <article className="h-full rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:border-emerald-200">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-bold text-[var(--text-muted)]">
              {label}
            </p>

            <p className="mt-2 text-3xl font-black text-[var(--text-primary)]">
              {content}
            </p>
          </div>

          <div
            className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
          >
            <Icon
              aria-hidden="true"
              size={19}
            />
          </div>
        </div>
      </article>
    </Link>
  );
}


function AttentionCard({
  icon: Icon,
  title,
  description,
  state,
  to,
}) {
  return (
    <Link
      to={to}
      className="rounded-[22px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
    >
      <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition hover:border-emerald-200">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <Icon
                aria-hidden="true"
                size={18}
              />
            </div>

            <div>
              <b>
                {title}
              </b>

              <p className="mt-1 text-sm text-[var(--text-muted)]">
                {description}
              </p>
            </div>
          </div>

          <State value={state} />
        </div>
      </article>
    </Link>
  );
}


function ControlCard({
  icon: Icon,
  title,
  description,
  to,
  action,
}) {
  return (
    <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
        <Icon
          aria-hidden="true"
          size={20}
        />
      </div>

      <h2 className="mt-4 text-lg font-black">
        {title}
      </h2>

      <p className="mt-2 min-h-[48px] text-sm leading-6 text-[var(--text-muted)]">
        {description}
      </p>

      <Link
        className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-[var(--brand-primary)]"
        to={to}
      >
        {action}

        <ArrowRight
          aria-hidden="true"
          size={16}
        />
      </Link>
    </article>
  );
}


function Quick({
  icon: Icon,
  to,
  label,
}) {
  return (
    <Link
      className="flex items-center gap-3 rounded-[18px] border border-slate-200 bg-white p-4 text-sm font-bold shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition hover:border-emerald-200 hover:bg-emerald-50/30"
      to={to}
    >
      <Icon
        size={18}
        className="text-emerald-700"
        aria-hidden="true"
      />

      {label}
    </Link>
  );
}