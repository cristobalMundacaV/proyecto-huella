import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Lightbulb,
} from "lucide-react";

import {
  Link,
} from "react-router-dom";

import {
  useOrganizacionActiva,
} from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  listProblems,
} from "@/features/mejora/services/improvementApi";

import {
  problemStatusLabel,
  problemTone,
  riskLabel,
} from "@/features/mejora/utils/improvementFormat";

import {
  EmptyState,
  SectionHeader,
  StatusBadge,
} from "@/shared/ui";


function isClosed(
  state,
) {
  return [
    "cerrada",
    "resuelta",
  ].includes(state);
}


function needsProfessional(
  state,
) {
  return [
    "escalada",
    "escalada_profesional",
    "no_resuelta",
  ].includes(state);
}


export default function IntelligencePage() {
  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const [
    state,
    setState,
  ] = useState({
    loading: true,
    rows: [],
    error: "",
  });


  useEffect(
    () => {
      if (
        !activeOrganizacionId
      ) {
        return;
      }

      setState({
        loading: true,
        rows: [],
        error: "",
      });

      listProblems(
        activeOrganizacionId
      )
        .then(
          (rows) => {
            setState({
              loading: false,
              rows:
                Array.isArray(rows)
                  ? rows
                  : [],
              error: "",
            });
          },
        )
        .catch(
          () => {
            setState({
              loading: false,
              rows: [],
              error:
                "No fue posible cargar el contexto de decisión.",
            });
          },
        );
    },
    [
      activeOrganizacionId,
    ],
  );


  const summary =
    useMemo(
      () => {
        const open =
          state.rows.filter(
            (item) =>
              !isClosed(
                item.estado
              ),
          );

        return {
          open:
            open.length,

          highRisk:
            open.filter(
              (item) =>
                [
                  "alto",
                  "critico",
                ].includes(
                  item.nivel_riesgo
                ),
            ).length,

          professional:
            open.filter(
              (item) =>
                needsProfessional(
                  item.estado
                ),
            ).length,
        };
      },
      [
        state.rows,
      ],
    );


  if (
    state.loading
  ) {
    return (
      <p className="text-sm text-[var(--text-muted)]">
        Preparando contexto de decisión...
      </p>
    );
  }


  return (
    <main className="space-y-6">
      <SectionHeader
        eyebrow="INTELIGENCIA AMBIENTAL"
        title="Decisiones"
        description="La inteligencia trabaja sobre problemas, indicadores y restricciones reales. No genera impactos ni escenarios ficticios."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <article className="rounded-2xl border bg-white p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle
              size={18}
            />

            <b>
              {
                summary.open
              }{" "}
              problemas abiertos
            </b>
          </div>
        </article>

        <article className="rounded-2xl border bg-white p-5">
          <div className="flex items-center gap-2">
            <Lightbulb
              size={18}
            />

            <b>
              {
                summary.highRisk
              }{" "}
              de riesgo alto
            </b>
          </div>
        </article>

        <article className="rounded-2xl border bg-white p-5">
          <div className="flex items-center gap-2">
            <Bot
              size={18}
            />

            <b>
              {
                summary.professional
              }{" "}
              requieren revisión profesional
            </b>
          </div>
        </article>
      </div>

      {state.error && (
        <p className="text-sm text-red-700">
          {state.error}
        </p>
      )}

      {!state.rows.length ? (
        <EmptyState
          icon={CheckCircle2}
          title="No hay decisiones pendientes"
          description="La inteligencia aparecerá cuando existan problemas ambientales reales que analizar."
        />
      ) : (
        <div className="space-y-3">
          {state.rows
            .filter(
              (item) =>
                !isClosed(
                  item.estado
                ),
            )
            .map(
              (item) => (
                <article
                  key={
                    item.id
                  }
                  className="rounded-[22px] border border-emerald-100 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="font-black">
                          {
                            item.titulo
                          }
                        </h2>

                        <StatusBadge
                          tone={problemTone(
                            item.estado
                          )}
                        >
                          {problemStatusLabel(
                            item.estado
                          )}
                        </StatusBadge>
                      </div>

                      <p className="mt-2 text-sm text-[var(--text-secondary)]">
                        {
                          item.descripcion
                        }
                      </p>

                      <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--text-muted)]">
                        <span>
                          Categoría:{" "}
                          {
                            item.categoria ||
                            "Sin categoría"
                          }
                        </span>

                        <span>
                          Riesgo:{" "}
                          {riskLabel(
                            item.nivel_riesgo
                          )}
                        </span>
                      </div>
                    </div>

                    <div className="flex shrink-0 gap-3">
                      <Link
                        className="text-sm font-bold text-[var(--brand-primary)]"
                        to={`/inteligencia/problemas/${item.id}`}
                      >
                        Ver gestión
                      </Link>

                      <Link
                        className="text-sm font-bold text-[var(--brand-primary)]"
                        to="/inteligencia/copiloto"
                      >
                        Consultar Copiloto
                      </Link>
                    </div>
                  </div>
                </article>
              ),
            )}
        </div>
      )}

      <section className="rounded-[22px] border border-sky-100 bg-sky-50/50 p-5">
        <h2 className="font-black">
          Qué hace la IA
        </h2>

        <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
          Puede organizar contexto,
          identificar restricciones,
          explicar señales y preparar
          alternativas. No modifica
          cálculos, no inventa factores,
          no demuestra causalidad y no
          ejecuta acciones sin una
          confirmación humana explícita.
        </p>
      </section>
    </main>
  );
}