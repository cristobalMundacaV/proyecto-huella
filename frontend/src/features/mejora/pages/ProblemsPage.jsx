import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  Plus,
  Search,
} from "lucide-react";

import {
  Link,
  useOutletContext,
  useParams,
} from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  Alert,
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  Modal,
  SearchInput,
  SectionHeader,
  Select,
  StatusBadge,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
  Textarea,
} from "@/shared/ui";

import { formatDate } from "@/shared/utils/formatters";

import {
  createProblem,
  listProblems,
} from "../services/improvementApi";

import {
  problemNextStep,
  problemStatusLabel,
  problemTone,
  riskLabel,
} from "../utils/improvementFormat";


const STATUS_OPTIONS = [
  "detectada",
  "analizando",
  "propuesta",
  "accion_seleccionada",
  "implementando",
  "seguimiento",
  "evaluando",
  "escalada_profesional",
  "cerrada",
  "en_analisis",
  "accion_propuesta",
  "en_implementacion",
  "en_seguimiento",
  "resuelta",
  "mejora_insuficiente",
  "no_resuelta",
  "escalada",
];


const RISK_OPTIONS = [
  "bajo",
  "medio",
  "alto",
  "critico",
];


function initialProblem() {
  return {
    titulo: "",
    descripcion: "",
    categoria: "",
    indicador: "co2e_total_kg",
    unidad_indicador: "kgCO2e",
    valor_inicial: "",
    objetivo_meta: "",
    fecha_deteccion:
      new Date()
        .toISOString()
        .slice(0, 10),
    nivel_riesgo: "medio",
  };
}


function riskTone(value) {
  switch (value) {
    case "critico":
      return "danger";

    case "alto":
      return "danger";

    case "medio":
      return "warning";

    case "bajo":
      return "success";

    default:
      return "neutral";
  }
}


function isClosedProblem(item) {
  return [
    "cerrada",
    "resuelta",
  ].includes(item.estado);
}


function needsProfessionalReview(item) {
  return [
    "escalada_profesional",
    "escalada",
    "no_resuelta",
  ].includes(item.estado);
}


export default function ProblemsPage({
  workScoped = false,
}) {
  const workspace =
    useOutletContext() || {};

  const { obraId } =
    useParams();

  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const work =
    workspace.obra;

  const workId =
    work?.id ||
    work?.obra_id;

  const [state, setState] =
    useState({
      scopeKey: "",
      status: "loading",
      rows: [],
      error: "",
    });

  const [query, setQuery] =
    useState("");

  const [status, setStatus] =
    useState("");

  const [form, setForm] =
    useState(null);

  const [saving, setSaving] =
    useState(false);

  const [
    mutationError,
    setMutationError,
  ] = useState("");

  const requestRef =
    useRef(0);


  const load = useCallback(
    (reset = false) => {
      if (
        !activeOrganizacionId ||
        (workScoped && !workId)
      ) {
        return Promise.resolve();
      }

      const scopeKey =
        `${activeOrganizacionId}:${workScoped
          ? workId
          : "global"
        }`;

      const requestId =
        ++requestRef.current;

      setState((current) => ({
        scopeKey,
        status: "loading",
        rows:
          reset
            ? []
            : current.scopeKey ===
              scopeKey
              ? current.rows
              : [],
        error: "",
      }));

      return listProblems(
        activeOrganizacionId,
        workScoped
          ? workId
          : undefined
      )
        .then((rows) => {
          if (
            requestRef.current !==
            requestId
          ) {
            return;
          }

          setState({
            scopeKey,
            status: "ready",
            rows: Array.isArray(rows)
              ? rows
              : [],
            error: "",
          });
        })
        .catch(() => {
          if (
            requestRef.current !==
            requestId
          ) {
            return;
          }

          setState((current) => ({
            ...current,
            scopeKey,
            status: "error",
            error:
              "No fue posible cargar los problemas.",
          }));
        });
    },
    [
      activeOrganizacionId,
      workId,
      workScoped,
    ]
  );


  useEffect(() => {
    setQuery("");
    setStatus("");

    load(true);

    return () => {
      requestRef.current += 1;
    };
  }, [load]);


  const visible =
    useMemo(
      () =>
        state.rows.filter(
          (item) => {
            const haystack = `
              ${item.titulo || ""}
              ${item.categoria || ""}
              ${item.unidad_operacional || ""}
              ${item.area_operacional || ""}
            `.toLowerCase();

            const matchesQuery =
              !query ||
              haystack.includes(
                query.toLowerCase()
              );

            const matchesStatus =
              !status ||
              item.estado === status;

            return (
              matchesQuery &&
              matchesStatus
            );
          }
        ),
      [
        query,
        state.rows,
        status,
      ]
    );


  const openCount =
    useMemo(
      () =>
        state.rows.filter(
          (item) =>
            !isClosedProblem(item)
        ).length,
      [state.rows]
    );


  const highRiskCount =
    useMemo(
      () =>
        state.rows.filter(
          (item) =>
            [
              "alto",
              "critico",
            ].includes(
              item.nivel_riesgo
            )
        ).length,
      [state.rows]
    );


  const professionalCount =
    useMemo(
      () =>
        state.rows.filter(
          needsProfessionalReview
        ).length,
      [state.rows]
    );


  async function submit(event) {
    event.preventDefault();

    setSaving(true);
    setMutationError("");

    try {
      await createProblem(
        activeOrganizacionId,
        {
          ...form,
          obra:
            workScoped
              ? workId
              : null,
        },
        workScoped
          ? workId
          : undefined,
      );

      setForm(null);

      await load(false);
    } catch (error) {
      setMutationError(
        error?.response?.data?.detail ||
        "No se pudo registrar el problema."
      );
    } finally {
      setSaving(false);
    }
  }


  const requestedScopeKey =
    activeOrganizacionId &&
      (!workScoped || workId)
      ? `${activeOrganizacionId}:${workScoped
        ? workId
        : "global"
      }`
      : "";


  const scopeChanged =
    state.scopeKey !==
    requestedScopeKey;


  const path = (id) =>
    workScoped
      ? `/obras/${obraId}/problemas/${id}`
      : `/inteligencia/problemas/${id}`;


  function openCreateModal() {
    setMutationError("");

    setForm(
      initialProblem()
    );
  }


  const createAction = (
    <Button
      leftIcon={Plus}
      onClick={openCreateModal}
    >
      Registrar problema
    </Button>
  );


  if (
    scopeChanged ||
    (
      state.status === "loading" &&
      !state.rows.length
    )
  ) {
    return (
      <PlatformLoader
        compact
        title="Cargando problemas"
        description="Estamos preparando las situaciones ambientales y su estado de gestión."
      />
    );
  }


  return (
    <main className="space-y-6">

      {/* HEADER / HERO */}
      {workScoped ? (
        <SectionHeader
          eyebrow="GESTIÓN AMBIENTAL"
          title="Problemas"
          description="Gestiona las situaciones ambientales detectadas en esta obra hasta verificar su resultado."
          action={createAction}
        />
      ) : (
        <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
                Gestión ambiental · Mejora
              </p>

              <h1 className="mt-2 text-3xl font-black">
                Problemas y acciones
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">
                Gestiona situaciones
                ambientales desde su
                detección, revisa su
                siguiente paso y acompaña
                cada acción hasta comprobar
                su resultado.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                  {openCount}{" "}
                  {openCount === 1
                    ? "problema abierto"
                    : "problemas abiertos"}
                </span>

                <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                  {highRiskCount}{" "}
                  {highRiskCount === 1
                    ? "de riesgo alto"
                    : "de riesgo alto"}
                </span>

                <span className="rounded-full border border-sky-200/30 bg-sky-200/10 px-3 py-1.5 text-xs font-bold text-sky-50">
                  {professionalCount}{" "}
                  {professionalCount === 1
                    ? "requiere revisión profesional"
                    : "requieren revisión profesional"}
                </span>
              </div>
            </div>

            <Button
              variant="secondary"
              leftIcon={Plus}
              onClick={
                openCreateModal
              }
              className="self-start border-white/30 bg-white text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] hover:bg-emerald-50 lg:self-center"
            >
              Registrar problema
            </Button>
          </div>
        </section>
      )}


      {/* ERROR DE CARGA */}
      {state.status ===
        "error" && (
          <ErrorState
            description={
              state.error
            }
            onRetry={() =>
              load(false)
            }
          />
        )}


      {/* FILTROS */}
      {!!state.rows.length && (
        <FilterBar>
          <div className="grid w-full gap-4 md:grid-cols-2">
            <SearchInput
              label="Buscar problemas"
              placeholder="Título, categoría o contexto"
              value={query}
              onChange={(event) =>
                setQuery(
                  event.target.value
                )
              }
            />

            <Select
              label="Estado"
              value={status}
              onChange={(event) =>
                setStatus(
                  event.target.value
                )
              }
            >
              <option value="">
                Todos los estados
              </option>

              {STATUS_OPTIONS.map(
                (value) => (
                  <option
                    key={value}
                    value={value}
                  >
                    {problemStatusLabel(
                      value
                    )}
                  </option>
                )
              )}
            </Select>
          </div>
        </FilterBar>
      )}


      {/* EMPTY */}
      {state.status !== "error" &&
        !visible.length ? (
        <EmptyState
          icon={
            state.rows.length
              ? Search
              : CheckCircle2
          }
          title={
            state.rows.length
              ? "No encontramos problemas"
              : "No hay problemas registrados"
          }
          description={
            state.rows.length
              ? "Prueba con otro término o cambia el estado seleccionado."
              : workScoped
                ? "Esta unidad no tiene problemas vinculados."
                : "Registra un problema cuando exista una situación ambiental que deba gestionarse y verificarse."
          }
          className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          primaryAction={
            !state.rows.length ? (
              <Button
                leftIcon={Plus}
                onClick={
                  openCreateModal
                }
              >
                Registrar primer problema
              </Button>
            ) : null
          }
        />
      ) : (
        !scopeChanged &&
        visible.length > 0 && (
          <div className="overflow-hidden rounded-[22px] border border-emerald-100 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.05)]">
            <TableShell>
              <TableHead>
                <tr>
                  <TableCell as="th">
                    Problema
                  </TableCell>

                  <TableCell as="th">
                    Estado
                  </TableCell>

                  <TableCell as="th">
                    Riesgo
                  </TableCell>

                  <TableCell as="th">
                    Contexto
                  </TableCell>

                  <TableCell as="th">
                    Siguiente paso
                  </TableCell>

                  <TableCell
                    as="th"
                    className="text-center"
                  >
                    Acción
                  </TableCell>
                </tr>
              </TableHead>

              <TableBody
                columns={6}
              >
                {visible.map(
                  (item) => {
                    /*
                     * Importante:
                     * este listado NO carga
                     * acciones, mediciones
                     * ni ciclos.
                     *
                     * El helper conserva
                     * UNKNOWN != EMPTY.
                     */
                    const next =
                      problemNextStep({
                        problem: item,
                      });

                    const context =
                      item.unidad_operacional ||
                      item.area_operacional ||
                      (
                        item.obra
                          ? "Unidad vinculada"
                          : "Organización"
                      );

                    return (
                      <tr
                        key={
                          item.id
                        }
                        className="transition-colors hover:bg-emerald-50/30"
                      >
                        <TableCell>
                          <div className="min-w-[230px]">
                            <p className="font-black text-[var(--text-primary)]">
                              {
                                item.titulo
                              }
                            </p>

                            {item.fecha_deteccion && (
                              <span className="mt-1 block text-xs text-[var(--text-muted)]">
                                Detectado{" "}
                                {formatDate(
                                  item.fecha_deteccion
                                )}
                              </span>
                            )}
                          </div>
                        </TableCell>

                        <TableCell>
                          <StatusBadge
                            tone={problemTone(
                              item.estado
                            )}
                          >
                            {problemStatusLabel(
                              item.estado
                            )}
                          </StatusBadge>
                        </TableCell>

                        <TableCell>
                          <StatusBadge
                            tone={riskTone(
                              item.nivel_riesgo
                            )}
                          >
                            {riskLabel(
                              item.nivel_riesgo
                            )}
                          </StatusBadge>
                        </TableCell>

                        <TableCell>
                          <span className="text-sm text-[var(--text-secondary)]">
                            {context}
                          </span>
                        </TableCell>

                        <TableCell>
                          <div className="max-w-[240px]">
                            <p className="text-sm font-bold text-[var(--text-primary)]">
                              {
                                next.title
                              }
                            </p>
                          </div>
                        </TableCell>

                        <TableCell className="text-center">
                          <Link
                            to={path(
                              item.id
                            )}
                            aria-label={`Ver problema ${item.titulo}`}
                            title="Ver detalle"
                            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 transition hover:bg-emerald-700 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
                          >
                            <Eye
                              aria-hidden="true"
                              size={18}
                            />
                          </Link>
                        </TableCell>
                      </tr>
                    );
                  }
                )}
              </TableBody>
            </TableShell>
          </div>
        )
      )}


      {/* MODAL */}
      <Modal
        open={Boolean(form)}
        title="Registrar problema"
        description="Describe la situación ambiental y define cómo se medirá. Registrar un problema no selecciona ni ejecuta ninguna acción."
        onClose={() => {
          if (!saving) {
            setForm(null);
            setMutationError("");
          }
        }}
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              disabled={saving}
              onClick={() => {
                setForm(null);
                setMutationError("");
              }}
            >
              Cancelar
            </Button>

            <Button
              form="problem-form"
              loading={saving}
              type="submit"
            >
              Registrar problema
            </Button>
          </div>
        }
      >
        <form
          id="problem-form"
          className="space-y-6"
          onSubmit={submit}
        >
          {mutationError && (
            <Alert
              tone="danger"
              title="No pudimos registrar el problema"
            >
              {mutationError}
            </Alert>
          )}


          <div className="rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
                <AlertTriangle
                  aria-hidden="true"
                  size={19}
                />
              </div>

              <div>
                <p className="font-black text-slate-900">
                  Situación a gestionar
                </p>

                <p className="mt-1 text-sm leading-5 text-slate-600">
                  El problema debe representar
                  una situación concreta que
                  pueda seguirse mediante un
                  indicador y comprobarse con
                  mediciones posteriores.
                </p>
              </div>
            </div>
          </div>


          <section className="space-y-4">
            <div>
              <h3 className="font-black text-[var(--text-primary)]">
                Problema
              </h3>

              <p className="mt-1 text-sm text-[var(--text-muted)]">
                Describe qué ocurre y cuál es
                su nivel de riesgo.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                required
                label="Título"
                placeholder="Ej: Consumo elevado de combustible"
                value={
                  form?.titulo ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    titulo:
                      event.target
                        .value,
                  })
                }
              />

              <Input
                required
                label="Categoría"
                placeholder="Ej: Combustible"
                value={
                  form?.categoria ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    categoria:
                      event.target
                        .value,
                  })
                }
              />

              <div className="sm:col-span-2">
                <Textarea
                  required
                  label="Descripción"
                  placeholder="Describe la situación observada y por qué requiere gestión."
                  value={
                    form?.descripcion ||
                    ""
                  }
                  onChange={(
                    event
                  ) =>
                    setForm({
                      ...form,
                      descripcion:
                        event.target
                          .value,
                    })
                  }
                />
              </div>

              <Select
                label="Nivel de riesgo"
                value={
                  form?.nivel_riesgo ||
                  "medio"
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    nivel_riesgo:
                      event.target
                        .value,
                  })
                }
              >
                {RISK_OPTIONS.map(
                  (value) => (
                    <option
                      key={value}
                      value={value}
                    >
                      {riskLabel(
                        value
                      )}
                    </option>
                  )
                )}
              </Select>

              <Input
                required
                label="Fecha de detección"
                type="date"
                value={
                  form?.fecha_deteccion ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    fecha_deteccion:
                      event.target
                        .value,
                  })
                }
              />
            </div>
          </section>


          <section className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50/60 p-4">
            <div>
              <h3 className="font-black text-[var(--text-primary)]">
                Medición inicial
              </h3>

              <p className="mt-1 text-sm text-[var(--text-muted)]">
                Define la situación BASE que
                permitirá comprobar después
                si la intervención produjo un
                resultado.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                required
                label="Indicador"
                value={
                  form?.indicador ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    indicador:
                      event.target
                        .value,
                  })
                }
              />

              <Input
                required
                label="Unidad"
                value={
                  form?.unidad_indicador ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    unidad_indicador:
                      event.target
                        .value,
                  })
                }
              />

              <Input
                required
                label="Situación actual"
                type="number"
                step="any"
                value={
                  form?.valor_inicial ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    valor_inicial:
                      event.target
                        .value,
                  })
                }
              />

              <Input
                required
                label="Meta"
                type="number"
                step="any"
                value={
                  form?.objetivo_meta ||
                  ""
                }
                onChange={(
                  event
                ) =>
                  setForm({
                    ...form,
                    objetivo_meta:
                      event.target
                        .value,
                  })
                }
              />
            </div>
          </section>
        </form>
      </Modal>
    </main>
  );
}