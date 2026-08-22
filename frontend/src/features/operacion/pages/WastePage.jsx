import { Link, useOutletContext } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { ErrorState, Pagination, SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import SectorDomainPage from "./SectorDomainPage";
import { isResourceReady, resourceData } from "../utils/operationSelectors";

function measurement(value, unit) {
  if (value === null || value === undefined) return "Sin datos";
  return unit ? `${formatNumber(value)} ${unit}` : `${formatNumber(value)} · unidad no informada`;
}
const PAGE_SIZE = 8;

export default function WastePage() {
  const { operation } = useOutletContext();
  const [page, setPage] = useState(1);
  const eventsReady = isResourceReady(operation.materialEvents);
  const materialWaste = resourceData(operation.materialEvents, []).filter((event) => event.tipo === "residuo");
  useEffect(() => { setPage(1); }, [materialWaste.length]);
  const pagedWaste = useMemo(() => materialWaste.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [materialWaste, page]);

  return <div className="space-y-8">
    <SectorDomainPage domain="residuos" />

    {!eventsReady && <ErrorState title="No fue posible cargar los residuos provenientes de materiales" description="Los registros de residuos del dominio principal permanecen disponibles si pudieron cargarse." />}

    {materialWaste.length > 0 && <section>
      <SectionHeader
        eyebrow="TRAZABILIDAD DE RESIDUOS"
        title="Residuos provenientes de materiales"
        description="Se muestran separados de los otros registros de residuos para no presentar una suma duplicada."
        count={materialWaste.length}
      />
      <TableShell>
        <TableHead><tr>
          <TableCell as="th">Fecha</TableCell>
          <TableCell as="th">Material</TableCell>
          <TableCell as="th">Cantidad</TableCell>
          <TableCell as="th">Destino registrado</TableCell>
          <TableCell as="th">Origen del dato</TableCell>
        </tr></TableHead>
        <TableBody columns={5}>{pagedWaste.map((event) => {
          const source = event.cantidad_detalle?.fuente_detalle?.nombre;
          const sensorId = event.cantidad_detalle?.sensor_detalle?.id;
          return <tr key={event.id}>
            <TableCell>{formatDateTime(event.fecha_hora)}</TableCell>
            <TableCell><span className="font-bold">{event.material_nombre || "Material sin nombre"}</span>{event.lote_codigo && <span className="block text-xs text-[var(--text-muted)]">Lote {event.lote_codigo}</span>}</TableCell>
            <TableCell>{measurement(event.cantidad_detalle?.valor_numerico, event.cantidad_detalle?.unidad)}</TableCell>
            <TableCell>{event.destino || "Sin clasificar"}</TableCell>
            <TableCell>{event.evidencia
              ? <Link className="font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${event.evidencia}`}>Ver documento</Link>
              : sensorId
                ? <Link className="font-bold text-[var(--brand-primary)]" to={`/operacion/sensores/${sensorId}`}>Sensor</Link>
                : source || "Sin origen identificable"}</TableCell>
          </tr>;
        })}</TableBody>
      </TableShell>
      <Pagination page={page} totalItems={materialWaste.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="residuos de materiales" />
    </section>}
  </div>;
}
