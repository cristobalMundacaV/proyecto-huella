import { NavLink, useNavigate } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getActivePreset, getPresetLabel } from "@/presets/registry";
import { navigationForPreset } from "@/app/navigation";

export default function Sidebar({ onNavigate, systemStatus }) {
  const navigate = useNavigate();
  const { activeOrganizacion, activeOrganizacionId, clearActiveOrganizacion, organizaciones, loadingOrganizaciones, setActiveOrganizacion } = useOrganizacionActiva();
  const presetKey = activeOrganizacion?.preset || "construccion";
  const preset = getActivePreset(presetKey);
  const statusItems = [[preset.processPluralLabel, systemStatus?.etapas ?? 0], [preset.unitPluralLabel, systemStatus?.obras ?? 0], ["Registros", systemStatus?.registros_emision ?? 0], ["Evidencias", systemStatus?.evidencias ?? 0]];
  return <aside className="w-full shrink-0 border-b border-[var(--sidebar-border)] bg-[var(--sidebar)] p-4 text-[var(--text-main)] shadow-[18px_0_50px_rgba(19,34,56,0.06)] sm:p-6 lg:sticky lg:top-[72px] lg:flex lg:h-[calc(100vh-72px)] lg:w-72 lg:flex-col lg:border-b-0 lg:border-r lg:overflow-y-auto">
    <section className="mb-6 mt-2 rounded-2xl border border-[var(--sidebar-border)] bg-white/64 p-4"><p className="text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">Estado de la empresa</p><div className="mt-3 space-y-2">{statusItems.map(([label,value]) => <div key={label} className="flex justify-between text-sm"><span>{label}</span><strong>{value}</strong></div>)}</div></section>
    <nav className="space-y-5">{navigationForPreset(preset).map((group) => <section key={group.label}><p className="px-1 text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">{group.label}</p><div className="mt-2 space-y-1">{group.items.map((item) => { const Icon=item.icon; return <NavLink key={item.path} to={item.path} onClick={onNavigate} className={({isActive}) => `sidebar-nav-item flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-bold transition ${isActive ? "border-emerald-200 bg-[var(--sidebar-active)] text-[var(--primary-dark)]" : "border-transparent text-slate-600 hover:bg-white/75"}`}><Icon size={18}/>{item.label}</NavLink>; })}</div></section>)}</nav>
    <section className="mt-8 rounded-2xl border border-[var(--sidebar-border)] bg-white/62 p-4 lg:mt-auto"><p className="text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">Empresa activa</p><select value={activeOrganizacionId} onChange={(event) => { const selected=organizaciones.find((org)=>String(org.organizacion_id)===event.target.value); if(selected){setActiveOrganizacion(selected);navigate("/inicio");}else clearActiveOrganizacion(); onNavigate?.(); }} className="mt-3 w-full rounded-xl border border-[var(--border)] bg-white px-3 py-2 text-sm font-bold"><option value="">Selecciona una empresa</option>{organizaciones.map((org)=><option key={org.organizacion_id} value={org.organizacion_id}>{org.nombre}</option>)}</select>{loadingOrganizaciones&&<p className="mt-2 text-xs">Cargando...</p>}<div className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-center text-[11px] font-black uppercase text-emerald-800">Preset: {getPresetLabel(presetKey)}</div></section>
  </aside>;
}
