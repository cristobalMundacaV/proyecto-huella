import { useEffect, useMemo, useState } from "react";
import { Calculator, FilePlus2, Inbox, Loader2, Plus, X } from "lucide-react";

import FactorCategoryBadge from "@/features/factores/components/FactorCategoryBadge";
import {
  isDieselEmission,
  isTransportEmission,
  normalizeEmissionText,
} from "@/shared/utils/emissionSemantics";
import { formatNumber } from "@/shared/utils/formatters";
import Pagination from "@/shared/components/Pagination";
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
  { value: "preparacion", label: "Preparación / movimiento" },
  { value: "despacho", label: "Despacho" },
  { value: "transporte", label: "Transporte" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "vehiculos", label: "Vehículos" },
];

const registrosPageSize = 5;

function isFuelEmission({ fuente_emision, fuente_emisionKey, categoria, unidad }) {
  const normalizedCategory = normalizeEmissionText(categoria);
  const normalizedText = normalizeEmissionText(
    [fuente_emision, fuente_emisionKey, unidad].filter(Boolean).join(" ")
  );

  return (
    normalizedCategory === "combustible" ||
    isDieselEmission({ fuente_emision, fuente_emision_key: fuente_emisionKey, categoria, unidad }) ||
    ["combustible", "gas natural", "glp", "gas licuado", "biodiesel"].some((token) =>
      normalizedText.includes(token)
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
  const [currentPage, setCurrentPage] = useState(1);
  const [routeDestination, setRouteDestination] = useState({ address: "", coords: null });
  const [routeOrigin, setRouteOrigin] = useState({ address: "", coords: null });
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

      if (source && unit) categoriesBySource.set(`${source}|${unit}`, category);
      if (sourceKey && unit) categoriesBySource.set(`${sourceKey}|${unit}`, category);
    });

    return categoriesBySource;
  }, [factoresEmision]);

  const selectedFactor = useMemo(
    () => factoresEmision.find((factor) => String(factor.id) === String(registroForm.factor_emision_id)) || null,
    [registroForm.factor_emision_id, factoresEmision]
  );

  const selectedFactorCategory = selectedFactor?.categoria || formCategory || "Otros";
  const visibleCategory = getConstructionCategoryLabel(
    selectedFactorCategory,
    registroForm.fuente_emision || selectedFactor?.fuente_emision
  );
  const fieldCopy = getCategoryFieldCopy(visibleCategory);
  const estimatedEmissions = Number(registroForm.cantidad || 0) * Number(registroForm.factor_emision || 0);
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
    }) ||
    normalizeEmissionText(registroForm.unidad) === "km";

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCategory, selectedObra?.codigo_obra]);

  useEffect(() => {
    if (shouldShowFuelUseSelect || !registroForm.tipo_consumo_combustible) return;

    onUpdateregistroForm({
      target: { name: "tipo_consumo_combustible", value: "" },
    });
  }, [registroForm.tipo_consumo_combustible, onUpdateregistroForm, shouldShowFuelUseSelect]);

  useEffect(() => {
    if (!isModalOpen || !shouldShowRouteMap) return;

    setRouteOrigin((currentOrigin) =>
      currentOrigin.address
        ? currentOrigin
        : { address: selectedObra?.origen || selectedObra?.etapa_nombre || "", coords: null }
    );
    setRouteDestination((currentDestination) =>
      currentDestination.address
        ? currentDestination
        : { address: selectedObra?.destino || "", coords: null }
    );
  }, [isModalOpen, selectedObra, shouldShowRouteMap]);

  useEffect(() => {
    if (!shouldShowRouteMap) return;

    onUpdateregistroForm({ target: { name: "origen_transporte", value: routeOrigin.address } });
    onUpdateregistroForm({ target: { name: "origen_coords", value: routeOrigin.coords } });
  }, [routeOrigin.address, routeOrigin.coords, shouldShowRouteMap]);

  useEffect(() => {
    if (!shouldShowRouteMap) return;

    onUpdateregistroForm({ target: { name: "destino_transporte", value: routeDestination.address } });
    onUpdateregistroForm({ target: { name: "destino_coords", value: routeDestination.coords } });
  }, [routeDestination.address, routeDestination.coords, shouldShowRouteMap]);

  const closeModal = () => {
    setIsModalOpen(false);
    setRouteOrigin({ address: "", coords: null });
    setRouteDestination({ address: "", coords: null });
    setRouteResult(null);
  };

  const handleRouteDistanceCalculated = (km, result) => {
    setRouteResult(result || null);
    if (km == null) return;

    onUpdateregistroForm({ target: { name: "cantidad", value: String(km) } });
    onUpdateregistroForm({ target: { name: "distancia_km", value: String(km) } });
    onUpdateregistroForm({ target: { name: "ruta_geometry", value: result?.route_geometry || [] } });
  };

  const handleRouteOriginChange = ({ address, coords }) => {
    setRouteOrigin({ address, coords });
    setRouteResult(null);
    onUpdateregistroForm({ target: { name: "origen_transporte", value: address } });
    onUpdateregistroForm({ target: { name: "origen_coords", value: coords } });
  };

  const handleRouteDestinationChange = ({ address, coords }) => {
    setRouteDestination({ address, coords });
    setRouteResult(null);
    onUpdateregistroForm({ target: { name: "destino_transporte", value: address } });
    onUpdateregistroForm({ target: { name: "destino_coords", value: coords } });
  };

  const resolveRegistroCategory = (registro) => {
    if (registro.categoria) return registro.categoria;

    const source = normalizeEmissionText(registro.fuente_emision);
    const sourceKey = normalizeEmissionText(registro.fuente_emision_key);
    const unit = normalizeEmissionText(registro.unidad);

    return (
      factorCategoriesBySource.get(`${source}|${unit}`) ||
      factorCategoriesBySource.get(`${sourceKey}|${unit}`) ||
      "Otros"
    );
  };

  const filteredRegistros = useMemo(() => {
    const records = selectedObra?.registros_emision || [];

    if (!selectedCategory) return records;

    return records.filter((registro) => {
      const category = getConstructionCategoryLabel(
        resolveRegistroCategory(registro),
        registro.fuente_emision
      );
      return category === selectedCategory;
    });
  }, [factorCategoriesBySource, selectedCategory, selectedObra?.registros_emision]);

  const totalPages = Math.max(1, Math.ceil(filteredRegistros.length / registrosPageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const paginatedRegistros = filteredRegistros.slice(
    (safeCurrentPage - 1) * registrosPageSize,
    safeCurrentPage * registrosPageSize
  );

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
            Registros de emisión
          </p>
          <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">Actividad ambiental de la obra</h2>
          <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
            {selectedObra?.codigo_obra} · {formatNumber(filteredRegistros.length, 0)} registros encontrados
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
            {formatNumber(Number(selectedObra?.emisiones_kg_co2e || 0))} kg CO2e
          </div>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="premium-button-primary flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold"
          >
            <Plus size={18} />
            Nuevo registro
          </button>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap gap-2">
        <CategoryFilterButton active={selectedCategory === ""} onClick={() => setSelectedCategory("")}>Todas</CategoryFilterButton>
        {constructionCategories.map((category) => (
          <CategoryFilterButton
            key={category}
            active={selectedCategory === category}
            onClick={() => setSelectedCategory(category)}
          >
            {category}
          </CategoryFilterButton>
        ))}
      </div>

      <div className="premium-table-wrapper overflow-x-auto">
        <table className="premium-table min-w-[980px] w-full table-fixed text-sm">
          <thead className="border-b border-[var(--border)] text-[var(--text-muted)]">
            <tr>
              <th className="w-[24%] px-4 py-3 text-center">Fuente de emisión</th>
              <th className="w-[14%] px-4 py-3 text-center">Categoría</th>
              <th className="w-[14%] px-4 py-3 text-center">Tipo de consumo</th>
              <th className="w-[12%] px-4 py-3 text-center">Cantidad</th>
              <th className="w-[14%] px-4 py-3 text-center">Unidad</th>
              <th className="w-[12%] px-4 py-3 text-center">Factor</th>
              <th className="w-[16%] px-4 py-3 text-center">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {filteredRegistros.length === 0 && (
              <tr>
                <td colSpan="7" className="px-4 py-10 text-center">
                  <EmptyTableState
                    action="Crear primer registro"
                    description="Agrega consumos de materiales, transporte, maquinaria, energía, agua o residuos para comenzar a medir la huella real del proyecto."
                    icon={<Inbox size={22} />}
                    onAction={() => setIsModalOpen(true)}
                    title="Aún no hay registros de emisión"
                  />
                </td>
              </tr>
            )}

            {paginatedRegistros.map((registro) => (
              <tr key={registro.id} className="border-b border-[#E2E8F0] transition hover:bg-[var(--success-bg)]/45">
                <td className="px-4 py-4 text-center align-middle font-semibold text-[var(--text-main)]">
                  {registro.fuente_emision || "Sin fuente"}
                </td>
                <td className="px-4 py-4 text-center align-middle">
                  <FactorCategoryBadge
                    category={getConstructionCategoryLabel(
                      resolveRegistroCategory(registro),
                      registro.fuente_emision
                    )}
                  />
                </td>
                <td className="px-4 py-4 text-center align-middle text-[var(--text-muted)]">
                  {registro.tipo_consumo_combustible
                    ? fuelUseOptions.find((option) => option.value === registro.tipo_consumo_combustible)?.label ||
                      registro.tipo_consumo_combustible
                    : "-"}
                </td>
                <td className="px-4 py-4 text-center align-middle font-semibold text-[var(--text-main)]">
                  {formatNumber(Number(registro.cantidad || 0))}
                </td>
                <td className="px-4 py-4 text-center align-middle text-[var(--text-muted)]">
                  {registro.unidad || "-"}
                </td>
                <td className="px-4 py-4 text-center align-middle text-[var(--text-muted)]">
                  {formatNumber(Number(registro.factor_emision || 0), 4)}
                </td>
                <td className="px-4 py-4 text-center align-middle font-black text-[#075985]">
                  {formatNumber(Number(registro.emisiones_kg_co2e || 0))} kg CO2e
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredRegistros.length > registrosPageSize && (
        <Pagination
          currentPage={safeCurrentPage}
          itemLabel="registros"
          onPageChange={setCurrentPage}
          pageSize={registrosPageSize}
          totalItems={filteredRegistros.length}
        />
      )}

      {isModalOpen && (
        <div className="premium-modal-overlay fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4">
          <form
            onSubmit={onRegistroSubmit}
            className={`premium-modal-shell my-8 w-full p-4 sm:p-6 ${shouldShowRouteMap ? "max-w-5xl" : "max-w-2xl"}`}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]">
                  <Calculator size={18} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-[var(--text-main)]">Agregar registro de emisión</h2>
                  <p className="text-sm text-[var(--text-muted)]">{selectedObra?.codigo_obra}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeModal}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-main)] transition hover:bg-slate-100"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mb-5 rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3">
              <p className="text-sm font-bold text-[#075985]">{visibleCategory}</p>
              <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">{fieldCopy.note}</p>
              {estimatedEmissions > 0 && (
                <p className="mt-2 text-sm font-bold text-[#075985]">
                  Emisión estimada: {formatNumber(estimatedEmissions, 3)} kg CO2e
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Obra">
                <input value={selectedObra?.codigo_obra || ""} readOnly className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none" />
              </Field>
              <Field label="Etapa">
                <input value={selectedObra?.etapa_nombre || "Sin etapa asignada"} readOnly className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none" />
              </Field>
              <Field label="Categoría de emisión">
                <select value={formCategory} onChange={(event) => setFormCategory(event.target.value)} disabled={!selectedObra} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60">
                  {constructionCategories.map((category) => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                </select>
              </Field>
              <Field label="Fecha">
                <input type="date" name="fecha" value={registroForm.fecha || ""} onChange={onUpdateregistroForm} disabled={!selectedObra} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60" />
              </Field>
              <Field label="Buscar fuente">
                <input value={factorSearch} onChange={(event) => setFactorSearch(event.target.value)} disabled={!selectedObra} placeholder={fieldCopy.sourcePlaceholder} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60" list="construction-factor-suggestions" />
                <datalist id="construction-factor-suggestions">
                  {constructionFactorSuggestions.map((suggestion) => (
                    <option key={suggestion} value={suggestion} />
                  ))}
                </datalist>
              </Field>
              <div className="sm:col-span-2">
                <Field label="Catálogo de factores sugeridos" error={registroFieldErrors.factor_emision?.[0]}>
                  <select name="factor_emision_id" value={registroForm.factor_emision_id} onChange={onselectRegistroFactor} disabled={!selectedObra || visibleFactores.length === 0} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60">
                    <option value="">{factoresEmision.length ? "Selecciona una fuente" : "No hay factores cargados"}</option>
                    {visibleFactores.map((factor) => (
                      <option key={factor.id} value={factor.id}>
                        {factor.fuente_emision || factor.fuente_emision_key} · {factor.unidad} · {factor.factor_emision}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              {shouldShowFuelUseSelect && (
                <Field label="Tipo de consumo">
                  <select name="tipo_consumo_combustible" value={registroForm.tipo_consumo_combustible || ""} onChange={onUpdateregistroForm} disabled={!selectedObra} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60">
                    <option value="">Selecciona tipo de consumo</option>
                    {fuelUseOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
              )}
              <Field label={fieldCopy.quantityLabel} error={registroFieldErrors.cantidad?.[0]}>
                <input type="number" min="0" step="0.001" name="cantidad" value={registroForm.cantidad} onChange={onUpdateregistroForm} disabled={!selectedObra || shouldShowRouteMap} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60" />
              </Field>
              <Field label="Unidad" error={registroFieldErrors.unidad?.[0]}>
                <input name="unidad" value={registroForm.unidad} onChange={onUpdateregistroForm} disabled={!selectedObra} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60" />
              </Field>
              <Field label="Factor de emisión" error={registroFieldErrors.factor_emision?.[0]}>
                <input type="number" min="0" step="0.000001" name="factor_emision" value={registroForm.factor_emision} onChange={onUpdateregistroForm} disabled={!selectedObra} className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60 disabled:cursor-not-allowed disabled:opacity-60" />
              </Field>
            </div>

            {shouldShowRouteMap && (
              <div className="mt-5 rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
                <RouteMapPicker
                  destinationCoords={routeDestination.coords}
                  destinationValue={routeDestination.address}
                  onDestinationChange={handleRouteDestinationChange}
                  onDistanceCalculated={handleRouteDistanceCalculated}
                  onOriginChange={handleRouteOriginChange}
                  originCoords={routeOrigin.coords}
                  originValue={routeOrigin.address}
                  routeGeometry={routeResult?.route_geometry || registroForm.ruta_geometry || []}
                />
              </div>
            )}

            {registroError && <p className="mt-4 text-sm font-semibold text-red-600">{registroError}</p>}

            <button type="submit" disabled={savingRegistro} className="premium-button-primary mt-6 flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60">
              {savingRegistro ? <Loader2 className="animate-spin" size={18} /> : <Calculator size={18} />}
              Guardar registro de emisión
            </button>
          </form>
        </div>
      )}
    </section>
  );
}

function CategoryFilterButton({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-xs font-black transition ${
        active
          ? "border-[var(--primary)]/35 bg-[var(--success-bg)] text-[var(--primary-dark)] shadow-[0_8px_18px_rgba(14,124,102,0.10)]"
          : "border-[var(--border)] bg-white text-[var(--text-muted)] hover:border-[var(--primary)]/35 hover:bg-[var(--success-bg)] hover:text-[var(--primary-dark)]"
      }`}
    >
      {children}
    </button>
  );
}

function EmptyTableState({ action, description, icon, onAction, title }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] px-6 py-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]">
        {icon || <FilePlus2 size={22} />}
      </div>
      <h3 className="mt-4 text-lg font-black text-[var(--text-main)]">{title}</h3>
      <p className="mt-2 text-sm font-medium leading-6 text-[var(--text-muted)]">{description}</p>
      {onAction && (
        <button type="button" onClick={onAction} className="premium-button-primary mt-5 inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold">
          <Plus size={18} />
          {action}
        </button>
      )}
    </div>
  );
}

export default RegistrosEmisionTab;
