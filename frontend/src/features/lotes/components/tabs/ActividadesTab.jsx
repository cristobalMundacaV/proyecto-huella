import { useEffect, useMemo, useState } from "react";
import { Calculator, Loader2, Plus, X } from "lucide-react";

import FactorCategoryBadge from "@/features/factores/components/FactorCategoryBadge";
import {
  isDieselActivity,
  isTransportActivity,
  normalizeActivityText,
} from "@/shared/utils/activitySemantics";
import { formatNumber } from "@/shared/utils/formatters";
import {
  categoryMatchesConstructionFilter,
  constructionCategories,
  constructionFactorSuggestions,
  getCategoryFieldCopy,
  getConstructionCategoryLabel,
} from "@/features/lotes/utils/constructionEmissionCategories";
import { Field } from "../common";
import RouteMapPicker from "../RouteMapPicker";

const fuelUseOptions = [
  { value: "cosecha", label: "Preparación / movimiento" },
  { value: "despacho", label: "Despacho" },
  { value: "transporte", label: "Transporte" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "vehiculos", label: "Vehiculos" },
];

function isFuelActivity({ actividad, actividadKey, categoria, unidad }) {
  const normalizedCategory = normalizeActivityText(categoria);
  const normalizedText = normalizeActivityText(
    [actividad, actividadKey, unidad].filter(Boolean).join(" ")
  );

  return (
    normalizedCategory === "combustible" ||
    isDieselActivity({
      actividad,
      actividad_key: actividadKey,
      categoria,
      unidad,
    }) ||
    ["combustible", "gas natural", "glp", "gas licuado", "biodiesel"].some(
      (token) => normalizedText.includes(token)
    )
  );
}

function ActividadesTab({
  activityError,
  activityFieldErrors,
  activityForm,
  factoresEmision,
  onActivitySubmit,
  onSelectActivityFactor,
  onUpdateActivityForm,
  savingActivity,
  selectedLote,
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
    const query = normalizeActivityText(factorSearch);
    return factoresEmision.filter((factor) => {
      const matchesCategory = categoryMatchesConstructionFilter(factor, formCategory);
      const searchable = [
        factor.actividad,
        factor.actividad_key,
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

  const factorCategoriesByActivity = useMemo(() => {
    const categoriesByActivity = new Map();

    factoresEmision.forEach((factor) => {
      const activity = normalizeActivityText(factor.actividad);
      const activityKey = normalizeActivityText(factor.actividad_key);
      const unit = normalizeActivityText(factor.unidad);
      const category = factor.categoria || "Otros";

      if (activity && unit) {
        categoriesByActivity.set(`${activity}|${unit}`, category);
      }

      if (activityKey && unit) {
        categoriesByActivity.set(`${activityKey}|${unit}`, category);
      }
    });

    return categoriesByActivity;
  }, [factoresEmision]);

  const selectedFactor = useMemo(
    () =>
      factoresEmision.find(
        (factor) => String(factor.id) === String(activityForm.factor_emision_id)
      ) || null,
    [activityForm.factor_emision_id, factoresEmision]
  );

  const selectedFactorCategory =
    selectedFactor?.categoria || formCategory || "Otros";
  const visibleCategory = getConstructionCategoryLabel(
    selectedFactorCategory,
    activityForm.actividad || selectedFactor?.actividad
  );
  const fieldCopy = getCategoryFieldCopy(visibleCategory);
  const estimatedEmissions =
    Number(activityForm.cantidad || 0) * Number(activityForm.factor_emision || 0);
  const shouldShowFuelUseSelect = isFuelActivity({
    actividad: activityForm.actividad || selectedFactor?.actividad,
    actividadKey: selectedFactor?.actividad_key,
    categoria: selectedFactorCategory,
    unidad: activityForm.unidad || selectedFactor?.unidad,
  });
  const shouldShowRouteMap =
    visibleCategory === "Transporte" ||
    isTransportActivity({
      actividad: activityForm.actividad || selectedFactor?.actividad,
      actividad_key: selectedFactor?.actividad_key,
      categoria: selectedFactorCategory,
      unidad: activityForm.unidad || selectedFactor?.unidad,
    }) || normalizeActivityText(activityForm.unidad) === "km";

  useEffect(() => {
    if (shouldShowFuelUseSelect || !activityForm.tipo_consumo_combustible) {
      return;
    }

    onUpdateActivityForm({
      target: {
        name: "tipo_consumo_combustible",
        value: "",
      },
    });
  }, [
    activityForm.tipo_consumo_combustible,
    onUpdateActivityForm,
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
        address: selectedLote?.origen || selectedLote?.unidad_operativa_nombre || "",
        coords: null,
      };
    });

    setRouteDestination((currentDestination) => {
      if (currentDestination.address) {
        return currentDestination;
      }

      return {
        address: selectedLote?.destino || "",
        coords: null,
      };
    });
  }, [isModalOpen, selectedLote, shouldShowRouteMap]);

  useEffect(() => {
    if (!shouldShowRouteMap) {
      return;
    }

    onUpdateActivityForm({
      target: {
        name: "origen_transporte",
        value: routeOrigin.address,
      },
    });
    onUpdateActivityForm({
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

    onUpdateActivityForm({
      target: {
        name: "destino_transporte",
        value: routeDestination.address,
      },
    });
    onUpdateActivityForm({
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

    onUpdateActivityForm({
      target: {
        name: "cantidad",
        value: String(km),
      },
    });
    onUpdateActivityForm({
      target: {
        name: "distancia_km",
        value: String(km),
      },
    });
    onUpdateActivityForm({
      target: {
        name: "ruta_geometry",
        value: result?.route_geometry || [],
      },
    });
  };

  const handleRouteOriginChange = ({ address, coords }) => {
    setRouteOrigin({ address, coords });
    setRouteResult(null);
    onUpdateActivityForm({
      target: {
        name: "origen_transporte",
        value: address,
      },
    });
    onUpdateActivityForm({
      target: {
        name: "origen_coords",
        value: coords,
      },
    });
  };

  const handleRouteDestinationChange = ({ address, coords }) => {
    setRouteDestination({ address, coords });
    setRouteResult(null);
    onUpdateActivityForm({
      target: {
        name: "destino_transporte",
        value: address,
      },
    });
    onUpdateActivityForm({
      target: {
        name: "destino_coords",
        value: coords,
      },
    });
  };

  const resolveActivityCategory = (actividad) => {
    if (actividad.categoria) {
      return actividad.categoria;
    }

    const activity = normalizeActivityText(actividad.actividad);
    const activityKey = normalizeActivityText(actividad.actividad_key);
    const unit = normalizeActivityText(actividad.unidad);
    const activityCategory = factorCategoriesByActivity.get(`${activity}|${unit}`);
    const activityKeyCategory = factorCategoriesByActivity.get(`${activityKey}|${unit}`);

    return activityCategory || activityKeyCategory || "Otros";
  };

  const filteredActivities = useMemo(() => {
    if (!selectedCategory) {
      return selectedLote?.actividades || [];
    }

    return (selectedLote?.actividades || []).filter((actividad) => {
      const category = getConstructionCategoryLabel(
        resolveActivityCategory(actividad),
        actividad.actividad
      );
      return category === selectedCategory;
    });
  }, [factorCategoriesByActivity, selectedCategory, selectedLote?.actividades]);

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Registros de emisión de la obra</h2>
          <p className="mt-1 text-sm text-slate-400">{selectedLote?.id_lote}</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200">
            {formatNumber(Number(selectedLote?.emisiones_kg_co2e || 0))} kg CO2e
          </div>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20"
          >
            <Plus size={18} />
            Nuevo registro de emisión
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
              <th className="w-[40%] py-3 pr-6 text-left">Fuente de emisión</th>
              <th className="w-[14%] px-4 py-3 text-left">Categoría</th>
              <th className="w-[14%] px-4 py-3 text-left">Tipo de consumo</th>
              <th className="w-[14%] py-3 px-4 text-right">Cantidad</th>
              <th className="w-[14%] py-3 px-4 text-left">Unidad</th>
              <th className="w-[14%] py-3 px-4 text-right">Factor de emisión</th>
              <th className="w-[18%] py-3 pl-4 pr-2 text-right">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {filteredActivities.length === 0 && (
              <tr>
                <td colSpan="7" className="py-8 text-center text-slate-400">
                  <p>Aún no hay registros de emisión en esta obra.</p>
                  <p className="mt-1 text-sm">
                    Agrega emisiones por materiales, transporte, maquinaria, energía, agua o residuos para comenzar a medir la huella del proyecto.
                  </p>
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(true)}
                    className="mt-4 inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20"
                  >
                    <Plus size={18} />
                    Nuevo registro de emisión
                  </button>
                </td>
              </tr>
            )}

            {filteredActivities.map((actividad) => (
              <tr key={actividad.id} className="border-b border-slate-800/60">
                <td className="py-3 pr-6 font-semibold text-slate-100 whitespace-nowrap overflow-hidden text-ellipsis">
                  {actividad.actividad}
                </td>
                <td className="px-4 py-4 text-left whitespace-nowrap">
                  <FactorCategoryBadge
                    category={getConstructionCategoryLabel(
                      resolveActivityCategory(actividad),
                      actividad.actividad
                    )}
                  />
                </td>
                <td className="px-4 py-3 text-slate-300 whitespace-nowrap">
                  {actividad.tipo_consumo_combustible
                    ? fuelUseOptions.find(
                        (option) =>
                          option.value === actividad.tipo_consumo_combustible
                      )?.label || actividad.tipo_consumo_combustible
                    : "-"}
                </td>
                <td className="py-3 px-4 text-right whitespace-nowrap">
                  {formatNumber(Number(actividad.cantidad))}
                </td>
                <td className="py-3 px-4 whitespace-nowrap">{actividad.unidad}</td>
                <td className="py-3 px-4 text-right whitespace-nowrap">
                  {formatNumber(Number(actividad.factor_emision), 6)}
                </td>
                <td className="py-3 pl-4 pr-2 text-right font-semibold text-cyan-200 whitespace-nowrap">
                  {formatNumber(Number(actividad.emisiones_kg_co2e))} kg CO2e
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
          <form
            onSubmit={onActivitySubmit}
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
                  <h2 className="text-xl font-semibold">Agregar registro de emisión</h2>
                  <p className="text-sm text-slate-400">{selectedLote?.id_lote}</p>
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
                  Emisión estimada: {formatNumber(estimatedEmissions, 3)} kg CO2e
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Obra">
                <input
                  value={selectedLote?.id_lote || ""}
                  readOnly
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-300 outline-none"
                />
              </Field>
              <Field label="Etapa / frente">
                <input
                  value={selectedLote?.unidad_operativa_nombre || "Sin etapa asignada"}
                  readOnly
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-300 outline-none"
                />
              </Field>
              <Field label="Categoría de emisión">
                <select
                  value={formCategory}
                  onChange={(event) => setFormCategory(event.target.value)}
                  disabled={!selectedLote}
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
                  value={activityForm.fecha || ""}
                  onChange={onUpdateActivityForm}
                  disabled={!selectedLote}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              <Field label="Buscar fuente">
                <input
                  value={factorSearch}
                  onChange={(event) => setFactorSearch(event.target.value)}
                  disabled={!selectedLote}
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
                  label="Catálogo de factores sugeridos"
                  error={activityFieldErrors.factor_emision?.[0]}
                >
                  <select
                    name="factor_emision_id"
                    value={activityForm.factor_emision_id}
                    onChange={onSelectActivityFactor}
                    disabled={!selectedLote || visibleFactores.length === 0}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">
                      {factoresEmision.length
                        ? "Selecciona una fuente"
                        : "No hay factores cargados"}
                    </option>
                    {visibleFactores.map((factor) => (
                      <option key={factor.id} value={factor.id}>
                        {factor.actividad} · {factor.unidad} · {formatNumber(Number(factor.factor_emision), 6)} kgCO2e/{factor.unidad}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label={fieldCopy.sourceLabel} error={activityFieldErrors.actividad?.[0]}>
                <input
                  name="actividad"
                  value={activityForm.actividad}
                  onChange={onUpdateActivityForm}
                  required
                  disabled={!selectedLote}
                  placeholder={fieldCopy.sourcePlaceholder}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              {shouldShowFuelUseSelect && (
                <Field
                  label="Tipo de consumo"
                  error={activityFieldErrors.tipo_consumo_combustible?.[0]}
                >
                  <select
                    name="tipo_consumo_combustible"
                    value={activityForm.tipo_consumo_combustible}
                    onChange={onUpdateActivityForm}
                    required
                    disabled={!selectedLote}
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
              <Field label="Unidad" error={activityFieldErrors.unidad?.[0]}>
                <input
                  name="unidad"
                  value={activityForm.unidad}
                  onChange={onUpdateActivityForm}
                  required
                  disabled={!selectedLote}
                  placeholder={fieldCopy.unitHelp.split(" · ")[0]}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                  list="construction-unit-suggestions"
                />
                <span className="block text-xs text-slate-400">{fieldCopy.unitHelp}</span>
                <datalist id="construction-unit-suggestions">
                  {fieldCopy.unitHelp.split(" · ").map((unit) => (
                    <option key={unit} value={unit} />
                  ))}
                </datalist>
              </Field>
              <Field label={fieldCopy.quantityLabel} error={activityFieldErrors.cantidad?.[0]}>
                <input
                  type="number"
                  min="0"
                  step="0.001"
                  name="cantidad"
                  value={activityForm.cantidad}
                  onChange={onUpdateActivityForm}
                  required
                  disabled={!selectedLote}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </Field>
              <Field
                label="Factor de emisión"
                error={activityFieldErrors.factor_emision?.[0]}
              >
                <input
                  type="number"
                  min="0"
                  step="0.000001"
                  name="factor_emision"
                  value={activityForm.factor_emision}
                  onChange={onUpdateActivityForm}
                  required
                  disabled={!selectedLote}
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
                  disabled={!selectedLote || (selectedLote.documentos?.length || 0) === 0}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">
                    {(selectedLote.documentos?.length || 0) > 0
                      ? "Sin evidencia asociada"
                      : "No hay evidencias cargadas"}
                  </option>
                  {selectedLote.documentos?.map((documento) => (
                    <option key={documento.id} value={documento.id}>
                      {documento.tipo_documento_label} · {documento.fecha}
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
                    placeholder="Proveedor, documento respaldo, destino, tratamiento u otro dato de obra."
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

            {activityError && (
              <p className="mt-4 text-sm text-red-300">{activityError}</p>
            )}

            <button
              type="submit"
              disabled={!selectedLote || savingActivity}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingActivity ? (
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

export default ActividadesTab;
