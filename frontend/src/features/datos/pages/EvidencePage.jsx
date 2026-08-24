import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Eye,
  FileCheck2,
  FileText,
  FileUp,
  Plus,
  Search,
} from "lucide-react";

import {
  Link,
  useOutletContext,
} from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { usePermissions } from "@/features/auth/hooks/usePermissions";

import {
  Alert,
  Button,
  EmptyState,
  ErrorState,
  Input,
  Modal,
  Pagination,
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

const PAGE_SIZE = 8;

import { formatDate } from "@/shared/utils/formatters";

import {
  listEvidence,
  listWorkEvidence,
  uploadEvidence,
  uploadWorkEvidence,
} from "../services/dataApi";

import {
  evidenceStatusInfo,
  evidenceTypeLabel,
} from "../utils/dataPresentation";

const EVIDENCE_STATES = [
  "pendiente",
  "validada",
  "observada",
  "rechazada",
  "sin_vinculo",
  "vinculada",
];

const EVIDENCE_TYPE_OPTIONS = [
  {
    value: "guia_despacho",
    label: "Guía de despacho",
  },
  {
    value: "factura_material",
    label: "Factura de materiales",
  },
  {
    value: "factura_combustible",
    label: "Factura de combustible",
  },
  {
    value: "boleta_electrica",
    label: "Boleta eléctrica",
  },
  {
    value: "ficha_tecnica_material",
    label: "Ficha técnica de material",
  },
  {
    value: "registro_maquinaria",
    label: "Registro de maquinaria",
  },
  {
    value: "registro_retiro_residuos",
    label: "Retiro o disposición de residuos",
  },
  {
    value: "documento_transporte",
    label: "Documento de transporte",
  },
  {
    value: "ticket_pesaje",
    label: "Ticket de pesaje",
  },
  {
    value: "certificado_proveedor",
    label: "Certificado de proveedor",
  },
  {
    value: "otro",
    label: "Otro documento",
  },
];

const EMPTY_UPLOAD_FORM = {
  nombre: "",
  tipo_evidencia: "otro",
  fecha_documento: "",
  observaciones: "",
  archivo: null,
};

function extractApiError(error) {
  const response =
    error?.response?.data ??
    error?.data;

  if (!response) {
    return "No se pudo agregar el documento. Revisa los datos e inténtalo nuevamente.";
  }

  if (typeof response === "string") {
    return response;
  }

  if (typeof response?.detail === "string") {
    return response.detail;
  }

  if (typeof response?.error === "string") {
    return response.error;
  }

  if (
    response &&
    typeof response === "object"
  ) {
    const firstError = Object.values(response)
      .flatMap((value) =>
        Array.isArray(value)
          ? value
          : [value]
      )
      .find(Boolean);

    if (firstError) {
      return String(firstError);
    }
  }

  return "No se pudo agregar el documento. Revisa los datos e inténtalo nuevamente.";
}

export default function EvidencePage({
  workScoped = false,
}) {
  const { can } = usePermissions();
  const canCreate = can("evidence.create");
  const workspace =
    useOutletContext() || {};

  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const workCode =
    workspace.obra?.codigo_obra;

  const workName =
    workspace.obra?.nombre;

  const scopeKey = `${activeOrganizacionId || ""
    }:${workScoped
      ? workCode || ""
      : "organization"
    }`;

  const [rows, setRows] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [loadError, setLoadError] =
    useState("");

  const [uploadError, setUploadError] =
    useState("");

  const [
    uploadFeedback,
    setUploadFeedback,
  ] = useState("");

  const [query, setQuery] =
    useState("");

  const [status, setStatus] =
    useState("");
  const [page, setPage] = useState(1);

  const [uploading, setUploading] =
    useState(false);

  const [
    uploadModalOpen,
    setUploadModalOpen,
  ] = useState(false);

  const [uploadForm, setUploadForm] =
    useState({
      ...EMPTY_UPLOAD_FORM,
    });

  const [
    loadedScope,
    setLoadedScope,
  ] = useState("");

  const requestRef = useRef(0);

  const scopeGenerationRef =
    useRef(0);

  const load = useCallback(
    async () => {
      if (
        !activeOrganizacionId ||
        (workScoped && !workCode)
      ) {
        return;
      }

      const requestId =
        ++requestRef.current;

      setLoading(true);
      setLoadError("");

      try {
        const nextRows = await (
          workScoped
            ? listWorkEvidence(
              workCode
            )
            : listEvidence(
              activeOrganizacionId
            )
        );

        if (
          requestRef.current !==
          requestId
        ) {
          return;
        }

        setRows(
          Array.isArray(nextRows)
            ? nextRows
            : []
        );

        setLoadedScope(
          scopeKey
        );
      } catch {
        if (
          requestRef.current ===
          requestId
        ) {
          setLoadError(
            "No fue posible cargar los documentos."
          );

          setLoadedScope(
            scopeKey
          );
        }
      } finally {
        if (
          requestRef.current ===
          requestId
        ) {
          setLoading(false);
        }
      }
    },
    [
      activeOrganizacionId,
      scopeKey,
      workCode,
      workScoped,
    ]
  );

  useEffect(() => {
    scopeGenerationRef.current += 1;

    setRows([]);
    setQuery("");
    setStatus("");
    setUploadError("");
    setUploadFeedback("");
    setUploadModalOpen(false);
    setUploadForm({
      ...EMPTY_UPLOAD_FORM,
    });
    setUploading(false);

    load();

    return () => {
      requestRef.current += 1;
    };
  }, [load]);

  const visible = useMemo(
    () =>
      rows.filter((row) => {
        const text = `
          ${row.nombre || ""}
          ${row.tipo_evidencia || ""}
          ${row.obra_nombre || ""}
          ${row.organizacion_nombre || ""}
        `
          .toLowerCase();

        const matchesQuery =
          !query ||
          text.includes(
            query.toLowerCase()
          );

        const matchesStatus =
          !status ||
          row.estado_documental ===
          status;

        return (
          matchesQuery &&
          matchesStatus
        );
      }),
    [
      query,
      rows,
      status,
    ]
  );
  useEffect(() => { setPage(1); }, [query, status, scopeKey, rows]);
  const pagedVisible = useMemo(() => visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [page, visible]);

  const pendingCount =
    useMemo(
      () =>
        rows.filter((row) =>
          [
            "pendiente",
            "observada",
          ].includes(
            row.estado_documental
          )
        ).length,
      [rows]
    );

  const validatedCount =
    useMemo(
      () =>
        rows.filter(
          (row) =>
            row.estado_documental ===
            "validada"
        ).length,
      [rows]
    );

  function openUploadModal() {
    setUploadError("");

    setUploadForm({
      ...EMPTY_UPLOAD_FORM,
    });

    setUploadModalOpen(true);
  }

  function closeUploadModal() {
    if (uploading) {
      return;
    }

    setUploadModalOpen(false);
    setUploadError("");
  }

  async function submitEvidence() {
    if (!uploadForm.archivo) {
      setUploadError(
        "Debes seleccionar un archivo."
      );
      return;
    }

    const organizationAtStart =
      activeOrganizacionId;

    const workAtStart =
      workCode;

    const scopeGeneration =
      scopeGenerationRef.current;

    const data =
      new FormData();

    data.append(
      "archivo",
      uploadForm.archivo
    );

    data.append(
      "nombre",
      uploadForm.nombre.trim() ||
      uploadForm.archivo.name
    );

    data.append(
      "tipo_evidencia",
      uploadForm.tipo_evidencia
    );

    /*
     * La evidencia recién ingresada
     * no se autovalida.
     */
    data.append(
      "estado_documental",
      "pendiente"
    );

    if (
      uploadForm.fecha_documento
    ) {
      data.append(
        "fecha_documento",
        uploadForm.fecha_documento
      );
    }

    if (
      uploadForm.observaciones.trim()
    ) {
      data.append(
        "observaciones",
        uploadForm.observaciones.trim()
      );
    }

    setUploading(true);
    setUploadError("");
    setUploadFeedback("");

    try {
      await (
        workScoped
          ? uploadWorkEvidence(
            workAtStart,
            data
          )
          : uploadEvidence(
            organizationAtStart,
            data
          )
      );

      if (
        scopeGenerationRef.current !==
        scopeGeneration
      ) {
        return;
      }

      setUploadModalOpen(false);

      setUploadForm({
        ...EMPTY_UPLOAD_FORM,
      });

      setUploadFeedback(
        workScoped
          ? "El documento quedó agregado a esta obra y pendiente de revisión."
          : "El documento fue agregado y quedó pendiente de revisión."
      );

      await load();
    } catch (error) {
      if (
        scopeGenerationRef.current !==
        scopeGeneration
      ) {
        return;
      }

      setUploadError(
        extractApiError(error)
      );
    } finally {
      if (
        scopeGenerationRef.current ===
        scopeGeneration
      ) {
        setUploading(false);
      }
    }
  }

  const uploadAction = canCreate ? (
    <Button
      leftIcon={FileUp}
      onClick={openUploadModal}
    >
      Agregar documento
    </Button>
  ) : undefined;

  if (
    loadedScope !== scopeKey ||
    (loading && !rows.length)
  ) {
    return (
      <PlatformLoader
        compact
        title="Cargando evidencias"
        description="Estamos preparando los documentos y su estado de revisión."
      />
    );
  }

  return (
    <main className="space-y-6">
      {workScoped ? (
        <SectionHeader
          eyebrow="TRAZABILIDAD DOCUMENTAL"
          title="Evidencias"
          description="Consulta y agrega los documentos que respaldan la información ambiental de esta obra."
          action={uploadAction}
        />
      ) : (
        <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
                Datos · Trazabilidad
              </p>

              <h1 className="mt-2 text-3xl font-black">
                Evidencias
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/80">
                Gestiona los documentos que
                respaldan la información
                ambiental de tu operación y
                revisa su estado documental.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                  {rows.length}{" "}
                  {rows.length === 1
                    ? "documento registrado"
                    : "documentos registrados"}
                </span>

                <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                  {pendingCount}{" "}
                  {pendingCount === 1
                    ? "requiere revisión"
                    : "requieren revisión"}
                </span>

                <span className="rounded-full border border-emerald-200/30 bg-emerald-200/10 px-3 py-1.5 text-xs font-bold text-emerald-50">
                  {validatedCount}{" "}
                  {validatedCount === 1
                    ? "validado"
                    : "validados"}
                </span>
              </div>
            </div>

            {canCreate && <Button
              variant="secondary"
              leftIcon={FileUp}
              onClick={
                openUploadModal
              }
              className="self-start border-white/30 bg-white text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] hover:bg-emerald-50 lg:self-center"
            >
              Agregar documento
            </Button>}
          </div>
        </section>
      )}

      {uploadFeedback && (
        <Alert
          tone="success"
          title="Documento agregado"
        >
          {uploadFeedback}
        </Alert>
      )}

      {loadError && (
        <ErrorState
          description={loadError}
          onRetry={load}
        />
      )}

      {!!rows.length && (
        <section className="rounded-2xl border border-[var(--border-subtle)] bg-white p-4 shadow-[0_10px_30px_rgba(15,23,42,0.04)]">
          <div className="grid w-full gap-4 md:grid-cols-2">
            <SearchInput
              label="Buscar evidencias"
              placeholder="Documento, tipo o contexto"
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
            />

            <Select
              label="Estado documental"
              value={status}
              onChange={(event) =>
                setStatus(event.target.value)
              }
            >
              <option value="">
                Todos los estados
              </option>

              {EVIDENCE_STATES.map((value) => (
                <option
                  key={value}
                  value={value}
                >
                  {evidenceStatusInfo(value).label}
                </option>
              ))}
            </Select>
          </div>
        </section>
      )}

      {!rows.length &&
        !loadError ? (
        <EmptyState
          icon={FileCheck2}
          title={
            workScoped
              ? "Aún no hay evidencias en esta obra"
              : "Aún no hay evidencias registradas"
          }
          description={
            workScoped
              ? "Agrega facturas, certificados, respaldos u otros documentos que permitan reconstruir y verificar la información de esta obra."
              : "Incorpora documentos que respalden y permitan verificar la información ambiental de tu operación."
          }
          className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.07)]"
          primaryAction={canCreate ?
            <Button
              leftIcon={Plus}
              onClick={
                openUploadModal
              }
            >
              Agregar primera evidencia
            </Button> : undefined
          }
          secondaryAction={
            !workScoped ? (
              <Link
                className="inline-flex items-center rounded-[var(--radius-md)] px-3 py-2 text-sm font-bold text-[var(--text-secondary)] transition hover:bg-white/70"
                to="/datos/importaciones"
              >
                Importar información
              </Link>
            ) : null
          }
        />
      ) : rows.length &&
        !visible.length ? (
        <EmptyState
          icon={Search}
          title="No encontramos evidencias"
          description="Prueba con otro término o cambia el estado documental seleccionado."
          className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
        />
      ) : (
        !!visible.length && (<>
          <TableShell>
            <TableHead>
              <tr>
                <TableCell as="th" align="left">
                  Documento
                </TableCell>

                <TableCell as="th">
                  Contexto
                </TableCell>

                <TableCell as="th">
                  Estado
                </TableCell>

                <TableCell as="th">
                  Ingreso
                </TableCell>

                <TableCell
                  as="th"
                  className="text-center"
                >
                  Acción
                </TableCell>
              </tr>
            </TableHead>

            <TableBody columns={5}>
              {pagedVisible.map((row) => {
                const rowStatus =
                  evidenceStatusInfo(
                    row.estado_documental
                  );

                return (
                  <tr key={row.id}>
                    <TableCell align="left">
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                          <FileText
                            aria-hidden="true"
                            size={17}
                          />
                        </div>

                        <div className="min-w-0">
                          <b className="block text-[var(--text-primary)]">
                            {row.nombre ||
                              "Documento"}
                          </b>

                          <span className="mt-0.5 block text-xs text-[var(--text-muted)]">
                            {evidenceTypeLabel(
                              row.tipo_evidencia
                            )}
                          </span>
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      {row.obra_nombre ||
                        row.organizacion_nombre ||
                        "Organización"}
                    </TableCell>

                    <TableCell>
                      <StatusBadge
                        tone={
                          rowStatus.tone
                        }
                      >
                        {rowStatus.label}
                      </StatusBadge>
                    </TableCell>

                    <TableCell>
                      {formatDate(
                        row.created_at
                      )}
                    </TableCell>

                    <TableCell className="text-center">
                      <Link
                        to={`/datos/evidencias/${row.id}`}
                        aria-label={`Ver evidencia ${row.nombre || ""
                          }`}
                        title="Ver evidencia"
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
              })}
            </TableBody>
          </TableShell>
          <Pagination page={page} totalItems={visible.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="evidencias" />
        </>)
      )}

      <Modal
        open={uploadModalOpen}
        eyebrow="TRAZABILIDAD DOCUMENTAL"
        icon={FileUp}
        title="Agregar evidencia"
        description={
          workScoped
            ? `Registra un documento que respalde ${workName ||
            "esta unidad"
            } y adjunta el archivo original.`
            : "Define el documento que incorporarás a la trazabilidad ambiental de la organización."
        }
        onClose={
          closeUploadModal
        }
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              disabled={uploading}
              onClick={
                closeUploadModal
              }
            >
              Cancelar
            </Button>

            <Button
              loading={uploading}
              leftIcon={FileUp}
              onClick={
                submitEvidence
              }
            >
              Agregar evidencia
            </Button>
          </div>
        }
      >
        <div className="space-y-5">
          {uploadError && (
            <Alert
              tone="danger"
              title="No pudimos agregar la evidencia"
            >
              {uploadError}
            </Alert>
          )}

          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                <FileText
                  aria-hidden="true"
                  size={19}
                />
              </div>

              <div>
                <p className="font-black text-slate-900">
                  Documento de respaldo
                </p>

                <p className="mt-1 text-sm leading-5 text-slate-600">
                  La evidencia conserva
                  antecedentes y
                  trazabilidad. Subir un
                  documento no lo valida ni
                  genera resultados
                  ambientales automáticamente.
                </p>
              </div>
            </div>
          </div>

          <Select
            label="Tipo de evidencia"
            value={
              uploadForm.tipo_evidencia
            }
            onChange={(event) =>
              setUploadForm(
                (current) => ({
                  ...current,
                  tipo_evidencia:
                    event.target.value,
                })
              )
            }
          >
            {EVIDENCE_TYPE_OPTIONS.map(
              (option) => (
                <option
                  key={
                    option.value
                  }
                  value={
                    option.value
                  }
                >
                  {option.label}
                </option>
              )
            )}
          </Select>

          <Input
            label="Nombre del documento"
            placeholder="Ej: Factura combustible generador junio"
            helper="Si lo dejas vacío utilizaremos el nombre original del archivo."
            value={
              uploadForm.nombre
            }
            onChange={(event) =>
              setUploadForm(
                (current) => ({
                  ...current,
                  nombre:
                    event.target.value,
                })
              )
            }
          />

          <Input
            label="Fecha del documento"
            type="date"
            value={
              uploadForm.fecha_documento
            }
            onChange={(event) =>
              setUploadForm(
                (current) => ({
                  ...current,
                  fecha_documento:
                    event.target.value,
                })
              )
            }
          />

          <Textarea
            label="Observaciones"
            placeholder="Contexto o información relevante que ayude a interpretar este documento."
            value={
              uploadForm.observaciones
            }
            onChange={(event) =>
              setUploadForm(
                (current) => ({
                  ...current,
                  observaciones:
                    event.target.value,
                })
              )
            }
          />

          <div>
            <label className="mb-2 block text-sm font-bold text-[var(--text-primary)]">
              Archivo *
            </label>

            <label className="group flex cursor-pointer items-center gap-4 rounded-2xl border border-dashed border-emerald-300 bg-emerald-50/40 p-5 transition hover:border-emerald-500 hover:bg-emerald-50">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 transition group-hover:bg-emerald-200">
                <FileUp
                  aria-hidden="true"
                  size={21}
                />
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate font-bold text-slate-900">
                  {uploadForm.archivo
                    ? uploadForm.archivo
                      .name
                    : "Seleccionar archivo"}
                </p>

                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Selecciona el
                  documento original que
                  quedará asociado a esta
                  evidencia.
                </p>
              </div>

              <span className="hidden rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs font-bold text-emerald-800 sm:inline">
                Examinar
              </span>

              <input
                type="file"
                className="hidden"
                disabled={uploading}
                onChange={(event) =>
                  setUploadForm(
                    (current) => ({
                      ...current,
                      archivo:
                        event.target
                          .files?.[0] ||
                        null,
                    })
                  )
                }
              />
            </label>

            {uploadForm.archivo && (
              <p className="mt-2 text-xs font-medium text-[var(--text-muted)]">
                Archivo seleccionado:{" "}
                {
                  uploadForm.archivo
                    .name
                }
              </p>
            )}
          </div>
        </div>
      </Modal>
    </main>
  );
}
