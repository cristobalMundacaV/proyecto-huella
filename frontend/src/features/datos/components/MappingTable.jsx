import { StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";

export default function MappingTable({ mappings, concepts, conceptLabel, onChange }) {
  return <TableShell>
    <TableHead><tr><TableCell as="th" align="left">Columna origen</TableCell><TableCell as="th">Campo destino</TableCell><TableCell as="th">Unidad esperada</TableCell><TableCell as="th">Estado</TableCell></tr></TableHead>
    <TableBody columns={4}>{mappings.map((item, index) => {
      const associated = Boolean(item.concepto_normalizado);
      return <tr key={`${item.columna_origen}-${index}`}>
        <TableCell align="left"><b>{item.columna_origen}</b></TableCell>
        <TableCell><select aria-label={`Campo destino de ${item.columna_origen}`} className="w-full min-w-52 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white p-2" value={item.concepto_normalizado || ""} onChange={(event) => onChange(index, "concepto_normalizado", event.target.value)}>{concepts.map((value) => <option key={value} value={value}>{value ? conceptLabel(value) : "No usar esta columna"}</option>)}</select></TableCell>
        <TableCell><input aria-label={`Unidad esperada de ${item.columna_origen}`} className="w-32 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white p-2" placeholder="Sin unidad" value={item.unidad_esperada || ""} onChange={(event) => onChange(index, "unidad_esperada", event.target.value)} /></TableCell>
        <TableCell><StatusBadge tone={associated ? "success" : "warning"}>{associated ? "Asociado" : "Sin asociar"}</StatusBadge></TableCell>
      </tr>;
    })}</TableBody>
  </TableShell>;
}
