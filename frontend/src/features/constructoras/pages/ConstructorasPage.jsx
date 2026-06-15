import { useEffect, useMemo, useState } from "react";
import { Building2, Pencil, Plus, Trash2 } from "lucide-react";

import ConstructoraForm from "../components/ConstructoraForm";
import Pagination from "@/shared/components/Pagination";
import Toast from "@/shared/components/Toast";
import { getPresetLabel } from "@/presets/registry";
import {
  createEmpresa,
  deleteEmpresa,
  getEmpresas,
  updateEmpresa,
} from "@/shared/services/api";
import { useToast } from "@/shared/hooks/useToast";
import {
  isValidChileanRut,
  isValidEmail,
  isValidPhone,
} from "@/shared/utils/validators";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";

const PAGE_SIZE = 8;

const emptyForm = {
  preset: "construccion",
  rut: "",
  nombre: "",
  region: "",
  comuna: "",
  rubro: "",
  direccion: "",
  email: "",
  telefono: "",
  observaciones: "",
};

const fieldLabels = {
  rut: "RUT",
  nombre: "nombre",
  region: "región",
  comuna: "comuna",
  rubro: "rubro",
  email: "email",
};

function normalizeEmpresaId(empresa) {
  return empresa?.constructora_id || empresa?.id || "";
}

function normalizeFormFromEmpresa(empresa) {
  return {
    preset: empresa?.preset || "construccion",
    rut: empresa?.rut || "",
    nombre: empresa?.nombre || "",
    region: empresa?.region || "",
    comuna: empresa?.comuna || "",
    rubro: empresa?.rubro || "",
    direccion: empresa?.direccion || "",
    email: empresa?.email || "",
    telefono: empresa?.telefono || "",
    observaciones: empresa?.observaciones || "",
  };
}

function validateForm(form) {
  const missingFields = ["rut", "nombre", "region", "comuna", "rubro", "email"].filter(
    (field) => !String(form[field] || "").trim()
  );
  const nextFieldErrors = {};

  missingFields.forEach((field) => {
    nextFieldErrors[field] = ["Campo obligatorio"];
  });

  if (form.rut && !isValidChileanRut(form.rut)) {
    nextFieldErrors.rut = ["Ingresa un RUT chileno válido."];
  }

  if (form.email && !isValidEmail(form.email)) {
    nextFieldErrors.email = ["Ingresa un email válido."];
  }

  if (form.telefono && !isValidPhone(form.telefono)) {
    nextFieldErrors.telefono = ["Ingresa un teléfono válido."];
  }

  return { missingFields, nextFieldErrors };
}

function ConstructorasView({
  onSetActiveView,
  initialOpenCreate = false,
  openCreateSignal = 0,
}) {
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [form, setForm] = useState(emptyForm);
  const [modalOpen, setModalOpen] = useState(initialOpenCreate);
  const [editingEmpresa, setEditingEmpresa] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const { clearToast, showToast, toast } = useToast();

  const {
    activeConstructora,
    activeConstructoraId,
    clearActiveConstructora,
    refreshConstructoras,
    setActiveConstructora,
  } = useConstructoraActiva();

  async function loadEmpresas() {
    try {
      setLoading(true);
      const data = await getEmpresas();
      setEmpresas(Array.isArray(data) ? data : []);
    } catch {
      showToast("No se pudieron cargar las empresas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEmpresas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (openCreateSignal > 0) {
      openCreateModal();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openCreateSignal]);

  const stats = useMemo(() => {
    const total = empresas.length;
    const active = empresas.filter((empresa) => empresa.activa !== false).length;
    const presets = new Set(empresas.map((empresa) => empresa.preset || "construccion")).size;
    const records = empresas.reduce((sum, empresa) => sum + Number(empresa.registros_count || 0), 0);

    return { total, active, presets, records };
  }, [empresas]);

  const totalPages = Math.max(1, Math.ceil(empresas.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const visibleEmpresas = empresas.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function openCreateModal() {
    setEditingEmpresa(null);
    setFieldErrors({});
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEditModal(empresa) {
    setEditingEmpresa(empresa);
    setFieldErrors({});
    setForm(normalizeFormFromEmpresa(empresa));
    setModalOpen(true);
  }

  function closeModal() {
    if (saving) return;
    setModalOpen(false);
    setEditingEmpresa(null);
    setFieldErrors({});
    setForm(emptyForm);
  }

  function updateForm(event) {
    const { name, value } = event.target;

    setForm((currentForm) => {
      if (name === "region") {
        return {
          ...currentForm,
          region: value,
          comuna: "",
        };
      }

      return { ...currentForm, [name]: value };
    });

    setFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const { missingFields, nextFieldErrors } = validateForm(form);

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);

      if (missingFields.length === 1) {
        showToast(`Falta completar ${fieldLabels[missingFields[0]]}.`);
      } else if (missingFields.length > 1) {
        showToast("Hay campos vacíos.");
      } else {
        showToast("Hay campos con formato inválido.");
      }

      return;
    }

    setSaving(true);
    setFieldErrors({});

    try {
      if (editingEmpresa) {
        const empresaId = normalizeEmpresaId(editingEmpresa);
        const updatedEmpresa = await updateEmpresa(empresaId, form);

        setEmpresas((current) =>
          current.map((empresa) =>
            String(normalizeEmpresaId(empresa)) === String(empresaId)
              ? updatedEmpresa
              : empresa
          )
        );

        if (String(activeConstructoraId) === String(empresaId)) {
          setActiveConstructora(updatedEmpresa);
        }

        showToast("Empresa actualizada correctamente.");
      } else {
        const createdEmpresa = await createEmpresa(form);
        setEmpresas((current) => [createdEmpresa, ...current]);
        setActiveConstructora(createdEmpresa);
        showToast("Empresa creada correctamente.");
      }

      await refreshConstructoras();
      closeModal();
      onSetActiveView?.("constructoras");
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setFieldErrors(responseData);
      }

      showToast("Revisa los datos de la empresa antes de guardar.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteEmpresa(empresa) {
    const empresaId = normalizeEmpresaId(empresa);
    const accepted = window.confirm(
      `¿Eliminar la empresa "${empresa.nombre}"? Esta acción eliminará sus datos relacionados.`
    );

    if (!accepted) return;

    try {
      await deleteEmpresa(empresaId);
      const nextEmpresas = empresas.filter(
        (item) => String(normalizeEmpresaId(item)) !== String(empresaId)
      );

      setEmpresas(nextEmpresas);

      if (String(activeConstructoraId) === String(empresaId)) {
        const nextActive = nextEmpresas[0] || null;

        if (nextActive) {
          setActiveConstructora(nextActive);
        } else {
          clearActiveConstructora();
        }
      }

      await refreshConstructoras();
      showToast("Empresa eliminada correctamente.");
    } catch (requestError) {
      showToast(
        requestError.response?.data?.error ||
        "No se pudo eliminar la empresa. Revisa si tiene datos relacionados."
      );
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <Toast message={toast?.message} onClose={clearToast} toastKey={toast?.id} />

      <header className="rounded-3xl border border-emerald-200/60 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-6 shadow-[var(--shadow-card)]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-3 text-emerald-700">
              <Building2 size={28} />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
                Gestión centralizada
              </p>
              <h1 className="mt-1 text-3xl font-black text-[var(--text-main)] sm:text-4xl">
                Empresas registradas
              </h1>
              <p className="mt-2 max-w-3xl text-sm font-semibold leading-7 text-[var(--text-muted)]">
                Crea, edita, elimina y cambia el preset de las empresas desde una vista dedicada.
                El sidebar queda solo para seleccionar la empresa activa.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(14,124,102,0.22)]"
          >
            <Plus size={18} />
            Nueva empresa
          </button>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Empresas" value={stats.total} />
        <SummaryCard label="Activas" value={stats.active} />
        <SummaryCard label="Presets usados" value={stats.presets} />
        <SummaryCard label="Registros" value={stats.records} />
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
        <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-black text-[var(--text-main)]">
              Listado de empresas
            </h2>
            <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
              Mostrando {visibleEmpresas.length} de {empresas.length} empresas.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-[var(--border)]">
          <table className="w-full min-w-[1100px] text-center text-sm">
            <thead className="bg-[var(--bg-surface)] text-center text-xs uppercase tracking-wide text-[var(--text-muted)]">
              <tr>
                <th className="px-4 py-3 text-center">Empresa</th>
                <th className="px-4 py-3 text-center">RUT</th>
                <th className="px-4 py-3 text-center">Preset</th>
                <th className="px-4 py-3 text-center">Rubro</th>
                <th className="px-4 py-3 text-center">Comuna</th>
                <th className="px-4 py-3 text-center">Email</th>
                <th className="px-4 py-3 text-center">Estado</th>
                <th className="px-4 py-3 text-center">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {visibleEmpresas.map((empresa) => {
                const empresaId = normalizeEmpresaId(empresa);
                const isActive = String(empresaId) === String(activeConstructoraId);

                return (
                  <tr key={empresaId} className="border-t border-[var(--border)]">
                    <td className="px-4 py-3 text-center font-black text-[var(--text-main)]">
                      {empresa.nombre}
                      {isActive && (
                        <span className="ml-2 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-black uppercase text-emerald-700">
                          Activa
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">{empresa.rut || "-"}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">
                        {getPresetLabel(empresa.preset || "construccion")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">{empresa.rubro || "-"}</td>
                    <td className="px-4 py-3 text-center">{empresa.comuna || "-"}</td>
                    <td className="px-4 py-3 text-center">{empresa.email || "-"}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`rounded-full border px-3 py-1 text-xs font-black ${empresa.activa !== false
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : "border-slate-200 bg-slate-100 text-slate-600"
                        }`}>
                        {empresa.activa !== false ? "Activa" : "Inactiva"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex justify-center gap-2">
                        <button
                          type="button"
                          onClick={() => setActiveConstructora(empresa)}
                          className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700"
                        >
                          Usar
                        </button>
                        <button
                          type="button"
                          onClick={() => openEditModal(empresa)}
                          className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black text-sky-700"
                        >
                          <Pencil size={13} />
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteEmpresa(empresa)}
                          className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-black text-rose-700"
                        >
                          <Trash2 size={13} />
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {!visibleEmpresas.length && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-sm font-semibold text-[var(--text-muted)]">
                    {loading ? "Cargando empresas..." : "No hay empresas registradas."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          currentPage={safePage}
          onPageChange={setCurrentPage}
          pageSize={PAGE_SIZE}
          totalItems={empresas.length}
          itemLabel="empresas"
        />
      </section>

      {modalOpen && (
        <ConstructoraForm
          error=""
          fieldErrors={fieldErrors}
          form={form}
          loading={saving}
          onClose={closeModal}
          onSubmit={handleSubmit}
          onUpdateForm={updateForm}
          onClearError={() => { }}
        />
      )}
    </div>
  );
}

function SummaryCard({ label, value }) {
  return (
    <article className="rounded-3xl border border-emerald-200/70 bg-[linear-gradient(180deg,#ECFDF5,#FFFFFF)] p-5 text-center shadow-[var(--shadow-card)]">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
        {label}
      </p>
      <p className="mt-3 text-3xl font-black text-[var(--text-main)]">
        {value}
      </p>
    </article>
  );
}

export default ConstructorasView;