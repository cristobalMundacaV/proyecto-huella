import { SelectField } from "@/shared/ui";
import { CHILE_REGIONS, getComunasByRegion, selectChileRegion } from "@/features/organizaciones/utils/chileRegions";

export default function ChileLocationFields({ region, comuna, onChange, errors = {}, onBlur, required = false }) {
  const comunas = getComunasByRegion(region);
  return <>
    <SelectField label="Región" required={required} value={region || ""} options={CHILE_REGIONS.map((item) => ({ value: item.nombre, label: item.nombre }))} onChange={(nextRegion) => onChange(selectChileRegion(nextRegion))} onBlur={() => onBlur?.("region")} error={errors.region} placeholder="Selecciona una región" />
    <SelectField label="Comuna" required={required} disabled={!region} searchable value={comuna || ""} options={comunas.map((item) => ({ value: item.nombre, label: item.nombre }))} onChange={(nextComuna) => onChange({ region, comuna: nextComuna })} onBlur={() => onBlur?.("comuna")} error={errors.comuna} helper={!region ? "Selecciona primero una región." : undefined} placeholder="Selecciona una comuna" searchPlaceholder="Buscar comuna..." />
  </>;
}
