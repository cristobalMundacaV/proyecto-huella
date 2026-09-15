import { NavLink, useLocation } from "react-router-dom";
import { FLOW_SECTIONS, flowBaseFromPathname, sectionFromPathname } from "../utils/flowWorkspaceSections.js";

export { FLOW_SECTIONS };

export function useFlowSection() {
  const { pathname } = useLocation();
  return sectionFromPathname(pathname);
}

export default function FlowWorkspaceNav({ sections = FLOW_SECTIONS }) {
  const { pathname } = useLocation();
  const section = useFlowSection();
  const base = flowBaseFromPathname(pathname, section);
  return <nav aria-label="Secciones del flujo" className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
    {sections.map((item) => <NavLink
      key={item}
      to={item === "resumen" ? base : `${base}/${item}`}
      end
      className={({ isActive }) => `rounded-xl px-4 py-2 text-sm font-bold transition ${isActive ? "bg-emerald-100 text-emerald-900" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}
    >{item.charAt(0).toUpperCase() + item.slice(1)}</NavLink>)}
  </nav>;
}
