import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  Plus,
  Radio,
} from "lucide-react";

import { Link } from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getAssets } from "@/features/activos/api/assetsApi";

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
} from "@/shared/ui";

import { formatDateTime } from "@/shared/utils/formatters";

import {
  createSensor,
  getSensors,
} from "../api/sensorsApi";

const SENSOR_TYPE_OPTIONS = [
  { value: "gps", label: "GPS" },
  { value: "combustible", label: "Combustible" },
  { value: "energia", label: "Energía" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "agua", label: "Agua" },
  { value: "ambiente", label: "Ambiente" },
  { value: "mixto", label: "Mixto" },
];

const SENSOR_STATUS_OPTIONS = [
  { value: "operativo", label: "Operativo" },
  {
    value: "requiere_revision",
    label: "Requiere revisión",
  },
  {
    value: "fuera_servicio",
    label: "Fuera de servicio",
  },
  {
    value: "calibracion_vencida",
    label: "Calibración vencida",
  },
];

const initial = {
  dispositivo_id: "",
  nombre: "",
  tipo_sensor: "gps",
  estado: "operativo",
  activo_operacional: "",
};

function optionLabel(options, value) {
  return (
    options.find(
      (option) => option.value === value
    )?.label ||
    String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (character) =>
        character.toUpperCase()
      )
  );
}

function calibrationLabel(sensor) {
  if (
    !sensor.ultima_calibracion &&
    !sensor.proxima_calibracion
  ) {
    return "Sin calibración registrada";
  }

  if (
    sensor.ultima_calibracion &&
    !sensor.proxima_calibracion
  ) {
    return `${sensor.ultima_calibracion} · Sin próxima fecha`;
  }

  if (
    !sensor.ultima_calibracion &&
    sensor.proxima_calibracion
  ) {
    return `Próxima: ${sensor.proxima_calibracion}`;
  }

  return `${sensor.ultima_calibracion} · Próxima: ${sensor.proxima_calibracion}`;
}

export default function SensoresPage() {
  const { activeOrganizacionId } =
    useOrganizacionActiva();

  const [state, setState] = useState({
    loading: true,
    sensors: [],
    assets: [],
    error: "",
  });

  const [filters, setFilters] = useState({
    query: "",
    tipo: "",
    estado: "",
  });

  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setState((current) => ({
      ...current,
      loading: true,
      error: "",
    }));

    Promise.allSettled([
      getSensors(activeOrganizacionId),
      getAssets(activeOrganizacionId),
    ]).then(([sensors, assets]) => {
      setState({
        loading: false,
        sensors:
          sensors.status === "fulfilled"
            ? sensors.value
            : [],
        assets:
          assets.status === "fulfilled"
            ? assets.value
            : [],
        error:
          sensors.status === "rejected"
            ? "No fue posible cargar los sensores."
            : "",
      });
    });
  }, [activeOrganizacionId]);

  useEffect(() => {
    load();
  }, [load]);

  const sensors = useMemo(() => {
    const query = filters.query
      .trim()
      .toLowerCase();

    return state.sensors.filter((sensor) => {
      const matchesQuery =
        !query ||
        `${sensor.nombre} ${sensor.dispositivo_id}`
          .toLowerCase()
          .includes(query);

      const matchesType =
        !filters.tipo ||
        sensor.tipo_sensor === filters.tipo;

      const matchesStatus =
        !filters.estado ||
        sensor.estado === filters.estado;

      return (
        matchesQuery &&
        matchesType &&
        matchesStatus
      );
    });
  }, [filters, state.sensors]);

  const attentionCount =
    state.sensors.filter(
      (sensor) =>
        sensor.estado === "requiere_revision" ||
        sensor.estado === "calibracion_vencida" ||
        sensor.estado === "fuera_servicio"
    ).length;

  async function save() {
    setBusy(true);

    try {
      await createSensor(
        activeOrganizacionId,
        Object.fromEntries(
          Object.entries(form).filter(
            ([, value]) => value !== ""
          )
        )
      );

      setForm(null);
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
              Operación · Telemetría
            </p>

            <h1 className="mt-2 text-3xl font-black">
              Sensores
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/80">
              Monitorea dispositivos, condición
              técnica y variables observadas dentro
              de tu operación. Las lecturas se
              mantienen separadas del cálculo
              ambiental gobernado.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {state.sensors.length}{" "}
                {state.sensors.length === 1
                  ? "sensor registrado"
                  : "sensores registrados"}
              </span>

              <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                {attentionCount}{" "}
                {attentionCount === 1
                  ? "requiere atención"
                  : "requieren atención"}
              </span>
            </div>
          </div>

          <Button
            variant="secondary"
            leftIcon={Plus}
            onClick={() =>
              setForm({ ...initial })
            }
            className="self-start border-white/30 bg-white text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] hover:bg-emerald-50 lg:self-center"
          >
            Crear sensor
          </Button>
        </div>
      </section>

      {state.sensors.length > 0 && (
        <FilterBar>
          <div className="grid w-full gap-4 md:grid-cols-[minmax(0,2fr)_minmax(180px,1fr)_minmax(180px,1fr)]">
            <SearchInput
              label="Buscar sensores"
              placeholder="Nombre o identificador"
              value={filters.query}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  query: event.target.value,
                })
              }
            />

            <Select
              label="Tipo de variable"
              value={filters.tipo}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  tipo: event.target.value,
                })
              }
            >
              <option value="">
                Todos los tipos
              </option>

              {SENSOR_TYPE_OPTIONS.map(
                (option) => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                )
              )}
            </Select>

            <Select
              label="Estado técnico"
              value={filters.estado}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  estado: event.target.value,
                })
              }
            >
              <option value="">
                Todos los estados
              </option>

              {SENSOR_STATUS_OPTIONS.map(
                (option) => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                )
              )}
            </Select>
          </div>
        </FilterBar>
      )}

      {state.error ? (
        <ErrorState
          description={state.error}
          onRetry={load}
        />
      ) : state.loading ? (
        <PlatformLoader
          compact
          title="Cargando sensores"
          description="Estamos preparando los dispositivos y su estado técnico."
        />
      ) : !state.sensors.length ? (
        <EmptyState
          icon={Radio}
          title="Aún no hay sensores registrados"
          description="Registra dispositivos cuando formen parte real de tu operación para comenzar a recibir y gobernar sus lecturas."
          className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.07)]"
          primaryAction={
            <Button
              leftIcon={Plus}
              onClick={() =>
                setForm({ ...initial })
              }
            >
              Crear primer sensor
            </Button>
          }
        />
      ) : !sensors.length ? (
        <EmptyState
          icon={Activity}
          title="No encontramos sensores"
          description="Prueba cambiando el nombre, tipo de variable o estado técnico."
        />
      ) : (
        <TableShell>
          <TableHead>
            <tr>
              <TableCell as="th">
                Sensor
              </TableCell>

              <TableCell as="th">
                Variable
              </TableCell>

              <TableCell as="th">
                Activo asociado
              </TableCell>

              <TableCell as="th">
                Estado técnico
              </TableCell>

              <TableCell as="th">
                Última comunicación
              </TableCell>

              <TableCell as="th">
                Calibración
              </TableCell>

              <TableCell as="th">
                Acción
              </TableCell>
            </tr>
          </TableHead>

          <TableBody columns={7}>
            {sensors.map((sensor) => (
              <tr key={sensor.id}>
                <TableCell>
                  <b>{sensor.nombre}</b>

                  <span className="block text-xs text-[var(--text-muted)]">
                    {sensor.dispositivo_id}
                  </span>
                </TableCell>

                <TableCell>
                  {optionLabel(
                    SENSOR_TYPE_OPTIONS,
                    sensor.tipo_sensor
                  )}
                </TableCell>

                <TableCell>
                  {sensor.activo_nombre ||
                    "Sin activo asociado"}
                </TableCell>

                <TableCell>
                  <StatusBadge>
                    {optionLabel(
                      SENSOR_STATUS_OPTIONS,
                      sensor.estado
                    )}
                  </StatusBadge>
                </TableCell>

                <TableCell>
                  {sensor.last_seen_at
                    ? formatDateTime(
                      sensor.last_seen_at
                    )
                    : "Sin comunicación registrada"}
                </TableCell>

                <TableCell>
                  {calibrationLabel(sensor)}
                </TableCell>

                <TableCell>
                  <Link
                    className="font-bold text-[var(--brand-primary)]"
                    to={`/operacion/sensores/${sensor.id}`}
                  >
                    Ver detalle
                  </Link>
                </TableCell>
              </tr>
            ))}
          </TableBody>
        </TableShell>
      )}

      <Modal
        open={Boolean(form)}
        title="Crear sensor"
        description="Registra un dispositivo físico para incorporar sus lecturas al seguimiento operacional. El sensor no genera emisiones automáticamente."
        onClose={() => setForm(null)}
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => setForm(null)}
            >
              Cancelar
            </Button>

            <Button
              loading={busy}
              onClick={save}
            >
              Crear sensor
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Input
            required
            label="Identificador del dispositivo"
            placeholder="Ej: SENSOR-DIESEL-01"
            helper="Código único utilizado para reconocer el dispositivo dentro de la plataforma."
            value={
              form?.dispositivo_id || ""
            }
            onChange={(event) =>
              setForm({
                ...form,
                dispositivo_id:
                  event.target.value,
              })
            }
          />

          <Input
            required
            label="Nombre"
            placeholder="Ej: Sensor generador diésel"
            value={form?.nombre || ""}
            onChange={(event) =>
              setForm({
                ...form,
                nombre: event.target.value,
              })
            }
          />

          <Select
            label="Tipo de variable"
            value={
              form?.tipo_sensor || "gps"
            }
            onChange={(event) =>
              setForm({
                ...form,
                tipo_sensor:
                  event.target.value,
              })
            }
          >
            {SENSOR_TYPE_OPTIONS.map(
              (option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              )
            )}
          </Select>

          <Select
            label="Activo asociado"
            value={
              form?.activo_operacional || ""
            }
            onChange={(event) =>
              setForm({
                ...form,
                activo_operacional:
                  event.target.value,
              })
            }
          >
            <option value="">
              Sin activo asociado
            </option>

            {state.assets.map((asset) => (
              <option
                key={asset.id}
                value={asset.id}
              >
                {asset.nombre}
              </option>
            ))}
          </Select>
        </div>
      </Modal>
    </main>
  );
}