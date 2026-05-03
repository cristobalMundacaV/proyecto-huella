import { useState } from "react";

import LoteTabs from "./LoteTabs";
import ActividadesTab from "./tabs/ActividadesTab";
import EvidenciasTab from "./tabs/EvidenciasTab";
import HistorialTab from "./tabs/HistorialTab";
import PasaporteTab from "./tabs/PasaporteTab";
import ResumenTab from "./tabs/ResumenTab";
import TransporteTab from "./tabs/TransporteTab";

function LoteDetailView({
  activeExtraction,
  activityError,
  activityFieldErrors,
  activityForm,
  balanceData,
  detailLoading,
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
  onActivitySubmit,
  onDocumentSubmit,
  onDownloadCertificate,
  onSelectActivityFactor,
  onRejectExtraction,
  onRejectHistoryExtraction,
  onRunOcr,
  onRunStructuredExtraction,
  onTransportSubmit,
  onUpdateActivityForm,
  onUpdateDocumentForm,
  onUpdateOcrForm,
  onUpdateTransportDestination,
  onUpdateTransportForm,
  onUpdateTransportOrigin,
  onValidateExtraction,
  onValidateHistoryExtraction,
  readingDocumentId,
  savingActivity,
  savingDocument,
  savingTransport,
  selectedLote,
  transportError,
  transportFieldErrors,
  transportForm,
  transportRouteGeometry,
  validatingExtraction,
}) {
  const [activeTab, setActiveTab] = useState("resumen");

  if (!selectedLote) {
    return <p className="text-slate-400">Selecciona un lote para continuar.</p>;
  }

  return (
    <div className="space-y-6">
      <LoteTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === "resumen" && (
        <ResumenTab balanceData={balanceData} selectedLote={selectedLote} />
      )}

      {activeTab === "actividades" && (
        <ActividadesTab
          activityError={activityError}
          activityFieldErrors={activityFieldErrors}
          activityForm={activityForm}
          factoresEmision={factoresEmision}
          onActivitySubmit={onActivitySubmit}
          onSelectActivityFactor={onSelectActivityFactor}
          onUpdateActivityForm={onUpdateActivityForm}
          savingActivity={savingActivity}
          selectedLote={selectedLote}
        />
      )}

      {activeTab === "pasaporte" && (
        <PasaporteTab
          balanceData={balanceData}
          generatingCertificate={generatingCertificate}
          onDownloadCertificate={onDownloadCertificate}
          selectedLote={selectedLote}
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
          selectedLote={selectedLote}
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
          selectedLote={selectedLote}
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

export default LoteDetailView;
