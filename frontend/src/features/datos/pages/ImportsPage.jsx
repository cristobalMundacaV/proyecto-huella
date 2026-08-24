import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Boxes,
  Database,
  Eye,
  FileCheck2,
  FileSpreadsheet,
  History,
  Search,
  UploadCloud,
} from "lucide-react";

import { Link, useNavigate } from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { usePermissions } from "@/features/auth/hooks/usePermissions";

import {
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  Pagination,
  SearchInput,
  Select,
  StatusBadge,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
} from "@/shared/ui";

const PAGE_SIZE = 8;

import {
  formatDateTime,
} from "@/shared/utils/formatters";

import ImportWorkflow from "../components/ImportWorkflow";
import ImportModeCard from "../components/ImportModeCard";

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
  const { can } = usePermissions();
  const canCreate = can("imports.create");
  const navigate = useNavigate();
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
  const [page, setPage] = useState(1);
  const [workflowOpen, setWorkflowOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const requestRef = useRef(0);
  const workflowRef = useRef(null);

  const openImportWorkflow = () => {
    setWorkflowOpen(true);
    window.requestAnimationFrame(() => {
      workflowRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      workflowRef.current?.focus({ preventScroll: true });
    });
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

  useEffect(() => { setPage(1); }, [filters.query, filters.status, scope, state.rows]);
  const pagedRows = useMemo(() => historyOpen ? visibleRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) : visibleRows.slice(0, 5), [historyOpen, page, visibleRows]);


  const pendingConfirmationCount =
    useMemo(
      () =>
        state.rows.filter(
          (row) =>
            [
              "requiere_mapeo",
              "listo_para_confirmar",
            ].includes(
              row.estado
            )
        ).length,
      [state.rows]
    );

  const scopeLabel = (row) => ({
    organizacion: "Organización", obra: "Obra", dominio: "Dominio ambiental", activo: "Activo",
  }[row.contexto_confirmado?.alcance] || "Organización");

  const contextLabel = (row) => {
    const context = row.contexto_confirmado || {};
    return [context.obra_nombre, context.dominio_label].filter(Boolean).join(" · ") || "Toda la organización";
  };


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
              {state.rows.length > 0 && <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {state.rows.length}{" "}
                {state.rows.length === 1
                  ? "importación registrada"
                  : "importaciones registradas"}
              </span>}

              {attentionCount > 0 && <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                {attentionCount}{" "}
                {attentionCount === 1
                  ? "requiere atención"
                  : "requieren atención"}
              </span>}

              {pendingConfirmationCount > 0 && <span className="rounded-full border border-emerald-200/30 bg-emerald-200/10 px-3 py-1.5 text-xs font-bold text-emerald-50">
                {pendingConfirmationCount}{" "}
                {pendingConfirmationCount === 1
                  ? "pendiente de confirmación"
                  : "pendientes de confirmación"}
              </span>}
            </div>
          </div>

          {canCreate && <Button
            onClick={openImportWorkflow}
            className="inline-flex self-start items-center gap-2 rounded-xl border border-white/30 bg-white px-4 py-3 text-sm font-black text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] transition hover:bg-emerald-50 lg:self-center"
          >
            <FileSpreadsheet
              aria-hidden="true"
              size={18}
            />

            Nueva importación
          </Button>}
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">Punto de entrada</p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">¿Qué quieres incorporar?</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Elige el flujo correcto antes de seleccionar archivos.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {canCreate && <ImportModeCard icon={UploadCloud} title="Importar datos operacionales" description="Consumos, materiales, residuos, transporte y otras mediciones." onClick={openImportWorkflow} />}
          <ImportModeCard icon={FileCheck2} title="Subir evidencia o documento" description="Respalda la trazabilidad ambiental con un antecedente documental." onClick={() => navigate("/datos/evidencias")} />
          <ImportModeCard icon={Database} title="Importar catálogo maestro" description="Carga administrada de catálogos y datos de referencia." disabled badge="Próximamente" />
          <ImportModeCard icon={Boxes} title="Importación masiva" description="Procesamiento coordinado de varios archivos o estructuras." disabled badge="Próximamente" />
        </div>
        <div className="flex flex-wrap gap-3">
          {canCreate && <Button onClick={openImportWorkflow}><UploadCloud aria-hidden="true" size={17} />Nueva importación</Button>}
          <Button variant="secondary" onClick={() => setHistoryOpen(true)}><History aria-hidden="true" size={17} />Ver historial</Button>
        </div>
      </section>


      {/* NUEVA IMPORTACIÓN */}
      {workflowOpen && <section
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
          onClose={() => setWorkflowOpen(false)}
        />
      </section>}


      {/* HISTORIAL */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Seguimiento
          </p>

          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            {historyOpen ? "Historial de importaciones" : "Importaciones recientes"}
          </h2>

          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Revisa cargas anteriores,
            su estado y el resultado que
            quedó registrado.
          </p>
          </div>
          {!historyOpen && state.rows.length > 5 && (
            <Button variant="secondary" onClick={() => setHistoryOpen(true)}><History aria-hidden="true" size={17} />Ver historial completo</Button>
          )}
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
            action={canCreate ? <Button onClick={openImportWorkflow}><UploadCloud aria-hidden="true" size={17} />Nueva importación</Button> : undefined}
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          />
        ) : (
          <>
            {/* FILTROS */}
            {historyOpen && <FilterBar>
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
            </FilterBar>}


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
                      <TableCell as="th">Fecha</TableCell>
                      <TableCell as="th">Archivo / fuente</TableCell>
                      <TableCell as="th">Alcance</TableCell>
                      <TableCell as="th">Contexto</TableCell>

                      <TableCell as="th">
                        Estado
                      </TableCell>

                      <TableCell as="th">
                        Resultado
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
                    columns={7}
                  >
                    {pagedRows.map(
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
                            <TableCell><span className="whitespace-nowrap text-sm text-[var(--text-secondary)]">{formatDateTime(row.created_at)}</span></TableCell>
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

                            <TableCell><span className="text-sm text-[var(--text-secondary)]">{scopeLabel(row)}</span></TableCell>
                            <TableCell><span className="text-sm text-[var(--text-secondary)]">{contextLabel(row)}</span></TableCell>

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
                {historyOpen && <Pagination page={page} totalItems={visibleRows.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="importaciones" />}
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
