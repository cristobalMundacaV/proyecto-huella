import { useEffect, useMemo, useRef, useState } from "react";

import CrearLoteModal from "@/features/lotes/components/CrearLoteModal";
import LoteDetailView from "@/features/lotes/components/LoteDetailView";
import LoteDetailModal from "@/features/lotes/components/LoteDetailModal";
import LotesHeader from "@/features/lotes/components/LotesHeader";
import LotesKpis from "@/features/lotes/components/LotesKpis";
import LotesTable from "@/features/lotes/components/LotesTable";
import EmptyState from "@/shared/components/EmptyState";
import ImportarDocumentoObraModal from "@/shared/components/ImportarDocumentoObraModal";
import {
  calculateRouteDistance,
  createLote,
  createLoteActividad,
  createLoteTransporte,
  downloadLoteCertificado,
  extractDocumentJsonById,
  getEmpresas,
  getEspeciesMadera,
  getFactoresEmision,
  getHistorialLote,
  getEmpresaLotes,
  getEmpresaUnidades,
  getLoteCarbono,
  getLoteDetail,
  rejectExtraccionDocumento,
  runDocumentoOcr,
  uploadLoteDocumento,
  validateExtraccionDocumento,
} from "@/shared/services/api";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";

const emptyForm = {
  id_lote: "",
  empresa_id: "",
  unidad_id: "",
  empresa_aserradero: "",
  fecha: "",
  especie: "",
  volumen_m3: "",
  origen: "",
};

const emptyActivityForm = {
  factor_emision_id: "",
  actividad: "",
  tipo_consumo_combustible: "",
  cantidad: "",
  unidad: "",
  fecha: "",
  factor_emision: "",
  origen_transporte: "",
  destino_transporte: "",
  origen_coords: null,
  destino_coords: null,
  distancia_km: "",
  ruta_geometry: [],
};

const emptyDocumentForm = {
  tipo_documento: "guia_despacho",
  fecha: "",
  archivo: null,
};

const emptyTransportForm = {
  vehiculo: "",
  patente: "",
  punto_partida: "",
  punto_partida_coords: null,
  fecha_hora: "",
  destino: "",
  destino_coords: null,
  distancia_km: "",
  consumo_estimado_litro_km: "0.3",
  litros_combustible: "",
};

function LotesView() {
  const [lotes, setLotes] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [unidadesOperativas, setUnidadesOperativas] = useState([]);
  const [especiesMadera, setEspeciesMadera] = useState([]);
  const [factoresEmision, setFactoresEmision] = useState([]);
  const [selectedLote, setSelectedLote] = useState(null);
  const [selectedCarbono, setSelectedCarbono] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [activityForm, setActivityForm] = useState(emptyActivityForm);
  const [documentForm, setDocumentForm] = useState(emptyDocumentForm);
  const [transportForm, setTransportForm] = useState(emptyTransportForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingActivity, setSavingActivity] = useState(false);
  const [savingDocument, setSavingDocument] = useState(false);
  const [savingTransport, setSavingTransport] = useState(false);
  const [generatingCertificate, setGeneratingCertificate] = useState(false);
  const [readingDocumentId, setReadingDocumentId] = useState(null);
  const [extractingDocumentId, setExtractingDocumentId] = useState(null);
  const [validatingExtraction, setValidatingExtraction] = useState(false);
  const [activeExtraction, setActiveExtraction] = useState(null);
  const [documentInsight, setDocumentInsight] = useState(null);
  const [ocrForm, setOcrForm] = useState({});
  const [transportDistanceResult, setTransportDistanceResult] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailModalLote, setDetailModalLote] = useState(null);
  const [documentImportOpen, setDocumentImportOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPageInfo, setHistoryPageInfo] = useState(null);
  const [error, setError] = useState("");
  const [activityError, setActivityError] = useState("");
  const [documentError, setDocumentError] = useState("");
  const [transportError, setTransportError] = useState("");
  const [ocrError, setOcrError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [activityFieldErrors, setActivityFieldErrors] = useState({});
  const [documentFieldErrors, setDocumentFieldErrors] = useState({});
  const [transportFieldErrors, setTransportFieldErrors] = useState({});
  const { activeEmpresa, activeEmpresaId, loadingEmpresas } = useEmpresaActiva();

  const totalEmisiones = useMemo(
    () =>
      lotes.reduce(
        (total, lote) => total + Number(lote.emisiones_kg_co2e || 0),
        0
      ),
    [lotes]
  );

  const totalEvidencias = useMemo(
    () =>
      lotes.reduce(
        (total, lote) =>
          total +
          Number(
            lote.documentos_count ?? lote.evidencias_count ?? lote.documentos?.length ?? 0
          ),
        0
      ),
    [lotes]
  );

  const obraCritica = useMemo(
    () =>
      lotes.reduce((critica, lote) => {
        if (!critica) {
          return lote;
        }

        return Number(lote.emisiones_kg_co2e || 0) >
          Number(critica.emisiones_kg_co2e || 0)
          ? lote
          : critica;
      }, null)?.id_lote || "",
    [lotes]
  );

  const unidadesDisponibles = useMemo(() => {
    if (!form.empresa_id) {
      return unidadesOperativas;
    }

    return unidadesOperativas.filter(
      (unidad) => String(unidad.empresa_id) === String(form.empresa_id)
    );
  }, [form.empresa_id, unidadesOperativas]);

  useEffect(() => {
    if (!activeEmpresaId) {
      setLoading(false);
      return;
    }

    const mounted = { current: true };
    const mountedRef = mounted; // keep name for clarity

    async function loadLotes() {
      try {
        const [
          lotesData,
          especiesData,
          unidadesData,
        ] = await Promise.all([
          getEmpresaLotes(activeEmpresaId),
          getEspeciesMadera(),
          getEmpresaUnidades(activeEmpresaId),
        ]);

        // Normalize responses to arrays in case API returns paginated objects
        const normalizedLotes = Array.isArray(lotesData)
          ? lotesData
          : lotesData?.results || [];
        const normalizedEspecies = Array.isArray(especiesData)
          ? especiesData
          : especiesData?.results || [];
        const normalizedUnidades = Array.isArray(unidadesData)
          ? unidadesData
          : unidadesData?.results || [];

        if (!mountedRef.current) return;

        setLotes(normalizedLotes);
        setUnidadesOperativas(normalizedUnidades);
        setEspeciesMadera(normalizedEspecies);
        setFactoresEmision([]);
        setSelectedLote(normalizedLotes[0] || null);
        setSelectedCarbono(null);
        setEmpresas(activeEmpresa ? [activeEmpresa] : []);
        setForm((currentForm) => ({
          ...currentForm,
          empresa_id: activeEmpresaId,
          empresa_aserradero: activeEmpresa?.nombre || currentForm.empresa_aserradero,
          especie: currentForm.especie || "",
        }));

        getFactoresEmision()
          .then((factoresData) => {
            if (!mountedRef.current) return;
            setFactoresEmision(
              Array.isArray(factoresData) ? factoresData : factoresData?.results || []
            );
          })
          .catch(() => {
            if (mountedRef.current) {
              setFactoresEmision([]);
            }
          });
      } catch (requestError) {
        if (mountedRef.current) {
          setError(
            requestError?.response?.data?.error || "No se pudieron cargar las obras."
          );
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    }

    loadLotes();

    return () => {
      mountedRef.current = false;
    };
  }, [activeEmpresa, activeEmpresaId]);

  useEffect(() => {
    if (
      !transportForm.punto_partida ||
      !transportForm.destino ||
      !transportForm.punto_partida_coords ||
      !transportForm.destino_coords
    ) {
      return;
    }

    let isCancelled = false;

    async function calculateTransportDistance() {
      try {
        const result = await calculateRouteDistance({
          origen: transportForm.punto_partida,
          destino: transportForm.destino,
          origen_coords: transportForm.punto_partida_coords,
          destino_coords: transportForm.destino_coords,
        });

        if (!isCancelled) {
          setTransportForm((currentForm) => ({
            ...currentForm,
            distancia_km: String(result.distancia_km),
          }));
          setTransportDistanceResult(result);
        }
      } catch (requestError) {
        if (!isCancelled) {
          setTransportError(
            requestError.response?.data?.error ||
              "No se pudo calcular la distancia del transporte."
          );
        }
      }
    }

    calculateTransportDistance();

    return () => {
      isCancelled = true;
    };
  }, [
    transportForm.destino,
    transportForm.destino_coords,
    transportForm.punto_partida,
    transportForm.punto_partida_coords,
  ]);

  const updateForm = (event) => {
    const { name, value } = event.target;
    setForm((currentForm) => {
      if (name === "empresa_id") {
        const selectedEmpresa = empresas.find(
          (empresa) => String(empresa.empresa_id) === String(value)
        );

        return {
          ...currentForm,
          empresa_id: value,
          unidad_id: "",
          empresa_aserradero:
            selectedEmpresa?.nombre || currentForm.empresa_aserradero,
        };
      }

      if (name === "unidad_id") {
        const selectedUnidad = unidadesOperativas.find(
          (unidad) => String(unidad.unidad_id) === String(value)
        );

        return {
          ...currentForm,
          unidad_id: value,
          empresa_id: selectedUnidad?.empresa_id || currentForm.empresa_id,
          empresa_aserradero:
            selectedUnidad?.empresa_nombre || currentForm.empresa_aserradero,
        };
      }

      return { ...currentForm, [name]: value };
    });
    setFieldErrors((currentErrors) => ({ ...currentErrors, [name]: null }));
  };

  const updateActivityForm = (event) => {
    const { name, value } = event.target;
    setActivityForm((currentForm) => ({ ...currentForm, [name]: value }));
    setActivityFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  };

  const selectActivityFactor = (event) => {
    const factorId = event.target.value;
    const selectedFactor = factoresEmision.find(
      (factor) => String(factor.id) === String(factorId)
    );

    setActivityForm((currentForm) => ({
      ...currentForm,
      factor_emision_id: factorId,
      actividad: selectedFactor?.actividad || currentForm.actividad,
      unidad: selectedFactor?.unidad || currentForm.unidad,
      factor_emision: selectedFactor?.factor_emision || "",
    }));
    setActivityFieldErrors((currentErrors) => ({
      ...currentErrors,
      actividad: null,
      unidad: null,
      factor_emision: null,
    }));
  };

  const updateDocumentForm = (event) => {
    const { name, files, value } = event.target;
    setDocumentForm((currentForm) => ({
      ...currentForm,
      [name]: files?.[0] || value,
    }));
    setDocumentFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  };

  const updateTransportForm = (event) => {
    const { name, value } = event.target;
    setTransportForm((currentForm) => ({ ...currentForm, [name]: value }));
    setTransportFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  };

  const updateTransportOrigin = ({ address, coords }) => {
    setTransportForm((currentForm) => ({
      ...currentForm,
      punto_partida: address,
      punto_partida_coords: coords,
    }));
    setTransportDistanceResult(null);
    setTransportFieldErrors((currentErrors) => ({
      ...currentErrors,
      latitud: null,
      longitud: null,
    }));
  };

  const updateTransportDestination = ({ address, coords }) => {
    setTransportForm((currentForm) => ({
      ...currentForm,
      destino: address,
      destino_coords: coords,
    }));
    setTransportDistanceResult(null);
    setTransportFieldErrors((currentErrors) => ({
      ...currentErrors,
      ruta: null,
    }));
  };

  const updateOcrForm = (event) => {
    const { name, value } = event.target;
    setOcrForm((currentForm) => ({ ...currentForm, [name]: value }));
  };

  const syncLote = (updatedLote) => {
    setSelectedLote(updatedLote);
    setSelectedCarbono(null);
    setLotes((currentLotes) =>
      currentLotes.map((lote) =>
        lote.id_lote === updatedLote.id_lote ? updatedLote : lote
      )
    );
  };

  const fetchHistory = async (idLote, page = 1, pageSize = 20) => {
    setHistoryLoading(true);

    try {
      const data = await getHistorialLote(idLote, {
        page,
        page_size: pageSize,
      });
      setHistory(data.results || []);
      setHistoryPageInfo({
        next: data.next,
        previous: data.previous,
        count: data.count,
      });
    } catch (requestError) {
      console.error(requestError);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadLoteDetail = async (idLote, { openModal = false } = {}) => {
    setDetailLoading(true);
    setError("");
    setDocumentInsight(null);

    if (openModal) {
      setDetailModalOpen(true);
      setDetailModalLote(null);
    }

    try {
      const [detail, carbono] = await Promise.all([
        getLoteDetail(idLote),
        getLoteCarbono(idLote),
      ]);
      setSelectedLote(detail);
      setSelectedCarbono(carbono);
      if (openModal) {
        setDetailModalLote(detail);
      }
      fetchHistory(idLote);
    } catch (requestError) {
      setError(
        requestError.response?.data?.error || "No se pudo cargar el detalle."
      );
      if (openModal) {
        setDetailModalLote(null);
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetailModal = () => {
    setDetailModalOpen(false);
    setDetailModalLote(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setFieldErrors({});

    try {
      const createdLote = await createLote({
        id_lote: form.id_lote,
        empresa_id: activeEmpresaId || form.empresa_id || undefined,
        unidad_id: form.unidad_id || undefined,
        empresa_aserradero: form.empresa_aserradero,
        fecha: form.fecha,
        especie: form.especie,
        volumen_m3: Number(form.volumen_m3),
        origen: form.origen,
      });

      setLotes((currentLotes) => [createdLote, ...currentLotes]);
      setSelectedLote(createdLote);
      setSelectedCarbono(null);
      setForm({
        ...emptyForm,
        empresa_id: activeEmpresaId,
        empresa_aserradero: activeEmpresa?.nombre || "",
        especie: "",
      });
      setCreateModalOpen(false);
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setFieldErrors(responseData);
      }

      setError("Revisa los datos de la obra antes de guardarla.");
    } finally {
      setSaving(false);
    }
  };

  const handleActivitySubmit = async (event) => {
    event.preventDefault();

    if (!selectedLote) {
      return;
    }

    setSavingActivity(true);
    setActivityError("");
    setActivityFieldErrors({});

    try {
      const activityPayload = {
        actividad: activityForm.actividad,
        tipo_consumo_combustible: activityForm.tipo_consumo_combustible,
        cantidad: Number(activityForm.cantidad),
        unidad: activityForm.unidad,
        fecha: activityForm.fecha || null,
        factor_emision: Number(activityForm.factor_emision),
        origen_transporte: activityForm.origen_transporte,
        destino_transporte: activityForm.destino_transporte,
        origen_coords: activityForm.origen_coords,
        destino_coords: activityForm.destino_coords,
        distancia_km: activityForm.distancia_km || null,
        ruta_geometry: activityForm.ruta_geometry || [],
      };

      if (activityForm.factor_emision_id) {
        activityPayload.factor_emision_id = activityForm.factor_emision_id;
      }

      const updatedLote = await createLoteActividad(selectedLote.id_lote, {
        ...activityPayload,
        cantidad: Number(activityForm.cantidad),
        factor_emision: Number(activityForm.factor_emision),
      });

      syncLote(updatedLote);
      setActivityForm(emptyActivityForm);
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setActivityFieldErrors(responseData);
      }

      setActivityError("Revisa los datos del registro de emisión antes de guardarlo.");
    } finally {
      setSavingActivity(false);
    }
  };

  const handleDownloadCertificate = async () => {
    if (!selectedLote) {
      return;
    }

    setGeneratingCertificate(true);

    try {
      const pdfBlob = await downloadLoteCertificado(selectedLote.id_lote);
      const downloadUrl = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `pasaporte-verde-${selectedLote.id_lote}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudo generar la ficha ambiental."
      );
    } finally {
      setGeneratingCertificate(false);
    }
  };

  const handleDocumentSubmit = async (event) => {
    event.preventDefault();

    if (!selectedLote) {
      return;
    }

    setSavingDocument(true);
    setDocumentError("");
    setDocumentFieldErrors({});

    try {
      const createdDocument = await uploadLoteDocumento(
        selectedLote.id_lote,
        documentForm
      );
      const refreshedLote = await getLoteDetail(selectedLote.id_lote);
      const updatedLote = {
        ...refreshedLote,
        documentos:
          refreshedLote.documentos?.length > 0
            ? refreshedLote.documentos
            : [createdDocument, ...(selectedLote.documentos || [])],
      };

      syncLote(updatedLote);
      setDocumentForm(emptyDocumentForm);
      event.target.reset();
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setDocumentFieldErrors(responseData);
      }

      setDocumentError("Revisa la evidencia antes de cargarla.");
    } finally {
      setSavingDocument(false);
    }
  };

  const handleTransportSubmit = async (event) => {
    event.preventDefault();

    if (!selectedLote) {
      return;
    }

    setSavingTransport(true);
    setTransportError("");
    setTransportFieldErrors({});

    try {
      if (!transportForm.punto_partida_coords || !transportForm.destino_coords) {
        setTransportError("Selecciona punto de partida y destino en el mapa.");
        return;
      }

      const routeResult = await calculateRouteDistance({
        origen: transportForm.punto_partida,
        destino: transportForm.destino,
        origen_coords: transportForm.punto_partida_coords,
        destino_coords: transportForm.destino_coords,
      });

      await createLoteTransporte(selectedLote.id_lote, {
        vehiculo: transportForm.vehiculo,
        patente: transportForm.patente,
        latitud: Number(transportForm.punto_partida_coords.lat),
        longitud: Number(
          transportForm.punto_partida_coords.lon ??
            transportForm.punto_partida_coords.lng
        ),
        fecha_hora: transportForm.fecha_hora,
        ruta: transportForm.destino,
        distancia_km: Number(routeResult.distancia_km),
        consumo_estimado_litro_km: Number(
          transportForm.consumo_estimado_litro_km || 0
        ),
        litros_combustible: transportForm.litros_combustible
          ? Number(transportForm.litros_combustible)
          : null,
      });
      const refreshedLote = await getLoteDetail(selectedLote.id_lote);
      syncLote(refreshedLote);
      setTransportForm(emptyTransportForm);
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setTransportFieldErrors(responseData);
      }

      setTransportError("Revisa los datos de transporte antes de guardarlos.");
    } finally {
      setSavingTransport(false);
    }
  };

  const handleRunOcr = async (documentoId) => {
    setReadingDocumentId(documentoId);
    setOcrError("");
    setDocumentInsight(null);

    try {
      const extraction = await runDocumentoOcr(documentoId);
      setActiveExtraction(extraction);
      setOcrForm(extraction.datos_sugeridos || {});
    } catch (requestError) {
      setOcrError(
        requestError.response?.data?.error ||
          "No se pudo leer automaticamente el documento."
      );
    } finally {
      setReadingDocumentId(null);
    }
  };

  const handleRunStructuredExtraction = async (documentoId) => {
    setExtractingDocumentId(documentoId);
    setOcrError("");

    try {
      const structuredExtraction = await extractDocumentJsonById(documentoId);
      setDocumentInsight(structuredExtraction);
    } catch (requestError) {
      setOcrError(
        requestError.response?.data?.error ||
          "No se pudo estructurar el documento con IA."
      );
    } finally {
      setExtractingDocumentId(null);
    }
  };

  const handleValidateExtraction = async () => {
    if (!activeExtraction) {
      return;
    }

    setValidatingExtraction(true);
    setOcrError("");

    try {
      const response = await validateExtraccionDocumento(activeExtraction.id, {
        datos_validados: ocrForm,
        aplicar_calculo: true,
      });
      syncLote(response.lote);
      setActiveExtraction(null);
      setOcrForm({});
    } catch (requestError) {
      setOcrError(
        requestError.response?.data?.error ||
          "No se pudieron validar los datos extraidos."
      );
    } finally {
      setValidatingExtraction(false);
    }
  };

  const handleRejectExtraction = async () => {
    if (!activeExtraction) {
      return;
    }

    try {
      await rejectExtraccionDocumento(activeExtraction.id);
      setActiveExtraction(null);
      setOcrForm({});
    } catch (requestError) {
      setOcrError(
        requestError.response?.data?.error ||
          "No se pudo rechazar la extraccion."
      );
    }
  };

  const handleValidateHistoryExtraction = async (
    extraccionId,
    datosValidados
  ) => {
    setValidatingExtraction(true);

    try {
      await validateExtraccionDocumento(extraccionId, {
        datos_validados: datosValidados,
        aplicar_calculo: true,
      });

      if (selectedLote) {
        await loadLoteDetail(selectedLote.id_lote);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Error al validar la extraccion");
    } finally {
      setValidatingExtraction(false);
    }
  };

  const handleRejectHistoryExtraction = async (extraccionId) => {
    setValidatingExtraction(true);

    try {
      await rejectExtraccionDocumento(extraccionId);

      if (selectedLote) {
        await loadLoteDetail(selectedLote.id_lote);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Error al rechazar la extraccion");
    } finally {
      setValidatingExtraction(false);
    }
  };

  const balanceData = selectedCarbono || selectedLote;

  return (
    <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
      {loadingEmpresas ? (
        <div className="min-h-[40vh] flex items-center justify-center text-slate-300">
          Cargando constructoras...
        </div>
      ) : !activeEmpresa ? (
        <EmptyState
          title="Selecciona o crea una constructora para comenzar"
          description="Las obras y registros de emisión se gestionan dentro de la constructora activa."
        />
      ) : (
        <>
      <LotesHeader onOpenCreate={() => setCreateModalOpen(true)} />
      <LotesKpis
        lotes={lotes}
        totalEmisiones={totalEmisiones}
        totalEvidencias={totalEvidencias}
        obraCritica={obraCritica}
      />

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <LotesTable
        loading={loading}
        lotes={lotes}
        onOpenDetail={(idLote) => loadLoteDetail(idLote, { openModal: true })}
        onSelectLote={(idLote) => loadLoteDetail(idLote)}
        selectedLote={selectedLote}
      />

      {detailModalOpen && (
        <LoteDetailModal
          detailLoading={detailLoading}
          lote={detailModalLote}
          onClose={closeDetailModal}
        />
      )}

      <LoteDetailView
        activeExtraction={activeExtraction}
        activityError={activityError}
        activityFieldErrors={activityFieldErrors}
        activityForm={activityForm}
        factoresEmision={factoresEmision}
        balanceData={balanceData}
        detailLoading={detailLoading}
        documentError={documentError}
        documentFieldErrors={documentFieldErrors}
        documentForm={documentForm}
        documentInsight={documentInsight}
        extractingDocumentId={extractingDocumentId}
        generatingCertificate={generatingCertificate}
        history={history}
        historyLoading={historyLoading}
        historyPageInfo={historyPageInfo}
        ocrError={ocrError}
        ocrForm={ocrForm}
        onImportDocumento={() => setDocumentImportOpen(true)}
        onActivitySubmit={handleActivitySubmit}
        onSelectActivityFactor={selectActivityFactor}
        onDocumentSubmit={handleDocumentSubmit}
        onDownloadCertificate={handleDownloadCertificate}
        onRejectExtraction={handleRejectExtraction}
        onRejectHistoryExtraction={handleRejectHistoryExtraction}
        onRunOcr={handleRunOcr}
        onRunStructuredExtraction={handleRunStructuredExtraction}
        onTransportSubmit={handleTransportSubmit}
        onUpdateActivityForm={updateActivityForm}
        onUpdateDocumentForm={updateDocumentForm}
        onUpdateOcrForm={updateOcrForm}
        onUpdateTransportForm={updateTransportForm}
        onUpdateTransportDestination={updateTransportDestination}
        onUpdateTransportOrigin={updateTransportOrigin}
        onValidateExtraction={handleValidateExtraction}
        onValidateHistoryExtraction={handleValidateHistoryExtraction}
        readingDocumentId={readingDocumentId}
        savingActivity={savingActivity}
        savingDocument={savingDocument}
        savingTransport={savingTransport}
        selectedLote={selectedLote}
        transportError={transportError}
        transportFieldErrors={transportFieldErrors}
        transportRouteGeometry={transportDistanceResult?.route_geometry || []}
        transportForm={transportForm}
        validatingExtraction={validatingExtraction}
      />

      {createModalOpen && (
        <CrearLoteModal
          activeEmpresa={activeEmpresa}
          empresas={empresas}
          especiesMadera={especiesMadera}
          fieldErrors={fieldErrors}
          form={form}
          unidadesOperativas={unidadesDisponibles}
          onClose={() => setCreateModalOpen(false)}
          onSubmit={handleSubmit}
          onUpdateForm={updateForm}
          saving={saving}
        />
      )}

      <ImportarDocumentoObraModal
        activeEmpresaId={activeEmpresaId}
        initialLoteId={selectedLote?.id_lote || ""}
        onClose={() => setDocumentImportOpen(false)}
        open={documentImportOpen}
      />
        </>
      )}
    </div>
  );
}

export default LotesView;
