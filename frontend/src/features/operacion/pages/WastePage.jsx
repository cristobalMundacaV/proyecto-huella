import { useOutletContext } from "react-router-dom";
import { SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import SectorDomainPage from "./SectorDomainPage";

export default function WastePage() {
  const { operation } = useOutletContext();
  const materialWaste = (operation.materialEvents || []).filter((event) => event.tipo === "residuo");
  return <div className="space-y-8"><SectorDomainPage domain="residuos" />
    {materialWaste.length > 0 && <section><SectionHeader title="Residuos originados en materiales" description="Se presentan separados del flujo sectorial para evitar doble conteo visual." count={materialWaste.length} />
      <TableShell><TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Material</TableCell><TableCell as="th">Lote</TableCell><TableCell as="th">Cantidad</TableCell><TableCell as="th">Destino registrado</TableCell></tr></TableHead><TableBody columns={5}>{materialWaste.map((event) => <tr key={event.id}><TableCell>{formatDateTime(event.fecha_hora)}</TableCell><TableCell>{event.material_nombre}</TableCell><TableCell>{event.lote_codigo || "Sin lote"}</TableCell><TableCell>{formatNumber(event.cantidad_detalle?.valor_numerico)} {event.cantidad_detalle?.unidad}</TableCell><TableCell>{event.destino || "Sin clasificar"}</TableCell></tr>)}</TableBody></TableShell>
    </section>}
  </div>;
}
