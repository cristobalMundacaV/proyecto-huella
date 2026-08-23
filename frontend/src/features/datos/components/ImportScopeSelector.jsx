import { Building2, Factory, Layers3, Wrench } from "lucide-react";
import ImportModeCard from "./ImportModeCard";

const scopes = [
  { value: "organizacion", icon: Building2, title: "Organización completa", description: "Información transversal que pertenece a la organización y no a una obra específica." },
  { value: "obra", icon: Factory, title: "Obra específica", description: "Información generada o utilizada dentro de una obra determinada." },
  { value: "dominio", icon: Layers3, title: "Ámbito ambiental", description: "Información asociada a un flujo ambiental concreto de una obra." },
  { value: "activo", icon: Wrench, title: "Activo o fuente operacional", description: "El modelo actual no permite verificar que un activo pertenezca a una obra.", disabled: true },
];

export default function ImportScopeSelector({ value, onChange }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="Alcance de la importación">
    {scopes.map((scope) => <ImportModeCard key={scope.value} {...scope} selected={value === scope.value} onSelect={() => onChange(scope.value)} />)}
  </div>;
}
