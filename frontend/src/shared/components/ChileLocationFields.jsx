import { Select } from "@/shared/ui";
import { CHILE_REGIONS, getComunasByRegion, selectChileRegion } from "@/features/organizaciones/utils/chileRegions";

export default function ChileLocationFields({ region, comuna, onChange, errors = {}, onBlur, required = false }) {
  const comunas = getComunasByRegion(region);
  return <>
    <Select label="Región" required={required} value={region || ""} onChange={(event) => onChange(selectChileRegion(event.target.value))} onBlur={() => onBlur?.("region")} error={errors.region}>
      <option value="">Selecciona una región</option>
      {CHILE_REGIONS.map((item) => <option key={item.codigo} value={item.nombre}>{item.nombre}</option>)}
    </Select>
    <Select label="Comuna" required={required} disabled={!region} value={comuna || ""} onChange={(event) => onChange({ region, comuna: event.target.value })} onBlur={() => onBlur?.("comuna")} error={errors.comuna} helper={!region ? "Selecciona primero una región." : undefined}>
      <option value="">Selecciona una comuna</option>
      {comunas.map((item) => <option key={item.codigo} value={item.nombre}>{item.nombre}</option>)}
    </Select>
  </>;
}
