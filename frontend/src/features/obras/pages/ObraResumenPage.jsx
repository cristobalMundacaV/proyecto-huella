import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  ListChecks,
  ShieldCheck,
} from "lucide-react";

import {
  Link,
  useOutletContext,
  useParams,
} from "react-router-dom";

import WorkStatus from "../components/WorkStatus";

import {
  EmptyState,
  KpiCard,
  SectionHeader,
  StatusBadge,
} from "@/shared/ui";

import {
  transportMetrics,
} from "@/features/operacion/utils/operationSelectors";


const label = (value) =>
  String(
    value ??
    "Sin información"
  ).replaceAll("_", " ");


const date = (value) =>
  value
    ? new Intl.DateTimeFormat(
      "es-CL",
      {
        dateStyle: "medium",
      }
    ).format(
      new Date(value)
    )
    : "Fecha no disponible";


export const selectFeaturedIndicators =
  (indicators) => {
    const result =
      transportMetrics(
        indicators?.transporte
      )
        .filter(
          (metric) =>
            metric.value !==
            null &&
            metric.value !==
            undefined
        )
        .map(
          (metric) => ({
            name:
              metric.label,
            value:
              metric.value,
            unit:
              metric.unit,
            helper:
              "Transporte operacional",
          })
        );


    for (
      const metric of
      Array.isArray(
        indicators?.flujos
      )
        ? indicators.flujos
        : []
    ) {
      if (
        result.length >= 3
      ) {
        break;
      }

      if (
        metric?.estrategia_agregacion !==
        "suma" ||
        metric.total ===
        null ||
        metric.total ===
        undefined
      ) {
        continue;
      }

      result.push({
        name: `${label(
          metric.flujo
        )} · ${label(
          metric.concepto
        )}`,

        value:
          metric.total,

        unit:
          metric.unidad ||
          undefined,

        helper:
          "Flujo ambiental",
      });
    }


    return result.slice(
      0,
      3
    );
  };


function activityStyle(type) {
  const value =
    String(
      type || ""
    ).toLowerCase();


  if (
    value.includes(
      "evidencia"
    )
  ) {
    return {
      icon: FileCheck2,
      label: "Evidencia",
      border:
        "border-l-emerald-500",
      iconBg:
        "bg-emerald-100",
      iconColor:
        "text-emerald-700",
      background:
        "bg-emerald-50/45",
    };
  }


  if (
    value.includes(
      "problema"
    )
  ) {
    return {
      icon: AlertTriangle,
      label: "Problema",
      border:
        "border-l-amber-500",
      iconBg:
        "bg-amber-100",
      iconColor:
        "text-amber-700",
      background:
        "bg-amber-50/45",
    };
  }


  if (
    value.includes(
      "accion"
    )
  ) {
    return {
      icon: ListChecks,
      label: "Acción",
      border:
        "border-l-sky-500",
      iconBg:
        "bg-sky-100",
      iconColor:
        "text-sky-700",
      background:
        "bg-sky-50/45",
    };
  }


  return {
    icon: Activity,
    label: "Actividad",
    border:
      "border-l-slate-400",
    iconBg:
      "bg-slate-100",
    iconColor:
      "text-slate-600",
    background:
      "bg-slate-50/60",
  };
}


export default function ObraResumenPage() {
  const {
    obraId,
  } = useParams();

  const {
    obra,
    context,
    indicators,
    timeline,
    resourceErrors = {},
  } = useOutletContext();


  const diagnosis =
    context?.diagnostico_obra ||
    {};


  const problems =
    Array.isArray(
      context
        ?.problematicas_abiertas
    )
      ? context.problematicas_abiertas
      : [];


  const actions =
    (
      Array.isArray(
        context
          ?.acciones_actuales
      )
        ? context.acciones_actuales
        : []
    ).filter(
      (item) =>
        item.acciones__id
    );


  const evidence =
    context?.evidencia ||
    {};


  const evidenceTotal =
    evidence.total ?? null;


  const featured =
    resourceErrors.indicators
      ? []
      : selectFeaturedIndicators(
        indicators
      );


  const recentEvents =
    Array.isArray(timeline)
      ? timeline
        .slice(-3)
        .reverse()
      : [];


  const coverage =
    Array.isArray(
      diagnosis.aplicabilidad
    )
      ? diagnosis.aplicabilidad
      : [];


  const stateSummary =
    problems.length
      ? `Hay ${problems.length
      } ${problems.length ===
        1
        ? "problema abierto"
        : "problemas abiertos"
      }${actions.length
        ? ` y ${actions.length
        } ${actions.length ===
          1
          ? "acción en seguimiento"
          : "acciones en seguimiento"
        }`
        : ""
      }.`
      : "No hay problemas abiertos registrados en la información disponible.";


  return (
    <div className="space-y-6">

      {/* ESTADO GENERAL */}
      <section className="overflow-hidden rounded-[22px] border border-emerald-100 bg-[linear-gradient(135deg,rgba(236,253,245,0.86),rgba(255,255,255,0.98))] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-center">

          <div>
            <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
              Lectura de la unidad
            </p>

            <h2 className="mt-1 text-xl font-black text-[var(--text-primary)]">
              Estado general
            </h2>

            <div className="mt-4">
              <WorkStatus
                value={
                  obra.estado_ambiental
                }
              />
            </div>

            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
              {stateSummary}
            </p>


            {obra.estado_ambiental ===
              "cierre_pendiente" && (
                <p className="mt-2 text-sm font-semibold text-amber-700">
                  El cierre ambiental
                  sigue pendiente.
                </p>
              )}


            {obra.estado_ambiental ===
              "cerrada" && (
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Cierre ambiental:{" "}
                  {date(
                    obra.fecha_cierre_ambiental
                  )}
                </p>
              )}
          </div>


          <div className="rounded-[18px] border border-emerald-100 bg-white/80 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                <ShieldCheck
                  aria-hidden="true"
                  size={19}
                />
              </div>

              <div>
                <p className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">
                  Lectura actual
                </p>

                <p className="mt-1 text-sm font-black text-[var(--text-primary)]">
                  {problems.length
                    ? "Requiere seguimiento"
                    : obra.estado_ambiental ===
                      "configuracion"
                      ? "Cobertura en configuración"
                      : "Sin problemas abiertos"}
                </p>

                <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">
                  Esta lectura refleja
                  únicamente la
                  información disponible
                  en la unidad.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* KPIS */}
      <section
        aria-label="Señales de gestión"
        className="grid gap-3 sm:grid-cols-3"
      >
        <KpiCard
          icon={AlertTriangle}
          label="Problemas abiertos"
          value={
            problems.length
          }
          helper={
            problems.length
              ? "Requieren seguimiento"
              : "Sin problemas abiertos"
          }
          status={
            problems.length
              ? "warning"
              : "success"
          }
        />

        <KpiCard
          icon={ListChecks}
          label="Acciones en curso"
          value={
            actions.length
          }
          helper={
            actions.length
              ? "Gestionadas desde Problemas"
              : "Sin acciones activas"
          }
          status={
            actions.length
              ? "info"
              : undefined
          }
        />

        <KpiCard
          icon={FileCheck2}
          label="Evidencias"
          value={
            evidenceTotal ??
            "No disponible"
          }
          helper={
            evidenceTotal ===
              null
              ? "Conteo no disponible"
              : evidenceTotal ===
                0
                ? "Sin evidencia vinculada"
                : `${evidence.versiones ??
                0
                } versiones documentales`
          }
          status={
            evidenceTotal >
              0
              ? "success"
              : undefined
          }
        />
      </section>


      {/* PROBLEMAS */}
      {problems.length >
        0 && (
          <section className="space-y-3">
            <SectionHeader
              title="Requiere atención"
              description="Problemas abiertos que necesitan seguimiento."
              action={
                <Link
                  className="inline-flex items-center gap-1.5 text-sm font-bold text-[var(--brand-primary)]"
                  to={`/obras/${obraId}/problemas`}
                >
                  Ver todos

                  <ArrowRight
                    aria-hidden="true"
                    size={15}
                  />
                </Link>
              }
            />

            <div className="overflow-hidden rounded-[22px] border border-amber-100 bg-white shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
              {problems
                .slice(0, 3)
                .map(
                  (
                    problem,
                    index
                  ) => (
                    <article
                      key={
                        problem.id
                      }
                      className={`flex flex-wrap items-center justify-between gap-4 p-5 ${index
                          ? "border-t border-slate-100"
                          : ""
                        }`}
                    >
                      <div className="min-w-0">
                        <p className="font-black text-[var(--text-primary)]">
                          {
                            problem.titulo
                          }
                        </p>

                        {problem.categoria && (
                          <p className="mt-1 text-sm text-[var(--text-muted)]">
                            {label(
                              problem.categoria
                            )}
                          </p>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3">
                        <StatusBadge tone="warning">
                          {label(
                            problem.estado
                          )}
                        </StatusBadge>

                        <Link
                          className="inline-flex items-center gap-1 text-sm font-bold text-[var(--brand-primary)]"
                          to={`/obras/${obraId}/problemas/${problem.id}`}
                        >
                          Ver problema

                          <ArrowRight
                            aria-hidden="true"
                            size={15}
                          />
                        </Link>
                      </div>
                    </article>
                  )
                )}
            </div>
          </section>
        )}


      {/* INDICADORES */}
      <section className="space-y-3">
        <SectionHeader
          title="Indicadores destacados"
          description="Señales principales disponibles para esta unidad."
          action={
            <Link
              className="inline-flex items-center gap-1.5 text-sm font-bold text-[var(--brand-primary)]"
              to={`/obras/${obraId}/indicadores`}
            >
              Ver indicadores

              <ArrowRight
                aria-hidden="true"
                size={15}
              />
            </Link>
          }
        />


        {resourceErrors.indicators ? (
          <div className="rounded-[18px] border border-amber-200 bg-amber-50/60 p-4 text-sm text-amber-900">
            Los indicadores no están
            disponibles en este
            momento.
          </div>
        ) : featured.length ? (
          <div className="grid gap-3 md:grid-cols-3">
            {featured.map(
              (item) => (
                <KpiCard
                  key={
                    item.name
                  }
                  label={
                    item.name
                  }
                  value={
                    item.value
                  }
                  unit={
                    item.unit
                  }
                  helper={
                    item.helper
                  }
                  icon={
                    Activity
                  }
                />
              )
            )}
          </div>
        ) : (
          <EmptyState
            icon={Activity}
            title="Aún no hay indicadores disponibles"
            description="Los indicadores aparecerán cuando exista información operacional suficiente para construirlos."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.12),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))]"
          />
        )}
      </section>


      {/* COBERTURA */}
      <section className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
        <SectionHeader
          title="Cobertura ambiental"
          description="Ámbitos ambientales evaluados para esta unidad."
        />

        {coverage.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {coverage
              .slice(0, 6)
              .map((item) => (
                <StatusBadge
                  key={
                    item.clave
                  }
                  tone={
                    item.estado_obra ===
                      "aplica"
                      ? "success"
                      : item.estado_obra ===
                        "no_aplica"
                        ? "neutral"
                        : "info"
                  }
                >
                  {label(
                    item.clave
                  )}{" "}
                  ·{" "}
                  {label(
                    item.estado_obra
                  )}
                </StatusBadge>
              ))}

            {coverage.length >
              6 && (
                <span className="self-center text-sm text-[var(--text-muted)]">
                  +
                  {coverage.length -
                    6}{" "}
                  más
                </span>
              )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-[var(--text-muted)]">
            Sin información de
            cobertura disponible.
          </p>
        )}
      </section>


      {/* ACTIVIDAD RECIENTE */}
      <section className="space-y-3">
        <SectionHeader
          title="Actividad reciente"
          description="Últimos movimientos registrados en esta unidad."
          action={
            <Link
              className="inline-flex items-center gap-1.5 text-sm font-bold text-[var(--brand-primary)]"
              to={`/obras/${obraId}/timeline`}
            >
              Ver historial

              <ArrowRight
                aria-hidden="true"
                size={15}
              />
            </Link>
          }
        />


        {resourceErrors.timeline ? (
          <div className="rounded-[18px] border border-amber-200 bg-amber-50/60 p-4 text-sm text-amber-900">
            El historial no está
            disponible en este
            momento.
          </div>
        ) : recentEvents.length ? (
          <div className="grid gap-3">
            {recentEvents.map(
              (
                event,
                index
              ) => {
                const style =
                  activityStyle(
                    event.tipo
                  );

                const Icon =
                  style.icon;

                return (
                  <article
                    key={`${event.tipo}-${event.referencia_id}-${index}`}
                    className={`rounded-[20px] border border-slate-200 border-l-4 ${style.border} ${style.background} p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)]`}
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${style.iconBg} ${style.iconColor}`}
                      >
                        <Icon
                          aria-hidden="true"
                          size={19}
                        />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
                          <div>
                            <p className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
                              {
                                style.label
                              }
                            </p>

                            <h3 className="mt-1 font-black text-[var(--text-primary)]">
                              {event.titulo ||
                                "Actividad registrada"}
                            </h3>
                          </div>

                          <time className="shrink-0 text-xs text-[var(--text-muted)]">
                            {date(
                              event.fecha
                            )}
                          </time>
                        </div>

                        <p className="mt-1 text-sm text-[var(--text-secondary)]">
                          {label(
                            event.tipo
                          )}
                        </p>
                      </div>
                    </div>
                  </article>
                );
              }
            )}
          </div>
        ) : (
          <EmptyState
            icon={CheckCircle2}
            title="Aún no hay actividad registrada"
            description="Los movimientos relacionados con esta unidad aparecerán aquí a medida que se incorporen datos y se realicen acciones."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.12),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))]"
          />
        )}
      </section>
    </div>
  );
}