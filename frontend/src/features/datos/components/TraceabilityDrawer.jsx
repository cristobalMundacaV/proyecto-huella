import {
  ClipboardList,
  Database,
  FileText,
  ShieldCheck,
} from "lucide-react";
import { evidenceDetailPath } from "../utils/evidencePaths";

import {
  ButtonLink,
  Drawer,
  StatusBadge,
} from "@/shared/ui";

import {
  formatDateTime,
  formatNumber,
} from "@/shared/utils/formatters";


const LABELS = {
  diesel: "Diésel",
  gasolina: "Gasolina",
  gas_licuado: "Gas licuado",
  gas_natural: "Gas natural",
  generador: "Generador",
  maquinaria: "Maquinaria",
  vehiculo: "Vehículo",
  equipo_menor: "Equipo menor",
  calefaccion: "Calefacción",
  manual: "Manual",
  declarativo: "Declarativo",
  pendiente: "Pendiente",
};


function human(value) {
  if (!value) {
    return null;
  }

  if (LABELS[value]) {
    return LABELS[value];
  }

  const normalized =
    String(value)
      .replaceAll(
        "_",
        " ",
      );

  return (
    normalized
      .charAt(0)
      .toUpperCase() +
    normalized.slice(1)
  );
}


function Row({
  label,
  value,
}) {
  if (
    value === undefined ||
    value === null ||
    value === ""
  ) {
    return null;
  }

  return (
    <div className="
      grid grid-cols-[140px_1fr]
      gap-4 py-2.5 text-sm
    ">
      <dt className="
        text-[var(--text-muted)]
      ">
        {label}
      </dt>

      <dd className="
        break-words
        font-semibold
        text-[var(--text-primary)]
      ">
        {value}
      </dd>
    </div>
  );
}


function Section({
  icon: Icon,
  title,
  children,
}) {
  return (
    <section className="
      rounded-2xl
      border border-[var(--border-default)]
      bg-[var(--bg-surface)]
      p-4
    ">
      <div className="
        mb-2 flex
        items-center gap-2
      ">
        {Icon && (
          <span className="
            flex h-8 w-8
            items-center justify-center
            rounded-lg
            bg-[var(--bg-surface-subtle)]
            text-[var(--brand-primary)]
          ">
            <Icon size={16} />
          </span>
        )}

        <h3 className="font-black">
          {title}
        </h3>
      </div>

      <dl>
        {children}
      </dl>
    </section>
  );
}


export default function TraceabilityDrawer({
  observation,
  open,
  onClose,
  workId,
}) {
  if (
    observation?.provenance_type ===
    "sensor_reading"
  ) {
    const reading =
      observation.reading;

    return (
      <Drawer
        open={open}
        onClose={onClose}
        title="Origen del dato"
      >
        <div className="space-y-4">
          <Section
            icon={ClipboardList}
            title="Lectura vinculada"
          >
            <Row
              label="Valor"
              value={`${formatNumber(
                reading.valor_numerico,
              )} ${reading.unidad || ""}`}
            />

            <Row
              label="Concepto"
              value={human(
                reading.concepto,
              )}
            />

            <Row
              label="Fecha"
              value={formatDateTime(
                reading.timestamp,
              )}
            />

            <Row
              label="Medición"
              value="Instrumental"
            />

            <Row
              label="Calidad técnica"
              value={human(
                reading.calidad_tecnica,
              )}
            />
          </Section>

          <Section
            icon={Database}
            title="Fuente"
          >
            <Row
              label="Nombre"
              value={
                reading.fuente_nombre ||
                observation.sensor_name
              }
            />

            <Row
              label="Tipo"
              value="Sensor"
            />
          </Section>
        </div>
      </Drawer>
    );
  }

  const source =
    observation?.fuente_detalle ||
    observation?.fuente;

  const evidence =
    observation?.evidencia_detalle ||
    observation?.evidencia;

  const version =
    observation
      ?.version_evidencia_detalle ||
    observation
      ?.version_evidencia;

  const record =
    observation?.__record;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Origen del dato"
    >
      {!observation ? (
        <p className="
          text-sm
          text-[var(--text-muted)]
        ">
          No hay trazabilidad
          identificable para este dato.
        </p>
      ) : (
        <div className="space-y-4">
          <Section
            icon={ClipboardList}
            title="Resumen del registro"
          >
            <Row
              label="Tipo"
              value={human(
                record?.tipo_recurso,
              )}
            />

            <Row
              label="Cantidad"
              value={
                observation.valor_numerico ===
                  null
                  ? observation.valor_texto
                  : `${formatNumber(
                    observation.valor_numerico,
                  )} ${observation.unidad ||
                  ""
                    }`.trim()
              }
            />

            <Row
              label="Concepto"
              value={human(
                observation.concepto,
              )}
            />

            <Row
              label="Estado"
              value={
                <StatusBadge
                  label={human(
                    observation.estado ||
                    "sin_estado",
                  )}
                />
              }
            />

            <Row
              label="Fecha"
              value={formatDateTime(
                observation.timestamp_observacion,
              )}
            />
          </Section>

          <Section
            icon={ClipboardList}
            title="Contexto operacional"
          >
            <Row
              label="Uso / destino"
              value={human(
                record?.destino_operacional,
              )}
            />

            <Row
              label="Ubicación"
              value={
                record?.ubicacion_contexto ||
                human(
                  record?.granularidad,
                )
              }
            />
          </Section>

          <Section
            icon={ShieldCheck}
            title="Captura y calidad"
          >
            <Row
              label="Método"
              value={human(
                observation.metodo_captura,
              )}
            />

            <Row
              label="Naturaleza"
              value={human(
                observation.naturaleza,
              )}
            />

            <Row
              label="Calidad"
              value={human(
                observation.estado_calidad ||
                observation.estado,
              )}
            />
          </Section>

          <Section
            icon={Database}
            title="Fuente"
          >
            <Row
              label="Nombre"
              value={
                source?.nombre ||
                (typeof source ===
                  "string"
                  ? source
                  : null)
              }
            />

            <Row
              label="Tipo"
              value={human(
                source?.tipo ||
                source?.tipo_fuente,
              )}
            />

            <Row
              label="Confiabilidad"
              value={human(
                source?.confiabilidad,
              )}
            />
          </Section>

          {(evidence ||
            version) && (
              <Section
                icon={FileText}
                title="Respaldo documental"
              >
                <Row
                  label="Documento"
                  value={
                    evidence?.nombre ||
                    observation.evidencia_nombre
                  }
                />

                <Row
                  label="Versión"
                  value={
                    version?.version ||
                    observation
                      .version_evidencia_version
                  }
                />

                <Row
                  label="Archivo"
                  value={
                    version?.nombre_original ||
                    observation
                      .version_evidencia_nombre_original
                  }
                />
              </Section>
            )}
          <div className="
  grid grid-cols-1 gap-2
  pt-1 sm:grid-cols-2
">
            {evidence?.id && (
              <ButtonLink
                variant="primary"
                leftIcon={FileText}
                to={evidenceDetailPath(evidence.id, workId)}
                className="
                  w-full
                  shadow-sm
                "
              >
                Ver evidencia
              </ButtonLink>
            )}

            {workId && (
              <ButtonLink
                variant="secondary"
                leftIcon={ClipboardList}
                to={`/obras/${workId}/operacion`}
                className="
                  w-full
                  border-emerald-200
                  bg-emerald-50
                  text-emerald-800
                  hover:bg-emerald-100
                "
              >
                Ver operación de la obra
              </ButtonLink>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
