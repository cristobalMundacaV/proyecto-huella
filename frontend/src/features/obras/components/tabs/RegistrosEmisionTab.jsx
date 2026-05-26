import { useEffect, useMemo, useState } from "react";
import { Calculator, Loader2, Plus, X } from "lucide-react";

import FactorCategoryBadge from "@/features/factores/components/FactorCategoryBadge";
import {
  isDieselEmission,
  isTransportEmission,
  normalizeEmissionText,
} from "@/shared/utils/emissionSemantics";
import { formatNumber } from "@/shared/utils/formatters";
import {
  categoryMatchesConstructionFilter,
  constructionCategories,
  constructionFactorSuggestions,
  getCategoryFieldCopy,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";
import { Field } from "../common";
import RouteMapPicker from "../RouteMapPicker";

const fuelUseOptions = [
  { value: "cosecha", label: "PreparaciÃ³n / movimiento" },
  { value: "despacho", label: "Despacho" },
  { value: "transporte", label: "Transporte" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "vehiculos", label: "Vehiculos" },
];

function isFuelEmission({ fuente_emision, fuente_emisionKey, categoria, unidad }) {
  const normalizedCategory = normalizeEmissionText(categoria);
  const normalizedText = normalizeEmissionText(
    [fuente_emision, fuente_emisionKey, unidad].filter(Boolean).join(" ")
  );

  return (
    normalizedCategory === "combustible" ||
    isDieselEmission({
      fuente_emision,
      fuente_emision_key: fuente_emisionKey,
      categoria,
      unidad,
    }) ||
    ["combustible", "gas natural", "glp", "gas licuado", "biodiesel"].some(
      (token) => normalizedText.includes(token)
    )
  );
}

function RegistrosEmisionTab({
  registroError,
  registroFieldErrors,
  registroForm,
  factoresEmision,
  onRegistroSubmit,
  onselectRegistroFactor,
  onUpdateregistroForm,
  savingRegistro,
  selectedObra,
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [formCategory, setFormCategory] = useState("Materiales");
  const [factorSearch, setFactorSearch] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [observations, setObservations] = useState("");
  const [routeDestination, setRouteDestination] = useState({
    address: "",
    coords: null,
  });
  const [routeOrigin, setRouteOrigin] = useState({
    address: "",
    coords: null,
  });
  const [routeResult, setRouteResult] = useState(null);

  const visibleFactores = useMemo(() => {
    const query = normalizeEmissionText(factorSearch);
    return factoresEmision.filter((factor) => {
      const matchesCategory = categoryMatchesConstructionFilter(factor, formCategory);
      const searchable = [
        factor.fuente_emision,
        factor.fuente_emision_key,
        factor.unidad,
        factor.factor_emision,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");

      return matchesCategory && (!query || searchable.includes(query));
    });
  }, [factorSearch, factoresEmision, formCategory]);

  const factorCategoriesBySource = useMemo(() => {
    const categoriesBySource = new Map();

    factoresEmision.forEach((factor) => {
      const source = normalizeEmissionText(factor.fuente_emision);
      const sourceKey = normalizeEmissionText(factor.fuente_emision_key);
      const unit = normalizeEmissionText(factor.unidad);
      const category = factor.categoria || "Otros";

      if (source && unit) {
        categoriesBySource.set(`${source}|${unit}`, category);
      }

      if (sourceKey && unit) {
        categoriesBySource.set(`${sourceKey}|${unit}`, category);
      }
    });

    return categoriesBySource;
  }, [factoresEmision]);

  const selectedFactor = useMemo(
    () =>
      factoresEmision.find(
        (factor) => String(factor.id) === String(registroForm.factor_emision_id)
      ) || null,
    [registroForm.factor_emision_id, factoresEmision]
  );

  const selectedFactorCategory =
    selectedFactor?.categoria || formCategory || "Otros";
  const visibleCategory = getConstructionCategoryLabel(
    selectedFactorCategory,
    registroForm.fuente_emision || selectedFactor?.fuente_emision
  );
  const fieldCopy = getCategoryFieldCopy(visibleCategory);
  const estimatedEmissions =
    Number(registroForm.cantidad || 0) * Number(registroForm.factor_emision || 0);
  const shouldShowFuelUseSelect = isFuelEmission({
    fuente_emision: registroForm.fuente_emision || selectedFactor?.fuente_emision,
    fuente_emisionKey: selectedFactor?.fuente_emision_key,
    categoria: selectedFactorCategory,
    unidad: registroForm.unidad || selectedFactor?.unidad,
  });
  const shouldShowRouteMap =
    visibleCategory === "Transporte" ||
    isTransportEmission({
      fuente_emision: registroForm.fuente_emision || selectedFactor?.fuente_emision,
      fuente_emision_key: selectedFactor?.fuente_emision_key,
      categoria: selectedFactorCategory,
      unidad: registroForm.unidad || selectedFactor?.unidad,
    }) || normalizeEmissionText(registroForm.unidad) === "km";

  useEffect(() => {
    if (shouldShowFuelUseSelect || !registroForm.tipo_consumo_combustible) {
      return;
    }

    onUpdateregistroForm({
      target: {
        name: "tipo_consumo_combustible",
        value: "",
      },
    });
  }, [
    registroForm.tipo_consumo_combustible,
    onUpdateregistroForm,
    shouldShowFuelUseSelect,
  ]);

  useEffect(() => {
    if (!isModalOpen || !shouldShowRouteMap) {
      return;
    }

    setRouteOrigin((currentOrigin) => {
      if (currentOrigin.address) {
        return currentOrigin;
      }

      return {
        address: selectedObra?.origen || selectedObra?.etapa_nombre || "",
        coords: null,
      };
    });

    setRouteDestination((currentDestination) => {
      if (currentDestination.address) {
        return currentDestination;
      }

      return {
        address: selectedObra?.destino || "",
        coords: null,
      };
    });
  }, [isModalOpen, selectedObra, shouldShowRouteMap]);

  useEffect(() => {
    if (!shouldShowRouteMap) {
      return;
    }

    onUpdateregistroForm({
      target: {
        name: "origen_transporte",
        value: routeOrigin.address,
      },
    });
    onUpdateregistroForm({
      target: {
        name: "origen_coords",
        value: routeOrigin.coords,
      },
    });
  }, [routeOrigin.address, routeOrigin.coords, shouldShowRouteMap]);

  useEffect(() => {
    if (!shouldShowRouteMap) {
      return;
    }

    onUpdateregistroForm({
      target: {
        name: "destino_transporte",
        value: routeDestination.address,
      },
    });
    onUpdateregistroForm({
      target: {
        name: "destino_coords",
        value: routeDestination.coords,
      },
    });
  }, [routeDestination.address, routeDestination.coords, shouldShowRouteMap]);

  const closeModal = () => {
    setIsModalOpen(false);
    setRouteOrigin({ address: "", coords: null });
    setRouteDestination({ address: "", coords: null });
    setRouteResult(null);
    setEvidenceReference("");
    setObservations("");
  };

  const handleRouteDistanceCalculated = (km, result) => {
    setRouteResult(result || null);

    if (km == null) {
      return;
    }

    onUpdateregistroForm({
      target: {
        name: "cantidad",
        value: String(km),
      },
    });
    onUpdateregistroForm({
      target: {
        name: "distancia_km",
        value: String(km),
      },
    });
    onUpdateregistroForm({
      target: {
        name: "ruta_geometry",
        value: result?.route_geometry || [],
      },
    });
  };

  const handleRouteOriginChange = ({ address, coords }) => {
    setRouteOrigin({ address, coords });
    setRouteResult(null);
    onUpdateregistroForm({
      target: {
        name: "origen_transporte",
        value: address,
      },
    });
    onUpdateregistroForm({
      target: {
        name: "origen_coords",
        value: coords,
      },
    });
  };

  const handleRouteDestinationChange = ({ address, coords }) => {
    setRouteDestination({ address, coords });
    setRouteResult(null);
    onUpdateregistroForm({
      target: {
        name: "destino_transporte",
        value: address,
      },
    });
    onUpdateregistroForm({
      target: {
        name: "destino_coords",
        value: coords,
      },
    });
  };

  const resolveRegistroCategory = (fuente_emision) => {
    if (fuente_emision.categoria) {
      return fuente_emision.categoria;
    }

    const source = normalizeEmissionText(fuente_emision.fuente_emision);
    const sourceKey = normalizeEmissionText(fuente_emision.fuente_emision_key);
    const unit = normalizeEmissionText(fuente_emision.unidad);
    const sourceCategory = factorCategoriesBySource.get(`${source}|${unit}`);
    const sourceKeyCategory = factorCategoriesBySource.get(`${sourceKey}|${unit}`);

    return sourceCategory || sourceKeyCategory || "Otros";
  };

  const filteredRegistros = useMemo(() => {
    if (!selectedCategory) {
      return selectedObra?.registros_emision || [];
    }

    return (selectedObra?.registros_emision || []).filter((fuente_emision) => {
      const category = getConstructionCategoryLabel(
        resolveRegistroCategory(fuente_emision),
        fuente_emision.fuente_emision
      );
      return category === selectedCategory;
    });
  }, [factorCategoriesBySource, selectedCategory, selectedObra?.registros_emision]);

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Registros de emision de la obra</h2>
          <p className="mt-1 text-sm text-slate-400">{selectedObra?.codigo_obra}</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200">
            {formatNumber(Number(selectedObra?.emisiones_kg_co2e || 0))} kg CO2e
          </div>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20"
          >
            <Plus size={18} />
            Nuevo registro de emision
          </button>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setSelectedCategory("")}
          className={`rounded-full border px-4 py-2 text-xs font-bold transition ${
            selectedCategory === ""
              ? "border-cyan-300 bg-cyan-300/20 text-cyan-100"
              : "border-slate-700 bg-slate-950 text-slate-300 hover:border-cyan-400/40"
          }`}
        >
          Todas
        </button>
        {constructionCategories.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setSelectedCategory(category)}
            className={`rounded-full border px-4 py-2 text-xs font-bold transition ${
              selectedCategory === category
                ? "border-cyan-300 bg-cyan-300/20 text-cyan-100"
                : "border-slate-700 bg-slate-950 text-slate-300 hover:border-cyan-400/40"
            }`}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[980px] w-full table-fixed text-sm">
          <thead className="border-b border-slate-800 text-slate-400">
            <tr>
              <th className="w-[40%] py-3 pr-6 text-left">Fuente de emision</th>
              <th className="w-[14%] px-4 py-3 text-left">CategorÃ­a</th>
              <th className="w-[14%] px-4 py-3 text-left">Tipo de consumo</th>
              <th className="w-[14%] py-3 px-4 text-right">Cantidad</th>
              <th className="w-[14%] py-3 px-4 text-left">Etapa</th>
              <th className="w-[14%] py-3 px-4 text-right">Factor de emision</th>
              <th className="w-[18%] py-3 pl-4 pr-2 text-right">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {filteredRegistros.length === 0 && (
              <tr>
                <td colSpan="7" className="py-8 text-center text-slate-400">
                  <p>AÃºn no hay registros de emision en esta obra.</p>
                  <p className="mt-1 text-sm">
                    Agrega emisiones por materiales, transporte, maquinaria, Energia, agua o residuos para comenzar a medir la huella del proyecto.
                  </p>
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(true)}
                    className="mt-4 inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20"
                  >
                    <Plus size={18} />
                    Nuevo registro de emision
                  </button>
                </td>
              </tr>
            )}

            {filteredRegistros.map((fuente_emision) => (
              <tr key={fuente_emision.id} className="border-b border-slate-800/60">
                <td className="py-3 pr-6 font-semibold text-slate-100 whitespace-nowrap overflow-hidden text-ellipsis">
                  {fuente_emision.fuente_emision}
                </td>
                <td className="px-4 py-4 text-left whitespace-nowrap">
                  <FactorCategoryBadge
                    category={getConstructionCategoryLabel(
                      resolveRegistroCategory(fuente_emision),
                      fuente_emision.fuente_emision
                    )}
                  />
                </td>
                <td className="px-4 py-3 text-slate-300 whitespace-nowrap">
                  {fuente_emision.tipo_consumo_combustible
                    ? fuelUseOptions.find(
                        (option) =>
                          option.value === fuente_emision.tipo_consumo_combustible
                      )?.label || fuente_emision.tipo_consumo_combustible
                    : "-"}
                </td>
                <td className="py-3 px-4 text-right whitespace-nowrap">
                  {formatNumber(Number(fuente_emision.cantidad))}
                </td>
                <td className="py-3 px-4 whitespace-nowrap">{fuente_emision.unidad}</td>
                <td className="py-3 px-4 text-right whitespace-nowrap">
                  {formatNumber(Number(fuente_emision.factor_emision), 6)}
                </td>
                <td className="py-3 pl-4 pr-2 text-right font-semibold text-cyan-200 whitespace-nowrap">
                  {formatNumber(Number(fuente_emision.emisiones_kg_co2e))} kg CO2e
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
          <form
            onSubmit={onRegistroSubmit}
            className={`my-8 w-full rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6 ${
              shouldShowRouteMap ? "max-w-5xl" : "max-w-2xl"
            }`}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-200">
                  <Calculator size={18} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">Agregar registro de emision</h2>
                  <p className="text-sm text-slate-400">{selectedObra?.codigo_obra}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeModal}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:bg-slate-800"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mb-5 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3">
              <p className="text-sm font-bold text-cyan-100">{visibleCategory}</p>
              <p className="mt-1 text-sm leading-6 text-cyan-200">{fieldCopy.note}</p>
              {estimatedEmissions > 0 && (
                <p className="mt-2 text-sm font-bold text-cyan-100">
                  emision estimada: {formatNumber(estimatedEmissions, 3)} kg CO2e
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Obra">
                <input
                  value={selectedObra?.codigo_obra || ""}
                  readOnly
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-300 outline-none"
                />
              </Field>
              <Field label="Etapa / frente">
                <input
                  value={selectedObra?.etapa_nombre || "Sin etapa asignada"}
                  readOnly
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-300 outline-none"
                />
              </Field>
              <Field label="CategorÃ­a de emision">
                <select
                  value={formCategory}
                  onChange={(event) => setFormCategory(event.target.value)}
                  disabled={!selectedObra}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {constructionCategories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fecha">
                <input
                  type="date"
                  name="fecha"
                  value={registroForm.fecha || ""}
                  onChange={onUpdateregistroForm}
                  disabled={!selectedObra}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              <Field label="Buscar fuente">
                <input
                  value={factorSearch}
                  onChange={(event) => setFactorSearch(event.target.value)}
                  disabled={!selectedObra}
                  placeholder={fieldCopy.sourcePlaceholder}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                  list="construction-factor-suggestions"
                />
                <datalist id="construction-factor-suggestions">
                  {constructionFactorSuggestions.map((suggestion) => (
                    <option key={suggestion} value={suggestion} />
                  ))}
                </datalist>
              </Field>
              <div className="sm:col-span-2">
                <Field
                  label="CatÃ¡logo de factores sugeridos"
                  error={registroFieldErrors.factor_emision?.[0]}
                >
                  <select
                    name="factor_emision_id"
                    value={registroForm.factor_emision_id}
                    onChange={onselectRegistroFactor}
                    disabled={!selectedObra || visibleFactores.length === 0}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">
                      {factoresEmision.length
                        ? "Selecciona una fuente"
                        : "No hay factores cargados"}
                    </option>
                    {visibleFactores.map((factor) => (
                      <option key={factor.id} value={factor.id}>
                        {factor.fuente_emision} Â· {factor.unidad} Â· {formatNumber(Number(factor.factor_emision), 6)} kgCO2e/{factor.unidad}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label={fieldCopy.sourceLabel} error={registroFieldErrors.fuente_emision?.[0]}>
                <input
                  name="fuente_emision"
                  value={registroForm.fuente_emision}
                  onChange={onUpdateregistroForm}
                  required
                  disabled={!selectedObra}
                  placeholder={fieldCopy.sourcePlaceholder}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              {shouldShowFuelUseSelect && (
                <Field
                  label="Tipo de consumo"
                  error={registroFieldErrors.tipo_consumo_combustible?.[0]}
                >
                  <select
                    name="tipo_consumo_combustible"
                    value={registroForm.tipo_consumo_combustible}
                    onChange={onUpdateregistroForm}
                    required
                    disabled={!selectedObra}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">Selecciona el uso</option>
                    {fuelUseOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              <Field label="Etapa" error={registroFieldErrors.unidad?.[0]}>
                <input
                  name="unidad"
                  value={registroForm.unidad}
                  onChange={onUpdateregistroForm}
                  required
                  disabled={!selectedObra}
                  placeholder={fieldCopy.unitHelp.split(" Â· ")[0]}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                  list="construction-unit-suggestions"
                />
                <span className="block text-xs text-slate-400">{fieldCopy.unitHelp}</span>
                <datalist id="construction-unit-suggestions">
                  {fieldCopy.unitHelp.split(" Â· ").map((unit) => (
                    <option key={unit} value={unit} />
                  ))}
                </datalist>
              </Field>
              <Field label={fieldCopy.quantityLabel} error={registroFieldErrors.cantidad?.[0]}>
                <input
                  type="number"
                  min="0"
                  step="0.001"
                  name="cantidad"
                  value={registroForm.cantidad}
                  onChange={onUpdateregistroForm}
                  required
                  disabled={!selectedObra}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              <Field
                label="Factor de emision"
                error={registroFieldErrors.factor_emision?.[0]}
              >
                <input
                  type="number"
                  min="0"
                  step="0.000001"
                  name="factor_emision"
                  value={registroForm.factor_emision}
                  onChange={onUpdateregistroForm}
                  required
                  disabled={!selectedObra}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              <Field label="Emisiones estimadas">
                <input
                  value={
                    estimatedEmissions > 0
                      ? `${formatNumber(estimatedEmissions, 3)} kg CO2e`
                      : "Completa cantidad y factor"
                  }
                  readOnly
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-300 outline-none"
                />
              </Field>
              <Field label="Evidencia asociada">
                <select
                  value={evidenceReference}
                  onChange={(event) => setEvidenceReference(event.target.value)}
                  disabled={!selectedObra || (selectedObra.evidencias?.length || 0) === 0}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">
                    {(selectedObra.evidencias?.length || 0) > 0
                      ? "Sin evidencia asociada"
                      : "No hay evidencias cargadas"}
                  </option>
                  {selectedObra.evidencias?.map((evidencia) => (
                    <option key={evidencia.id} value={evidencia.id}>
                      {evidencia.tipo_evidencia_label} Â· {evidencia.fecha}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="sm:col-span-2">
                <Field label="Observaciones">
                  <textarea
                    value={observations}
                    onChange={(event) => setObservations(event.target.value)}
                    rows={3}
                    placeholder="Proveedor, evidencia respaldo, destino, tratamiento u otro dato de obra."
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60"
                  />
                </Field>
              </div>
            </div>

            {shouldShowRouteMap && (
              <div className="mt-5">
                <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3">
                  <p className="text-sm font-bold text-cyan-100">
                    Trazabilidad de transporte
                  </p>
                  <p className="mt-1 text-sm leading-6 text-cyan-200">
                    Busca o marca origen y destino. La distancia calculada se usara como cantidad en kilometros.
                  </p>
                </div>
                <RouteMapPicker
                  destinationCoords={routeDestination.coords}
                  destinationValue={routeDestination.address}
                  onDestinationChange={handleRouteDestinationChange}
                  onDistanceCalculated={handleRouteDistanceCalculated}
                  onOriginChange={handleRouteOriginChange}
                  originCoords={routeOrigin.coords}
                  originValue={routeOrigin.address}
                  routeGeometry={routeResult?.route_geometry || []}
                />
              </div>
            )}

            {registroError && (
              <p className="mt-4 text-sm text-red-300">{registroError}</p>
            )}

            <button
              type="submit"
              disabled={!selectedObra || savingRegistro}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingRegistro ? (
                <Loader2 className="animate-spin" size={18} />
              ) : (
                <Plus size={18} />
              )}
              Agregar registro
            </button>
          </form>
        </div>
      )}
    </section>
  );
}

export default RegistrosEmisionTab;
