import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Boxes,
} from "lucide-react";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import {
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  Modal,
  SearchInput,
  Select,
  StatusBadge,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
  Textarea,
} from "@/shared/ui";

import {
  createAsset,
  createMaintenance,
  getAssets,
  updateAsset,
} from "../api/assetsApi";

const blank = {
  codigo: "",
  nombre: "",
  tipo: "vehiculo",
  estado: "operativo",
  descripcion: "",
};

const ASSET_TYPE_OPTIONS = [
  { value: "vehiculo", label: "Vehículo" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "equipo", label: "Equipo" },
  { value: "medidor", label: "Medidor" },
  { value: "infraestructura", label: "Infraestructura" },
  { value: "otro", label: "Otro" },
];

const ASSET_STATUS_OPTIONS = [
  { value: "operativo", label: "Operativo" },
  {
    value: "requiere_revision",
    label: "Requiere revisión",
  },
  {
    value: "fuera_servicio",
    label: "Fuera de servicio",
  },
  { value: "retirado", label: "Retirado" },
];

const MAINTENANCE_STATUS_OPTIONS = [
  { value: "programado", label: "Programado" },
  { value: "realizado", label: "Realizado" },
  { value: "vencido", label: "Vencido" },
];

const optionLabel = (options, value) =>
  options.find((option) => option.value === value)?.label ||
  String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase()
    );

export default function ActivosPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();

  const [state, setState] = useState({
    loading: true,
    rows: [],
    error: "",
  });

  const [filters, setFilters] = useState({
    tipo: "",
    estado: "",
    query: "",
  });

  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setState((current) => ({
      ...current,
      loading: true,
      error: "",
    }));

    getAssets(activeOrganizacionId, {
      tipo: filters.tipo,
      estado: filters.estado,
    })
      .then((rows) =>
        setState({
          loading: false,
          rows,
          error: "",
        })
      )
      .catch(() =>
        setState({
          loading: false,
          rows: [],
          error: "No fue posible cargar los activos.",
        })
      );
  }, [
    activeOrganizacionId,
    filters.estado,
    filters.tipo,
  ]);

  useEffect(() => {
    load();
  }, [load]);

  const rows = useMemo(
    () =>
      state.rows.filter(
        (item) =>
          !filters.query ||
          `${item.nombre} ${item.codigo}`
            .toLowerCase()
            .includes(filters.query.toLowerCase())
      ),
    [filters.query, state.rows]
  );

  async function save() {
    setBusy(true);

    try {
      if (dialog.id) {
        await updateAsset(
          activeOrganizacionId,
          dialog.id,
          dialog
        );
      } else {
        await createAsset(
          activeOrganizacionId,
          dialog
        );
      }

      setDialog(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function maintenance() {
    setBusy(true);

    try {
      await createMaintenance(
        activeOrganizacionId,
        dialog.asset.id,
        dialog.form
      );

      setDialog(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              Operación · Mundo físico
            </p>

            <h1 className="mt-2 text-3xl font-black">
              Activos operacionales
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/80">
              Gestiona equipos, maquinaria, medidores e infraestructura
              que forman parte real de tu operación.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {state.rows.length}{" "}
                {state.rows.length === 1
                  ? "activo registrado"
                  : "activos registrados"}
              </span>

              <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                {
                  state.rows.filter(
                    (item) =>
                      item.estado === "requiere_revision"
                  ).length
                }{" "}
                con revisión pendiente
              </span>
            </div>
          </div>

          <Button
            variant="secondary"
            leftIcon={Plus}
            onClick={() =>
              setDialog({ ...blank })
            }
            className="self-start border-white/30 bg-white text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] hover:bg-emerald-50 lg:self-center"
          >
            Crear activo
          </Button>
        </div>
      </section>

      <FilterBar>
        <div className="grid w-full gap-4 md:grid-cols-[minmax(0,2fr)_minmax(180px,1fr)_minmax(180px,1fr)]">
          <SearchInput
            label="Buscar activos"
            placeholder="Nombre o código"
            value={filters.query}
            onChange={(e) =>
              setFilters({
                ...filters,
                query: e.target.value,
              })
            }
          />

          <Select
            label="Tipo"
            value={filters.tipo}
            onChange={(e) =>
              setFilters({
                ...filters,
                tipo: e.target.value,
              })
            }
          >
            <option value="">
              Todos los tipos
            </option>

            {ASSET_TYPE_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </Select>

          <Select
            label="Estado"
            value={filters.estado}
            onChange={(e) =>
              setFilters({
                ...filters,
                estado: e.target.value,
              })
            }
          >
            <option value="">
              Todos los estados
            </option>

            {ASSET_STATUS_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </Select>
        </div>
      </FilterBar>

      {state.error ? (
        <ErrorState
          description={state.error}
          onRetry={load}
        />
      ) : state.loading ? (
        <PlatformLoader
          compact
          title="Cargando activos"
          description="Estamos preparando los equipos y su estado operacional."
        />
      ) : !rows.length ? (
        <div className="overflow-hidden rounded-[26px] border border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.12),transparent_38%),linear-gradient(135deg,rgba(236,253,245,0.92),rgba(255,255,255,0.98))] p-2 shadow-[0_12px_36px_rgba(6,78,59,0.06)]">
          <EmptyState
            icon={Boxes}
            title="Aún no hay activos registrados"
            description="Incorpora maquinaria, vehículos, equipos, medidores o infraestructura cuando formen parte real de tu operación."
            primaryAction={
              <Button
                leftIcon={Plus}
                onClick={() =>
                  setDialog({ ...blank })
                }
              >
                Crear primer activo
              </Button>
            }
          />
        </div>
      ) : (
        <TableShell>
          <TableHead>
            <tr>
              <TableCell as="th">
                Activo
              </TableCell>

              <TableCell as="th">
                Tipo
              </TableCell>

              <TableCell as="th">
                Estado
              </TableCell>

              <TableCell as="th">
                Contexto
              </TableCell>

              <TableCell as="th">
                Condición reciente
              </TableCell>

              <TableCell as="th">
                Sensores
              </TableCell>

              <TableCell as="th">
                Acciones
              </TableCell>
            </tr>
          </TableHead>

          <TableBody columns={7}>
            {rows.map((item) => (
              <tr key={item.id}>
                <TableCell>
                  <b>{item.nombre}</b>

                  <span className="block text-xs text-[var(--text-muted)]">
                    {item.codigo}
                  </span>
                </TableCell>

                <TableCell>
                  {optionLabel(
                    ASSET_TYPE_OPTIONS,
                    item.tipo
                  )}
                </TableCell>

                <TableCell>
                  <StatusBadge>
                    {optionLabel(
                      ASSET_STATUS_OPTIONS,
                      item.estado
                    )}
                  </StatusBadge>
                </TableCell>

                <TableCell>
                  {item.unidad_nombre ||
                    "Sin unidad"}{" "}
                  ·{" "}
                  {item.proceso_nombre ||
                    "Sin proceso"}
                </TableCell>

                <TableCell>
                  {item.condiciones?.[0]?.estado
                    ? String(item.condiciones[0].estado)
                      .replaceAll("_", " ")
                      .replace(/\b\w/g, (character) =>
                        character.toUpperCase()
                      )
                    : "Sin registro"}
                </TableCell>

                <TableCell>
                  <Link
                    className="font-bold text-[var(--brand-primary)]"
                    to="/operacion/sensores"
                  >
                    {item.sensores_count ?? 0}{" "}
                    sensores
                  </Link>
                </TableCell>

                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        setDialog({
                          ...item,
                        })
                      }
                    >
                      Editar
                    </Button>

                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        setDialog({
                          type: "maintenance",
                          asset: item,
                          form: {
                            tipo: "Preventivo",
                            fecha_programada: "",
                            estado: "programado",
                          },
                        })
                      }
                    >
                      Mantenimiento
                    </Button>
                  </div>
                </TableCell>
              </tr>
            ))}
          </TableBody>
        </TableShell>
      )}

      <Modal
        open={Boolean(dialog)}
        title={
          dialog?.type === "maintenance"
            ? `Mantenimiento · ${dialog.asset.nombre}`
            : dialog?.id
              ? "Editar activo"
              : "Crear activo"
        }
        description={
          dialog?.type === "maintenance"
            ? "Programa o registra una intervención sobre este activo."
            : dialog?.id
              ? "Actualiza la información operacional del activo."
              : "Registra un equipo físico para incorporarlo al seguimiento de tu operación."
        }
        onClose={() => setDialog(null)}
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => setDialog(null)}
            >
              Cancelar
            </Button>

            <Button
              loading={busy}
              onClick={
                dialog?.type ===
                  "maintenance"
                  ? maintenance
                  : save
              }
            >
              Guardar
            </Button>
          </div>
        }
      >
        {dialog?.type === "maintenance" ? (
          <div className="space-y-4">
            <Input
              label="Tipo"
              value={dialog.form.tipo}
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  form: {
                    ...dialog.form,
                    tipo: e.target.value,
                  },
                })
              }
            />

            <Input
              type="date"
              label="Fecha programada"
              value={
                dialog.form.fecha_programada
              }
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  form: {
                    ...dialog.form,
                    fecha_programada:
                      e.target.value,
                  },
                })
              }
            />

            <Select
              label="Estado"
              value={dialog.form.estado}
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  form: {
                    ...dialog.form,
                    estado: e.target.value,
                  },
                })
              }
            >
              {MAINTENANCE_STATUS_OPTIONS.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        ) : (
          <div className="space-y-4">
            <Input
              required
              label="Código"
              helper="Identificador interno del activo. Por ejemplo: EXC-01 o CAM-03."
              placeholder="Ej: EXC-01"
              value={dialog?.codigo || ""}
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  codigo: e.target.value,
                })
              }
            />

            <Input
              required
              label="Nombre"
              value={dialog?.nombre || ""}
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  nombre: e.target.value,
                })
              }
            />

            <Select
              label="Tipo"
              value={
                dialog?.tipo || "vehiculo"
              }
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  tipo: e.target.value,
                })
              }
            >
              {[
                "vehiculo",
                "maquinaria",
                "equipo",
                "medidor",
                "infraestructura",
                "otro",
              ].map((v) => (
                <option key={v}>
                  {v}
                </option>
              ))}
            </Select>

            <Select
              label="Estado"
              value={
                dialog?.estado ||
                "operativo"
              }
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  estado: e.target.value,
                })
              }
            >
              {[
                "operativo",
                "requiere_revision",
                "fuera_servicio",
                "retirado",
              ].map((v) => (
                <option key={v}>
                  {v}
                </option>
              ))}
            </Select>

            <Textarea
              label="Descripción"
              value={
                dialog?.descripcion || ""
              }
              onChange={(e) =>
                setDialog({
                  ...dialog,
                  descripcion:
                    e.target.value,
                })
              }
            />
          </div>
        )}
      </Modal>
    </main>
  );
}