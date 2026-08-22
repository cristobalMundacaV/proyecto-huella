import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Eye,
  FileSpreadsheet,
  Search,
} from "lucide-react";

import { Link } from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
  EmptyState,
  ErrorState,
  FilterBar,
  SearchInput,
  Select,
  StatusBadge,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
} from "@/shared/ui";

import {
  formatDateTime,
} from "@/shared/utils/formatters";

import ImportWorkflow from "../components/ImportWorkflow";

import {
  listImports,
} from "../services/dataApi";

import {
  destinationLabel,
  importDisplayName,
  importNeedsAttention,
  importResultLabel,
  importStatusInfo,
} from "../utils/dataPresentation";


const IMPORT_STATUS_OPTIONS = [
  {
    value: "recibido",
    label: "Recibida",
  },
  {
    value: "analizando",
    label: "Analizando",
  },
  {
    value: "requiere_mapeo",
    label: "Requiere definir columnas",
  },
  {
    value: "listo_para_confirmar",
    label: "Lista para confirmar",
  },
  {
    value: "procesando",
    label: "Procesando",
  },
  {
    value: "completado",
    label: "Completada",
  },
  {
    value: "completado_con_observaciones",
    label: "Completada con observaciones",
  },
  {
    value: "fallido",
    label: "Fallida",
  },
];


export default function ImportsPage() {
  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const scope = String(
    activeOrganizacionId || ""
  );

  const [state, setState] =
    useState({
      scope: null,
      loading: true,
      rows: [],
      error: "",
    });

  const [filters, setFilters] =
    useState({
      query: "",
      status: "",
    });

  const requestRef = useRef(0);
  const workflowRef = useRef(null);

  const openImportWorkflow = () => {
    workflowRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    workflowRef.current?.focus({ preventScroll: true });
    window.history.replaceState(null, "", "#nueva-importacion");
  };


  const load = useCallback(
    async () => {
      if (!activeOrganizacionId) {
        return;
      }

      const requestId =
        ++requestRef.current;

      const organizationAtStart =
        String(activeOrganizacionId);

      setState((current) => ({
        ...current,
        scope: organizationAtStart,
        loading: true,
        error: "",
      }));

      try {
        const rows =
          await listImports(
            activeOrganizacionId
          );

        if (
          requestRef.current !==
          requestId
        ) {
          return;
        }

        setState({
          scope:
            organizationAtStart,
          loading: false,
          rows: Array.isArray(rows)
            ? rows
            : [],
          error: "",
        });
      } catch {
        if (
          requestRef.current !==
          requestId
        ) {
          return;
        }

        setState((current) => ({
          ...current,
          scope:
            organizationAtStart,
          loading: false,
          error:
            "No fue posible cargar el historial. Puedes iniciar una nueva importación igualmente.",
        }));
      }
    },
    [activeOrganizacionId]
  );


  useEffect(() => {
    setState({
      scope,
      loading: true,
      rows: [],
      error: "",
    });

    setFilters({
      query: "",
      status: "",
    });

    load();

    return () => {
      requestRef.current += 1;
    };
  }, [
    load,
    scope,
  ]);


  const visibleRows =
    useMemo(() => {
      const query =
        filters.query
          .trim()
          .toLowerCase();

      return state.rows.filter(
        (row) => {
          const searchableText = `
            ${importDisplayName(row)}
            ${row.fuente_nombre || ""}
            ${destinationLabel(
            row.destino_operacional
          )}
          `.toLowerCase();

          const matchesQuery =
            !query ||
            searchableText.includes(
              query
            );

          const matchesStatus =
            !filters.status ||
            row.estado ===
            filters.status;

          return (
            matchesQuery &&
            matchesStatus
          );
        }
      );
    }, [
      filters,
      state.rows,
    ]);


  const attentionCount =
    useMemo(
      () =>
        state.rows.filter(
          importNeedsAttention
        ).length,
      [state.rows]
    );


  const completedCount =
    useMemo(
      () =>
        state.rows.filter(
          (row) =>
            [
              "completado",
              "completado_con_observaciones",
            ].includes(
              row.estado
            )
        ).length,
      [state.rows]
    );


  if (
    state.scope !== scope
  ) {
    return (
      <PlatformLoader
        compact
        title="Preparando importaciones"
        description="Estamos organizando tus cargas y su historial."
      />
    );
  }


  return (
    <main className="space-y-6">

      {/* HERO */}
      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              Datos · Incorporación
            </p>

            <h1 className="mt-2 text-3xl font-black">
              Importaciones
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/80">
              Incorpora información operacional
              desde planillas, revisa cómo fue
              interpretada y confirma únicamente
              los datos que estés listo para
              incorporar.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {state.rows.length}{" "}
                {state.rows.length === 1
                  ? "importación registrada"
                  : "importaciones registradas"}
              </span>

              <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                {attentionCount}{" "}
                {attentionCount === 1
                  ? "requiere atención"
                  : "requieren atención"}
              </span>

              <span className="rounded-full border border-emerald-200/30 bg-emerald-200/10 px-3 py-1.5 text-xs font-bold text-emerald-50">
                {completedCount}{" "}
                {completedCount === 1
                  ? "completada"
                  : "completadas"}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={openImportWorkflow}
            className="inline-flex self-start items-center gap-2 rounded-xl border border-white/30 bg-white px-4 py-3 text-sm font-black text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] transition hover:bg-emerald-50 lg:self-center"
          >
            <FileSpreadsheet
              aria-hidden="true"
              size={18}
            />

            Nueva importación
          </button>
        </div>
      </section>


      {/* NUEVA IMPORTACIÓN */}
      <section
        ref={workflowRef}
        id="nueva-importacion"
        tabIndex={-1}
        className="scroll-mt-28"
      >
        <ImportWorkflow
          key={
            activeOrganizacionId
          }
          organizationId={
            activeOrganizacionId
          }
          onCompleted={load}
        />
      </section>


      {/* HISTORIAL */}
      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Seguimiento
          </p>

          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            Historial de importaciones
          </h2>

          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Revisa cargas anteriores,
            su estado y el resultado que
            quedó registrado.
          </p>
        </div>


        {state.loading ? (
          <PlatformLoader
            compact
            title="Cargando historial"
            description="Estamos preparando tus importaciones anteriores."
          />
        ) : state.error ? (
          <ErrorState
            description={
              state.error
            }
            onRetry={load}
          />
        ) : !state.rows.length ? (
          <EmptyState
            icon={
              FileSpreadsheet
            }
            title="Aún no hay importaciones anteriores"
            description="Cuando completes tu primera carga, aparecerá aquí con su estado y resultado."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          />
        ) : (
          <>
            {/* FILTROS */}
            <FilterBar>
              <div className="grid w-full gap-4 md:grid-cols-2">
                <SearchInput
                  label="Buscar importaciones"
                  placeholder="Archivo, fuente o destino"
                  value={
                    filters.query
                  }
                  onChange={(
                    event
                  ) =>
                    setFilters(
                      (current) => ({
                        ...current,
                        query:
                          event
                            .target
                            .value,
                      })
                    )
                  }
                />

                <Select
                  label="Estado"
                  value={
                    filters.status
                  }
                  onChange={(
                    event
                  ) =>
                    setFilters(
                      (current) => ({
                        ...current,
                        status:
                          event
                            .target
                            .value,
                      })
                    )
                  }
                >
                  <option value="">
                    Todos los estados
                  </option>

                  {IMPORT_STATUS_OPTIONS.map(
                    (option) => (
                      <option
                        key={
                          option.value
                        }
                        value={
                          option.value
                        }
                      >
                        {
                          option.label
                        }
                      </option>
                    )
                  )}
                </Select>
              </div>
            </FilterBar>


            {!visibleRows.length ? (
              <EmptyState
                icon={Search}
                title="No encontramos importaciones"
                description="Prueba con otro término o cambia el estado seleccionado."
                className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
              />
            ) : (
              <div className="overflow-hidden rounded-[22px] border border-emerald-100 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.05)]">
                <TableShell>
                  <TableHead>
                    <tr>
                      <TableCell as="th">
                        Archivo / fuente
                      </TableCell>

                      <TableCell as="th">
                        Estado
                      </TableCell>

                      <TableCell as="th">
                        Resultado
                      </TableCell>

                      <TableCell as="th">
                        Fecha
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
                    columns={5}
                  >
                    {visibleRows.map(
                      (row) => {
                        const status =
                          importStatusInfo(
                            row.estado
                          );

                        return (
                          <tr
                            key={
                              row.id
                            }
                            className="transition-colors hover:bg-emerald-50/30"
                          >
                            <TableCell>
                              <div className="flex min-w-[220px] items-start gap-3">
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                                  <FileSpreadsheet
                                    aria-hidden="true"
                                    size={
                                      17
                                    }
                                  />
                                </div>

                                <div className="min-w-0">
                                  <b className="block truncate text-[var(--text-primary)]">
                                    {importDisplayName(
                                      row
                                    )}
                                  </b>

                                  <span className="mt-0.5 block text-xs text-[var(--text-muted)]">
                                    {destinationLabel(
                                      row.destino_operacional
                                    )}
                                  </span>
                                </div>
                              </div>
                            </TableCell>

                            <TableCell>
                              <StatusBadge
                                tone={
                                  status.tone
                                }
                              >
                                {
                                  status.label
                                }
                              </StatusBadge>
                            </TableCell>

                            <TableCell>
                              <span className="text-sm text-[var(--text-secondary)]">
                                {importResultLabel(
                                  row
                                )}
                              </span>
                            </TableCell>

                            <TableCell>
                              <span className="text-sm text-[var(--text-secondary)]">
                                {formatDateTime(
                                  row.created_at
                                )}
                              </span>
                            </TableCell>

                            <TableCell className="text-center">
                              <Link
                                to={`/datos/importaciones/${row.id}`}
                                aria-label={`Ver detalle de ${importDisplayName(
                                  row
                                )}`}
                                title="Ver detalle"
                                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 transition hover:bg-emerald-700 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
                              >
                                <Eye
                                  aria-hidden="true"
                                  size={
                                    18
                                  }
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
            )}
          </>
        )}
      </section>
    </main>
  );
}
