import { useState } from "react";
import { Building2, CheckCircle2, MousePointerClick } from "lucide-react";

import ObraTabs from "./ObraTabs";
import EvidenciasTab from "./tabs/EvidenciasTab";
import HistorialTab from "./tabs/HistorialTab";
import FichaAmbientalTab from "./tabs/FichaAmbientalTab";
import ResumenTab from "./tabs/ResumenTab";
import EstadoEmisionesTab from "./tabs/EstadoEmisionesTab";
import TransporteTab from "./tabs/TransporteTab";

function ObraDetailView({
  activeExtraction,
  balanceData,
  documentError,
  documentFieldErrors,
  documentForm,
  documentInsight,
  extractingDocumentId,
  generatingCertificate,
  history,
  historyLoading,
  historyPageInfo,
  ocrError,
  ocrForm,
  onDocumentSubmit,
  onDownloadCertificate,
  onRejectExtraction,
  onRejectHistoryExtraction,
  onRunOcr,
  onRunStructuredExtraction,
  onTransportSubmit,
  onUpdateDocumentForm,
  onUpdateOcrForm,
  onUpdateTransportDestination,
  onUpdateTransportForm,
  onUpdateTransportOrigin,
  onValidateExtraction,
  onValidateHistoryExtraction,
  readingDocumentId,
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
    return <SelectObraEmptyState />;
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

      {activeTab === "ficha_ambiental" && (
        <FichaAmbientalTab
          balanceData={balanceData}
          generatingCertificate={generatingCertificate}
          onDownloadCertificate={onDownloadCertificate}
          selectedObra={selectedObra}
        />
      )}
    </div>
  );
}

function SelectObraEmptyState() {
  return (
    <section className="relative overflow-hidden rounded-[32px] border border-[var(--border)] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_45%,#ECFDF5_100%)] p-6 shadow-[var(--shadow-card)] sm:p-8">
      <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-emerald-200/45 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-16 h-56 w-56 rounded-full bg-sky-200/35 blur-3xl" />

      <div className="relative z-10 mx-auto flex max-w-3xl flex-col items-center text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-3xl border border-[#A7F3D0] bg-[#ECFDF5] text-[#047857] shadow-[0_18px_38px_rgba(4,120,87,0.14)]">
          <Building2 size={28} />
        </div>

        <p className="mt-5 text-xs font-black uppercase tracking-[0.16em] text-[var(--primary-dark)]">
          Sin obra seleccionada
        </p>
        <h2 className="mt-2 text-2xl font-black leading-tight text-[var(--text-main)] sm:text-3xl">
          Selecciona una obra para ver su inteligencia ambiental
        </h2>
        <p className="mt-3 max-w-2xl text-sm font-medium leading-7 text-[var(--text-muted)] sm:text-base">
          El resumen, estado de emisiones, evidencias, transporte, historial y ficha ambiental se habilitan solo cuando eliges una obra desde la tabla superior.
        </p>

        <div className="mt-6 grid w-full gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-[#B8D6DE] bg-white/80 p-4 text-left shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#BFDBFE] bg-[#EFF6FF] text-[#1D4ED8]">
                <MousePointerClick size={18} />
              </span>
              <div>
                <p className="text-sm font-black text-[var(--text-main)]">Selecciona una fila</p>
                <p className="text-xs font-semibold text-[var(--text-muted)]">Haz clic sobre una obra registrada.</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-[#A7F3D0] bg-white/80 p-4 text-left shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#A7F3D0] bg-[#ECFDF5] text-[#047857]">
                <CheckCircle2 size={18} />
              </span>
              <div>
                <p className="text-sm font-black text-[var(--text-main)]">Vista limpia y confiable</p>
                <p className="text-xs font-semibold text-[var(--text-muted)]">No se muestran datos hasta tener contexto.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default ObraDetailView;
