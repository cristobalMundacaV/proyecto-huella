import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Bot,
  CheckCircle2,
  ChevronRight,
  FileText,
  Lightbulb,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Link } from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  Alert,
  Button,
  EmptyState,
  ErrorState,
  Modal,
  Select,
  StatusBadge,
  Textarea,
} from "@/shared/ui";

import { listProblems } from "@/features/mejora/services/improvementApi";

import {
  problemStatusLabel,
  problemTone,
} from "@/features/mejora/utils/improvementFormat";

import {
  confirmCommand,
  createProposal,
  getProblemContext,
  getProposals,
  sendFeedback,
} from "../services/copilotApi";


const resource = (
  status = "idle",
  data = null
) => ({
  status,
  data,
});


function proposalStatus(value) {
  return (
    {
      propuesta: {
        label: "Propuesta",
        tone: "info",
      },

      ajustada: {
        label: "Ajustada",
        tone: "info",
      },

      aceptada: {
        label: "Preparada para confirmar",
        tone: "warning",
      },

      rechazada: {
        label: "Rechazada",
        tone: "neutral",
      },

      descartada: {
        label: "Descartada",
        tone: "neutral",
      },
    }[value] || {
      label: String(
        value || "Sin estado"
      ).replaceAll("_", " "),
      tone: "neutral",
    }
  );
}


export default function CopilotPage() {
  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const [
    problems,
    setProblems,
  ] = useState({
    scopeKey: "",
    status: "loading",
    data: [],
    error: "",
  });

  const [
    problemId,
    setProblemId,
  ] = useState("");

  const [
    resources,
    setResources,
  ] = useState({
    scopeKey: "",
    context: resource(),
    proposals: resource(),
  });

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    dialog,
    setDialog,
  ] = useState(null);

  const [
    busy,
    setBusy,
  ] = useState(false);

  const [
    actionError,
    setActionError,
  ] = useState("");

  const problemsRequestRef =
    useRef(0);

  const resourceRequestRef =
    useRef(0);


  useEffect(() => {
    if (!activeOrganizacionId) {
      return undefined;
    }

    const requestId =
      ++problemsRequestRef.current;

    resourceRequestRef.current += 1;

    setProblemId("");

    const scopeKey =
      String(
        activeOrganizacionId
      );

    setProblems({
      scopeKey,
      status: "loading",
      data: [],
      error: "",
    });

    setResources({
      scopeKey: "",
      context: resource(),
      proposals: resource(),
    });

    listProblems(
      activeOrganizacionId
    )
      .then((items) => {
        if (
          problemsRequestRef.current !==
          requestId
        ) {
          return;
        }

        const rows =
          Array.isArray(items)
            ? items
            : [];

        setProblems({
          scopeKey,
          status: "ready",
          data: rows,
          error: "",
        });

        setProblemId(
          String(
            rows[0]?.id ||
            ""
          )
        );
      })
      .catch(() => {
        if (
          problemsRequestRef.current ===
          requestId
        ) {
          setProblems({
            scopeKey,
            status: "error",
            data: [],
            error:
              "No fue posible cargar los problemas.",
          });
        }
      });

    return () => {
      problemsRequestRef.current += 1;
      resourceRequestRef.current += 1;
    };
  }, [
    activeOrganizacionId,
  ]);


  const load = useCallback(
    () => {
      if (!problemId) {
        setResources({
          scopeKey: "",
          context: resource(),
          proposals: resource(),
        });

        return Promise.resolve();
      }

      const scopeKey =
        `${activeOrganizacionId}:${problemId}`;

      const requestId =
        ++resourceRequestRef.current;

      setResources({
        scopeKey,
        context:
          resource("loading"),
        proposals:
          resource(
            "loading",
            []
          ),
      });

      return Promise.allSettled([
        getProblemContext(
          problemId
        ),
        getProposals(
          problemId
        ),
      ]).then(
        ([
          context,
          proposals,
        ]) => {
          if (
            resourceRequestRef.current !==
            requestId
          ) {
            return;
          }

          setResources({
            scopeKey,

            context:
              context.status ===
                "fulfilled"
                ? {
                  status:
                    "ready",
                  data:
                    context.value,
                }
                : {
                  status:
                    "error",
                  data: null,
                },

            proposals:
              proposals.status ===
                "fulfilled"
                ? {
                  status:
                    "ready",
                  data:
                    proposals.value ||
                    [],
                }
                : {
                  status:
                    "error",
                  data: [],
                },
          });
        }
      );
    },
    [
      activeOrganizacionId,
      problemId,
    ]
  );


  useEffect(() => {
    setMessage("");
    setActionError("");

    load();

    return () => {
      resourceRequestRef.current += 1;
    };
  }, [load]);


  async function propose() {
    if (
      !problemId ||
      resources.scopeKey !==
      `${activeOrganizacionId}:${problemId}` ||
      resourceState.context.status !==
      "ready" ||
      !message.trim()
    ) {
      return;
    }

    setBusy(true);
    setActionError("");

    try {
      await createProposal(
        problemId,
        message.trim()
      );

      setMessage("");

      await load();
    } catch (error) {
      setActionError(
        error?.response?.data
          ?.detail ||
        "No se pudo preparar una propuesta."
      );
    } finally {
      setBusy(false);
    }
  }


  async function feedback(
    proposal,
    decision,
    explanation = ""
  ) {
    setBusy(true);
    setActionError("");

    try {
      const result =
        await sendFeedback(
          problemId,
          proposal.id,
          decision,
          explanation
        );

      if (
        result.requiere_confirmacion &&
        result.comando
      ) {
        setDialog({
          type: "command",
          command:
            result.comando,
          proposal,
        });
      } else {
        setDialog(null);
        await load();
      }
    } catch (error) {
      setActionError(
        error?.response?.data
          ?.detail ||
        "No se pudo registrar esta decisión."
      );
    } finally {
      setBusy(false);
    }
  }


  async function submitDialog() {
    if (!dialog) {
      return;
    }

    if (
      dialog.type === "refute"
    ) {
      if (
        !dialog.message?.trim()
      ) {
        return;
      }

      return feedback(
        dialog.proposal,
        "refutar",
        dialog.message.trim()
      );
    }

    setBusy(true);
    setActionError("");

    try {
      await confirmCommand(
        dialog.command
      );

      setDialog(null);

      await load();
    } catch (error) {
      setActionError(
        error?.response?.data
          ?.detail ||
        "No se pudo crear la acción formal."
      );
    } finally {
      setBusy(false);
    }
  }


  const organizationScopeKey =
    String(
      activeOrganizacionId ||
      ""
    );

  const problemsState =
    problems.scopeKey ===
      organizationScopeKey
      ? problems
      : {
        scopeKey:
          organizationScopeKey,
        status: "loading",
        data: [],
        error: "",
      };


  const resourceScopeKey =
    problemId
      ? `${activeOrganizacionId}:${problemId}`
      : "";


  const resourceState =
    resources.scopeKey ===
      resourceScopeKey
      ? resources
      : {
        scopeKey:
          resourceScopeKey,
        context:
          resource("loading"),
        proposals:
          resource(
            "loading",
            []
          ),
      };


  const selectedProblem =
    problemsState.data.find(
      (item) =>
        String(item.id) ===
        String(problemId)
    );


  if (
    problemsState.status ===
    "loading"
  ) {
    return (
      <PlatformLoader
        compact
        title="Preparando Copiloto"
        description="Estamos cargando los problemas disponibles y su contexto ambiental."
      />
    );
  }


  return (
    <main className="space-y-6">

      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              Inteligencia · Asistencia
            </p>

            <h1 className="mt-2 text-3xl font-black">
              Copiloto ambiental
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">
              Explora un problema concreto,
              comprende su contexto y prepara
              alternativas antes de convertir
              cualquier propuesta en una
              acción formal.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {problemsState.data.length}{" "}
                {problemsState.data.length === 1
                  ? "problema disponible"
                  : "problemas disponibles"}
              </span>

              <span className="rounded-full border border-sky-200/30 bg-sky-200/10 px-3 py-1.5 text-xs font-bold text-sky-50">
                Decisión humana obligatoria
              </span>
            </div>
          </div>

          <Link
            to="/inteligencia/problemas"
            className="inline-flex self-start items-center gap-2 rounded-xl border border-white/30 bg-white px-4 py-3 text-sm font-black text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] transition hover:bg-emerald-50 lg:self-center"
          >
            <FileText
              aria-hidden="true"
              size={18}
            />

            Ver problemas
          </Link>
        </div>
      </section>


      {problemsState.status ===
        "error" ? (
        <ErrorState
          description={
            problemsState.error
          }
        />
      ) : !problemsState.data
        .length ? (
        <EmptyState
          icon={Bot}
          title="No hay problemas disponibles para consultar"
          description="El Copiloto trabaja sobre situaciones ambientales reales y acotadas. Registra o revisa un problema para comenzar."
          className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          primaryAction={
            <Link
              className="font-bold text-[var(--brand-primary)]"
              to="/inteligencia/problemas"
            >
              Ver problemas
            </Link>
          }
        />
      ) : (
        <>
          <section className="rounded-[22px] border border-emerald-100 bg-white p-4 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
            <Select
              label="Problema a analizar"
              value={problemId}
              onChange={(event) =>
                setProblemId(
                  event.target.value
                )
              }
            >
              {problemsState.data.map(
                (item) => (
                  <option
                    key={item.id}
                    value={item.id}
                  >
                    {item.titulo} ·{" "}
                    {problemStatusLabel(
                      item.estado
                    )}
                  </option>
                )
              )}
            </Select>
          </section>


          {actionError && (
            <Alert tone="danger">
              {Array.isArray(
                actionError
              )
                ? actionError.join(
                  " "
                )
                : actionError}
            </Alert>
          )}


          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">

            <section className="space-y-4">

              <article className="rounded-[22px] border border-emerald-100 bg-white p-5 shadow-[0_12px_30px_rgba(15,23,42,0.05)]">
                <div className="flex items-start gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                    <Sparkles
                      aria-hidden="true"
                      size={21}
                    />
                  </div>

                  <div>
                    <h2 className="font-black text-[var(--text-primary)]">
                      ¿Qué necesitas entender?
                    </h2>

                    <p className="mt-1 text-sm text-[var(--text-muted)]">
                      Haz una pregunta concreta
                      sobre el problema
                      seleccionado.
                    </p>
                  </div>
                </div>

                <div className="mt-5">
                  <Textarea
                    label="Consulta"
                    placeholder="Ej: ¿Qué restricciones debería revisar antes de decidir una acción?"
                    rows={5}
                    value={message}
                    onChange={(
                      event
                    ) =>
                      setMessage(
                        event.target
                          .value
                      )
                    }
                  />
                </div>

                {resourceState.context
                  .status ===
                  "error" && (
                    <div className="mt-4">
                      <Alert tone="warning">
                        El contexto no está
                        disponible. Puedes
                        revisar propuestas
                        anteriores, pero no
                        preparar una nueva
                        hasta recuperar el
                        contexto.
                      </Alert>
                    </div>
                  )}

                <div className="mt-4 flex justify-end">
                  <Button
                    leftIcon={Send}
                    disabled={
                      !message.trim() ||
                      resourceState.context
                        .status !==
                      "ready"
                    }
                    loading={busy}
                    onClick={propose}
                  >
                    Preparar propuesta
                  </Button>
                </div>
              </article>


              {resourceState.proposals
                .status ===
                "loading" ? (
                <PlatformLoader
                  compact
                  title="Cargando propuestas"
                  description="Estamos recuperando las alternativas asociadas al problema."
                />
              ) : resourceState
                .proposals.status ===
                "error" ? (
                <ErrorState
                  description="No fue posible cargar las propuestas. El contexto del problema puede seguir disponible."
                />
              ) : !resourceState
                .proposals.data
                .length ? (
                <EmptyState
                  icon={Lightbulb}
                  title="Aún no hay propuestas"
                  description="Formula una pregunta concreta para preparar una alternativa basada en el contexto disponible."
                  className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.12),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))]"
                />
              ) : (
                resourceState.proposals.data.map(
                  (proposal) => {
                    const status =
                      proposalStatus(
                        proposal.estado
                      );

                    return (
                      <article
                        key={
                          proposal.id
                        }
                        className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">
                              Propuesta ambiental
                            </p>

                            <h2 className="mt-1 text-lg font-black text-[var(--text-primary)]">
                              {proposal.titulo ||
                                "Propuesta"}
                            </h2>
                          </div>

                          <StatusBadge
                            tone={
                              status.tone
                            }
                          >
                            {
                              status.label
                            }
                          </StatusBadge>
                        </div>

                        <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                          {proposal.justificacion ||
                            proposal.descripcion ||
                            "Sin explicación adicional."}
                        </p>

                        {!!proposal
                          .restricciones_consideradas
                          ?.length && (
                            <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50/60 px-4 py-3 text-sm">
                              <b className="text-amber-900">
                                Restricciones
                                consideradas:
                              </b>{" "}
                              <span className="text-amber-900/80">
                                {proposal.restricciones_consideradas
                                  .slice(
                                    0,
                                    3
                                  )
                                  .join(
                                    ", "
                                  )}
                              </span>
                            </div>
                          )}

                        {(proposal
                          .kpis_afectados
                          ?.length ||
                          proposal
                            .referencias_contexto
                            ?.length ||
                          proposal
                            .requisitos
                            ?.length ||
                          proposal
                            .riesgos
                            ?.length) && (
                            <details className="mt-4 text-sm group">
                              <summary className="cursor-pointer list-none font-bold text-emerald-800">
                                <span className="inline-flex items-center gap-2">
                                  <ChevronRight
                                    size={
                                      16
                                    }
                                    className="transition group-open:rotate-90"
                                  />
                                  Detalles considerados
                                </span>
                              </summary>

                              <div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-4 text-[var(--text-secondary)]">
                                {!!proposal
                                  .requisitos
                                  ?.length && (
                                    <p>
                                      <b>
                                        Requisitos:
                                      </b>{" "}
                                      {proposal.requisitos.join(
                                        ", "
                                      )}
                                    </p>
                                  )}

                                {!!proposal
                                  .riesgos
                                  ?.length && (
                                    <p>
                                      <b>
                                        Riesgos:
                                      </b>{" "}
                                      {proposal.riesgos.join(
                                        ", "
                                      )}
                                    </p>
                                  )}

                                {!!proposal
                                  .kpis_afectados
                                  ?.length && (
                                    <p>
                                      <b>
                                        Indicadores:
                                      </b>{" "}
                                      {proposal.kpis_afectados.join(
                                        ", "
                                      )}
                                    </p>
                                  )}

                                {!!proposal
                                  .referencias_contexto
                                  ?.length && (
                                    <p>
                                      <b>
                                        Referencias:
                                      </b>{" "}
                                      {proposal.referencias_contexto.join(
                                        ", "
                                      )}
                                    </p>
                                  )}
                              </div>
                            </details>
                          )}

                        {[
                          "propuesta",
                          "ajustada",
                        ].includes(
                          proposal.estado
                        ) && (
                            <div className="mt-5 flex flex-wrap gap-2">
                              <Button
                                size="sm"
                                onClick={() =>
                                  feedback(
                                    proposal,
                                    "aceptar"
                                  )
                                }
                              >
                                Preparar acción
                              </Button>

                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() =>
                                  setDialog({
                                    type:
                                      "refute",
                                    proposal,
                                    message:
                                      "",
                                  })
                                }
                              >
                                Indicar por qué
                                no aplica
                              </Button>

                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() =>
                                  feedback(
                                    proposal,
                                    "rechazar"
                                  )
                                }
                              >
                                Rechazar
                              </Button>
                            </div>
                          )}
                      </article>
                    );
                  }
                )
              )}
            </section>


            <aside className="space-y-4">
              <article className="rounded-[22px] border border-emerald-100 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                    <ShieldCheck
                      aria-hidden="true"
                      size={19}
                    />
                  </div>

                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">
                      Contexto utilizado
                    </p>

                    <h2 className="font-black text-[var(--text-primary)]">
                      {selectedProblem?.titulo ||
                        "Problema seleccionado"}
                    </h2>
                  </div>
                </div>

                <div className="mt-3">
                  {selectedProblem && (
                    <StatusBadge
                      tone={problemTone(
                        selectedProblem.estado
                      )}
                    >
                      {problemStatusLabel(
                        selectedProblem.estado
                      )}
                    </StatusBadge>
                  )}
                </div>

                {resourceState.context
                  .status ===
                  "loading" ? (
                  <div className="mt-5">
                    <PlatformLoader
                      compact
                      title="Cargando contexto"
                      description="Preparando antecedentes."
                    />
                  </div>
                ) : resourceState
                  .context.status ===
                  "error" ? (
                  <p className="mt-5 text-sm text-[var(--text-muted)]">
                    Contexto no
                    disponible.
                  </p>
                ) : resourceState
                  .context.status ===
                  "ready" ? (
                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <ContextMetric
                      label="Indicadores"
                      value={
                        resourceState
                          .context.data
                          ?.kpis
                          ?.length ??
                        0
                      }
                    />

                    <ContextMetric
                      label="Acciones"
                      value={
                        resourceState
                          .context.data
                          ?.acciones_probadas
                          ?.length ??
                        0
                      }
                    />

                    <ContextMetric
                      label="Restricciones"
                      value={
                        resourceState
                          .context.data
                          ?.restricciones
                          ?.length ??
                        0
                      }
                    />

                    <ContextMetric
                      label="Evidencias"
                      value={
                        resourceState
                          .context.data
                          ?.evidencia
                          ?.totales
                          ?.evidencias ??
                        0
                      }
                    />
                  </div>
                ) : null}

                <p className="mt-5 text-xs leading-5 text-[var(--text-muted)]">
                  Las propuestas se basan en
                  referencias estructuradas
                  del problema. Crear una
                  acción siempre requiere una
                  decisión humana explícita.
                </p>

                {problemId && (
                  <Link
                    className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-[var(--brand-primary)]"
                    to={`/inteligencia/problemas/${problemId}`}
                  >
                    Ver problema
                    <ChevronRight
                      aria-hidden="true"
                      size={16}
                    />
                  </Link>
                )}
              </article>
            </aside>
          </div>
        </>
      )}


      <Modal
        open={Boolean(dialog)}
        title={
          dialog?.type ===
            "command"
            ? "Confirmar creación de acción"
            : "Indicar por qué no aplica"
        }
        description={
          dialog?.type ===
            "command"
            ? "Se creará una acción formal a partir de esta propuesta. La propuesta por sí sola no ejecuta ninguna intervención."
            : "Describe la restricción o corrección que debe considerarse antes de preparar otra alternativa."
        }
        onClose={() => {
          const wasCommand =
            dialog?.type ===
            "command";

          setDialog(null);

          if (wasCommand) {
            load();
          }
        }}
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                const wasCommand =
                  dialog?.type ===
                  "command";

                setDialog(null);

                if (
                  wasCommand
                ) {
                  load();
                }
              }}
            >
              Cancelar
            </Button>

            <Button
              disabled={
                dialog?.type ===
                "refute" &&
                !dialog?.message?.trim()
              }
              loading={busy}
              onClick={
                submitDialog
              }
            >
              {dialog?.type ===
                "command"
                ? "Crear acción"
                : "Guardar restricción"}
            </Button>
          </div>
        }
      >
        {dialog?.type ===
          "command" ? (
          <Alert tone="warning">
            La acción sólo se creará
            después de esta confirmación.
          </Alert>
        ) : (
          <Textarea
            required
            label="Motivo o restricción"
            value={
              dialog?.message ||
              ""
            }
            onChange={(event) =>
              setDialog({
                ...dialog,
                message:
                  event.target
                    .value,
              })
            }
          />
        )}
      </Modal>
    </main>
  );
}


function ContextMetric({
  label,
  value,
}) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
      <p className="text-xs font-bold text-[var(--text-muted)]">
        {label}
      </p>

      <p className="mt-1 text-xl font-black text-[var(--text-primary)]">
        {value}
      </p>
    </div>
  );
}