import { useEffect, useMemo, useRef, useState } from "react";

import CrearObraModal from "@/features/obras/components/CrearObraModal";
import ObraDetailView from "@/features/obras/components/ObraDetailView";
import ObraDetailModal from "@/features/obras/components/ObraDetailModal";
import ObrasHeader from "@/features/obras/components/ObrasHeader";
import ObrasKpis from "@/features/obras/components/ObrasKpis";
import ObrasTable from "@/features/obras/components/ObrasTable";
import EmptyState from "@/shared/components/EmptyState";
import ImportarEvidenciaObraModal from "@/shared/components/ImportarEvidenciaObraModal";
import {
  calculateRouteDistance,
  createObra,
  createRegistroEmision,
  createTransporteObra,
  downloadObraFichaAmbiental,
  extractDocumentJsonById,
  getOrganizaciones,
  getMaterialesConstruccion,
  getFactoresEmision,
  getHistorialObra,
  getOrganizacionObras,
  getOrganizacionEtapas,
  getObraBalanceAmbiental,
  getObraDetail,
  rejectExtraccionEvidencia,
  runEvidenciaOcr,
  uploadObraEvidencia,
  validateExtraccionEvidencia,
} from "@/shared/services/api";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const emptyForm = {
  codigo_obra: "",
  organizacion_id: "",
  etapa_id: "",
  organizacion_nombre: "",
  fecha: "",
  tipo_proyecto: "",
  superficie_m2: "",
  origen: "",
};

const emptyRegistroForm = {
  factor_emision_id: "",
  fuente_emision: "",
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
  tipo_evidencia: "guia_despacho",
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

function ObrasView() {
  const [obras, setObras] = useState([]);
  const [organizaciones, setOrganizaciones] = useState([]);
  const [etapasOperativas, setEtapasOperativas] = useState([]);
  const [materialesConstruccion, setMaterialesConstruccion] = useState([]);
  const [factoresEmision, setFactoresEmision] = useState([]);
  const [selectedObra, setSelectedObra] = useState(null);
  const [selectedBalanceAmbiental, setSelectedBalanceAmbiental] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [registroForm, setregistroForm] = useState(emptyRegistroForm);
  const [documentForm, setDocumentForm] = useState(emptyDocumentForm);
  const [transportForm, setTransportForm] = useState(emptyTransportForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingRegistro, setsavingRegistro] = useState(false);
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
  const [detailModalObra, setDetailModalObra] = useState(null);
  const [documentImportOpen, setDocumentImportOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPageInfo, setHistoryPageInfo] = useState(null);
  const [error, setError] = useState("");
  const [registroError, setregistroError] = useState("");
  const [documentError, setDocumentError] = useState("");
  const [transportError, setTransportError] = useState("");
  const [ocrError, setOcrError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [registroFieldErrors, setregistroFieldErrors] = useState({});
  const [documentFieldErrors, setDocumentFieldErrors] = useState({});
  const [transportFieldErrors, setTransportFieldErrors] = useState({});
  const { activeOrganizacion, activeOrganizacionId, loadingOrganizaciones } = useOrganizacionActiva();

  const totalEmisiones = useMemo(
    () =>
      obras.reduce(
        (total, obra) => total + Number(obra.emisiones_kg_co2e || 0),
        0
      ),
    [obras]
  );

  const etapasDisponibles = useMemo(() => {
    if (!form.organizacion_id) {
      return etapasOperativas;
    }

    return etapasOperativas.filter(
      (unidad) => String(unidad.organizacion_id) === String(form.organizacion_id)
    );
  }, [form.organizacion_id, etapasOperativas]);

  useEffect(() => {
    if (!activeOrganizacionId) {
      setSelectedObra(null);
      setSelectedBalanceAmbiental(null);
      setHistory([]);
      setHistoryPageInfo(null);
      setLoading(false);
      return;
    }

    const mounted = { current: true };
    const mountedRef = mounted; // keep name for clarity

    async function loadObras() {
      try {
        const [
          obrasData,
          materialesData,
          etapasData,
        ] = await Promise.all([
          getOrganizacionObras(activeOrganizacionId),
          getMaterialesConstruccion(),
          getOrganizacionEtapas(activeOrganizacionId),
        ]);

        // Normalize responses to arrays in case API returns paginated objects
        const normalizedObras = Array.isArray(obrasData)
          ? obrasData
          : obrasData?.results || [];
        const normalizedMateriales = Array.isArray(materialesData)
          ? materialesData
          : materialesData?.results || [];
        const normalizedEtapas = Array.isArray(etapasData)
          ? etapasData
          : etapasData?.results || [];

        if (!mountedRef.current) return;

        setObras(normalizedObras);
        setEtapasOperativas(normalizedEtapas);
        setMaterialesConstruccion(normalizedMateriales);
        setFactoresEmision([]);
        setSelectedObra((currentSelected) => {
          if (currentSelected && normalizedObras.some((obra) => obra.codigo_obra === currentSelected.codigo_obra)) {
            return currentSelected;
          }

          return null;
        });
        setSelectedBalanceAmbiental(null);
        setHistory([]);
        setHistoryPageInfo(null);
        setOrganizaciones(activeOrganizacion ? [activeOrganizacion] : []);
        setForm((currentForm) => ({
          ...currentForm,
          organizacion_id: activeOrganizacionId,
          organizacion_nombre: activeOrganizacion?.nombre || currentForm.organizacion_nombre,
          tipo_proyecto: currentForm.tipo_proyecto || "",
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

    loadObras();

    return () => {
      mountedRef.current = false;
    };
  }, [activeOrganizacion, activeOrganizacionId]);

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
      if (name === "organizacion_id") {
        const selectedOrganizacion = organizaciones.find(
          (organizacion) => String(organizacion.organizacion_id) === String(value)
        );

        return {
          ...currentForm,
          organizacion_id: value,
          etapa_id: "",
          organizacion_nombre:
            selectedOrganizacion?.nombre || currentForm.organizacion_nombre,
        };
      }

      if (name === "etapa_id") {
        const selectedEtapa = etapasOperativas.find(
          (unidad) => String(unidad.etapa_id) === String(value)
        );

        return {
          ...currentForm,
          etapa_id: value,
          organizacion_id: selectedEtapa?.organizacion_id || currentForm.organizacion_id,
          organizacion_nombre:
            selectedEtapa?.organizacion_nombre || currentForm.organizacion_nombre,
        };
      }

      return { ...currentForm, [name]: value };
    });
    setFieldErrors((currentErrors) => ({ ...currentErrors, [name]: null }));
  };

  const updateregistroForm = (event) => {
    const { name, value } = event.target;
    setregistroForm((currentForm) => ({ ...currentForm, [name]: value }));
    setregistroFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  };

  const selectRegistroFactor = (event) => {
    const factorId = event.target.value;
    const selectedFactor = factoresEmision.find(
      (factor) => String(factor.id) === String(factorId)
    );

    setregistroForm((currentForm) => ({
      ...currentForm,
      factor_emision_id: factorId,
      fuente_emision: selectedFactor?.fuente_emision || currentForm.fuente_emision,
      unidad: selectedFactor?.unidad || currentForm.unidad,
      factor_emision: selectedFactor?.factor_emision || "",
    }));
    setregistroFieldErrors((currentErrors) => ({
      ...currentErrors,
      fuente_emision: null,
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

  const updateOcrForm = (event) => {
    const { name, value } = event.target;
    setOcrForm((currentForm) => ({ ...currentForm, [name]: value }));
  };

  const updateTransportForm = (event) => {
    const { name, value } = event.target;
    setTransportForm((currentForm) => ({ ...currentForm, [name]: value }));
    setTransportFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  };

  const updateTransportOrigin = (payload) => {
    setTransportForm((currentForm) => ({
      ...currentForm,
      punto_partida: payload.label || "",
      punto_partida_coords: payload.coords || null,
      distancia_km: "",
    }));
    setTransportDistanceResult(null);
  };

  const updateTransportDestination = (payload) => {
    setTransportForm((currentForm) => ({
      ...currentForm,
      destino: payload.label || "",
      destino_coords: payload.coords || null,
      distancia_km: "",
    }));
    setTransportDistanceResult(null);
  };

  const syncObra = async (updatedObra) => {
    const detail = await getObraDetail(updatedObra.codigo_obra);
    setSelectedObra(detail);
    setSelectedBalanceAmbiental(detail.analisis_ambiental || detail);
    setObras((currentObras) =>
      currentObras.map((obra) =>
        obra.codigo_obra === detail.codigo_obra ? { ...obra, ...detail } : obra
      )
    );
  };

  const loadObraDetail = async (codigoObra, options = {}) => {
    const { openModal = false } = options;
    setDetailLoading(true);
    setError("");
    setHistory([]);
    setHistoryPageInfo(null);

    try {
      const [detail, balance, historyData] = await Promise.all([
        getObraDetail(codigoObra),
        getObraBalanceAmbiental(codigoObra).catch(() => null),
        getHistorialObra(codigoObra, { page_size: 5 }).catch(() => null),
      ]);

      setSelectedObra(detail);
      setSelectedBalanceAmbiental(balance || detail.analisis_ambiental || detail);
      setObras((currentObras) =>
        currentObras.map((obra) =>
          obra.codigo_obra === codigoObra ? { ...obra, ...detail } : obra
        )
      );

      if (openModal) {
        setDetailModalObra(detail);
      }

      if (historyData) {
        setHistory(Array.isArray(historyData.results) ? historyData.results : []);
        setHistoryPageInfo(historyData);
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.error || "No se pudo cargar el detalle de la obra."
      );
      if (openModal) {
        setDetailModalOpen(false);
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetailModal = () => {
    setDetailModalOpen(false);
    setDetailModalObra(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setFieldErrors({});

    try {
      const payload = {
        ...form,
        superficie_m2: form.superficie_m2 ? Number(form.superficie_m2) : null,
      };
      const createdObra = await createObra(payload);
      setObras((currentObras) => [createdObra, ...currentObras]);
      setSelectedObra(createdObra);
      setCreateModalOpen(false);
      setForm({
        ...emptyForm,
        organizacion_id: activeOrganizacionId,
        organizacion_nombre: activeOrganizacion?.nombre || "",
      });
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

  const handleRegistroSubmit = async (event) => {
    event.preventDefault();

    if (!selectedObra) {
      return;
    }

    setsavingRegistro(true);
    setregistroError("");
    setregistroFieldErrors({});

    try {
      const registroPayload = {
        fuente_emision: registroForm.fuente_emision,
        tipo_consumo_combustible: registroForm.tipo_consumo_combustible,
        cantidad: Number(registroForm.cantidad),
        unidad: registroForm.unidad,
        fecha: registroForm.fecha || null,
        factor_emision: Number(registroForm.factor_emision),
        origen_transporte: registroForm.origen_transporte,
        destino_transporte: registroForm.destino_transporte,
        origen_coords: registroForm.origen_coords,
        destino_coords: registroForm.destino_coords,
        distancia_km: registroForm.distancia_km || null,
        ruta_geometry: registroForm.ruta_geometry || [],
      };

      if (registroForm.factor_emision_id) {
        registroPayload.factor_emision_id = registroForm.factor_emision_id;
      }

      const updatedObra = await createRegistroEmision(selectedObra.codigo_obra, {
        ...registroPayload,
        cantidad: Number(registroForm.cantidad),
        factor_emision: Number(registroForm.factor_emision),
      });

      syncObra(updatedObra);
      setregistroForm(emptyRegistroForm);
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setregistroFieldErrors(responseData);
      }

      setregistroError("Revisa los datos del registro de emision antes de guardarlo.");
    } finally {
      setsavingRegistro(false);
    }
  };

  const handleDownloadCertificate = async () => {
    if (!selectedObra) {
      return;
    }

    setGeneratingCertificate(true);

    try {
      const pdfBlob = await downloadObraFichaAmbiental(selectedObra.codigo_obra);
      const downloadUrl = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `ficha_ambiental-verde-${selectedObra.codigo_obra}.pdf`;
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

    if (!selectedObra) {
      return;
    }

    setSavingDocument(true);
    setDocumentError("");
    setDocumentFieldErrors({});

    try {
      const createdDocument = await uploadObraEvidencia(
        selectedObra.codigo_obra,
        documentForm
      );
      const refreshedObra = await getObraDetail(selectedObra.codigo_obra);
      const updatedObra = {
        ...refreshedObra,
        evidencias:
          refreshedObra.evidencias?.length > 0
            ? refreshedObra.evidencias
            : [createdDocument, ...(selectedObra.evidencias || [])],
      };

      syncObra(updatedObra);
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

    if (!selectedObra) {
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

      await createTransporteObra(selectedObra.codigo_obra, {
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
      const refreshedObra = await getObraDetail(selectedObra.codigo_obra);
      syncObra(refreshedObra);
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

  const handleRunOcr = async (evidenciaId) => {
    setReadingDocumentId(evidenciaId);
    setOcrError("");
    setDocumentInsight(null);

    try {
      const extraction = await runEvidenciaOcr(evidenciaId);
      setActiveExtraction(extraction);
      setOcrForm(extraction.datos_sugeridos || {});
    } catch (requestError) {
      setOcrError(
        requestError.response?.data?.error ||
          "No se pudo leer automaticamente el evidencia."
      );
    } finally {
      setReadingDocumentId(null);
    }
  };

  const handleRunStructuredExtraction = async (evidenciaId) => {
    setExtractingDocumentId(evidenciaId);
    setOcrError("");

    try {
      const structuredExtraction = await extractDocumentJsonById(evidenciaId);
      setDocumentInsight(structuredExtraction);
    } catch (requestError) {
      setOcrError(
        requestError.response?.data?.error ||
          "No se pudo estructurar el evidencia con IA."
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
      const response = await validateExtraccionEvidencia(activeExtraction.id, {
        datos_validados: ocrForm,
        aplicar_calculo: true,
      });
      syncObra(response.obra);
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
      await rejectExtraccionEvidencia(activeExtraction.id);
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
      await validateExtraccionEvidencia(extraccionId, {
        datos_validados: datosValidados,
        aplicar_calculo: true,
      });

      if (selectedObra) {
        await loadObraDetail(selectedObra.codigo_obra);
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
      await rejectExtraccionEvidencia(extraccionId);

      if (selectedObra) {
        await loadObraDetail(selectedObra.codigo_obra);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Error al rechazar la extraccion");
    } finally {
      setValidatingExtraction(false);
    }
  };

  const balanceData = selectedBalanceAmbiental || selectedObra;

  return (
    <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
      {loadingOrganizaciones ? (
        <div className="min-h-[40vh] flex items-center justify-center text-slate-300">
          Cargando organizaciones...
        </div>
      ) : !activeOrganizacion ? (
        <EmptyState
          title="Selecciona o crea una organizacion para comenzar"
          description="Las obras y registros de emision se gestionan dentro de la organizacion activa."
        />
      ) : (
        <>
      <ObrasHeader onOpenCreate={() => setCreateModalOpen(true)} />
      <ObrasKpis
        obras={obras}
        selectedObra={selectedObra}
        totalEmisiones={totalEmisiones}
      />

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <ObrasTable
        loading={loading}
        obras={obras}
        onOpenDetail={(codigoObra) => loadObraDetail(codigoObra, { openModal: true })}
        onSelectObra={(codigoObra) => loadObraDetail(codigoObra)}
        selectedObra={selectedObra}
      />

      {detailModalOpen && (
        <ObraDetailModal
          detailLoading={detailLoading}
          obra={detailModalObra}
          onClose={closeDetailModal}
        />
      )}

      <ObraDetailView
        activeExtraction={activeExtraction}
        registroError={registroError}
        registroFieldErrors={registroFieldErrors}
        registroForm={registroForm}
        factoresEmision={factoresEmision}
        balanceData={balanceData}
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
        onRegistroSubmit={handleRegistroSubmit}
        onselectRegistroFactor={selectRegistroFactor}
        onDocumentSubmit={handleDocumentSubmit}
        onDownloadCertificate={handleDownloadCertificate}
        onRejectExtraction={handleRejectExtraction}
        onRejectHistoryExtraction={handleRejectHistoryExtraction}
        onRunOcr={handleRunOcr}
        onRunStructuredExtraction={handleRunStructuredExtraction}
        onTransportSubmit={handleTransportSubmit}
        onUpdateregistroForm={updateregistroForm}
        onUpdateDocumentForm={updateDocumentForm}
        onUpdateOcrForm={updateOcrForm}
        onUpdateTransportForm={updateTransportForm}
        onUpdateTransportDestination={updateTransportDestination}
        onUpdateTransportOrigin={updateTransportOrigin}
        onValidateExtraction={handleValidateExtraction}
        onValidateHistoryExtraction={handleValidateHistoryExtraction}
        readingDocumentId={readingDocumentId}
        savingRegistro={savingRegistro}
        savingDocument={savingDocument}
        savingTransport={savingTransport}
        selectedObra={selectedObra}
        transportError={transportError}
        transportFieldErrors={transportFieldErrors}
        transportRouteGeometry={transportDistanceResult?.route_geometry || []}
        transportForm={transportForm}
        validatingExtraction={validatingExtraction}
      />

      {createModalOpen && (
        <CrearObraModal
          activeOrganizacion={activeOrganizacion}
          organizaciones={organizaciones}
          materialesConstruccion={materialesConstruccion}
          fieldErrors={fieldErrors}
          form={form}
          etapasOperativas={etapasDisponibles}
          onClose={() => setCreateModalOpen(false)}
          onSubmit={handleSubmit}
          onUpdateForm={updateForm}
          saving={saving}
        />
      )}

      <ImportarEvidenciaObraModal
        activeOrganizacionId={activeOrganizacionId}
        initialObraId={selectedObra?.codigo_obra || ""}
        onClose={() => setDocumentImportOpen(false)}
        open={documentImportOpen}
      />
        </>
      )}
    </div>
  );
}

export default ObrasView;
