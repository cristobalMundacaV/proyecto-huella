import { useState } from "react";
import { Building2 } from "lucide-react";

import { Button, Input, Modal, Select, Textarea } from "@/shared/ui";

import {
    DEPARTMENT_PRESENTATION,
    DEPARTMENT_TYPE_OPTIONS,
} from "../config/departmentPresentation";

export default function CreateDepartmentModal({ loading, onClose, onCreate }) {
    const initialType = "otro";
    const formId = "create-department-form";
    const [type, setType] = useState(initialType);
    const presentation = DEPARTMENT_PRESENTATION[type] || DEPARTMENT_PRESENTATION.otro;
    const PreviewIcon = presentation.icon;

    function submit(event) {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const form = {
            nombre: String(data.get("nombre") || "").trim(),
            tipo: String(data.get("tipo") || initialType),
            descripcion: String(data.get("descripcion") || "").trim(),
        };
        if (form.nombre) onCreate(form);
    }

    return (
        <Modal
            title="Crear departamento"
            description="Define una unidad organizacional y su identidad visual dentro de Carbono Zero."
            icon={Building2}
            onClose={loading ? undefined : onClose}
            size="sm"
            footer={(
                <div className="flex justify-end gap-3">
                    <Button variant="secondary" disabled={loading} onClick={onClose}>
                        Cancelar
                    </Button>
                    <Button type="submit" form={formId} loading={loading}>
                        Crear departamento
                    </Button>
                </div>
            )}
        >
            <form id={formId} className="space-y-5" onSubmit={submit}>
                <Input
                    data-autofocus
                    name="nombre"
                    label="Nombre del departamento"
                    placeholder="Ej.: Gestión de contratos"
                    maxLength={120}
                    required
                    disabled={loading}
                />
                <Select
                    name="tipo"
                    label="Tipo, color e icono"
                    helper="Esta selección define la identidad visual del encabezado."
                    defaultValue={initialType}
                    onChange={(event) => setType(event.target.value)}
                    disabled={loading}
                >
                    {DEPARTMENT_TYPE_OPTIONS.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                    ))}
                </Select>
                <div className={`flex items-center gap-3 rounded-2xl border p-4 ${presentation.headerClass}`}>
                    <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${presentation.iconClass}`}>
                        <PreviewIcon aria-hidden="true" size={21} />
                    </span>
                    <div>
                        <p className="text-sm font-bold text-slate-950">Icono representativo</p>
                        <p className="mt-0.5 text-xs text-slate-600">Vista previa del estilo seleccionado.</p>
                    </div>
                </div>
                <Textarea
                    name="descripcion"
                    label="Descripción"
                    placeholder="Describe brevemente la función de este departamento."
                    maxLength={400}
                    disabled={loading}
                />
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    <p className="font-bold text-slate-900">Identidad visual consistente</p>
                    <p className="mt-1 leading-5">
                        Cada tipo utiliza un color suave y un icono reconocible. Podrás cambiar el tipo posteriormente mediante la configuración del área.
                    </p>
                </div>
            </form>
        </Modal>
    );
}
