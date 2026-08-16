import { Fragment } from "react";
import { ChevronRight } from "lucide-react";
import { Link, useLocation, useParams } from "react-router-dom";

const labels = {
  inicio: "Inicio", obras: "Obras", resumen: "Resumen", operacion: "Operación",
  indicadores: "Indicadores", problemas: "Problemas", evidencias: "Evidencias",
  timeline: "Timeline", informes: "Informes", datos: "Datos", importaciones: "Importaciones",
  inteligencia: "Inteligencia", acciones: "Acciones", copiloto: "Copiloto",
  gobernanza: "Gobernanza", revision: "Revisión profesional", expedientes: "Expedientes", calidad: "Calidad", auditoria: "Auditoría", conocimiento: "Conocimiento", factores: "Factores", administracion: "Administración",
  organizacion: "Organización", usuarios: "Usuarios", configuracion: "Configuración",
  diagnostico: "Diagnóstico", estructura: "Estructura", activos: "Activos", sensores: "Sensores",
};

export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const { obraId } = useParams();
  const segments = pathname.split("/").filter(Boolean);
  return (
    <nav aria-label="Breadcrumb" className="mb-5 flex flex-wrap items-center gap-2 text-xs font-semibold text-[var(--text-muted)]">
      {segments.map((segment, index) => {
        const current = `/${segments.slice(0, index + 1).join("/")}`;
        const label = segment === obraId ? `Obra ${decodeURIComponent(segment)}` : labels[segment] || segment;
        const last = index === segments.length - 1;
        return <Fragment key={current}>
          {index > 0 && <ChevronRight size={13} aria-hidden="true" />}
          {last ? <span aria-current="page" className="text-[var(--brand-primary)]">{label}</span> : <Link to={current} className="hover:text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]">{label}</Link>}
        </Fragment>;
      })}
    </nav>
  );
}
