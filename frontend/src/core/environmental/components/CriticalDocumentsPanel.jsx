import { FileCheck2 } from "lucide-react";

import EnvironmentalItemGrid from "./EnvironmentalItemGrid";

function CriticalDocumentsPanel({ matrix }) {
  return (
    <EnvironmentalItemGrid
      icon={FileCheck2}
      tone="blue"
      title="Documentos criticos esperados"
      description="Datos necesarios para respaldar calculos, evidencias y obligaciones ambientales."
      items={matrix.criticalDocuments}
    />
  );
}

export default CriticalDocumentsPanel;
