import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
} from "lucide-react";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useAuth } from "@/features/auth/context/AuthContext";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  Alert,
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  Modal,
  Select,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
  Textarea,
} from "@/shared/ui";

import {
  formatDateTime,
} from "@/shared/utils/formatters";

import {
  addReviewFinding,
  decideReview,
  getProfessionalReviews,
} from "../api/professionalV2Api";

import {
  human,
  maxFindingSeverity,
  objectTypeLabel,
  reviewReference,
  State,
} from "../components/GovernanceShared";


const REVIEW_TYPES = [
  "evidencia",
  "observacion",
  "calculo",
  "indicador",
  "problematica",
  "intervencion",
  "expediente",
  "metodologia",
];


const REVIEW_STATES = [
  "pendiente",
  "validada",
  "validada_con_observaciones",
  "solicita_antecedentes",
  "rechazada",
];


const initialDialog = {
  kind: "finding",
  review: null,
  estado: "validada",
  tipo: "observacion",
  severidad: "media",
  text: "",
};


export default function ReviewQueuePage() {
  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const {
    user,
  } = useAuth();

  const [
    filters,
    setFilters,
  ] = useState({
    tipo: "",
    estado: "pendiente",
  });

  const [
    state,
    setState,
  ] = useState({
    scopeKey: "",
    status: "loading",
    rows: [],
    error: "",
  });

  const [
    dialog,
    setDialog,
  ] = useState(null);

  const [
    mutationError,
    setMutationError,
  ] = useState("");

  const [
    saving,
    setSaving,
  ] = useState(false);

  const requestRef =
    useRef(0);


  const load =
    useCallback(
      async () => {
        if (
          !activeOrganizacionId
        ) {
          return;
        }

        const scopeKey =
          `${activeOrganizacionId}:${filters.tipo}:${filters.estado}`;

        const requestId =
          ++requestRef.current;

        setState({
          scopeKey,
          status:
            "loading",
          rows: [],
          error: "",
        });

        try {
          const rows =
            await getProfessionalReviews(
              activeOrganizacionId,
              Object.fromEntries(
                Object.entries(
                  filters
                ).filter(
                  ([, value]) =>
                    value
                )
              )
            );

          if (
            requestRef.current ===
            requestId
          ) {
            setState({
              scopeKey,
              status:
                "ready",
              rows:
                Array.isArray(
                  rows
                )
                  ? rows
                  : [],
              error: "",
            });
          }
        } catch (error) {
          if (
            requestRef.current ===
            requestId
          ) {
            setState({
              scopeKey,
              status:
                "error",
              rows: [],
              error:
                error.response
                  ?.data
                  ?.detail ||
                "No se pudo cargar la revisión profesional.",
            });
          }
        }
      },
      [
        activeOrganizacionId,
        filters,
      ]
    );


  useEffect(() => {
    load();

    return () => {
      requestRef.current += 1;
    };
  }, [load]);


  const requestedScopeKey =
    activeOrganizacionId
      ? `${activeOrganizacionId}:${filters.tipo}:${filters.estado}`
      : "";


  const metadata =
    state.status !== "ready"
      ? undefined
      : filters.tipo
        ? `${state.rows.length} resultados`
        : filters.estado ===
          "pendiente"
          ? `${state.rows.length} pendientes`
          : filters.estado
            ? `${state.rows.length} resultados`
            : `${state.rows.filter(
              (item) =>
                item.estado ===
                "pendiente"
            ).length} pendientes`;


  async function submit() {
    setSaving(true);
    setMutationError("");

    try {
      if (
        dialog.kind ===
        "finding"
      ) {
        await addReviewFinding(
          activeOrganizacionId,
          dialog.review.id,
          {
            tipo:
              dialog.tipo,
            severidad:
              dialog.severidad,
            observacion:
              dialog.text,
          }
        );
      } else {
        await decideReview(
          activeOrganizacionId,
          dialog.review.id,
          {
            estado:
              dialog.estado,

            conclusion:
              dialog.text,

            observaciones:
              dialog.text,

            antecedentes_solicitados:
              dialog.estado ===
                "solicita_antecedentes"
                ? [
                  dialog.text,
                ]
                : [],
          }
        );
      }

      setDialog(null);

      await load();
    } catch (error) {
      setMutationError(
        error.response?.data
          ?.detail ||
        (
          dialog.kind ===
            "finding"
            ? "No se pudo registrar el hallazgo."
            : "No se pudo registrar la decisión profesional."
        )
      );
    } finally {
      setSaving(false);
    }
  }


  if (
    state.scopeKey !==
    requestedScopeKey ||
    state.status ===
    "loading"
  ) {
    return (
      <PlatformLoader
        compact
        title="Cargando revisiones"
        description="Estamos preparando la cola de validación profesional."
      />
    );
  }


  const pendingCount =
    state.rows.filter(
      (item) =>
        item.estado ===
        "pendiente"
    ).length;


  const requiringBackground =
    state.rows.filter(
      (item) =>
        item.estado ===
        "solicita_antecedentes"
    ).length;


  return (
    <main className="space-y-6">

      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="max-w-3xl">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
            Gobernanza · Validación
          </p>

          <h1 className="mt-2 text-3xl font-black">
            Revisión profesional
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">
            Revisa antecedentes,
            registra hallazgos y toma
            decisiones formales antes de
            considerar información como
            validada.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {metadata && (
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {metadata}
              </span>
            )}

            <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
              {requiringBackground} requieren
              antecedentes
            </span>
          </div>
        </div>
      </section>


      {user?.is_demo && (
        <Alert
          title="Solo lectura en modo demo"
        >
          Puedes revisar antecedentes
          y decisiones históricas,
          pero no registrar hallazgos
          ni decisiones.
        </Alert>
      )}


      {mutationError && (
        <Alert tone="danger">
          {String(
            mutationError
          )}
        </Alert>
      )}


      <FilterBar>
        <div className="grid w-full gap-4 md:grid-cols-2">
          <Select
            label="Tipo"
            value={
              filters.tipo
            }
            onChange={(event) =>
              setFilters(
                (current) => ({
                  ...current,
                  tipo:
                    event.target
                      .value,
                })
              )
            }
          >
            <option value="">
              Todos los tipos
            </option>

            {REVIEW_TYPES.map(
              (value) => (
                <option
                  key={value}
                  value={value}
                >
                  {objectTypeLabel(
                    value
                  )}
                </option>
              )
            )}
          </Select>

          <Select
            label="Estado"
            value={
              filters.estado
            }
            onChange={(event) =>
              setFilters(
                (current) => ({
                  ...current,
                  estado:
                    event.target
                      .value,
                })
              )
            }
          >
            <option value="">
              Todos los estados
            </option>

            {REVIEW_STATES.map(
              (value) => (
                <option
                  key={value}
                  value={value}
                >
                  {human(
                    value
                  )}
                </option>
              )
            )}
          </Select>
        </div>
      </FilterBar>


      {state.status ===
        "error" ? (
        <ErrorState
          description={String(
            state.error
          )}
          onRetry={load}
        />
      ) : !state.rows.length ? (
        <EmptyState
          icon={
            filters.estado ===
              "pendiente"
              ? CheckCircle2
              : FileSearch
          }
          title={
            filters.estado ===
              "pendiente"
              ? "No hay revisiones pendientes"
              : "No hay revisiones con estos filtros"
          }
          description="La ausencia de revisiones pendientes no certifica por sí sola que todos los antecedentes estén validados."
          className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))]"
        />
      ) : (
        <div className="overflow-hidden rounded-[22px] border border-emerald-100 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.05)]">
          <TableShell>
            <TableHead>
              <tr>
                <TableCell as="th">
                  Elemento
                </TableCell>

                <TableCell as="th">
                  Estado
                </TableCell>

                <TableCell as="th">
                  Fecha
                </TableCell>

                <TableCell as="th">
                  Hallazgos
                </TableCell>

                <TableCell as="th">
                  Profesional
                </TableCell>

                <TableCell as="th">
                  Siguiente acción
                </TableCell>
              </tr>
            </TableHead>

            <TableBody
              columns={6}
            >
              {state.rows.map(
                (review) => {
                  const reference =
                    reviewReference(
                      review
                    );

                  const severity =
                    maxFindingSeverity(
                      review.hallazgos
                    );

                  const historical =
                    review.estado !==
                    "pendiente";


                  return (
                    <tr
                      key={
                        review.id
                      }
                      className="transition-colors hover:bg-emerald-50/30"
                    >
                      <TableCell>
                        <div className="min-w-[210px]">
                          <b>
                            {
                              reference.title
                            }
                          </b>

                          <span className="mt-1 block text-xs text-[var(--text-muted)]">
                            Revisión #
                            {
                              review.id
                            }{" "}
                            · Versión{" "}
                            {
                              review.version
                            }
                          </span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <State
                          value={
                            review.estado
                          }
                        />
                      </TableCell>

                      <TableCell>
                        {formatDateTime(
                          review.fecha ||
                          review.created_at
                        )}
                      </TableCell>

                      <TableCell>
                        <div className="min-w-[150px]">
                          <b>
                            {review
                              .hallazgos
                              ?.length ||
                              0}{" "}
                            hallazgos
                          </b>

                          {severity && (
                            <span className="mt-1 block text-xs text-[var(--text-muted)]">
                              Mayor
                              severidad:{" "}
                              {human(
                                severity
                              )}
                            </span>
                          )}

                          {review
                            .hallazgos
                            ?.length >
                            0 && (
                              <details className="mt-2 text-xs">
                                <summary className="cursor-pointer font-bold text-emerald-800">
                                  Ver
                                  hallazgos
                                </summary>

                                <ul className="mt-2 space-y-1 rounded-xl bg-slate-50 p-3">
                                  {review.hallazgos.map(
                                    (
                                      finding
                                    ) => (
                                      <li
                                        key={
                                          finding.id
                                        }
                                      >
                                        <b>
                                          {human(
                                            finding.severidad
                                          )}
                                          :
                                        </b>{" "}
                                        {
                                          finding.observacion
                                        }
                                      </li>
                                    )
                                  )}
                                </ul>
                              </details>
                            )}
                        </div>
                      </TableCell>

                      <TableCell>
                        {review.profesional_nombre ||
                          (
                            historical
                              ? "Profesional no informado"
                              : "Pendiente"
                          )}
                      </TableCell>

                      <TableCell>
                        {!historical &&
                          !user?.is_demo ? (
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => {
                                setMutationError(
                                  ""
                                );

                                setDialog({
                                  ...initialDialog,
                                  review,
                                });
                              }}
                            >
                              Registrar hallazgo
                            </Button>

                            <Button
                              size="sm"
                              onClick={() => {
                                setMutationError(
                                  ""
                                );

                                setDialog({
                                  ...initialDialog,
                                  kind:
                                    "decision",
                                  review,
                                });
                              }}
                            >
                              Tomar decisión
                            </Button>
                          </div>
                        ) : (
                          <div className="text-xs text-[var(--text-muted)]">
                            {user?.is_demo &&
                              !historical
                              ? "Solo lectura en modo demo"
                              : "Solo lectura"}

                            {review.estado ===
                              "solicita_antecedentes" &&
                              review
                                .antecedentes_solicitados
                                ?.length >
                              0 && (
                                <details className="mt-2">
                                  <summary className="cursor-pointer font-bold">
                                    Antecedentes solicitados
                                  </summary>

                                  <ul className="mt-1 list-disc pl-4">
                                    {review.antecedentes_solicitados.map(
                                      (
                                        item,
                                        index
                                      ) => (
                                        <li
                                          key={`${review.id}-${index}`}
                                        >
                                          {String(
                                            item
                                          )}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                </details>
                              )}
                          </div>
                        )}
                      </TableCell>
                    </tr>
                  );
                }
              )}
            </TableBody>
          </TableShell>
        </div>
      )}


      <Modal
        open={Boolean(dialog)}
        title={
          dialog?.kind ===
            "finding"
            ? "Registrar hallazgo"
            : "Registrar decisión profesional"
        }
        description={
          dialog?.kind ===
            "finding"
            ? "El hallazgo queda asociado a esta revisión y no toma una decisión automáticamente."
            : "Esta decisión quedará registrada y no sobrescribirá los antecedentes históricos."
        }
        onClose={() =>
          setDialog(null)
        }
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() =>
                setDialog(
                  null
                )
              }
            >
              Cancelar
            </Button>

            <Button
              loading={saving}
              disabled={
                !dialog?.text.trim()
              }
              onClick={submit}
            >
              {dialog?.kind ===
                "finding"
                ? "Registrar hallazgo"
                : "Confirmar decisión"}
            </Button>
          </div>
        }
      >
        {dialog?.kind ===
          "finding" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Tipo"
              value={
                dialog.tipo
              }
              onChange={(
                event
              ) =>
                setDialog(
                  (current) => ({
                    ...current,
                    tipo:
                      event
                        .target
                        .value,
                  })
                )
              }
            >
              <option value="observacion">
                Observación
              </option>

              <option value="inconsistencia">
                Inconsistencia
              </option>

              <option value="falta_antecedente">
                Falta antecedente
              </option>

              <option value="correccion_requerida">
                Corrección requerida
              </option>

              <option value="validacion">
                Validación
              </option>

              <option value="recomendacion">
                Recomendación
              </option>
            </Select>

            <Select
              label="Severidad"
              value={
                dialog.severidad
              }
              onChange={(
                event
              ) =>
                setDialog(
                  (current) => ({
                    ...current,
                    severidad:
                      event
                        .target
                        .value,
                  })
                )
              }
            >
              <option value="baja">
                Baja
              </option>

              <option value="media">
                Media
              </option>

              <option value="alta">
                Alta
              </option>

              <option value="critica">
                Crítica
              </option>
            </Select>
          </div>
        ) : (
          <Select
            label="Decisión"
            value={
              dialog?.estado ||
              "validada"
            }
            onChange={(event) =>
              setDialog(
                (current) => ({
                  ...current,
                  estado:
                    event.target
                      .value,
                })
              )
            }
          >
            <option value="validada">
              Validar
            </option>

            <option value="validada_con_observaciones">
              Validar con observaciones
            </option>

            <option value="solicita_antecedentes">
              Solicitar antecedentes
            </option>

            <option value="rechazada">
              Rechazar
            </option>
          </Select>
        )}

        <Textarea
          className="mt-4"
          label={
            dialog?.kind ===
              "finding"
              ? "Descripción"
              : dialog?.estado ===
                "solicita_antecedentes"
                ? "Antecedentes solicitados"
                : "Conclusión profesional"
          }
          rows={5}
          required
          value={
            dialog?.text ||
            ""
          }
          onChange={(event) =>
            setDialog(
              (current) => ({
                ...current,
                text:
                  event.target
                    .value,
              })
            )
          }
        />
      </Modal>
    </main>
  );
}