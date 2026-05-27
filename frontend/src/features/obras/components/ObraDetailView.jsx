import { useState } from "react";

import ObraTabs from "./ObraTabs";
import RegistrosEmisionTab from "./tabs/RegistrosEmisionTab";
import EvidenciasTab from "./tabs/EvidenciasTab";
import HistorialTab from "./tabs/HistorialTab";
import FichaAmbientalTab from "./tabs/FichaAmbientalTab";
import ResumenTab from "./tabs/ResumenTab";
import EstadoEmisionesTab from "./tabs/EstadoEmisionesTab";
import TransporteTab from "./tabs/TransporteTab";

function ObraDetailView({
  activeExtraction,
  registroError,
  registroFieldErrors,
  registroForm,
  balanceData,
  documentError,
  documentFieldErrors,
  documentForm,
  documentInsight,
  extractingDocumentId,
  factoresEmision,
  generatingCertificate,
  history,
  historyLoading,
  historyPageInfo,
  ocrError,
  ocrForm,
  onRegistroSubmit,
  onDocumentSubmit,
  onDownloadCertificate,
  onselectRegistroFactor,
  onRejectExtraction,
  onRejectHistoryExtraction,
  onRunOcr,
  onRunStructuredExtraction,
  onTransportSubmit,
  onUpdateregistroForm,
  onUpdateDocumentForm,
  onUpdateOcrForm,
  onUpdateTransportDestination,
  onUpdateTransportForm,
  onUpdateTransportOrigin,
  onValidateExtraction,
  onValidateHistoryExtraction,
  readingDocumentId,
  savingRegistro,
  savingDocument,
  savingTransport,
  selectedObra,
  transportError,
  transportFieldErrors,
  transportForm,
  transportRouteGeometry,
  validatingExtraction,
}) {
  const [activeTab, setActiveTab] = useState("resumen");

  if (!selectedObra) {
    return <p className="text-slate-400">Selecciona una obra para continuar.</p>;
  }

  return (
    <div className="space-y-6">
      <ObraTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === "resumen" && (
        <ResumenTab balanceData={balanceData} selectedObra={selectedObra} />
      )}

      {activeTab === "estado_emisiones" && (
        <EstadoEmisionesTab selectedObra={selectedObra} />
      )}

      {activeTab === "registros_emision" && (
        <RegistrosEmisionTab
          registroError={registroError}
          registroFieldErrors={registroFieldErrors}
          registroForm={registroForm}
          factoresEmision={factoresEmision}
          onRegistroSubmit={onRegistroSubmit}
          onselectRegistroFactor={onselectRegistroFactor}
          onUpdateregistroForm={onUpdateregistroForm}
          savingRegistro={savingRegistro}
          selectedObra={selectedObra}
        />
      )}

      {activeTab === "ficha_ambiental" && (
        <FichaAmbientalTab
          balanceData={balanceData}
          generatingCertificate={generatingCertificate}
          onDownloadCertificate={onDownloadCertificate}
          selectedObra={selectedObra}
        />
      )}

      {activeTab === "evidencias" && (
        <EvidenciasTab
          activeExtraction={activeExtraction}
          documentError={documentError}
          documentFieldErrors={documentFieldErrors}
          documentForm={documentForm}
          documentInsight={documentInsight}
          extractingDocumentId={extractingDocumentId}
          ocrError={ocrError}
          ocrForm={ocrForm}
          onDocumentSubmit={onDocumentSubmit}
          onRejectExtraction={onRejectExtraction}
          onRunOcr={onRunOcr}
          onRunStructuredExtraction={onRunStructuredExtraction}
          onUpdateDocumentForm={onUpdateDocumentForm}
          onUpdateOcrForm={onUpdateOcrForm}
          onValidateExtraction={onValidateExtraction}
          readingDocumentId={readingDocumentId}
          savingDocument={savingDocument}
          selectedObra={selectedObra}
          validatingExtraction={validatingExtraction}
        />
      )}

      {activeTab === "transporte" && (
        <TransporteTab
          onUpdateTransportDestination={onUpdateTransportDestination}
          onTransportSubmit={onTransportSubmit}
          onUpdateTransportForm={onUpdateTransportForm}
          onUpdateTransportOrigin={onUpdateTransportOrigin}
          savingTransport={savingTransport}
          selectedObra={selectedObra}
          transportError={transportError}
          transportFieldErrors={transportFieldErrors}
          transportForm={transportForm}
          transportRouteGeometry={transportRouteGeometry}
        />
      )}

      {activeTab === "historial" && (
        <HistorialTab
          history={history}
          historyLoading={historyLoading}
          historyPageInfo={historyPageInfo}
          onRejectHistoryExtraction={onRejectHistoryExtraction}
          onValidateHistoryExtraction={onValidateHistoryExtraction}
          validatingExtraction={validatingExtraction}
        />
      )}
    </div>
  );
}

export default ObraDetailView;
